"use client";
import { X, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { useState, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import * as React from "react";
import { DataTable } from "@/components/ui/data-table";
import { TablePagination } from "@/components/ui/table-pagination";
import { tableConfigs } from "@/config/tableConfigs";
import { QuestionsList } from "./QuestionsList";
import { Input } from "@/components/ui/input";

import { renderCellWithTooltip } from "@/components/ui/data-table";

const StyledDialogContent = React.forwardRef(
  ({ children, isMobile, ...props }, ref) => (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-[49] bg-black/80 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
      <DialogPrimitive.Content
        ref={ref}
        className={cn(
          "fixed z-[50] bg-white shadow-lg transition ease-in-out data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:duration-300 data-[state=open]:duration-500",
          isMobile
            ? "inset-x-0 bottom-0 h-[90vh] w-full rounded-t-[20px] data-[state=closed]:slide-out-to-bottom data-[state=open]:slide-in-from-bottom"
            : "right-0 top-0 h-full w-full max-w-5xl data-[state=closed]:slide-out-to-right data-[state=open]:slide-in-from-right"
        )}
        {...props}>
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
);

StyledDialogContent.displayName = "StyledDialogContent";

export default function TableComponent({
  data,
  onFilterChange,
  onPageChange,
  currentFilter = "all",
  currentPage = 1,
  isLoading = false,
  metricType,
  guruType,
  interval,
  onSearch,
  searchQuery = "",
  onSortChange,
  sortOrder,
  timeRange = null,
  onTimeRangeChange
}) {
  const [isUrlSidebarOpen, setIsUrlSidebarOpen] = useState(false);
  const [clickedSource, setClickedSource] = useState(null);
  const [searchTerm, setSearchTerm] = useState(searchQuery);

  useEffect(() => {
    setSearchTerm(searchQuery);
  }, [searchQuery]);

  useEffect(() => {
    // Only reset if timeRange changes from null to value or vice versa
    if ((!timeRange && prevTimeRange) || (timeRange && !prevTimeRange)) {
      onFilterChange && onFilterChange("all");
      onSearch && onSearch("");
      onSortChange && onSortChange("desc");
      onPageChange && onPageChange(1);
    }
  }, [timeRange]);

  // Keep track of previous timeRange value
  const prevTimeRangeRef = useRef(timeRange);
  useEffect(() => {
    prevTimeRangeRef.current = timeRange;
  }, [timeRange]);
  const prevTimeRange = prevTimeRangeRef.current;

  if (!data && !isLoading) return null;

  const {
    results = [],
    total_pages: totalPages = 1,
    current_page: pageNum = 1,
    available_filters: filters = [],
    total_items: totalItems = 0
  } = data || {};

  const tableConfig = tableConfigs[metricType];
  if (!tableConfig) return null;

  const handleReferenceClick = (item) => {
    setClickedSource(item);
    setIsUrlSidebarOpen(true);
  };

  const handleSearch = (e) => {
    if (e.key === "Enter") {
      onSearch(searchTerm);
    }
  };

  const handleSort = (column) => {
    if (column.sortable) {
      const newSortOrder = sortOrder === "desc" ? "asc" : "desc";
      onPageChange(1);
      onSortChange(newSortOrder);
    }
  };

  const formatSelectedTimeRange = (timeRange) => {
    if (!timeRange) return "";

    const startDate = new Date(timeRange.startTime);
    const endDate = timeRange.endTime ? new Date(timeRange.endTime) : null;

    if (interval === "today" || interval === "yesterday") {
      // For hourly data, show the hour
      return startDate.toLocaleString([], {
        hour: "numeric",
        minute: "2-digit",
        hour12: true
      });
    } else if (interval === "7d" || interval === "30d") {
      // For daily data, show only the day
      return startDate.toLocaleString([], {
        month: "short",
        day: "numeric"
      });
    } else {
      // For larger intervals, show date range without hours
      return `${startDate.toLocaleString([], {
        month: "short",
        day: "numeric"
      })} - ${endDate.toLocaleString([], {
        month: "short",
        day: "numeric"
      })}`;
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="flex flex-row items-center justify-between sm:justify-start gap-2">
              <div className="flex items-center gap-2">
                <Select
                  value={currentFilter}
                  onValueChange={onFilterChange}
                  disabled={isLoading || !filters.length}>
                  <SelectTrigger className="max-w-[280px] w-fit h-8 px-3 flex justify-start items-center gap-2 rounded-[11000px] border-[#E2E2E2] bg-white">
                    <div className="flex items-start gap-1 text-xs">
                      <span className="text-[#6D6D6D]">Sources by:</span>
                      <SelectValue
                        placeholder="All"
                        className="font-medium text-[#191919]"
                      />
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 20 20"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg">
                        <path
                          fillRule="evenodd"
                          clipRule="evenodd"
                          d="M3.69198 7.09327C3.91662 6.83119 4.31118 6.80084 4.57326 7.02548L9.99985 11.6768L15.4264 7.02548C15.6885 6.80084 16.0831 6.83119 16.3077 7.09327C16.5324 7.35535 16.502 7.74991 16.2399 7.97455L10.4066 12.9745C10.1725 13.1752 9.82716 13.1752 9.5931 12.9745L3.75977 7.97455C3.49769 7.74991 3.46734 7.35535 3.69198 7.09327Z"
                          fill="#6D6D6D"
                        />
                      </svg>
                    </div>
                  </SelectTrigger>
                  <SelectContent>
                    {filters.map((filter) => (
                      <SelectItem key={filter.label} value={filter.value}>
                        {filter.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {timeRange && (
                  <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-[#E2E2E2]">
                    <span className="text-xs text-blue-700">
                      {formatSelectedTimeRange(timeRange)}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-5 w-5 p-0 hover:bg-gray-100 rounded-full"
                      onClick={() => onTimeRangeChange(null)}>
                      <X className="h-3 w-3 text-blue-700" />
                    </Button>
                  </div>
                )}
              </div>

              <div className="text-xs text-[#6D6D6D] sm:hidden">
                Total items: {totalItems}
              </div>
            </div>

            <div className="hidden sm:block text-xs text-[#6D6D6D]">
              Total items: {totalItems}
            </div>
          </div>

          <div className="relative hidden sm:block">
            <Input
              className="w-[250px] h-[32px] px-3 py-[14px] pl-9 rounded-[8px] border border-[#E2E2E2] bg-white"
              placeholder="Search..."
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={handleSearch}
              disabled={isLoading}
            />
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          </div>
        </div>

        {/* Search bar for mobile */}
        <div className="relative sm:hidden">
          <Input
            className="w-full h-[32px] px-3 py-[14px] pl-9 rounded-[8px] border border-[#E2E2E2] bg-white sm:text-xs text-[16px]"
            placeholder="Search..."
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={handleSearch}
            disabled={isLoading}
          />
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        </div>
      </div>

      <div className="rounded-xl bg-background pt-2">
        <DataTable
          columns={tableConfig.columns}
          data={results}
          isLoading={isLoading}
          renderActions={{
            onReferenceClick: handleReferenceClick,
            renderCellWithTooltip: renderCellWithTooltip
          }}
          onSort={handleSort}
          sortOrder={sortOrder}
        />
        <TablePagination
          currentPage={pageNum}
          totalPages={totalPages}
          onPageChange={onPageChange}
          isLoading={isLoading}
        />
      </div>

      {isUrlSidebarOpen && clickedSource && (
        <QuestionsList
          url={clickedSource.link}
          guruType={guruType}
          interval={interval}
          onClose={() => setIsUrlSidebarOpen(false)}
        />
      )}
    </div>
  );
}
