import React, { useState, useEffect } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "@/components/ui/tooltip";
import {
  AlertTriangle,
  Edit,
  Info,
  LinkIcon,
  LoaderCircle,
  Lock,
  MoreVertical,
  RotateCw,
  Unlock
} from "lucide-react";
import {
  JiraIcon,
  SolarFileTextBold,
  SolarTrashBinTrashBold,
  SolarVideoLibraryBold
} from "@/components/Icons";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { getNormalizedDomain } from "@/utils/common";
import { SourceActions } from "@/components/NewEditGuru/SourceActions";
import {
  getSourceFilterItems,
  getSourceTypeConfigById
} from "@/config/sourceTypes";

export function SourcesTableSection({
  sources,
  isProcessing,
  isSourcesProcessing,
  isSubmitting,
  isLoadingIntegration,
  jiraIntegration,
  pdfInputRef,
  excelInputRef,
  handleEditSource,
  handleDeleteSource,
  handleReindexSource,
  handlePrivacyBadgeClick,
  setClickedSource,
  setIsYoutubeSidebarOpen,
  setIsJiraSidebarOpen,
  setIsUrlSidebarOpen,
  setShowJiraIntegrationModal,
  setIsZendeskSidebarOpen,
  setShowZendeskIntegrationModal,
  zendeskIntegration,
  setIsConfluenceSidebarOpen,
  setShowConfluenceIntegrationModal,
  confluenceIntegration,
  isLoadingConfluenceIntegration,
  isEditMode
}) {
  const [filterType, setFilterType] = useState("all");

  const handleAddWebsite = () => {
    setClickedSource([]);
    setIsUrlSidebarOpen(true);
  };

  const handleAddYoutube = () => {
    setClickedSource([]);
    setIsYoutubeSidebarOpen(true);
  };

  const handleAddJira = () => {
    if (jiraIntegration) {
      setClickedSource([]);
      setIsJiraSidebarOpen(true);
    } else {
      setShowJiraIntegrationModal(true);
    }
  };

  const handleAddConfluence = () => {
    if (confluenceIntegration) {
      setClickedSource([]);
      setIsConfluenceSidebarOpen(true);
    } else {
      setShowConfluenceIntegrationModal(true);
    }
  };

  const handleAddZendesk = () => {
    if (zendeskIntegration) {
      setClickedSource([]);
      setIsZendeskSidebarOpen(true);
    } else {
      setShowZendeskIntegrationModal(true);
    }
  };

  const handleUploadPdf = () => {
    if (pdfInputRef.current) {
      pdfInputRef.current.click();
    }
  };

  const handleUploadExcel = () => {
    if (excelInputRef.current) {
      excelInputRef.current.click();
    }
  };

  const sourceActionHandlers = {
    website: handleAddWebsite,
    youtube: handleAddYoutube,
    jira: handleAddJira,
    confluence: handleAddConfluence,
    onUploadPdfClick: handleUploadPdf,
    onUploadExcelClick: handleUploadExcel,
    zendesk: handleAddZendesk
  };

  const sourceLoadingStates = {
    isLoadingIntegration: isLoadingIntegration,
    isLoadingConfluenceIntegration: isLoadingConfluenceIntegration
  };

  const isSourceProcessing = (source) => {
    if (typeof source.id === "string") {
      return false;
    }

    if (source.domains) {
      return source.domains.some((domain) => domain.status === "NOT_PROCESSED");
    }

    return source.status === "NOT_PROCESSED";
  };

  const renderBadges = (source) => {
    const config = getSourceTypeConfigById(source.type);
    if (!config) return null;

    if (config.hasPrivacyToggle) {
      return (
        <div className="flex items-center gap-1">
          {(() => {
            let badgeProps = {
              className: cn(
                "flex items-center rounded-full gap-1 px-2 py-1 text-body4 font-medium cursor-pointer",
                isSourcesProcessing && "pointer-events-none opacity-50"
              ),
              variant: "secondary"
            };

            switch (source.private) {
              case true:
                badgeProps.icon = Lock;
                badgeProps.iconColor = "text-gray-500";
                badgeProps.text = "Private";
                break;
              default:
                badgeProps.icon = Unlock;
                badgeProps.iconColor = "text-blue-base";
                badgeProps.text = "Public";
                break;
            }

            return (
              <div className="flex items-center gap-1">
                <div
                  key={source.id}
                  role="button"
                  tabIndex={0}
                  onClick={(e) => handlePrivacyBadgeClick(e, source)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      handlePrivacyBadgeClick(e, source);
                    }
                  }}>
                  <Badge {...badgeProps}>
                    <badgeProps.icon
                      className={cn("h-3 w-3", badgeProps.iconColor)}
                    />
                    {badgeProps.text}
                  </Badge>
                </div>
                <div className="relative flex items-center">
                  <TooltipProvider>
                    <Tooltip delayDuration={0}>
                      <TooltipTrigger className="cursor-pointer hover:text-gray-600 transition-colors flex items-center">
                        <Info className="h-3.5 w-3.5 text-gray-400" />
                      </TooltipTrigger>
                      <TooltipContent
                        align="center"
                        className="rounded-lg shadow-lg border p-3 md:bg-[#1B242D] md:text-white bg-background"
                        side="top"
                        sideOffset={8}>
                        <div
                          className="absolute w-4 h-4 border-l border-t md:bg-[#1B242D] bg-background"
                          style={{
                            bottom: "-8px",
                            left: "50%",
                            transform: "translateX(-50%) rotate(225deg)",
                            borderColor: "inherit"
                          }}
                        />
                        <p className="text-center relative font-inter px-2 text-xs font-medium">
                          {source.private
                            ? "This resource will be listed but not linked as a question reference."
                            : "This resource will be listed and linked as a question reference."}
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </div>
            );
          })()}
        </div>
      );
    }

    if (source.domains && config.canEdit) {
      const statusGroups = source.domains.reduce((acc, domain) => {
        const status =
          domain.status === "NOT_PROCESSED"
            ? "NOT_PROCESSED"
            : domain.status?.toLowerCase() === "fail"
              ? "FAIL"
              : "SUCCESS";
        acc[status] = (acc[status] || 0) + 1;
        return acc;
      }, {});

      const handleBadgeClick = (e, status, sourceToEdit) => {
        if (isSourcesProcessing) return;
        e.preventDefault();
        e.stopPropagation();
        const tabValue =
          status === "SUCCESS"
            ? "success"
            : status === "NOT_PROCESSED"
              ? "not_processed"
              : "failed";
        setTimeout(() => handleEditSource(sourceToEdit, tabValue), 0);
      };

      return (
        <div className="flex items-center space-x-2">
          {Object.entries(statusGroups).map(([status, count]) => {
            if (count === 0) return null;
            let badgeProps = {
              className:
                "flex items-center rounded-full gap-1 px-2 py-1 text-body4 font-medium cursor-pointer",
              variant: "secondary",
              text: `${count} URL${count > 1 ? "s" : ""}`
            };
            switch (status) {
              case "SUCCESS":
                badgeProps = {
                  ...badgeProps,
                  icon: LinkIcon,
                  iconColor: "text-blue-base",
                  className: `${badgeProps.className} hover:bg-blue-50`
                };
                break;
              case "NOT_PROCESSED":
                badgeProps = {
                  ...badgeProps,
                  icon: AlertTriangle,
                  iconColor: "text-warning-base",
                  className: `${badgeProps.className} hover:bg-warning-50`
                };
                break;
              case "FAIL":
                badgeProps = {
                  ...badgeProps,
                  icon: AlertTriangle,
                  iconColor: "text-error-base",
                  className: `${badgeProps.className} hover:bg-error-50`
                };
                break;
              default:
                return null;
            }
            return (
              <div
                key={status}
                className={cn(
                  "cursor-pointer",
                  isSourcesProcessing && "pointer-events-none opacity-50"
                )}
                role="button"
                tabIndex={0}
                onClick={(e) => handleBadgeClick(e, status, source)}>
                <Badge {...badgeProps} />
              </div>
            );
          })}
        </div>
      );
    }

    return null;
  };

  const filteredSources =
    filterType === "all"
      ? sources
      : sources.filter(
          (source) => source.type.toLowerCase() === filterType.toLowerCase()
        );

  const urlSources = filteredSources.filter(
    (source) =>
      source.type.toLowerCase() === "youtube" ||
      source.type.toLowerCase() === "website" ||
      source.type.toLowerCase() === "jira" ||
      source.type.toLowerCase() === "confluence" ||
      source.type.toLowerCase() === "zendesk"
  );
  const fileSources = filteredSources.filter(
    (source) =>
      source.type.toLowerCase() === "pdf" ||
      source.type.toLowerCase() === "excel"
  );

  const groupedSources = urlSources.reduce((acc, source) => {
    const domain = getNormalizedDomain(source.url);
    if (!domain) return acc;
    const existingSource = acc.find(
      (item) => item.domain === domain && item.type === source.type
    );
    if (existingSource) {
      existingSource.count += 1;
      existingSource.domains.push(source);
    } else {
      acc.push({
        ...source,
        count: 1,
        domains: [source],
        domain: domain
      });
    }
    return acc;
  }, []);

  const displaySources = [...groupedSources, ...fileSources];
  const sourceFilterItems = getSourceFilterItems();

  return (
    <div className="max-w-full">
      <div className="flex flex-col mb-5">
        <h3 className="text-lg font-semibold mb-1">Sources</h3>
        <div className="flex items-center justify-between">
          <p className="text-body2 text-gray-400">
            Your guru will answer questions based on the sources you provided
            below
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between space-x-4 mb-3">
        {sources.length > 0 && (
          <Select
            disabled={isSourcesProcessing || isProcessing || isSubmitting}
            onValueChange={(value) => setFilterType(value)}
            value={filterType}>
            <SelectTrigger className="guru-sm:w-[100px] guru-md:w-[180px] guru-lg:w-[180px]">
              <SelectValue placeholder="All" />
            </SelectTrigger>
            <SelectContent>
              {sourceFilterItems.map((item) => (
                <SelectItem key={item.value} value={item.value}>
                  {item.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <SourceActions
          isProcessing={isProcessing}
          isSourcesProcessing={isSourcesProcessing}
          actionHandlers={sourceActionHandlers}
          loadingStates={sourceLoadingStates}
          isEditMode={isEditMode}
        />
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[20%]">Type</TableHead>
            <TableHead className="w-[50%]">Name</TableHead>
            <TableHead className="w-[30%]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {displaySources.length === 0 ? (
            <TableRow>
              <TableCell className="text-center" colSpan={3}>
                No sources added
              </TableCell>
            </TableRow>
          ) : (
            displaySources.map((source) => {
              const config = getSourceTypeConfigById(source.type);
              const IconComponent = config?.icon;

              return (
                <TableRow key={source.id}>
                  <TableCell className="font-medium">
                    <div className="flex items-center">
                      {IconComponent && (
                        <IconComponent className="mr-2 h-4 w-4" />
                      )}
                      <span>{config?.displaySourceText || source.sources}</span>
                    </div>
                  </TableCell>

                  <TableCell>
                    {isSourceProcessing(source) && isSourcesProcessing ? (
                      <div className="flex items-center gap-2 text-gray-500">
                        <LoaderCircle className="h-4 w-4 animate-spin" />
                        <span className="text-sm">Processing source...</span>
                      </div>
                    ) : (
                      <span>
                        {source?.type?.toLowerCase() === "pdf" ||
                        source?.type?.toLowerCase() === "excel"
                          ? source?.name
                          : source?.domain}
                      </span>
                    )}
                  </TableCell>

                  <TableCell className="">
                    <div className="flex items-center space-x-2 justify-end">
                      {renderBadges(source)}
                      <span>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button
                              className="h-8 w-8 p-0"
                              disabled={isSourcesProcessing}
                              size="icon"
                              variant="ghost">
                              <span className="sr-only">Open menu</span>
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            {config?.canEdit && (
                              <DropdownMenuItem
                                disabled={isSourcesProcessing}
                                onClick={() => handleEditSource(source)}>
                                <Edit className="mr-2 h-3 w-3" />
                                Edit
                              </DropdownMenuItem>
                            )}
                            {config?.canReindex && (
                              <DropdownMenuItem
                                disabled={isSourcesProcessing}
                                onClick={() => handleReindexSource(source)}>
                                <RotateCw className="mr-2 h-3 w-3" />
                                Reindex
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuItem
                              disabled={isSourcesProcessing}
                              onClick={() => handleDeleteSource(source)}>
                              <SolarTrashBinTrashBold className="mr-2 h-3 w-3" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </span>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })
          )}
        </TableBody>
      </Table>
    </div>
  );
}
