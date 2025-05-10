"use client";

import { useState, useEffect } from "react";
import { SolarInfoCircleBold } from "@/components/Icons";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "@/components/ui/tooltip";

export const HeaderTooltip = ({ text, html }) => {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!event.target.closest("[data-tooltip-trigger]")) {
        setIsOpen(false);
      }
    };

    // Handle both touch and click events
    document.addEventListener("click", handleClickOutside);
    document.addEventListener("touchend", handleClickOutside);

    return () => {
      document.removeEventListener("click", handleClickOutside);
      document.removeEventListener("touchend", handleClickOutside);
    };
  }, []);

  const handleInteraction = (e) => {
    e.preventDefault();
    e.stopPropagation();

    // Check if it's a mobile device
    const isMobile = window.matchMedia("(max-width: 768px)").matches;
    if (isMobile) {
      setIsOpen(!isOpen);
    }
  };

  return (
    <div className="ml-2">
      <TooltipProvider>
        <Tooltip open={isOpen} onOpenChange={setIsOpen}>
          <TooltipTrigger
            asChild
            data-tooltip-trigger
            onClick={handleInteraction}
            onTouchEnd={handleInteraction}>
            <div>
              <SolarInfoCircleBold className="h-4 w-4 text-gray-200" />
            </div>
          </TooltipTrigger>
          <TooltipContent side="top" align="center" className="z-50">
            {html ? (
              <div
                className="text-[12px] font-medium max-w-[400px]"
                dangerouslySetInnerHTML={{ __html: html }}
              />
            ) : (
              <p className="text-[12px] font-medium max-w-[400px]">{text}</p>
            )}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
};
