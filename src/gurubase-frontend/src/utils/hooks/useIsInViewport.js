import { useEffect, useState } from "react";

export default function useIsInViewport(className) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      const element = document.querySelector(`.${className}`);

      //  use Observer
      if (!element) return;
      const observer = new IntersectionObserver(
        ([entry]) => {
          setIsVisible(entry.isIntersecting);
        },
        {
          root: null,
          rootMargin: "0px",
          threshold: 0.1
        }
      );
      observer.observe(element);

      return () => {
        observer.disconnect();
      };
    };

    window.addEventListener("scroll", handleScroll);
    handleScroll();

    return () => {
      window.removeEventListener("scroll", handleScroll);
    };
  }, [className]);

  return isVisible;
}
