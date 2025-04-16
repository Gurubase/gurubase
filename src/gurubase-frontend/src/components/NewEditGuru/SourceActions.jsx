import React from "react";
import { Button } from "@/components/ui/button";
import { LoaderCircle } from "lucide-react";
import { getAllSourceTypeConfigs } from "@/config/sourceTypes";

// Updated component to dynamically render action buttons based on config
export const SourceActions = ({
  isProcessing,
  isSourcesProcessing,
  // Pass down specific handlers keyed by a predictable name or ID
  actionHandlers = {},
  // Pass down specific loading states keyed similarly
  loadingStates = {}
}) => {
  const configs = getAllSourceTypeConfigs();

  return (
    <div className="flex flex-wrap items-center justify-end gap-2">
      {configs.map((config) => {
        const ActionIcon = config.actionButtonIcon;
        const isLoading =
          config.requiresIntegrationCheck &&
          loadingStates[config.integrationLoadingProp];
        const isDisabled = isProcessing || isSourcesProcessing || isLoading;

        // Determine the correct handler: prioritize specific actionHandlerName, fallback to id
        const handlerKey = config.actionHandlerName || config.id;
        const onClickHandler = actionHandlers[handlerKey];

        // Optionally log a warning if a handler is missing for a configured type
        if (!onClickHandler && !config.requiresIntegrationCheck) {
          // Don't warn for integration types here, as the check is in the handler
          console.warn(
            `SourceActions: Missing handler for key '${handlerKey}' (source type: ${config.id})`
          );
          // Decide how to handle missing handlers: skip rendering, disable, show error?
          // return null; // Skip rendering button if handler is missing
        }

        // Jira (and potentially future integration types) needs a special check within its handler,
        // but we use the handler name from the config to call it.
        // The loading state is used to show the spinner.

        return (
          <Button
            key={config.id}
            className="text-black-600"
            disabled={isDisabled}
            type="button"
            variant="outline"
            // Use the determined handler. If it's missing for non-integration types, button might do nothing or be skipped.
            // For integration types, the handler passed in (e.g., actionHandlers.jira) contains the integration check.
            onClick={onClickHandler}>
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
      })}
    </div>
  );
};
