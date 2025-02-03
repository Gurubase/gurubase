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

const sampleData = Array(12)
  .fill({
    date: "27.01.2024, 7:00 AM",
    type: "Bug",
    question: "I want to create pods with custom ordinal index in stateful set"
  })
  .map((item) => ({
    ...item
  }));

export default function TableComponent() {
  const currentPage = 3;
  const totalPages = 12;

  const getPaginationGroup = (current, total) => {
    if (current <= 2) return [1, 2, 3];
    if (current >= total - 1) return [total - 2, total - 1, total];
    return [current - 1, current, current + 1];
  };

  const paginationGroup = getPaginationGroup(currentPage, totalPages);

  return (
    <div className="space-y-2">
      <div className="flex items-center">
        <Select defaultValue="all">
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
            <SelectItem value="long-option">
              A Much Longer Option Text
            </SelectItem>
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
              <TableHead className="w-[50px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sampleData.map((item, i) => (
              <TableRow
                key={i}
                className="hover:bg-transparent border-b border-[#E2E2E2]">
                <TableCell className="font-inter text-xs font-medium">
                  {item.date}
                </TableCell>
                <TableCell className="font-inter text-xs font-medium">
                  {item.type}
                </TableCell>
                <TableCell className="font-inter text-xs font-medium">
                  {item.question}
                </TableCell>
                {/* <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreHorizontal className="h-4 w-4" />
                        <span className="sr-only">More actions</span>
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-[140px]">
                      <DropdownMenuItem className="gap-2">
                        <Copy className="h-4 w-4" />
                        <span>Copy</span>
                      </DropdownMenuItem>
                      <DropdownMenuItem className="gap-2">
                        <Pencil className="h-4 w-4" />
                        <span>Edit</span>
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell> */}
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <div className="flex items-center justify-end gap-1 border-t border-[#E2E2E2] p-2">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 px-0 hover:bg-[#F6F6F6] hover:rounded-lg">
            <div className="flex items-center px-2">
              <ChevronLeft className="h-4 w-4 mr-1" />
              <span className="px-[10px]">Previous</span>
            </div>
          </Button>
          <div className="flex items-center gap-2">
            {currentPage > 2 && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 hover:bg-[#F6F6F6] hover:rounded-lg">
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
                className={`h-8 w-8 hover:bg-[#F6F6F6] hover:rounded-lg ${
                  number === currentPage
                    ? "border border-[#E2E2E2] rounded-lg"
                    : ""
                }`}>
                {number}
              </Button>
            ))}
            {currentPage < totalPages - 2 && (
              <>
                <span>
                  <MoreHorizontal className="h-4 w-4" />
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 hover:bg-[#F6F6F6] hover:rounded-lg">
                  {totalPages}
                </Button>
              </>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 px-0 hover:bg-[#F6F6F6] hover:rounded-lg">
            <div className="flex items-center px-2">
              <span className="px-[10px]">Next</span>
              <ChevronRight className="h-4 w-4 ml-1" />
            </div>
          </Button>
        </div>
      </div>
    </div>
  );
}
