"use client";

import { useState, useEffect } from "react";
import { X, ExternalLink, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { TablePagination } from "@/components/ui/table-pagination";
import { useDataSourceQuestions } from "@/hooks/useAnalytics";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { cn } from "@/lib/utils";
import * as React from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { tableConfigs } from "@/config/tableConfigs";
import { METRIC_TYPES } from "@/services/analyticsService";
import { renderCellWithTooltip } from "@/components/ui/data-table";

const StyledDialogContent = React.forwardRef(
  ({ children, isMobile, ...props }, ref) => (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-[51] bg-black/80 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
      <DialogPrimitive.Content
        ref={ref}
        className={cn(
          "fixed z-[52] bg-white shadow-lg transition ease-in-out data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:duration-300 data-[state=open]:duration-500",
          isMobile
            ? "inset-x-0 bottom-0 h-[90vh] w-full rounded-t-[20px] data-[state=closed]:slide-out-to-bottom data-[state=open]:slide-in-from-bottom border border-gray-200"
            : "right-0 top-0 h-full w-full max-w-5xl data-[state=closed]:slide-out-to-right data-[state=open]:slide-in-from-right"
        )}
        {...props}>
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
);

StyledDialogContent.displayName = "StyledDialogContent";

const questionsTableColumns = tableConfigs[METRIC_TYPES.QUESTIONS_LIST].columns;

export function QuestionsList({ url, guruType, onClose, interval }) {
  const [filterType, setFilterType] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [sortOrder, setSortOrder] = useState("desc");

  const {
    data: questions,
    loading,
    page,
    setPage,
    setSortOrder: setQuestionsSortOrder
  } = useDataSourceQuestions(
    guruType,
    url,
    filterType,
    interval,
    1,
    searchQuery,
    sortOrder
  );

  const isMobile = useMediaQuery("(max-width: 915px)");

  const handleSearch = (e) => {
    if (e.key === "Enter") {
      if (searchTerm !== searchQuery) {
        setSearchQuery(searchTerm);
        setPage(1);
      }
    }
  };

  const handleSort = (column) => {
    if (column.sortable) {
      const newSortOrder = sortOrder === "desc" ? "asc" : "desc";
      setSortOrder(newSortOrder);
      setQuestionsSortOrder(newSortOrder);
      setPage(1);
    }
  };

  // Reset filters when interval changes
  useEffect(() => {
    setFilterType("all");
    setPage(1);
    setSearchQuery("");
    setSearchTerm("");
    setSortOrder("desc");
  }, [interval]);

  const handleFilterChange = (newFilter) => {
    setFilterType(newFilter);
    setPage(1);
  };

  return (
    <DialogPrimitive.Root open={true} onOpenChange={onClose}>
      <StyledDialogContent isMobile={isMobile}>
        <div className="flex flex-col h-full overflow-hidden">
          <div className="guru-sm:hidden guru-md:flex guru-lg:flex px-5 py-6 items-center gap-5 border-b border-gray-85 bg-gray-25 sticky top-0 z-10">
            <div className="flex-grow">
              <h2 className="text-h5 font-semibold mb-1">
                Questions referencing this source
              </h2>
            </div>
            <DialogPrimitive.Close asChild>
              <Button size="icon" variant="ghost">
                <X className="h-6 w-6 text-gray-400" />
                <span className="sr-only">Close</span>
              </Button>
            </DialogPrimitive.Close>
          </div>

          <div className="flex-2 overflow-auto py-4 px-8">
            <div className="flex flex-col gap-4">
              {/* Filter and Total Items Row */}
              <div className="flex items-center justify-between">
                <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                  <Select
                    value={filterType}
                    onValueChange={handleFilterChange}
                    disabled={loading || !questions?.available_filters?.length}
                    portalRoot={document.querySelector('[role="dialog"]')}>
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
                    <SelectContent className="z-[60]">
                      {questions?.available_filters?.map((filter) => (
                        <SelectItem key={filter.label} value={filter.value}>
                          {filter.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <div className="relative hidden sm:block">
                    <Input
                      className="w-[250px] h-[32px] px-3 py-[14px] pl-9 rounded-[8px] border border-[#E2E2E2] bg-white"
                      placeholder="Search..."
                      type="text"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      onKeyDown={handleSearch}
                      disabled={loading}
                    />
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  </div>
                </div>

                <div className="text-xs text-[#6D6D6D]">
                  Total items: {questions?.total_items || 0}
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
                  disabled={loading}
                />
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              </div>
            </div>

            <div className="mt-4">
              <DataTable
                columns={questionsTableColumns}
                data={questions?.results}
                isLoading={loading}
                onSort={handleSort}
                sortOrder={sortOrder}
                renderActions={{
                  renderCellWithTooltip: renderCellWithTooltip
                }}
              />
              <TablePagination
                currentPage={page}
                totalPages={questions?.total_pages || 1}
                onPageChange={setPage}
                isLoading={loading}
              />
            </div>
          </div>
        </div>
      </StyledDialogContent>
    </DialogPrimitive.Root>
  );
}
