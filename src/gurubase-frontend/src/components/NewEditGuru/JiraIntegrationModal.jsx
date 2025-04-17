import React from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from "@/components/ui/modal-dialog";
import { Button } from "@/components/ui/button";
import { JiraIcon } from "@/components/Icons";
import { useAppNavigation } from "@/lib/navigation";

// Modal to prompt user to configure Jira integration
export const JiraIntegrationModal = ({ isOpen, onOpenChange, guruSlug }) => {
  const navigation = useAppNavigation();

  const goToIntegrations = () => {
    if (guruSlug) {
      navigation.push(`/guru/${guruSlug}/integrations`);
    }
    onOpenChange(false); // Close modal after navigation
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md p-6">
        <DialogHeader>
          <div className="flex justify-center mb-4">
            <JiraIcon className="h-10 w-10 text-blue-500" />
          </div>
          <DialogTitle className="text-center text-lg font-semibold">
            Jira Integration Required
          </DialogTitle>
          <DialogDescription className="text-center text-sm text-gray-500 mt-2">
            To add Jira issues as a data source, you need to connect your Jira
            account first.
          </DialogDescription>
        </DialogHeader>
        <div className="mt-6 flex flex-col gap-3">
          <Button onClick={goToIntegrations} className="w-full">
            Go to Integrations
          </Button>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="w-full">
            Cancel
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
