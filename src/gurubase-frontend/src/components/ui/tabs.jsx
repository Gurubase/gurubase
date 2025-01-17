"use client";

import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";

import { cn } from "@/lib/utils";

const Tabs = TabsPrimitive.Root;

const TabsList = React.forwardRef(
  ({ className, customTab = false, ...props }, ref) => (
    <TabsPrimitive.List
      ref={ref}
      className={cn(
        !customTab &&
          "inline-flex h-9 items-center justify-center rounded-lg bg-muted p-1 text-muted-foreground",
        customTab && "py-0",
        className
      )}
      {...props}
    />
  )
);
TabsList.displayName = TabsPrimitive.List.displayName;

const TabsTrigger = React.forwardRef(
  ({ className, customTab = false, ...props }, ref) => (
    <TabsPrimitive.Trigger
      ref={ref}
      className={cn(
        !customTab &&
          "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow",
        customTab &&
          " inline-flex h-9 items-center justify-center px-4 pb-3 text-sm font-medium text-gray-500 hover:text-gray-700 focus:outline-none data-[state=active]:relative data-[state=active]:top-[0.5px] data-[state=active]:text-gray-700 data-[state=active]:border-b data-[state=active]:border-gray-700",
        className
      )}
      {...props}
    />
  )
);
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

const TabsContent = React.forwardRef(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      "mt-2 ring-offset-background focus-visible:outline-none ",
      className
    )}
    {...props}
  />
));
TabsContent.displayName = TabsPrimitive.Content.displayName;

export { Tabs, TabsList, TabsTrigger, TabsContent };
