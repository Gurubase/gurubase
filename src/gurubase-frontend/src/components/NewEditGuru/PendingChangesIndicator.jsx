import React from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "@/components/ui/tooltip";
import { AlertTriangle } from "lucide-react";

// Component to display pending changes information
export const PendingChangesIndicator = ({ dirtyChanges, sources }) => {
  // Count non-processed newly added sources
  const newSources = dirtyChanges.sources.filter(
    (source) => source.newAddedSource && !source.deleted
  );
  const newSourcesCount = newSources.length;

  // Get deleted sources directly from dirtyChanges
  const deletedSources = dirtyChanges.sources.filter(
    (source) => source.deleted
  );
  const deletedSourcesCount = deletedSources.length;

  // Find original sources that are being deleted
  const getDeletedSourceDetails = (sourceIds) => {
    return sources
      .filter((source) =>
        Array.isArray(sourceIds)
          ? sourceIds.includes(source.id)
          : source.id === sourceIds
      )
      .map((source) => source.url || source.name);
  };

  // Only show counts if there are any
  const hasChanges = newSourcesCount > 0 || deletedSourcesCount > 0;

  const tooltipContent = hasChanges ? (
    <div className="space-y-2">
      {newSourcesCount > 0 && (
        <div>
          <p className="font-medium text-warning-base">
            Pending addition: {newSourcesCount}
          </p>
          <div className="mt-1 space-y-1">
            {newSources.map((source, index) => (
              <p key={source.id} className="text-sm text-gray-500">
                {index + 1}. {source.url || source.name}
              </p>
            ))}
          </div>
        </div>
      )}
      {deletedSourcesCount > 0 && (
        <div>
          <p className="font-medium text-error-base">
            Pending deletion: {deletedSourcesCount}
          </p>
          <div className="mt-1 space-y-1">
            {deletedSources.map((source) => {
              const deletedUrls = getDeletedSourceDetails(source.id);

              return deletedUrls.map((url, urlIndex) => (
                <p
                  key={`${source.id}-${urlIndex}`}
                  className="text-sm text-gray-500">
                  {urlIndex + 1}. {url}
                </p>
              ));
            })}
          </div>
        </div>
      )}
    </div>
  ) : (
    <p>Other changes pending</p>
  );

  return (
    <Alert className="w-full" variant="warning">
      <div className="flex items-center gap-2">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <AlertTriangle className="h-4 w-4" />
            </TooltipTrigger>
            <TooltipContent>{tooltipContent}</TooltipContent>
          </Tooltip>
        </TooltipProvider>

        <AlertDescription>
          You have pending changes. Click &quot;Update Guru&quot; to save them.
        </AlertDescription>
      </div>
    </Alert>
  );
};
