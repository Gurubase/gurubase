"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "lucide-react";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { formatDate } from "@/utils/dateUtils";
import { cn } from "@/lib/utils";
import { ChevronUp, ChevronDown } from "lucide-react";

export function DataTable({
  columns,
  data,
  isLoading,
  renderActions,
  emptyState = {
    icon: Link,
    title: "No data found",
    description: "No data is available for the selected filters."
  },
  onSort,
  sortOrder
}) {
  const isMobile = useMediaQuery("(max-width: 915px)");

  return (
    <div className={isMobile ? "overflow-x-auto" : "overflow-hidden"}>
      <Table>
        <TableHeader className="bg-[#FAFAFA]">
          <TableRow className="border-b border-[#E2E2E2]">
            {columns.map((column) => (
              <TableHead
                key={column.key}
                className={cn(
                  "text-ellipsis overflow-hidden text-[#6D6D6D] font-inter text-xs font-regular px-4 py-2",
                  column.width,
                  column.sortable && "cursor-pointer hover:bg-gray-50",
                  "transition-colors"
                )}
                onClick={() => column.sortable && onSort?.(column)}>
                <div className="flex items-center gap-2">
                  {column.header}
                  {column.sortable && (
                    <div className="flex items-center">
                      {sortOrder === "asc" ? (
                        <ChevronUp className="h-3 w-3 text-primary" />
                      ) : (
                        <ChevronDown className="h-3 w-3 text-primary" />
                      )}
                    </div>
                  )}
                </div>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {!data?.length && !isLoading ? (
            <TableRow>
              <TableCell
                colSpan={columns.length}
                className="h-[300px] text-center">
                <div className="flex flex-col items-center justify-center py-8">
                  <div className="text-gray-400 mb-2">
                    <emptyState.icon className="h-12 w-12" />
                  </div>
                  <h3 className="text-base font-regular text-gray-900 mb-1">
                    {emptyState.title}
                  </h3>
                  <p className="text-sm text-gray-500">
                    {emptyState.description}
                  </p>
                </div>
              </TableCell>
            </TableRow>
          ) : isLoading ? (
            Array.from({ length: 10 }).map((_, i) => (
              <TableRow
                key={i}
                className="hover:bg-transparent border-b border-[#E2E2E2]">
                {columns.map(
                  (column) =>
                    (!column.hideOnMobile || !isMobile) && (
                      <TableCell
                        key={column.key}
                        className="font-inter text-xs font-regular px-4 py-2">
                        <Skeleton
                          className={`h-4 ${
                            column.width ? "w-[80px]" : "w-full max-w-[400px]"
                          }`}
                        />
                      </TableCell>
                    )
                )}
              </TableRow>
            ))
          ) : (
            data.map((item, idx) => (
              <TableRow
                key={idx}
                className="hover:bg-transparent border-b border-[#E2E2E2]">
                {columns.map(
                  (column) =>
                    (!column.hideOnMobile || !isMobile) && (
                      <TableCell
                        key={column.key}
                        style={{ minWidth: column.minWidth }}
                        className={`font-inter text-xs font-regular px-4 py-2 ${column.width || ""}`}>
                        <div className="overflow-hidden">
                          {column.render
                            ? column.render(item, renderActions)
                            : column.key === "date"
                              ? formatDate(item[column.key])
                              : item[column.key]}
                        </div>
                      </TableCell>
                    )
                )}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
