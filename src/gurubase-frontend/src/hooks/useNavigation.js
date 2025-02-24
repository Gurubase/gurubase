import { create } from "zustand";

export const useNavigation = create((set) => ({
  isNavigating: false,
  startNavigation: () => set({ isNavigating: true }),
  endNavigation: () => set({ isNavigating: false }),
  handleNavigationComplete: () => {
    // Small delay to ensure any route data is loaded
    setTimeout(() => set({ isNavigating: false }), 100);
  }
}));
