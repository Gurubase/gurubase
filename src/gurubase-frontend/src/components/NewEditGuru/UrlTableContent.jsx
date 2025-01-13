import { format, parseISO } from "date-fns";
import { AlertTriangle, Check, Copy, Search, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export const UrlTableContent = ({
  clickedSource,
  selectedUrls,
  setSelectedUrls,
  initialActiveTab,
  onDeleteUrls
}) => {
  const successUrls = clickedSource.filter(
    (url) => url.status?.toLowerCase() === "success"
  );
  const notProcessedUrls = clickedSource.filter(
    (url) => url.status === "NOT_PROCESSED"
  );
  const failedUrls = clickedSource.filter(
    (url) => url.status?.toLowerCase() === "fail"
  );

  const [activeTab, setActiveTab] = useState(initialActiveTab);
  const [searchTerm, setSearchTerm] = useState("");
  const [hasCopied, setHasCopied] = useState(false);

  useEffect(() => {
    setActiveTab(initialActiveTab);
  }, [initialActiveTab]);

  // Filter URLs based on search term and active tab
  const displayUrls = useMemo(() => {
    const tabUrls =
      activeTab === "success"
        ? successUrls
        : activeTab === "failed"
          ? failedUrls
          : notProcessedUrls;

    if (!searchTerm) return tabUrls;

    return tabUrls.filter((url) =>
      url.url.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [activeTab, successUrls, failedUrls, notProcessedUrls, searchTerm]);

  const handleDeleteSelected = () => {
    onDeleteUrls(selectedUrls);
    setSelectedUrls([]);
  };

  const handleCopyUrls = async () => {
    const urlsToCopy = displayUrls.map((url) => url.url).join("\n");

    await navigator.clipboard.writeText(urlsToCopy);
    setHasCopied(true);

    // Reset back to copy icon after 2 seconds
    setTimeout(() => {
      setHasCopied(false);
    }, 1000);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Tabs first */}
      <div className="flex space-x-1 border-b">
        {successUrls.length > 0 && (
          <button
            className={cn(
              "px-4 py-2 text-sm font-medium",
              "focus:outline-none",
              activeTab === "success"
                ? "border-b-2 border-success-base text-success-base"
                : "text-gray-500 hover:text-gray-700"
            )}
            onClick={() => setActiveTab("success")}>
            Success ({successUrls.length})
          </button>
        )}
        {notProcessedUrls.length > 0 && (
          <button
            className={cn(
              "px-4 py-2 text-sm font-medium",
              "focus:outline-none",
              activeTab === "not_processed"
                ? "border-b-2 border-warning-base text-warning-base"
                : "text-gray-500 hover:text-gray-700"
            )}
            onClick={() => setActiveTab("not_processed")}>
            Pending ({notProcessedUrls.length})
          </button>
        )}
        {failedUrls.length > 0 && (
          <button
            className={cn(
              "px-4 py-2 text-sm font-medium",
              "focus:outline-none",
              activeTab === "failed"
                ? "border-b-2 border-error-base text-error-base"
                : "text-gray-500 hover:text-gray-700"
            )}
            onClick={() => setActiveTab("failed")}>
            Failed ({failedUrls.length})
          </button>
        )}
      </div>

      {/* Search and actions row */}
      <div className="flex items-center justify-between gap-2 my-4">
        {/* Search input */}
        <div className="relative">
          <Input
            className="w-[250px] h-[36px] px-3 py-[14px] pl-9 rounded-[8px] border border-[#E2E2E2] bg-white"
            placeholder="Search URLs..."
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {selectedUrls.length > 0 && (
            <>
              <Button
                className="flex px-3 py-2 justify-center items-center gap-2 self-stretch rounded-[11000px] border border-[#E2E2E2] text-[#191919] hover:text-gray-700 hover:bg-gray-50 font-inter text-[14px] font-medium"
                size="sm"
                variant="outline"
                onClick={() => setSelectedUrls([])}>
                Cancel
              </Button>
              <Button
                className="flex px-3 py-2 justify-center items-center gap-2 self-stretch rounded-full bg-[#DC2626] hover:bg-[#B91C1C] text-white font-inter text-[14px] font-medium text-center"
                size="sm"
                onClick={handleDeleteSelected}>
                <Trash2 className="h-4 w-4" />
                Delete Selected ({selectedUrls.length})
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Table with scroll */}
      <div className="flex-1 overflow-auto rounded-[8px]">
        <Table>
          <TableHeader className="sticky top-0 bg-white z-10">
            <TableRow>
              <TableHead className="w-[50px]">
                <Checkbox
                  checked={
                    selectedUrls.length === displayUrls.length &&
                    displayUrls.length > 0
                  }
                  onCheckedChange={(checked) => {
                    setSelectedUrls(
                      checked ? displayUrls.map((url) => url.id) : []
                    );
                  }}
                />
              </TableHead>
              <TableHead className="w-[80%] pl-4">
                <div className="flex items-center gap-2">
                  URLs
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          className="h-3 w-3 text-gray-500 hover:text-gray-700"
                          size="icon"
                          variant="ghost"
                          onClick={handleCopyUrls}>
                          {hasCopied ? (
                            <Check className="h-3 w-3 text-green-500" />
                          ) : (
                            <Copy className="h-3 w-3" />
                          )}
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>{hasCopied ? "Copied!" : "Copy all visible URLs"}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </TableHead>
              <TableHead className="w-[20%]">Last Indexed</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {displayUrls.map((url) => (
              <TableRow key={url.id} className="group relative">
                <TableCell>
                  <Checkbox
                    checked={selectedUrls.includes(url.id)}
                    onCheckedChange={(checked) => {
                      setSelectedUrls((prev) =>
                        checked
                          ? [...prev, url.id]
                          : prev.filter((id) => id !== url.id)
                      );
                    }}
                  />
                </TableCell>
                <TableCell className="font-medium break-all pl-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {url.status === "NOT_PROCESSED" ? (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger>
                              <AlertTriangle className="w-4 h-4 text-warning-base shrink-0" />
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>
                                URL not processed yet. Click the Update Guru
                                button to process it.
                              </p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      ) : (
                        url.status?.toLowerCase() === "fail" && (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger>
                                <AlertTriangle className="w-4 h-4 text-error-base shrink-0" />
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>{url.error || "Failed to process URL"}</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        )
                      )}
                      <span>{url.url}</span>
                    </div>
                    {/* Add trash icon that appears on hover */}
                    <button
                      className="invisible group-hover:visible p-2"
                      onClick={() => onDeleteUrls([url.id])}>
                      <Trash2 className="h-4 w-4 text-[#DC2626]" />
                    </button>
                  </div>
                </TableCell>
                <TableCell className="text-sm text-gray-500">
                  {url.last_reindex_date ? (
                    format(
                      parseISO(url.last_reindex_date),
                      "MMM d, yyyy 'at' h:mm a"
                    )
                  ) : (
                    <span className="text-gray-400">Never</span>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {displayUrls.length === 0 && (
              <TableRow>
                <TableCell
                  className="text-center py-4 text-gray-500"
                  colSpan={2}>
                  {searchTerm
                    ? "No URLs found matching your search"
                    : `No ${activeTab === "failed" ? "failed" : activeTab === "not_processed" ? "unprocessed" : "successful"} URLs found`}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

UrlTableContent.displayName = "UrlTableContent";
