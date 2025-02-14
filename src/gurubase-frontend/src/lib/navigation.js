"use client";

import { useRouter } from "next/navigation";

import { useNavigation } from "@/hooks/useNavigation";

// USAGE
// // Using the hook in a component
// import { useAppNavigation } from "@/lib/navigation";

// const YourComponent = () => {
//   const navigation = useAppNavigation();

//   const handleClick = () => {
//     navigation.push("/some-path");
//   };

//   return <button onClick={handleClick}>Navigate</button>;
// };

// // OR using the singleton version in a non-component context
// import { getNavigation } from "@/lib/navigation";

// const handleNavigation = () => {
//   const navigation = getNavigation();
//   navigation.push("/some-path");
// };

// Create a singleton instance for the navigation state
let navigationInstance = null;

export const getNavigation = () => {
  if (!navigationInstance) {
    const router = useRouter();
    const { startNavigation, endNavigation } = useNavigation();

    navigationInstance = {
      push: async (path) => {
        startNavigation();
        try {
          router.push(path);
        } finally {
          setTimeout(endNavigation, 1500);
        }
      },
      replace: async (path) => {
        startNavigation();
        try {
          router.replace(path);
        } finally {
          setTimeout(endNavigation, 1500);
        }
      },
      back: () => {
        startNavigation();
        try {
          router.back();
        } finally {
          setTimeout(endNavigation, 1500);
        }
      },
      setHref: (url) => {
        startNavigation();
        // Don't need to end navigation as the page will reload
        window.location.href = url;
      },
      pushState: (state, title, url) => {
        startNavigation();
        window.history.pushState(state, title, url);
        setTimeout(endNavigation, 1500);
      }
    };
  }

  return navigationInstance;
};

// Hook version for use within components
export const useAppNavigation = () => {
  const router = useRouter();
  const { startNavigation, endNavigation } = useNavigation();

  return {
    push: async (path) => {
      if (!useNavigation.getState().isNavigating) {
        // Only start if not already navigating
        startNavigation();
        try {
          router.push(path);
        } finally {
          // Increased delay to ensure the animation completes smoothly
          setTimeout(endNavigation, 1500);
        }
      }
    },
    replace: async (path) => {
      if (!useNavigation.getState().isNavigating) {
        // Only start if not already navigating
        startNavigation();
        try {
          router.replace(path);
        } finally {
          // Increased delay to ensure the animation completes smoothly
          setTimeout(endNavigation, 1500);
        }
      }
    },
    back: () => {
      if (!useNavigation.getState().isNavigating) {
        // Only start if not already navigating
        startNavigation();
        try {
          router.back();
        } finally {
          // Increased delay to ensure the animation completes smoothly
          setTimeout(endNavigation, 1500);
        }
      }
    },
    setHref: (url) => {
      if (!useNavigation.getState().isNavigating) {
        // Only start if not already navigating
        startNavigation();
        // Don't need to end navigation as the page will reload
        window.location.href = url;
      }
    },
    pushState: (state, title, url) => {
      startNavigation();
      window.history.pushState(state, title, url);
      setTimeout(endNavigation, 1500);
    }
  };
};
