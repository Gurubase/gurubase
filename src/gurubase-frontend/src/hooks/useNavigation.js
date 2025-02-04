import { create } from "zustand";

export const useNavigation = create((set) => ({
  isNavigating: false,
  startNavigation: () => set({ isNavigating: true }),
  endNavigation: () => set({ isNavigating: false })
}));
