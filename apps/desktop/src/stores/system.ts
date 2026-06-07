// System store — Ollama state, active model, RAM, sandbox availability.

import { create } from "zustand";
import type { SystemStatus } from "@inclave/ipc-contract";
import { ipc, onEvent } from "@/lib/ipc";

interface SystemState {
  status: SystemStatus | null;
  activeModel: string | null;
  refresh: () => Promise<void>;
  setActiveModel: (m: string) => void;
  ensureOllama: () => Promise<void>;
  watch: () => void;
}

let watching = false;

export const useSystem = create<SystemState>((set, get) => ({
  status: null,
  activeModel: null,

  refresh: async () => {
    const status = (await ipc("system.status", {})) as SystemStatus;
    set((s) => ({ status, activeModel: s.activeModel ?? status.default_model }));
  },

  setActiveModel: (m) => set({ activeModel: m }),

  ensureOllama: async () => {
    await ipc("ollama.ensure_running", {});
    await get().refresh();
  },

  watch: () => {
    if (watching) return;
    watching = true;
    onEvent("system.ollama_state", ({ running }) => {
      set((s) => ({ status: s.status ? { ...s.status, ollama_running: running } : s.status }));
    });
  },
}));
