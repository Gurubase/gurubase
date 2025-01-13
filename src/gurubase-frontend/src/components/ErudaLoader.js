import React, { useEffect } from "react";

const ErudaLoader = () => {
  useEffect(() => {
    if (typeof window !== "undefined") {
      // Create script element to load Eruda
      const script = document.createElement("script");
      script.src = "https://cdn.jsdelivr.net/npm/eruda";
      script.async = true;
      script.onload = () => {
        // Initialize Eruda after script has loaded
        if (typeof eruda !== "undefined") {
          eruda.init();
        }
      };
      document.body.appendChild(script);
    }

    // Cleanup function to remove script
    return () => {
      document.body
        .querySelectorAll('script[src="https://cdn.jsdelivr.net/npm/eruda"]')
        .forEach((script) => script.remove());
    };
  }, []);

  return null; // This component does not render anything
};

export default ErudaLoader;
