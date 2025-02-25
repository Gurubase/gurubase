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

  // Helper to normalize paths for comparison
  const normalizePath = (path) => {
    // Remove trailing slash if present (except for root path)
    return path === "/" ? path : path.replace(/\/$/, "");
  };

  // Helper to check if paths are the same
  const isSamePath = (targetPath) => {
    // Get current URL with query params
    const currentFullPath =
      pathname + (searchParams.toString() ? `?${searchParams.toString()}` : "");

    // Normalize both paths
    const normalizedCurrentPath = normalizePath(currentFullPath);
    const normalizedTargetPath = normalizePath(targetPath);

    return normalizedCurrentPath === normalizedTargetPath;
  };

  return {
    push: async (path) => {
      // Don't start navigation if already navigating or if it's the same path
      if (!useNavigation.getState().isNavigating && !isSamePath(path)) {
        startNavigation();
        router.push(path);
      }
    },
    replace: async (path) => {
      // Don't start navigation if already navigating or if it's the same path
      if (!useNavigation.getState().isNavigating && !isSamePath(path)) {
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
      // Don't start navigation if already navigating or if it's the same URL
      if (!useNavigation.getState().isNavigating && !isSamePath(url)) {
        startNavigation();
        window.location.href = url;
      }
    }
  };
};
