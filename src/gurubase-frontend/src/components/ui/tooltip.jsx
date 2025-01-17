"use client";

import * as React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";

import { cn } from "@/lib/utils";

const TooltipProvider = TooltipPrimitive.Provider;

const Tooltip = TooltipPrimitive.Root;

const TooltipTrigger = TooltipPrimitive.Trigger;

const TooltipContent = React.forwardRef(
  ({ className, sideOffset = 4, ...props }, ref) => (
    <TooltipPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(
        "z-50 overflow-visible rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground",
        "relative max-w-[calc(100vw-32px)]",
        className
      )}
      {...props}>
      {props.children}
      <div
        className="absolute h-2 w-2 rotate-45 bg-primary"
        style={{
          bottom: "-4px",
          left: "50%",
          transform: "translateX(-50%) rotate(45deg)",
          zIndex: -1
        }}
      />
    </TooltipPrimitive.Content>
  )
);
TooltipContent.displayName = TooltipPrimitive.Content.displayName;

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider };
