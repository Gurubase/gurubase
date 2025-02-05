"use client";
import {
  ChevronLeft,
  ChevronRight,
  MoreHorizontal,
  ExternalLink,
  Link,
  X
} from "lucide-react";
import { SolarFileTextBold, SolarVideoLibraryBold } from "@/components/Icons";
import { Icon } from "@iconify/react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { METRIC_TYPES } from "@/services/analyticsService";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useState, useEffect } from "react";
import { useDataSourceQuestions } from "@/hooks/useAnalytics";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { cn } from "@/lib/utils";
import * as React from "react";
import { DataTable } from "@/components/ui/data-table";
import { TablePagination } from "@/components/ui/table-pagination";
import { tableConfigs } from "@/config/tableConfigs";
import { QuestionsList } from "./QuestionsList";

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
  interval
}) {
  const [isUrlSidebarOpen, setIsUrlSidebarOpen] = useState(false);
  const [clickedSource, setClickedSource] = useState(null);

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

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Select
          defaultValue={currentFilter}
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
        <div className="text-xs text-[#6D6D6D]">Total items: {totalItems}</div>
      </div>

      <div className="rounded-xl bg-background pt-2">
        <DataTable
          columns={tableConfig.columns}
          data={results}
          isLoading={isLoading}
          renderActions={{ onReferenceClick: handleReferenceClick }}
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
