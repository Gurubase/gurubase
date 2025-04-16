import React from "react";
import { Button } from "@/components/ui/button";
import {
  LogosYoutubeIcon,
  JiraIcon,
  SolarTrashBinTrashBold
} from "@/components/Icons";
import { LinkIcon, LoaderCircle, Upload } from "lucide-react";

// Component for the action buttons to add various data sources
export const SourceActions = ({
  isProcessing,
  isSourcesProcessing,
  isLoadingIntegration,
  jiraIntegration,
  onAddYoutubeClick,
  onAddJiraClick,
  onAddWebsiteClick,
  onUploadPdfClick,
  setShowJiraIntegrationModal // Need this to show the modal
}) => {
  return (
    <div className="flex flex-wrap items-center justify-end gap-2">
      {" "}
      {/* Use flex-wrap and gap */}
      <Button
        className="text-black-600"
        disabled={isProcessing || isSourcesProcessing}
        type="button"
        variant="outline"
        onClick={onAddYoutubeClick}>
        <LogosYoutubeIcon className="guru-sm:mr-0 guru-md:mr-2 guru-lg:mr-2 h-4 w-4" />
        <span className="guru-sm:hidden guru-md:block guru-lg:block">
          Add YouTube
        </span>
      </Button>
      <Button
        className="text-black-600"
        disabled={
          isProcessing || isSourcesProcessing || isLoadingIntegration // Disable while checking integration
        }
        type="button"
        variant="outline"
        onClick={() => {
          // Check if integration exists and is properly configured
          if (jiraIntegration) {
            onAddJiraClick(); // Call the passed handler
          } else {
            // Show modal prompting user to integrate
            setShowJiraIntegrationModal(true);
          }
        }}>
        {isLoadingIntegration ? (
          <LoaderCircle className="guru-sm:mr-0 guru-md:mr-2 guru-lg:mr-2 h-4 w-4 animate-spin" />
        ) : (
          <JiraIcon className="guru-sm:mr-0 guru-md:mr-2 guru-lg:mr-2 h-4 w-4" />
        )}
        <span className="guru-sm:hidden guru-md:block guru-lg:block">
          Add Jira Issues
        </span>
      </Button>
      <Button
        className="text-black-600"
        disabled={isProcessing || isSourcesProcessing}
        type="button"
        variant="outline"
        onClick={onAddWebsiteClick}>
        <LinkIcon className="guru-sm:mr-0 guru-md:mr-2 guru-lg:mr-2 h-4 w-4" />
        <span className="guru-sm:hidden guru-md:block guru-lg:block">
          Add Website
        </span>
      </Button>
      <Button
        className="text-black-600"
        disabled={isProcessing || isSourcesProcessing}
        type="button"
        variant="outline"
        onClick={onUploadPdfClick}>
        <Upload className="guru-sm:mr-0 guru-md:mr-2 guru-lg:mr-2 h-4 w-4" />
        <span className="guru-sm:hidden guru-md:block guru-lg:block">
          Upload PDFs
        </span>
      </Button>
    </div>
  );
};
