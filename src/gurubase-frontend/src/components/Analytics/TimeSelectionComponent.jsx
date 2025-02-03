"use client";

import { Inter } from "next/font/google";
import React from "react"; // Import React

const inter = Inter({ subsets: ["latin"] });

const periods = [
  { label: "Today", value: "today" },
  { label: "Yesterday", value: "yesterday" },
  { label: "7D", value: "7d" },
  { label: "30D", value: "30d" },
  { label: "3M", value: "3m" },
  { label: "6M", value: "6m" },
  { label: "12M", value: "12m" }
];

export default function TimeSelectionComponent({
  onPeriodChange,
  defaultPeriod = "today",
  className
}) {
  const [activePeriod, setActivePeriod] = React.useState(defaultPeriod);

  const handlePeriodChange = (period) => {
    setActivePeriod(period);
    onPeriodChange?.(period);
  };

  const cn = (...classes) => classes.filter(Boolean).join(" ");

  return (
    <nav
      className={cn(
        "inline-flex h-10 md:h-10 h-8 items-center divide-x divide-[#E2E2E2] rounded-lg border border-[#E2E2E2] bg-white text-[11px] md:text-base",
        inter.className,
        className
      )}
      role="tablist"
      aria-label="Time period navigation">
      {periods.map((period) => (
        <button
          key={period.value}
          onClick={() => handlePeriodChange(period.value)}
          role="tab"
          aria-selected={activePeriod === period.value}
          aria-controls={`panel-${period.value}`}
          className={cn(
            "relative flex h-full items-center justify-center md:px-3 px-[6px] transition-colors hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
            "text-[11px] md:text-[14px] font-medium leading-normal",
            activePeriod === period.value
              ? "bg-[#EFF6FF] text-[#2563EB]"
              : "text-[#6D6D6D]",
            "first:rounded-l-lg last:rounded-r-lg"
          )}>
          {period.label}
        </button>
      ))}
    </nav>
  );
}
