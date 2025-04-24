import React from "react";
import { Button } from "@/components/ui/button";
import { LoaderCircle } from "lucide-react";
import { getAllSourceTypeConfigs } from "@/config/sourceTypes";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

// Updated component to dynamically render action buttons based on config
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
    <div className="flex flex-wrap items-center justify-end gap-2">
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

        // Jira (and potentially future integration types) needs a special check within its handler,
        // but we use the handler name from the config to call it.
        // The loading state is used to show the spinner.

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

        const button = (
          <Button
            key={config.id}
            className={cn("text-black-600")}
            disabled={finalDisabled}
            type="button"
            variant="outline"
            // Use the determined handler. If it's missing for non-integration types, button might do nothing or be skipped.
            // For integration types, the handler passed in (e.g., actionHandlers.jira) contains the integration check.
            onClick={isJiraInCreateMode ? undefined : onClickHandler}
            aria-disabled={finalDisabled}
            tabIndex={isJiraInCreateMode ? -1 : 0} // Prevent tabbing to disabled button
          >
            {isLoading ? (
              <LoaderCircle className="guru-sm:mr-0 guru-md:mr-2 guru-lg:mr-2 h-4 w-4 animate-spin" />
            ) : (
              <ActionIcon className="guru-sm:mr-0 guru-md:mr-2 guru-lg:mr-2 h-4 w-4" />
            )}
            <span className="guru-sm:hidden guru-md:block guru-lg:block">
              {config.actionButtonText}
            </span>
          </Button>
        );

        // Conditionally wrap Jira button with Tooltip in create mode
        if (isJiraInCreateMode) {
          return (
            <TooltipProvider key={config.id} delayDuration={100}>
              <Tooltip>
                <TooltipTrigger asChild>
                  {/* Wrap the button in a span for TooltipTrigger when disabled */}
                  <span tabIndex={-1}>{button}</span>
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
                  <span tabIndex={-1}>{button}</span>
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
                  <span tabIndex={-1}>{button}</span>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Confluence integration requires an existing Guru.</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          );
        }

        // Return the button directly for other source types or when in edit mode
        return button;
      })}
    </div>
  );
};
