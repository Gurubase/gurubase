"use client";
import { useAppSelector } from "@/redux/hooks";
import { useState, useEffect, useRef } from "react";
import { useNavigation } from "@/hooks/useNavigation";
import { useAppDispatch } from "@/redux/hooks";

export const PageTransition = () => {
  const isNavigating = useNavigation((state) => state.isNavigating);
  const [isVisible, setIsVisible] = useState(false);
  const progressRef = useRef(null);
  const isPageTransitioning = useAppSelector(
    (state) => state.mainForm.isPageTransitioning
  );

  useEffect(() => {
    if (isNavigating || isPageTransitioning) {
      setIsVisible(true);
    } else if (isVisible && progressRef.current) {
      // Stop the current animation and keep it on the last frame
      const element = progressRef.current;
      const computedStyle = window.getComputedStyle(element);
      const currentWidth = computedStyle.getPropertyValue("width");

      element.style.animation = "none";
      element.style.width = currentWidth;

      // Necessary for reflow
      element.offsetHeight;

      // Start the completion animation
      element.style.animation = "progress-to-complete 500ms ease-out forwards";

      // Hide when animation ends
      element.addEventListener(
        "animationend",
        () => {
          setIsVisible(false);
        },
        { once: true }
      );
    }
  }, [isNavigating, isPageTransitioning]);

  if (!isVisible) return null;

  return (
    <div className="fixed top-0 left-0 right-0 h-1 z-[100]">
      <div
        ref={progressRef}
        className="h-full bg-orange-500 animate-progress"
        style={{ width: "0%" }}
      />
    </div>
  );
};
