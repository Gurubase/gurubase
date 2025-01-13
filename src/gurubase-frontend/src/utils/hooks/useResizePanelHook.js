// create a custom hook to resize the panel

import { useAppDispatch, useAppSelector } from "@/redux/hooks";
import { setPanelHintsListed } from "@/redux/slices/mainFormSlice";
import { useState, useEffect } from "react";

const useResizePanelHook = () => {
  const dispatch = useAppDispatch();
  const [searchWidth, setSearchWidth] = useState(0);
  const mobileInputFocused = useAppSelector(
    (state) => state.mainForm.mobileInputFocused
  );

  useEffect(() => {
    const fixedSearch = document.querySelector(`.mobile-fixed-search`);

    const updateWidth = () => {
      setSearchWidth(fixedSearch.offsetWidth);
    };

    // Set up the intersection observer
    const observer = new ResizeObserver((entries) => {
      for (let entry of entries) {
        updateWidth();
      }
    });

    // Mutation Observer to detect when aa-Panel is added to the DOM
    const mutationObserver = new MutationObserver((mutationsList) => {
      for (let mutation of mutationsList) {
        if (mutation.type === "childList") {
          for (let addedNode of mutation.addedNodes) {
            if (
              addedNode.classList &&
              addedNode.classList.contains("aa-Panel")
            ) {
              requestAnimationFrame(() => {
                // Set the width and max-width of the panel based on the search width and mobile input focus
                addedNode.style.width = `${searchWidth - (mobileInputFocused ? 0 : 2)}px`;
                addedNode.style.maxWidth = `${searchWidth - (mobileInputFocused ? 0 : 2)}px`;

                // Set the left position of the panel based on the fixed search element's position and mobile input focus
                addedNode.style.left = `${fixedSearch.offsetLeft + (mobileInputFocused ? 0 : 1)}px`;

                // Set the top position of the panel based on the fixed search element's position, height, and mobile input focus
                addedNode.style.top = `${fixedSearch.offsetTop + fixedSearch.offsetHeight - 8 + (mobileInputFocused ? window.scrollY : 0)}px`;

                // Set the border radius for the panel to have rounded bottom corners and flat top corners
                addedNode.style.borderRadius = "0 0 20px 20px";
                addedNode.style.borderTopLeftRadius = "0";
                addedNode.style.borderTopRightRadius = "0";

                // Dispatch an action to show or hide panel hints based on mobile input focus or window width
                if (mobileInputFocused || window.innerWidth > 915)
                  dispatch(setPanelHintsListed(true));
                else dispatch(setPanelHintsListed(false));
              });
            }
          }
          for (let removedNode of mutation.removedNodes) {
            if (
              removedNode.classList &&
              removedNode.classList.contains("aa-Panel")
            ) {
              dispatch(setPanelHintsListed(false));
            }
          }
        }
      }
    });

    // Start observing the body or the parent element that those dropdowns are appended
    mutationObserver.observe(document.body, { childList: true, subtree: true });

    if (fixedSearch) {
      observer.observe(fixedSearch);
      // Initial width set
      updateWidth();
    }

    // Clean up the observer on component unmount
    return () => {
      if (fixedSearch) {
        observer.unobserve(fixedSearch);
      }
      mutationObserver.disconnect();
    };
  }, [searchWidth, mobileInputFocused, dispatch]);

  return searchWidth;
};

export default useResizePanelHook;
