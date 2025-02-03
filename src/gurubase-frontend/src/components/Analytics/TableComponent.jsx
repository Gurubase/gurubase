"use client";
import {
  ChevronLeft,
  ChevronRight,
  Copy,
  MoreHorizontal,
  Pencil
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
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

export default function TableComponent({
  data,
  onFilterChange,
  onPageChange,
  currentFilter = "all",
  currentPage = 1
}) {
  if (!data) return null;

  const { results, total_pages: totalPages, current_page: pageNum } = data;

  const getPaginationGroup = (current, total) => {
    if (current <= 2) return [1, 2, 3];
    if (current >= total - 1) return [total - 2, total - 1, total];
    return [current - 1, current, current + 1];
  };

  const paginationGroup = getPaginationGroup(pageNum, totalPages);

  const handleFilterChange = (value) => {
    onFilterChange?.(value);
  };

  const handlePageChange = (page) => {
    onPageChange?.(page);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center">
        <Select defaultValue={currentFilter} onValueChange={handleFilterChange}>
          <SelectTrigger className="max-w-[280px] w-fit h-8 px-3 flex justify-start items-center gap-2 rounded-[11000px] border-[#E2E2E2] bg-white">
            <div className="flex items-start gap-1 text-xs">
              <span className="text-[#6D6D6D]">Sources by:</span>
              <SelectValue placeholder="All" className="font-medium" />
            </div>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="bugs">Bugs</SelectItem>
            <SelectItem value="features">Features</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-xl bg-background pt-2">
        <Table>
          <TableHeader className="bg-[#FAFAFA]">
            <TableRow className="border-b border-[#E2E2E2]">
              <TableHead className="w-[200px] text-ellipsis overflow-hidden text-[#6D6D6D] font-inter text-xs font-medium">
                Date
              </TableHead>
              <TableHead className="w-[100px] text-ellipsis overflow-hidden text-[#6D6D6D] font-inter text-xs font-medium">
                Type
              </TableHead>
              <TableHead className="text-ellipsis overflow-hidden text-[#6D6D6D] font-inter text-xs font-medium">
                Question
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {results.map((item, i) => (
              <TableRow
                key={i}
                className="hover:bg-transparent border-b border-[#E2E2E2]">
                <TableCell className="font-inter text-xs font-medium">
                  {item.date}
                </TableCell>
                <TableCell className="font-inter text-xs font-medium">
                  {item.type}
                </TableCell>
                <TableCell className="font-inter text-xs font-medium max-w-0">
                  <div className="truncate">{item.question}</div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <div className="flex items-center justify-end gap-1 border-t border-[#E2E2E2] p-2">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 md:h-8 h-7 px-0 hover:bg-[#F6F6F6] hover:rounded-lg"
            onClick={() => handlePageChange(pageNum - 1)}
            disabled={pageNum === 1}>
            <div className="flex items-center px-2">
              <ChevronLeft className="h-4 w-4 mr-1" />
            </div>
          </Button>
          <div className="flex items-center gap-2 md:gap-2 gap-1">
            {pageNum > 2 && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 md:h-8 h-7 w-8 md:w-8 w-6 hover:bg-[#F6F6F6] hover:rounded-lg"
                  onClick={() => handlePageChange(1)}>
                  1
                </Button>
                <span>
                  <MoreHorizontal className="h-4 w-4" />
                </span>
              </>
            )}
            {paginationGroup.map((number) => (
              <Button
                key={number}
                variant="ghost"
                size="sm"
                className={`h-8 md:h-8 h-7 w-8 md:w-8 w-6 hover:bg-[#F6F6F6] hover:rounded-lg ${
                  number === pageNum ? "border border-[#E2E2E2] rounded-lg" : ""
                }`}
                onClick={() => handlePageChange(number)}>
                {number}
              </Button>
            ))}
            {pageNum < totalPages - 2 && (
              <>
                <span>
                  <MoreHorizontal className="h-4 w-4" />
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 md:h-8 h-7 w-8 md:w-8 w-6 hover:bg-[#F6F6F6] hover:rounded-lg"
                  onClick={() => handlePageChange(totalPages)}>
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
            disabled={pageNum === totalPages}>
            <div className="flex items-center px-2">
              <ChevronRight className="h-4 w-4 ml-1" />
            </div>
          </Button>
        </div>
      </div>
    </div>
  );
}
