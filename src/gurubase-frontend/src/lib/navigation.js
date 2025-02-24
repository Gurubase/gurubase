"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";

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
// UNUSED:
// let navigationInstance = null;

// export const getNavigation = () => {
//   if (!navigationInstance) {
//     const router = useRouter();
//     const { startNavigation, handleNavigationComplete } = useNavigation();

//     navigationInstance = {
//       push: async (path) => {
//         startNavigation();
//         router.push(path);
//       },
//       replace: async (path) => {
//         startNavigation();
//         router.replace(path);
//       },
//       back: () => {
//         startNavigation();
//         router.back();
//       },
//       setHref: (url) => {
//         startNavigation();
//         // Don't need to end navigation as the page will reload
//         window.location.href = url;
//       },
//       pushState: (state, title, url) => {
//         startNavigation();
//         window.history.pushState(state, title, url);
//         handleNavigationComplete();
//       }
//     };
//   }

//   return navigationInstance;
// };

// Hook version for use within components
export const useAppNavigation = () => {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { startNavigation, handleNavigationComplete } = useNavigation();

  // Listen for route changes
  useEffect(() => {
    handleNavigationComplete();
  }, [pathname, searchParams, handleNavigationComplete]);

  return {
    push: async (path) => {
      if (!useNavigation.getState().isNavigating) {
        startNavigation();
        router.push(path);
      }
    },
    replace: async (path) => {
      if (!useNavigation.getState().isNavigating) {
        startNavigation();
        router.replace(path);
      }
    },
    back: () => {
      if (!useNavigation.getState().isNavigating) {
        startNavigation();
        router.back();
      }
    },
    setHref: (url) => {
      if (!useNavigation.getState().isNavigating) {
        startNavigation();
        window.location.href = url;
      }
    }
  };
};
