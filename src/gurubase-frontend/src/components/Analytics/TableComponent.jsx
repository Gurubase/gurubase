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
import { Badge } from "@/components/ui/badge";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useState, useEffect } from "react";
import { useDataSourceQuestions } from "@/hooks/useAnalytics";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { cn } from "@/lib/utils";
import * as React from "react";

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

const QuestionsList = ({ url, guruType, onClose, interval }) => {
  const [filterType, setFilterType] = useState("all");
  const {
    data: questions,
    loading,
    page,
    setPage
  } = useDataSourceQuestions(guruType, url, filterType, interval);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  const isMobile = useMediaQuery("(max-width: 915px)");

  const getPaginationGroup = (current, total) => {
    if (total <= 3) {
      return Array.from({ length: total }, (_, i) => i + 1);
    }

    if (current <= 2) {
      return [1, 2, 3];
    }
    if (current >= total - 1) {
      return [total - 2, total - 1, total];
    }
    return [current - 1, current, current + 1];
  };

  const handleFilterChange = (value) => {
    setFilterType(value);
  };

  console.log("QuestionsList", questions);
  console.log("Available filters", questions?.available_filters);

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
              {questions?.available_filters?.length > 0 && (
                <Select
                  defaultValue={"all"}
                  onValueChange={handleFilterChange}
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
                          fill-rule="evenodd"
                          clip-rule="evenodd"
                          d="M3.69198 7.09327C3.91662 6.83119 4.31118 6.80084 4.57326 7.02548L9.99985 11.6768L15.4264 7.02548C15.6885 6.80084 16.0831 6.83119 16.3077 7.09327C16.5324 7.35535 16.502 7.74991 16.2399 7.97455L10.4066 12.9745C10.1725 13.1752 9.82716 13.1752 9.5931 12.9745L3.75977 7.97455C3.49769 7.74991 3.46734 7.35535 3.69198 7.09327Z"
                          fill="#6D6D6D"
                        />
                      </svg>
                    </div>
                  </SelectTrigger>
                  <SelectContent className="z-[100]">
                    {questions?.available_filters?.map((filter) => (
                      <SelectItem key={filter.label} value={filter.value}>
                        {filter.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <div className="text-xs text-[#6D6D6D]">
                Total items: {questions?.total_items || 0}
              </div>
            </div>

            <Table>
              <TableHeader className="bg-[#FAFAFA]">
                <TableRow className="border-b border-[#E2E2E2]">
                  <TableHead className="w-[200px] text-ellipsis overflow-hidden text-[#6D6D6D] font-inter text-xs font-regular px-4 py-2">
                    Date
                  </TableHead>
                  <TableHead className="w-[140px] text-ellipsis overflow-hidden text-[#6D6D6D] font-inter text-xs font-regular px-4 py-2">
                    Source
                  </TableHead>
                  <TableHead className="text-ellipsis overflow-hidden text-[#6D6D6D] font-inter text-xs font-regular px-4 py-2">
                    Question
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  [...Array(10)].map((_, i) => (
                    <TableRow
                      key={i}
                      className="hover:bg-transparent border-b border-[#E2E2E2]">
                      <TableCell className="font-inter text-xs font-regular px-4 py-2">
                        <Skeleton className="h-4 w-[120px]" />
                      </TableCell>
                      <TableCell className="font-inter text-xs font-regular px-4 py-2">
                        <Skeleton className="h-4 w-full" />
                      </TableCell>
                      <TableCell className="font-inter text-xs font-regular px-4 py-2">
                        <Skeleton className="h-4 w-[80px]" />
                      </TableCell>
                    </TableRow>
                  ))
                ) : !questions?.results?.length ? (
                  <TableRow>
                    <TableCell colSpan={3}>
                      <div className="flex flex-col items-center justify-center py-8 text-center">
                        <div className="text-gray-400 mb-2">
                          <Link className="h-12 w-12" />
                        </div>
                        <h3 className="text-base font-regular text-gray-900 mb-1">
                          No questions found
                        </h3>
                        <p className="text-sm text-gray-500">
                          No data is available for the selected filters.
                        </p>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  questions.results.map((question, idx) => (
                    <TableRow
                      key={idx}
                      className="hover:bg-gray-50 border-b border-[#E2E2E2]">
                      <TableCell className="font-inter text-xs font-regular px-4 py-2">
                        {formatDate(question.date)}
                      </TableCell>
                      <TableCell className="font-inter text-xs font-regular px-4 py-2">
                        <div className="flex items-center gap-2">
                          {(() => {
                            switch (question.source?.toLowerCase()) {
                              case "pdf":
                                return (
                                  <SolarFileTextBold className="h-4 w-4" />
                                );
                              case "youtube":
                                return (
                                  <SolarVideoLibraryBold className="h-4 w-4" />
                                );
                              case "website":
                                return <Link className="h-4 w-4" />;
                              case "codebase":
                                return (
                                  <Icon
                                    icon="simple-icons:github"
                                    className="h-4 w-4"
                                  />
                                );
                              default:
                                return null;
                            }
                          })()}
                          {question.source}
                        </div>
                      </TableCell>
                      <TableCell className="font-inter text-xs font-regular px-4 py-2">
                        <a
                          href={question.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 group hover:text-blue-600">
                          <div className="truncate">{question.title}</div>
                          <ExternalLink className="h-3 w-3 flex-shrink-0 opacity-100" />
                        </a>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {questions?.total_pages > 1 && (
            <div className="flex items-center justify-end gap-1 p-2">
              <Button
                variant="ghost"
                size="sm"
                className="h-8 md:h-8 h-7 px-0 hover:bg-[#F6F6F6] hover:rounded-lg"
                onClick={() => setPage(page - 1)}
                disabled={page === 1}>
                <div className="flex items-center px-2">
                  <ChevronLeft className="h-4 w-4 mr-1" />
                </div>
              </Button>
              <div className="flex items-center gap-2 md:gap-2 gap-1">
                {page > 2 && questions.total_pages > 3 && (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 md:h-8 h-7 w-8 md:w-8 w-6 hover:bg-[#F6F6F6] hover:rounded-lg"
                      onClick={() => setPage(1)}
                      disabled={loading}>
                      1
                    </Button>
                    {page > 3 && (
                      <span>
                        <MoreHorizontal className="h-4 w-4" />
                      </span>
                    )}
                  </>
                )}
                {getPaginationGroup(page, questions.total_pages).map(
                  (number) => (
                    <Button
                      key={number}
                      variant="ghost"
                      size="sm"
                      className={`h-8 md:h-8 h-7 w-8 md:w-8 w-6 hover:bg-[#F6F6F6] hover:rounded-lg ${
                        number === page
                          ? "border border-[#E2E2E2] rounded-lg"
                          : ""
                      }`}
                      onClick={() => setPage(number)}
                      disabled={loading}>
                      {number}
                    </Button>
                  )
                )}
                {page < questions.total_pages - 1 &&
                  questions.total_pages > 3 && (
                    <>
                      {page < questions.total_pages - 2 && (
                        <span>
                          <MoreHorizontal className="h-4 w-4" />
                        </span>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 md:h-8 h-7 w-8 md:w-8 w-6 hover:bg-[#F6F6F6] hover:rounded-lg"
                        onClick={() => setPage(questions.total_pages)}
                        disabled={loading}>
                        {questions.total_pages}
                      </Button>
                    </>
                  )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 md:h-8 h-7 px-0 hover:bg-[#F6F6F6] hover:rounded-lg"
                onClick={() => setPage(page + 1)}
                disabled={page === questions.total_pages || loading}>
                <div className="flex items-center px-2">
                  <ChevronRight className="h-4 w-4 ml-1" />
                </div>
              </Button>
            </div>
          )}
        </div>
      </StyledDialogContent>
    </DialogPrimitive.Root>
  );
};

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
  const [clickedSource, setClickedSource] = useState([]);
  const [selectedUrls, setSelectedUrls] = useState([]);
  const [urlEditorContent, setUrlEditorContent] = useState("");
  const isMobile = useMediaQuery("(max-width: 915px)");

  if (!data && !isLoading) return null;

  const {
    results = [],
    total_pages: totalPages = 1,
    current_page: pageNum = 1,
    available_filters: filters = [],
    total_items: totalItems = 0
  } = data || {};

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  const getPaginationGroup = (current, total) => {
    if (total <= 3) {
      // If total pages is 3 or less, show all pages
      return Array.from({ length: total }, (_, i) => i + 1);
    }

    if (current <= 2) {
      // If we're at the start, show first 3 pages
      return [1, 2, 3];
    }
    if (current >= total - 1) {
      // If we're at the end, show last 3 pages
      return [total - 2, total - 1, total];
    }
    // Otherwise show current page and neighbors
    return [current - 1, current, current + 1];
  };

  const paginationGroup = getPaginationGroup(pageNum, totalPages);

  const handleFilterChange = (value) => {
    onFilterChange?.(value);
  };

  const handlePageChange = (page) => {
    onPageChange?.(page);
  };

  const handleReferenceClick = (item) => {
    setClickedSource([
      {
        id: item.id,
        link: item.link,
        type: "website",
        status: "SUCCESS"
      }
    ]);
    setIsUrlSidebarOpen(true);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Select
          defaultValue={currentFilter}
          onValueChange={handleFilterChange}
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
                  fill-rule="evenodd"
                  clip-rule="evenodd"
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
        <Table>
          <TableHeader className="bg-[#FAFAFA]">
            <TableRow className="border-b border-[#E2E2E2]">
              <TableHead className="w-[200px] text-ellipsis overflow-hidden text-[#6D6D6D] font-inter text-xs font-regular px-4 py-2">
                Date
              </TableHead>
              <TableHead className="w-[140px] text-ellipsis overflow-hidden text-[#6D6D6D] font-inter text-xs font-regular px-4 py-2">
                {metricType !== METRIC_TYPES.REFERENCED_SOURCES
                  ? "Source"
                  : "Type"}
              </TableHead>
              <TableHead className="text-ellipsis overflow-hidden text-[#6D6D6D] font-inter text-xs font-regular px-4 py-2">
                {metricType !== METRIC_TYPES.REFERENCED_SOURCES
                  ? "Question"
                  : "Source"}
              </TableHead>
              {metricType === METRIC_TYPES.REFERENCED_SOURCES && (
                <TableHead className="w-[100px] text-ellipsis overflow-hidden text-[#6D6D6D] font-inter text-xs font-regular px-4 py-2">
                  Referenced
                </TableHead>
              )}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              [...Array(10)].map((_, i) => (
                <TableRow
                  key={i}
                  className="hover:bg-transparent border-b border-[#E2E2E2]">
                  <TableCell className="font-inter text-xs font-regular px-4 py-2">
                    <div className="flex items-center gap-2">
                      <Skeleton className="h-4 w-full max-w-[400px]" />
                      <div className="w-3 flex-shrink-0" />
                    </div>
                  </TableCell>
                  <TableCell className="font-inter text-xs font-regular px-4 py-2">
                    <Skeleton className="h-4 w-16" />
                  </TableCell>
                  <TableCell className="font-inter text-xs font-regular px-4 py-2">
                    <Skeleton className="h-4 w-full max-w-[400px]" />
                  </TableCell>
                </TableRow>
              ))
            ) : !results.length ? (
              <TableRow>
                <TableCell
                  colSpan={
                    metricType === METRIC_TYPES.REFERENCED_SOURCES ? 4 : 3
                  }>
                  <div className="flex flex-col items-center justify-center py-8 text-center">
                    <div className="text-gray-400 mb-2">
                      <Link className="h-12 w-12" />
                    </div>
                    <h3 className="text-base font-regular text-gray-900 mb-1">
                      No data found
                    </h3>
                    <p className="text-sm text-gray-500">
                      No data is available for the selected filters.
                    </p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              results.map((item, i) => (
                <TableRow
                  key={i}
                  className="hover:bg-transparent border-b border-[#E2E2E2]">
                  <TableCell className="font-inter text-xs font-regular px-4 py-2">
                    {formatDate(item.date)}
                  </TableCell>
                  <TableCell className="font-inter text-xs font-regular px-4 py-2">
                    <div className="flex items-center gap-2">
                      {(() => {
                        switch (item.type?.toLowerCase()) {
                          case "pdf":
                            return <SolarFileTextBold className="h-4 w-4" />;
                          case "youtube":
                            return (
                              <SolarVideoLibraryBold className="h-4 w-4" />
                            );
                          case "website":
                            return <Link className="h-4 w-4" />;
                          case "codebase":
                            return (
                              <Icon
                                icon="simple-icons:github"
                                className="h-4 w-4"
                              />
                            );
                          default:
                            return null;
                        }
                      })()}
                      {item.type}
                    </div>
                  </TableCell>
                  <TableCell className="font-inter text-xs font-regular px-4 py-2 max-w-0">
                    {metricType === METRIC_TYPES.QUESTIONS ||
                    (metricType === METRIC_TYPES.REFERENCED_SOURCES &&
                      item.link) ? (
                      <a
                        href={item.link || "#"}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={`flex items-center gap-2 group ${item.link ? "hover:text-blue-600" : "cursor-default"}`}>
                        <div className="truncate">{item.title}</div>
                        <ExternalLink
                          className={`h-3 w-3 flex-shrink-0 transition-opacity ${
                            item.link ? "opacity-100" : "opacity-0"
                          }`}
                        />
                      </a>
                    ) : (
                      <div className="truncate">{item.title}</div>
                    )}
                  </TableCell>
                  {metricType === METRIC_TYPES.REFERENCED_SOURCES && (
                    <TableCell className="font-inter text-xs font-regular px-4 py-2 flex items-center justify-center">
                      <Badge
                        iconColor="text-gray-500"
                        text={
                          <div className="flex items-center gap-1">
                            <Link className="h-3 w-3 text-gray-500" />
                            <span>{item.reference_count}</span>
                          </div>
                        }
                        variant="secondary"
                        className="cursor-pointer hover:bg-gray-100"
                        onClick={() => handleReferenceClick(item)}></Badge>
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <div className="flex items-center justify-end gap-1 p-2">
          {totalPages > 0 && (
            <>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 md:h-8 h-7 px-0 hover:bg-[#F6F6F6] hover:rounded-lg"
                onClick={() => handlePageChange(pageNum - 1)}
                disabled={pageNum === 1 || isLoading}>
                <div className="flex items-center px-2">
                  <ChevronLeft className="h-4 w-4 mr-1" />
                </div>
              </Button>
              <div className="flex items-center gap-2 md:gap-2 gap-1">
                {pageNum > 2 && totalPages > 3 && (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 md:h-8 h-7 w-8 md:w-8 w-6 hover:bg-[#F6F6F6] hover:rounded-lg"
                      onClick={() => handlePageChange(1)}
                      disabled={isLoading}>
                      1
                    </Button>
                    {pageNum > 3 && (
                      <span>
                        <MoreHorizontal className="h-4 w-4" />
                      </span>
                    )}
                  </>
                )}
                {paginationGroup.map((number) => (
                  <Button
                    key={number}
                    variant="ghost"
                    size="sm"
                    className={`h-8 md:h-8 h-7 w-8 md:w-8 w-6 hover:bg-[#F6F6F6] hover:rounded-lg ${
                      number === pageNum
                        ? "border border-[#E2E2E2] rounded-lg"
                        : ""
                    }`}
                    onClick={() => handlePageChange(number)}
                    disabled={isLoading}>
                    {number}
                  </Button>
                ))}
                {pageNum < totalPages - 1 && totalPages > 3 && (
                  <>
                    {pageNum < totalPages - 2 && (
                      <span>
                        <MoreHorizontal className="h-4 w-4" />
                      </span>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 md:h-8 h-7 w-8 md:w-8 w-6 hover:bg-[#F6F6F6] hover:rounded-lg"
                      onClick={() => handlePageChange(totalPages)}
                      disabled={isLoading}>
                      {totalPages}
                    </Button>
                  </>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 md:h-8 h-7 px-0 hover:bg-[#F6F6F6] hover:rounded-lg"
                onClick={() => handlePageChange(pageNum + 1)}
                disabled={pageNum === totalPages || isLoading}>
                <div className="flex items-center px-2">
                  <ChevronRight className="h-4 w-4 ml-1" />
                </div>
              </Button>
            </>
          )}
        </div>
      </div>

      {isUrlSidebarOpen && (
        <QuestionsList
          url={clickedSource[0]?.link}
          guruType={guruType}
          interval={interval}
          onClose={() => setIsUrlSidebarOpen(false)}
        />
      )}
    </div>
  );
}
