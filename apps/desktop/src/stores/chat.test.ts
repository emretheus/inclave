import { describe, expect, it, beforeEach } from "vitest";
import { useChat } from "./chat";
import { mockEmit } from "@/lib/ipc";

// The chat store assembles streamed events into a transcript. We drive it by
// emitting the same events the bridge would, and assert the transcript shape.

describe("chat store", () => {
  beforeEach(() => {
    useChat.setState({ items: [], busy: false, error: null, sessionId: "test-session" });
  });

  it("assembles streamed tokens into one assistant message", () => {
    const sid = useChat.getState().sessionId;
    mockEmit("chat.token", { session_id: sid, delta: "Hel" });
    mockEmit("chat.token", { session_id: sid, delta: "lo" });
    const items = useChat.getState().items;
    expect(items).toHaveLength(1);
    expect(items[0]).toMatchObject({ kind: "message", role: "assistant", content: "Hello", streaming: true });
  });

  it("finalizes a message on message_done", () => {
    const sid = useChat.getState().sessionId;
    mockEmit("chat.token", { session_id: sid, delta: "Hi" });
    mockEmit("chat.message_done", { session_id: sid, role: "assistant", content: "Hi there" });
    const item = useChat.getState().items[0];
    expect(item).toMatchObject({ kind: "message", content: "Hi there", streaming: false });
  });

  it("creates a running run card on run_start and fills it on run_output", () => {
    const sid = useChat.getState().sessionId;
    mockEmit("chat.run_start", { session_id: sid, code: "print(1)" });
    let run = useChat.getState().items.find((i) => i.kind === "run");
    expect(run && run.kind === "run" && run.card.status).toBe("running");

    mockEmit("chat.run_output", {
      session_id: sid,
      stdout: "1\n",
      stderr: "",
      exit_code: 0,
      duration_ms: 12,
      timed_out: false,
    });
    run = useChat.getState().items.find((i) => i.kind === "run");
    expect(run && run.kind === "run" && run.card.status).toBe("done");
    expect(run && run.kind === "run" && run.card.stdout).toBe("1\n");
  });

  it("ignores events from other sessions", () => {
    mockEmit("chat.token", { session_id: "other", delta: "nope" });
    expect(useChat.getState().items).toHaveLength(0);
  });

  it("clears busy on turn_done", () => {
    const sid = useChat.getState().sessionId;
    useChat.setState({ busy: true });
    mockEmit("chat.turn_done", { session_id: sid, n_turns: 1 });
    expect(useChat.getState().busy).toBe(false);
  });

  it("surfaces errors", () => {
    const sid = useChat.getState().sessionId;
    mockEmit("chat.error", { session_id: sid, code: "ollama_unavailable", message: "down" });
    expect(useChat.getState().error).toBe("down");
  });
});
