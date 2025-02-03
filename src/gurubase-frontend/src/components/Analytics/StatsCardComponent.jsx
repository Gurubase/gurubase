"use client";

import { Minus } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Inter } from "next/font/google";
import { Skeleton } from "@/components/ui/skeleton";

const inter = Inter({ subsets: ["latin"] });

const UpArrow = (
  <svg
    width="16"
    height="16"
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg">
    <path
      fill-rule="evenodd"
      clip-rule="evenodd"
      d="M7.64645 2.31442C7.84171 2.11915 8.15829 2.11915 8.35355 2.31442L12.3536 6.31442C12.5488 6.50968 12.5488 6.82626 12.3536 7.02152C12.1583 7.21678 11.8417 7.21678 11.6464 7.02152L8.5 3.87508L8.5 13.3346C8.5 13.6108 8.27614 13.8346 8 13.8346C7.72386 13.8346 7.5 13.6108 7.5 13.3346L7.5 3.87508L4.35355 7.02152C4.15829 7.21678 3.84171 7.21678 3.64645 7.02152C3.45118 6.82626 3.45118 6.50968 3.64645 6.31441L7.64645 2.31442Z"
      fill="currentColor"
    />
  </svg>
);

const DownArrow = (
  <svg
    width="16"
    height="16"
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg">
    <path
      fill-rule="evenodd"
      clip-rule="evenodd"
      d="M8 2.16797C8.27614 2.16797 8.5 2.39183 8.5 2.66797L8.5 12.1275L11.6464 8.98108C11.8417 8.78582 12.1583 8.78582 12.3536 8.98108C12.5488 9.17634 12.5488 9.49293 12.3536 9.68819L8.35355 13.6882C8.25979 13.782 8.13261 13.8346 8 13.8346C7.86739 13.8346 7.74022 13.782 7.64645 13.6882L3.64645 9.68819C3.45118 9.49293 3.45118 9.17634 3.64645 8.98108C3.84171 8.78582 4.15829 8.78582 4.35355 8.98108L7.5 12.1275L7.5 2.66797C7.5 2.39183 7.72386 2.16797 8 2.16797Z"
      fill="currentColor"
    />
  </svg>
);

const STAT_TYPES = {
  HIGHER_BETTER: "higher_better", // e.g., Total Questions
  LOWER_BETTER: "lower_better", // e.g., Out of Context Questions
  NEUTRAL: "neutral" // e.g., Stats where direction doesn't matter
};

export default function StatsCardComponent({
  title = "Total Questions",
  value = 100,
  percentageChange = 0,
  statType = STAT_TYPES.HIGHER_BETTER, // default to higher is better
  isLoading = false
}) {
  const getChangeIndicator = () => {
    const isPositiveChange = percentageChange > 0;
    const isNegativeChange = percentageChange < 0;

    // Determine if the change is good based on the stat type
    const isGoodChange =
      statType === STAT_TYPES.NEUTRAL
        ? null
        : statType === STAT_TYPES.HIGHER_BETTER
          ? isPositiveChange
          : isNegativeChange;

    if (percentageChange === 0) {
      return (
        <div className="flex items-center text-gray-500">
          <Minus className="h-4 w-4 mr-0.5" />
          <span className="text-sm font-semibold">%{percentageChange}</span>
        </div>
      );
    }

    const color =
      statType === STAT_TYPES.NEUTRAL
        ? isPositiveChange
          ? "text-emerald-500"
          : "text-red-500"
        : isGoodChange
          ? "text-emerald-500"
          : "text-red-500";

    return (
      <div className={`flex items-center ${color}`}>
        {isPositiveChange ? UpArrow : DownArrow}
        <span className="text-sm font-semibold">
          {isPositiveChange ? "+" : "-"}%{Math.abs(percentageChange)}
        </span>
      </div>
    );
  };

  if (isLoading) {
    return (
      <Card
        className={`w-full p-4 space-y-2 bg-[#FBFBFB] rounded-xl border border-gray-200 ${inter.className}`}>
        <div>
          <Skeleton className="h-[14px] w-24" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-[31px] w-16" />
          <Skeleton className="h-[16px] w-16" />
        </div>
      </Card>
    );
  }

  return (
    <Card
      className={`w-full p-4 space-y-2 bg-[#FBFBFB] rounded-xl border border-gray-200 ${inter.className}`}>
      <div>
        <span className="text-[14px] font-medium text-[#6D6D6D]">{title}</span>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-[31px] font-semibold text-[#191919]">
          {value}
        </span>
        {getChangeIndicator()}
      </div>
    </Card>
  );
}

// Export STAT_TYPES for use in other components
export { STAT_TYPES };
