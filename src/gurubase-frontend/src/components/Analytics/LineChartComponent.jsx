"use client";

import { useMemo } from "react";

export default function LineChartComponent({ data }) {
  const colors = [
    "bg-orange-500",
    "bg-cyan-400",
    "bg-blue-500",
    "bg-purple-500",
    "bg-fuchsia-400",
    "bg-pink-500",
    "bg-red-500"
  ];

  const maxItems = 8;

  const processedData = useMemo(() => {
    if (!Array.isArray(data)) {
      console.error("Data must be an array");
      return [];
    }

    // Separate "Others" from the rest of the data
    const othersItem = data.find((item) => item.text === "Others");
    const regularItems = data.filter((item) => item.text !== "Others");

    // Sort regular items by value in descending order and take first (maxItems - 1) if we have "Others"
    const sortedRegularItems = [...regularItems]
      .sort((a, b) => b.value - a.value)
      .slice(0, othersItem ? maxItems - 1 : maxItems);

    // Combine sorted items with "Others" at the end
    const combinedItems = othersItem
      ? [...sortedRegularItems, othersItem]
      : sortedRegularItems;

    // Calculate total for percentages
    const total = combinedItems.reduce((sum, item) => sum + item.value, 0);

    // Add color and percentage to each item
    return combinedItems.map((item, index) => ({
      ...item,
      color: item.text === "Others" ? "bg-gray-200" : colors[index],
      dotColor: item.text === "Others" ? "bg-gray-200" : colors[index],
      percentage: (item.value / total) * 100
    }));
  }, [data, maxItems]);

  if (!processedData.length) {
    return <div>No data available</div>;
  }

  return (
    <div className="w-full p-6 space-y-6 rounded-xl border border-[#E2E2E2] bg-background">
      {/* Distribution bar */}
      <div className="flex w-full h-[19px] items-start gap-[2px] rounded-lg overflow-hidden">
        {processedData.map((item, index) => (
          <div
            key={index}
            className={`h-full ${item.color}`}
            style={{ width: `${item.percentage}%` }}
          />
        ))}
      </div>

      {/* List items */}
      <div className="space-y-4">
        {processedData.map((item, index) => (
          <div key={index} className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${item.dotColor}`} />
              <span className="text-sm text-muted-foreground">{item.text}</span>
            </div>
            <span className="text-sm font-medium">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
