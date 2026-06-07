import { create } from "zustand";
import type { Session, SessionSummary } from "@inclave/ipc-contract";
import { ipc } from "@/lib/ipc";

interface SessionsState {
  list: SessionSummary[];
  refresh: () => Promise<void>;
  load: (name: string) => Promise<Session>;
  remove: (name: string) => Promise<void>;
}

export const useSessions = create<SessionsState>((set, get) => ({
  list: [],
  refresh: async () => {
    const list = (await ipc("sessions.list", {})) as SessionSummary[];
    set({ list });
  },
  load: async (name) => {
    return (await ipc("sessions.load", { name })) as Session;
  },
  remove: async (name) => {
    await ipc("sessions.delete", { name });
    await get().refresh();
  },
}));
