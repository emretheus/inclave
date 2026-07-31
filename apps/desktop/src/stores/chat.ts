// Chat store — the streaming state machine. Subscribes to chat.* events from
// the bridge and assembles them into a transcript of messages + run cards.

import { create } from "zustand";
import { ipc, onEvent } from "@/lib/ipc";

export type RunCard = {
  code: string;
  stdout: string;
  stderr: string;
  exitCode: number;
  durationMs: number;
  timedOut: boolean;
  status: "running" | "done";
};

export type TranscriptItem =
  | { kind: "message"; id: string; role: "user" | "assistant"; content: string; streaming: boolean; fileNames?: string[] }
  | { kind: "run"; id: string; card: RunCard };

interface ChatState {
  sessionId: string;
  items: TranscriptItem[];
  busy: boolean;
  /** Cancel requested, turn not yet confirmed stopped. Still busy. */
  cancelling: boolean;
  error: string | null;
  newSession: () => void;
  loadTranscript: (items: TranscriptItem[]) => void;
  send: (text: string, fileIds: string[], fileNames: string[]) => Promise<void>;
  runLast: () => Promise<void>;
  cancel: () => Promise<void>;
}

let subscribed = false;
let idSeq = 0;
const nextId = () => `t${++idSeq}`;

export const useChat = create<ChatState>((set, get) => {
  function subscribe() {
    if (subscribed) return;
    subscribed = true;

    onEvent("chat.token", ({ session_id, delta }) => {
      if (session_id !== get().sessionId) return;
      set((s) => {
        const items = [...s.items];
        const last = items[items.length - 1];
        if (last && last.kind === "message" && last.role === "assistant" && last.streaming) {
          items[items.length - 1] = { ...last, content: last.content + delta };
        } else {
          items.push({
            kind: "message",
            id: nextId(),
            role: "assistant",
            content: delta,
            streaming: true,
          });
        }
        return { items };
      });
    });

    onEvent("chat.message_done", ({ session_id, content }) => {
      if (session_id !== get().sessionId) return;
      set((s) => {
        const items = [...s.items];
        const last = items[items.length - 1];
        if (last && last.kind === "message" && last.streaming) {
          items[items.length - 1] = { ...last, content, streaming: false };
        }
        return { items };
      });
    });

    onEvent("chat.run_start", ({ session_id, code }) => {
      if (session_id !== get().sessionId) return;
      set((s) => ({
        items: [
          ...s.items,
          {
            kind: "run",
            id: nextId(),
            card: {
              code,
              stdout: "",
              stderr: "",
              exitCode: 0,
              durationMs: 0,
              timedOut: false,
              status: "running",
            },
          },
        ],
      }));
    });

    onEvent("chat.run_output", ({ session_id, stdout, stderr, exit_code, duration_ms, timed_out }) => {
      if (session_id !== get().sessionId) return;
      set((s) => {
        const items = [...s.items];
        for (let i = items.length - 1; i >= 0; i--) {
          const it = items[i];
          if (it.kind === "run" && it.card.status === "running") {
            items[i] = {
              ...it,
              card: {
                ...it.card,
                stdout,
                stderr,
                exitCode: exit_code,
                durationMs: duration_ms,
                timedOut: timed_out,
                status: "done",
              },
            };
            break;
          }
        }
        return { items };
      });
    });

    onEvent("chat.turn_done", ({ session_id }) => {
      if (session_id !== get().sessionId) return;
      set({ busy: false, cancelling: false });
    });

    // The turn actually stopped. This — not the reply to chat.cancel — is what
    // clears the busy state: the reply only confirms the request was received,
    // and the turn keeps streaming for a moment after it.
    onEvent("chat.cancelled", ({ session_id }) => {
      if (session_id !== get().sessionId) return;
      set((s) => {
        // Close out any message still marked streaming, so it doesn't sit with
        // a blinking cursor forever.
        const items = [...s.items];
        const last = items[items.length - 1];
        if (last && last.kind === "message" && last.streaming) {
          items[items.length - 1] = { ...last, streaming: false };
        }
        return { items, busy: false, cancelling: false };
      });
    });

    onEvent("chat.error", ({ session_id, message }) => {
      if (session_id !== get().sessionId) return;
      set({ error: message, busy: false, cancelling: false });
    });
  }

  // Subscribe to bridge events immediately so the store reacts even before the
  // first send (and so tests can drive it by emitting events).
  subscribe();

  return {
    sessionId: "last",
    items: [],
    busy: false,
    cancelling: false,
    error: null,

    newSession: () => {
      set({
        sessionId: `s-${Date.now()}`,
        items: [],
        busy: false,
        cancelling: false,
        error: null,
      });
    },

    loadTranscript: (items) => set({ items }),

    send: async (text, fileIds, fileNames) => {
      set((s) => ({
        items: [
          ...s.items,
          {
            kind: "message",
            id: nextId(),
            role: "user",
            content: text,
            streaming: false,
            fileNames: fileNames.length ? fileNames : undefined,
          },
        ],
        busy: true,
        cancelling: false,
        error: null,
      }));
      try {
        await ipc("chat.send", { session_id: get().sessionId, text, file_ids: fileIds });
      } catch (e) {
        set({ error: String(e), busy: false, cancelling: false });
      }
    },

    runLast: async () => {
      set({ busy: true, error: null });
      try {
        await ipc("chat.run_last", { session_id: get().sessionId });
      } catch (e) {
        set({ error: String(e) });
      } finally {
        set({ busy: false });
      }
    },

    cancel: async () => {
      // Do NOT clear `busy` here. The bridge answers this request as soon as it
      // sets the cancel flag, while the turn is still winding down — clearing
      // busy on the reply made the UI claim it had stopped while tokens kept
      // streaming in, and unblocked the composer so a second send could race
      // the running turn. Wait for the chat.cancelled event instead.
      set({ cancelling: true });
      try {
        await ipc("chat.cancel", { session_id: get().sessionId });
      } catch (e) {
        set({ error: String(e), cancelling: false });
      }
    },
  };
});
