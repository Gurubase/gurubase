"use client"; // Error components must be Client Components
import "react-sliding-pane/dist/react-sliding-pane.css";

import { Icon } from "@iconify/react";
import clsx from "clsx";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ReactSlidingPane } from "react-sliding-pane";

import {
  getGuruPromptMap,
  getGuruTypeComboboxBg
} from "@/components/Header/utils";

import OtherGurus from ".";

const MobileOtherGurus = ({ allGuruTypes, isLongGuruName }) => {
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const { guruType } = useParams();

  useEffect(() => {
    if (isPanelOpen) {
      // Prevent scrolling on body
      document.body.style.overflow = "hidden";
      document.body.style.overscrollBehavior = "none"; // Prevent overscroll behavior
    } else {
      // Re-enable scrolling on body
      document.body.style.overflow = "";
      document.body.style.overscrollBehavior = ""; // Reset overscroll behavior
    }
  }, [isPanelOpen]);

  if (!guruType) return null;

  return (
    <div className="hidden guru-sm:block">
      <div
        className={clsx(
          "flex gap-1 items-center p-2 rounded-lg float-right",
          "cursor-pointer",
          isLongGuruName ? "text-[10px]" : "text-xs",
          "font-medium text-white"
        )}
        style={{
          backgroundColor:
            guruType && getGuruTypeComboboxBg(guruType, allGuruTypes)
        }}
        onClick={() => setIsPanelOpen(true)}>
        <div className="self-stretch my-auto">
          {getGuruPromptMap(guruType, allGuruTypes)}
        </div>
        <Icon icon="tabler:chevron-down" />
      </div>
      <ReactSlidingPane
        hideHeader
        className="z-20 p-0 bg-black bg-opacity-70"
        from="bottom"
        isOpen={isPanelOpen}
        overlayClassName="z-20 bg-black bg-opacity-70"
        width="100%"
        onRequestClose={() => setIsPanelOpen(false)}>
        <div
          className="w-full min-h-[5px] min-w-[36px] py-4 flex justify-center"
          onClick={() => setIsPanelOpen(false)}
          onTouchStart={(e) => {
            e.stopPropagation(); // Prevent touch event from propagating to underlying elements
            const startY = e.touches[0].clientY;
            let isScrolling; // Flag to determine if scrolling occurred

            const handleTouchMove = (e) => {
              if (isScrolling === undefined) {
                isScrolling = true; // Set flag to true when touchmove starts
                e.stopPropagation(); // Prevent touchmove from propagating
              }
              const currentY = e.touches[0].clientY;

              if (currentY - startY > 50) {
                // Threshold for downward swipe
                setIsPanelOpen(false);
                document.removeEventListener("touchmove", handleTouchMove);
              }
            };

            const handleTouchEnd = () => {
              if (!isScrolling) {
                // If scrolling didn't occur, allow the click event
                setIsPanelOpen(false);
              }
              // Clean up touchmove and touchend listeners
              document.removeEventListener("touchmove", handleTouchMove);
              document.removeEventListener("touchend", handleTouchEnd);
            };

            document.addEventListener("touchmove", handleTouchMove, {
              passive: false
            });
            document.addEventListener("touchend", handleTouchEnd, {
              once: true,
              passive: false
            });
          }}>
          <span className="h-[5px] min-w-[36px] bg-gray-300 rounded-md"></span>
        </div>
        <OtherGurus
          allGuruTypes={allGuruTypes}
          className="z-30"
          isMobile={true}
        />
      </ReactSlidingPane>
    </div>
  );
};

export default MobileOtherGurus;
