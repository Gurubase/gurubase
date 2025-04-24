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
  Check,
  Clock,
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
  getSourceTypeConfigById,
  SOURCE_TYPES_CONFIG
} from "@/config/sourceTypes";
import { formatFileSize } from "@/utils/common";

export function SourcesTableSection({
  sources,
  isProcessing,
  isSourcesProcessing,
  isSubmitting,
  isLoadingIntegration,
  jiraIntegration,
  fileInputRef,
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
  isEditMode,
  setIsGithubSidebarOpen,
  handleEditGithubGlob,
  setIsEditingRepo,
  setEditingRepo,
  deletingSources = []
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

  const handleAddGithub = () => {
    setClickedSource([]);
    if (typeof setIsEditingRepo === "function") {
      setIsEditingRepo(false);
    }
    if (typeof setEditingRepo === "function") {
      setEditingRepo(null);
    }
    setIsGithubSidebarOpen(true);
  };

  const handleUploadPdf = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const sourceActionHandlers = {
    website: handleAddWebsite,
    youtube: handleAddYoutube,
    jira: handleAddJira,
    confluence: handleAddConfluence,
    onUploadPdfClick: handleUploadPdf,
    zendesk: handleAddZendesk,
    github_repo: handleAddGithub
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

    return (
      source.status === "NOT_PROCESSED" ||
      (source.status === "SUCCESS" && !source.in_milvus)
    );
  };

  const isSourceDeleting = (source) => {
    return deletingSources.some(
      (deletingSource) =>
        deletingSource.id === source.id ||
        (source.domains &&
          source.domains.some((domain) => domain.id === deletingSource.id))
    );
  };

  const renderBadges = (source) => {
    const config = getSourceTypeConfigById(source.type);
    const isGithubSource =
      source.type?.toLowerCase() === SOURCE_TYPES_CONFIG.GITHUB.id;
    const isPdfSource =
      source.type?.toLowerCase() === SOURCE_TYPES_CONFIG.PDF.id;

    if (!config) return null;

    const sourceDone =
      (source.status === "SUCCESS" && source.in_milvus) ||
      source.status === "FAIL";

    if (isGithubSource) {
      let badgeProps = {
        className:
          "flex items-center rounded-full gap-1 px-2 py-0.5 text-xs font-medium pointer-events-none",
        icon: Clock,
        iconColor: "text-gray-500",
        text: "Pending"
      };

      switch (source.status) {
        case "SUCCESS":
          badgeProps.icon = Check;
          badgeProps.iconColor = "text-green-700";
          badgeProps.text = `${source.file_count} files`;
          badgeProps.className += " bg-green-50 text-green-700";
          break;
        case "FAIL":
          badgeProps.icon = AlertTriangle;
          badgeProps.iconColor = "text-red-700";
          badgeProps.text = "Failed";
          badgeProps.className += " bg-red-50 text-red-700";
          break;
        case "NOT_PROCESSED":
        default:
          badgeProps.icon = Clock;
          badgeProps.iconColor = "text-yellow-700";
          badgeProps.text = "Processing";
          badgeProps.className += " bg-yellow-50 text-yellow-700";
          break;
      }

      const badgeElement = sourceDone ? (
        <Badge {...badgeProps}>
          <badgeProps.icon
            className={cn(
              "h-3 w-3",
              badgeProps.iconColor,
              isSourcesProcessing && "pointer-events-none opacity-50"
            )}
          />
          {badgeProps.text}
        </Badge>
      ) : null;

      const lastIndexedDate = source.last_reindex_date
        ? new Date(source.last_reindex_date).toLocaleString()
        : null;

      return (
        <div className="flex items-center gap-2">
          {source.status === "FAIL" && source.error ? (
            <TooltipProvider>
              <Tooltip delayDuration={0}>
                <TooltipTrigger asChild>
                  <span
                    className={cn(
                      isSourcesProcessing && "pointer-events-none opacity-50"
                    )}>
                    {badgeElement}
                  </span>
                </TooltipTrigger>
                <TooltipContent
                  align="center"
                  className="rounded-lg shadow-lg border p-3 bg-background max-w-xs"
                  side="top"
                  sideOffset={8}>
                  <p className="text-center relative font-inter px-2 text-xs font-medium text-red-600">
                    {source.error}
                  </p>
                  <div
                    className="absolute w-3 h-3 border-l border-t bg-background"
                    style={{
                      bottom: "-6px",
                      left: "50%",
                      transform: "translateX(-50%) rotate(225deg)",
                      borderColor: "inherit"
                    }}
                  />
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : source.last_reindex_date ? (
            <TooltipProvider>
              <Tooltip delayDuration={0}>
                <TooltipTrigger asChild>
                  <span
                    className={cn(
                      isSourcesProcessing && "pointer-events-none opacity-50"
                    )}>
                    {badgeElement}
                  </span>
                </TooltipTrigger>
                <TooltipContent
                  align="center"
                  className="rounded-lg shadow-lg border p-3 bg-background max-w-xs"
                  side="top"
                  sideOffset={8}>
                  <p className="text-center relative font-inter px-2 text-xs font-medium text-green-700">
                    Last indexed at {lastIndexedDate}
                  </p>
                  <div
                    className="absolute w-3 h-3 border-l border-t bg-background"
                    style={{
                      bottom: "-6px",
                      left: "50%",
                      transform: "translateX(-50%) rotate(225deg)",
                      borderColor: "inherit"
                    }}
                  />
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : (
            <span
              className={cn(
                isSourcesProcessing && "pointer-events-none opacity-50"
              )}>
              {badgeElement}
            </span>
          )}
        </div>
      );
    }

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

    if (!isPdfSource && !isGithubSource && config.canEdit) {
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

  // Separate sources based on the willGroup flag from config
  const sourcesToGroup = [];
  const sourcesNotToGroup = [];

  filteredSources.forEach((source) => {
    const config = getSourceTypeConfigById(source.type);
    if (config?.willGroup) {
      sourcesToGroup.push(source);
    } else {
      sourcesNotToGroup.push(source);
    }
  });

  // Group the sources marked for grouping
  const groupedSources = sourcesToGroup.reduce((acc, source) => {
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

  const displaySources = [...groupedSources, ...sourcesNotToGroup];
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
        {sources.length > 0 ? (
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
        ) : (
          // To preserve the layout when source selection is not available during initial loading and new guru creation
          <div className="w-[180px]"></div>
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
            <TableHead className="w-[60%]">Name</TableHead>
            <TableHead className="w-[20%]"></TableHead>
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
                        <IconComponent className="mr-2 h-4 w-4 text-gray-600" />
                      )}
                      <span>{config?.displaySourceText || source.sources}</span>
                    </div>
                  </TableCell>

                  <TableCell>
                    {isSourceDeleting(source) ? (
                      <div className="flex items-center gap-2 text-gray-500">
                        <LoaderCircle className="h-4 w-4 animate-spin" />
                        <span className="text-sm">Deleting source...</span>
                      </div>
                    ) : isSourceProcessing(source) && isSourcesProcessing ? (
                      <div className="flex items-center gap-2 text-gray-500">
                        <LoaderCircle className="h-4 w-4 animate-spin" />
                        <span className="text-sm">Processing source...</span>
                      </div>
                    ) : (
                      <span>
                        {source.domain || source.name}
                        {source.type === "pdf" && source.size && (
                          <span className="ml-2 text-xs text-gray-400">
                            ({formatFileSize(source.size)})
                          </span>
                        )}
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
                              disabled={
                                isSourcesProcessing || isSourceDeleting(source)
                              }
                              size="icon"
                              variant="ghost">
                              <span className="sr-only">Open menu</span>
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            {config?.canEdit && (
                              <DropdownMenuItem
                                disabled={
                                  isSourcesProcessing ||
                                  isSourceDeleting(source)
                                }
                                onClick={() => handleEditSource(source)}>
                                <Edit className="mr-2 h-3 w-3" />
                                Edit
                              </DropdownMenuItem>
                            )}
                            {source.type === "github_repo" && (
                              <DropdownMenuItem
                                disabled={
                                  isSourcesProcessing ||
                                  isSourceDeleting(source)
                                }
                                onClick={() => handleEditGithubGlob(source)}>
                                <Edit className="mr-2 h-3 w-3" />
                                Edit Glob
                              </DropdownMenuItem>
                            )}
                            {config?.canReindex && (
                              <DropdownMenuItem
                                disabled={
                                  isSourcesProcessing ||
                                  isSourceDeleting(source)
                                }
                                onClick={() => handleReindexSource(source)}>
                                <RotateCw className="mr-2 h-3 w-3" />
                                Reindex
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuItem
                              disabled={
                                isSourcesProcessing || isSourceDeleting(source)
                              }
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
