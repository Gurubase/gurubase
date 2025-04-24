import React from "react";
import { Button } from "@/components/ui/button";
import { LoaderCircle, ChevronDown } from "lucide-react";
import { getAllSourceTypeConfigs } from "@/config/sourceTypes";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

// Updated component to render actions in a dropdown menu
export const SourceActions = ({
  isProcessing,
  isSourcesProcessing,
  // Pass down specific handlers keyed by a predictable name or ID
  actionHandlers = {},
  // Pass down specific loading states keyed similarly
  loadingStates = {},
  isEditMode
}) => {
  const configs = getAllSourceTypeConfigs();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className="text-black-600"
          disabled={isProcessing || isSourcesProcessing}>
          Add
          <ChevronDown className="ml-2 h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {configs.map((config) => {
          const ActionIcon = config.actionButtonIcon;
          const isLoading =
            config.requiresIntegrationCheck &&
            loadingStates[config.integrationLoadingProp];
          const baseDisabled = isProcessing || isSourcesProcessing || isLoading;

          // Determine the correct handler: prioritize specific actionHandlerName, fallback to id
          const handlerKey = config.actionHandlerName || config.id;
          const onClickHandler = actionHandlers[handlerKey];

          // Optionally log a warning if a handler is missing for a configured type
          if (!onClickHandler && !config.requiresIntegrationCheck) {
            // Don't warn for integration types here, as the check is in the handler
          }

          // Special disabling logic for Jira in 'create' mode
          const isJiraInCreateMode = config.id === "jira" && !isEditMode;
          const isZendeskInCreateMode = config.id === "zendesk" && !isEditMode;
          const isConfluenceInCreateMode =
            config.id === "confluence" && !isEditMode;
          const finalDisabled =
            baseDisabled ||
            isJiraInCreateMode ||
            isZendeskInCreateMode ||
            isConfluenceInCreateMode;

          const menuItem = (
            <DropdownMenuItem
              key={config.id}
              className={cn("flex items-center gap-2")}
              disabled={finalDisabled}
              onClick={
                isJiraInCreateMode ||
                isZendeskInCreateMode ||
                isConfluenceInCreateMode
                  ? undefined
                  : onClickHandler
              }
              tabIndex={
                isJiraInCreateMode ||
                isZendeskInCreateMode ||
                isConfluenceInCreateMode
                  ? -1
                  : 0
              }>
              {isLoading ? (
                <LoaderCircle className="h-4 w-4 animate-spin" />
              ) : (
                <ActionIcon className="h-4 w-4" />
              )}
              <span>{config.actionButtonText}</span>
            </DropdownMenuItem>
          );

          // Conditionally wrap with Tooltip in create mode
          if (isJiraInCreateMode) {
            return (
              <TooltipProvider key={config.id} delayDuration={100}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div>{menuItem}</div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Jira integration requires an existing Guru.</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            );
          }

          if (isZendeskInCreateMode) {
            return (
              <TooltipProvider key={config.id} delayDuration={100}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div>{menuItem}</div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Zendesk integration requires an existing Guru.</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            );
          }

          if (isConfluenceInCreateMode) {
            return (
              <TooltipProvider key={config.id} delayDuration={100}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div>{menuItem}</div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Confluence integration requires an existing Guru.</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            );
          }

          // Return the menu item directly for other source types or when in edit mode
          return menuItem;
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
