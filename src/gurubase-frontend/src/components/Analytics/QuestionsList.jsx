"use client";

import { useState } from "react";
import { X, ExternalLink } from "lucide-react";
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

const questionsTableColumns = [
  {
    key: "date",
    header: "Date",
    width: "w-[120px] md:w-[200px]"
  },
  {
    key: "source",
    header: "Source",
    width: "w-[140px]",
    hideOnMobile: false
  },
  {
    key: "title",
    header: "Question",
    render: (item) => (
      <a
        href={item.link}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-2 group hover:text-blue-600">
        <div className="truncate">{item.title}</div>
        <ExternalLink className="h-3 w-3 flex-shrink-0 opacity-100" />
      </a>
    )
  }
];

export function QuestionsList({ url, guruType, onClose, interval }) {
  const [filterType, setFilterType] = useState("all");
  const {
    data: questions,
    loading,
    page,
    setPage
  } = useDataSourceQuestions(guruType, url, filterType, interval);

  const isMobile = useMediaQuery("(max-width: 915px)");

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
            {/* Filter Section */}
            <div className="flex items-center justify-between space-x-4 mb-3">
              {
                <Select
                  defaultValue={"all"}
                  onValueChange={setFilterType}
                  disabled={!questions?.available_filters?.length}>
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
                    {questions?.available_filters?.map((filter) => (
                      <SelectItem key={filter.label} value={filter.value}>
                        {filter.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              }
              <div className="text-xs text-[#6D6D6D]">
                Total items: {questions?.total_items || 0}
              </div>
            </div>

            <DataTable
              columns={questionsTableColumns}
              data={questions?.results}
              isLoading={loading}
            />
            <TablePagination
              currentPage={page}
              totalPages={questions?.total_pages || 1}
              onPageChange={setPage}
              isLoading={loading}
            />
          </div>
        </div>
      </StyledDialogContent>
    </DialogPrimitive.Root>
  );
}
