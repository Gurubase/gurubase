import { useEffect } from "react";

const usePreventScroll = (isActive) => {
  useEffect(() => {
    const preventDefault = (e) => e.preventDefault();

    if (
      isActive &&
      typeof window !== "undefined" &&
      typeof document !== "undefined"
    ) {
      // Apply overflow hidden to body
      document.body.style.overflow = "hidden";

      // Add event listeners to prevent scroll/touch actions

      document.body.addEventListener("touchmove", preventDefault, {
        passive: false
      });

      // Add mouse event listeners
      document.body.addEventListener("wheel", preventDefault, {
        passive: false
      });
      document.body.addEventListener("mousewheel", preventDefault, {
        passive: false
      });
      document.body.addEventListener("mousedrag", preventDefault, {
        passive: false
      });

      return () => {
        // Remove overflow hidden
        document.body.style.overflow = "";

        // Remove event listeners

        document.body.removeEventListener("touchmove", preventDefault, {
          passive: false
        });

        document.body.removeEventListener("wheel", preventDefault, {
          passive: false
        });
        document.body.removeEventListener("mousewheel", preventDefault, {
          passive: false
        });
        document.body.removeEventListener("mousedrag", preventDefault, {
          passive: false
        });
      };
    }
  }, [isActive]);
};

export default usePreventScroll;
