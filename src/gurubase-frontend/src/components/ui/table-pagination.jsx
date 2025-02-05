"use client";

import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react";

export const getPaginationGroup = (current, total) => {
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

export function TablePagination({
  currentPage,
  totalPages,
  onPageChange,
  isLoading
}) {
  if (totalPages <= 1) return null;

  const paginationGroup = getPaginationGroup(currentPage, totalPages);

  return (
    <div className="flex items-center justify-end gap-1 p-2">
      <Button
        variant="ghost"
        size="sm"
        className="h-8 md:h-8 h-7 px-0 hover:bg-[#F6F6F6] hover:rounded-lg"
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1 || isLoading}>
        <div className="flex items-center px-2">
          <ChevronLeft className="h-4 w-4 mr-1" />
        </div>
      </Button>
      <div className="flex items-center gap-2 md:gap-2 gap-1">
        {currentPage > 2 && totalPages > 3 && (
          <>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 md:h-8 h-7 w-8 md:w-8 w-6 hover:bg-[#F6F6F6] hover:rounded-lg"
              onClick={() => onPageChange(1)}
              disabled={isLoading}>
              1
            </Button>
            {currentPage > 3 && (
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
              number === currentPage ? "border border-[#E2E2E2] rounded-lg" : ""
            }`}
            onClick={() => onPageChange(number)}
            disabled={isLoading}>
            {number}
          </Button>
        ))}
        {currentPage < totalPages - 1 && totalPages > 3 && (
          <>
            {currentPage < totalPages - 2 && (
              <span>
                <MoreHorizontal className="h-4 w-4" />
              </span>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="h-8 md:h-8 h-7 w-8 md:w-8 w-6 hover:bg-[#F6F6F6] hover:rounded-lg"
              onClick={() => onPageChange(totalPages)}
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
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages || isLoading}>
        <div className="flex items-center px-2">
          <ChevronRight className="h-4 w-4 ml-1" />
        </div>
      </Button>
    </div>
  );
}
