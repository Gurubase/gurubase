import { create } from "zustand";

export const useNavigation = create((set, get) => ({
  isNavigating: false,
  timeoutId: null,
  startNavigation: () => set({ isNavigating: true }),
  endNavigation: () => set({ isNavigating: false }),
  handleNavigationComplete: () => {
    const state = get();

    // Clear existing timeout if any
    if (state.timeoutId) {
      clearTimeout(state.timeoutId);
    }
    // Set new timeout and store its ID
    const timeoutId = setTimeout(() => set({ isNavigating: false }), 100);

    set({ timeoutId });
  }
}));
