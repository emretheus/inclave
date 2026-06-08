// Workspace store — attached files for the active session + the global file list.

import { create } from "zustand";
import type { FileEntry } from "@inclave/ipc-contract";
import { ipc } from "@/lib/ipc";

interface WorkspaceState {
  files: FileEntry[];
  attachedIds: Set<string>;
  refresh: () => Promise<void>;
  addPaths: (paths: string[]) => Promise<void>;
  remove: (ref: string) => Promise<void>;
  toggleAttached: (id: string) => void;
  attach: (id: string) => void;
  clearAttached: () => void;
}

export const useWorkspace = create<WorkspaceState>((set, get) => ({
  files: [],
  attachedIds: new Set(),

  refresh: async () => {
    const files = (await ipc("files.list", {})) as FileEntry[];
    set({ files });
  },

  addPaths: async (paths) => {
    const added = (await ipc("files.add", { paths })) as FileEntry[];
    const ids = new Set(get().attachedIds);
    added.forEach((f) => ids.add(f.id));
    await get().refresh();
    set({ attachedIds: ids });
  },

  remove: async (ref) => {
    await ipc("files.remove", { ref });
    await get().refresh();
    const ids = new Set(get().attachedIds);
    ids.delete(ref);
    set({ attachedIds: ids });
  },

  toggleAttached: (id) =>
    set((s) => {
      const ids = new Set(s.attachedIds);
      if (ids.has(id)) ids.delete(id);
      else ids.add(id);
      return { attachedIds: ids };
    }),

  attach: (id) =>
    set((s) => {
      const ids = new Set(s.attachedIds);
      ids.add(id);
      return { attachedIds: ids };
    }),

  clearAttached: () => set({ attachedIds: new Set() }),
}));
