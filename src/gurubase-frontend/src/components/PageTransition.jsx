"use client";
import { useAppSelector } from "@/redux/hooks";
import { useState, useEffect, useRef } from "react";

export const PageTransition = () => {
  const isTransitioning = useAppSelector(
    (state) => state.mainForm.isPageTransitioning
  );
  const [isVisible, setIsVisible] = useState(false);
  const progressRef = useRef(null);

  useEffect(() => {
    if (isTransitioning) {
      setIsVisible(true);
    } else if (isVisible && progressRef.current) {
      // Mevcut animasyonu durdur ve son frame'de tut
      const element = progressRef.current;
      const computedStyle = window.getComputedStyle(element);
      const currentWidth = computedStyle.getPropertyValue("width");

      element.style.animation = "none";
      element.style.width = currentWidth;

      // Reflow için gerekli
      element.offsetHeight;

      // Tamamlama animasyonunu başlat
      element.style.animation = "progress-to-complete 500ms ease-out forwards";

      // Animasyon bitince gizle
      element.addEventListener(
        "animationend",
        () => {
          setIsVisible(false);
        },
        { once: true }
      );
    }
  }, [isTransitioning]);

  if (!isVisible) return null;

  return (
    <div className="fixed top-0 left-0 right-0 h-1 z-[100]">
      <div
        ref={progressRef}
        className="h-full bg-orange-500 animate-progress"
      />
    </div>
  );
};
