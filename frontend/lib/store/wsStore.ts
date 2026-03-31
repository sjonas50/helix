import { create } from "zustand";

interface WSStore {
  connected: boolean;
  lastEventAt: string | null;
  setConnected: (v: boolean) => void;
  setLastEvent: () => void;
}

export const useWSStore = create<WSStore>((set) => ({
  connected: false,
  lastEventAt: null,
  setConnected: (connected) => set({ connected }),
  setLastEvent: () => set({ lastEventAt: new Date().toISOString() }),
}));
