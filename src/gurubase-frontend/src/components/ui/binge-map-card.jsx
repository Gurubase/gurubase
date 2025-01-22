import * as React from "react";

import { cn } from "@/lib/utils";
import { useAppSelector } from "@/redux/hooks";

const Card = React.forwardRef(({ className, ...props }, ref) => {
  const isBingeMapOpen = useAppSelector(
    (state) => state.mainForm.isBingeMapOpen
  );

  return (
    <div
      ref={ref}
      className={cn(
        "rounded-xl",
        "bg-transparent",
        "overflow-visible",
        "flex flex-col",
        isBingeMapOpen ? "" : "border bg-card text-card-foreground shadow",
        className
      )}
      {...props}
    />
  );
});
Card.displayName = "Card";

const CardHeader = React.forwardRef(
  ({ className, isBingeMapOpen, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "flex flex-col space-y-1.5 flex-none",
        isBingeMapOpen ? "p-2" : "p-4",
        className
      )}
      {...props}
    />
  )
);
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("font-semibold leading-none tracking-tight", className)}
    {...props}
  />
));
CardTitle.displayName = "CardTitle";

const CardDescription = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
));
CardDescription.displayName = "CardDescription";

const CardContent = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("pt-0 relative flex-1 min-h-0", className)}
    {...props}
  />
));
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center pt-0 flex-none", className)}
    {...props}
  />
));
CardFooter.displayName = "CardFooter";

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardDescription,
  CardContent
};
