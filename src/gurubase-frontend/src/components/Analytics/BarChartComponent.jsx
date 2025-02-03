"use client";

import { useState } from "react";
import { Bar, BarChart, XAxis, YAxis, CartesianGrid } from "recharts";
import { ChartContainer } from "@/components/ui/chart";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

export default function BarChartComponent({
  data = [],
  interval,
  isLoading = false
}) {
  const [tooltip, setTooltip] = useState(null);

  const isHourly = interval === "today" || interval === "yesterday";

  const chartConfig = {
    questions: {
      label: "Question",
      color: "#CCE2FF"
    }
  };

  // Format date for display
  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString);
      if (isHourly) {
        return date.getHours().toString().padStart(2, "0") + ":00";
      }
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric"
      });
    } catch (e) {
      console.error("Error formatting date:", e);
      return dateString;
    }
  };

  // Format tooltip date
  const formatTooltipDate = (dateString) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        ...(isHourly && { hour: "numeric", minute: "numeric" })
      });
    } catch (e) {
      console.error("Error formatting tooltip date:", e);
      return dateString;
    }
  };

  return (
    <div className="rounded-xl border border-[#E2E2E2]">
      <div className="w-full relative">
        {isLoading ? (
          <div className="aspect-[2/1] p-8">
            <div className="h-full w-full flex flex-col justify-between">
              <Skeleton className="w-full h-[80%]" />
              <div className="flex justify-between w-full">
                {[...Array(6)].map((_, i) => (
                  <Skeleton key={i} className="w-12 h-4" />
                ))}
              </div>
            </div>
          </div>
        ) : (
          <>
            <style jsx global>{`
              .recharts-bar-rectangle {
                cursor: pointer;
              }
            `}</style>
            {tooltip && (
              <div
                className="absolute bg-white shadow-lg rounded-lg p-4 border z-50 pointer-events-none min-w-[180px]"
                style={{
                  left: tooltip.x,
                  top: Math.max(40, tooltip.y),
                  transform: "translate(-50%, -100%)",
                  marginTop: "-10px"
                }}>
                <div className="text-sm font-medium">
                  {formatTooltipDate(tooltip.date)}
                </div>
                <Separator className="my-2" />
                <div className="flex items-center gap-1">
                  <span className="text-sm text-muted-foreground">
                    Question:
                  </span>
                  <span className="text-sm font-medium">
                    {tooltip.questions}
                  </span>
                </div>
              </div>
            )}
            <ChartContainer config={chartConfig} className="aspect-[2/1]">
              <BarChart
                data={data}
                margin={{
                  top: 30,
                  right: 10,
                  left: -10
                }}>
                <CartesianGrid
                  horizontal={true}
                  vertical={false}
                  stroke="#E2E2E2"
                />
                <XAxis
                  dataKey="date"
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#000000" }}
                  tickFormatter={formatDate}
                  interval={isHourly ? 3 : interval === "30d" ? 4 : 0}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#000000" }}
                  tickCount={6}
                />
                <Bar
                  dataKey="questions"
                  fill="#CCE2FF"
                  radius={[4, 4, 0, 0]}
                  maxBarSize={40}
                  style={{
                    transition: "fill 0.2s ease"
                  }}
                  onMouseOver={(data, index, event) => {
                    const rect = event.target.getBoundingClientRect();
                    const chartRect = event.target
                      .closest("svg")
                      .getBoundingClientRect();

                    const x = rect.left + rect.width / 2 - chartRect.left;
                    const y = rect.top - chartRect.top;

                    event.target.style.fill = "#2563EB";
                    setTooltip({
                      x,
                      y,
                      date: data.date,
                      questions: data.questions
                    });
                  }}
                  onMouseLeave={(data, index, event) => {
                    event.target.style.fill = "#CCE2FF";
                    setTooltip(null);
                  }}
                />
              </BarChart>
            </ChartContainer>
          </>
        )}
      </div>
    </div>
  );
}
