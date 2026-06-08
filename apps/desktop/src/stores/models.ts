import { create } from "zustand";
import type { ModelInfo } from "@inclave/ipc-contract";
import { ipc, onEvent } from "@/lib/ipc";

interface PullState {
  name: string;
  status: string;
  pct: number;
}

interface ModelsState {
  list: ModelInfo[];
  pulling: PullState | null;
  refresh: () => Promise<void>;
  setDefault: (name: string) => Promise<void>;
  remove: (name: string) => Promise<void>;
  pull: (name: string) => Promise<void>;
  watch: () => void;
}

let watching = false;

export const useModels = create<ModelsState>((set, get) => ({
  list: [],
  pulling: null,

  refresh: async () => {
    const list = (await ipc("models.list", {})) as ModelInfo[];
    set({ list });
  },

  setDefault: async (name) => {
    await ipc("models.set_default", { name });
    await get().refresh();
  },

  remove: async (name) => {
    await ipc("models.remove", { name });
    await get().refresh();
  },

  pull: async (name) => {
    set({ pulling: { name, status: "starting", pct: 0 } });
    try {
      await ipc("models.pull", { name });
      await get().refresh();
    } finally {
      set({ pulling: null });
    }
  },

  watch: () => {
    if (watching) return;
    watching = true;
    onEvent("models.pull_progress", ({ name, status, completed, total }) => {
      set({
        pulling: {
          name,
          status,
          pct: total > 0 ? Math.round((completed / total) * 100) : 0,
        },
      });
    });
  },
}));
