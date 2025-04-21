import {
  Dialog as AlertDialog,
  DialogContent as AlertDialogContent,
  DialogDescription as AlertDialogDescription,
  DialogHeader as AlertDialogHeader,
  DialogTitle as AlertDialogTitle
} from "@/components/ui/modal-dialog";
import { Button } from "@/components/ui/button";

// Create a new component for the confirmation dialog

const config = {
  titles: {
    close: {
      crawling: "Close While Crawling?",
      "jira-fetch-issues": "Close While Fetching Issues?",
      default: "Close While Importing?"
    },
    stop: {
      crawling: "Stop Crawling?",
      "jira-fetch-issues": "Stop Fetching Issues?",
      default: "Stop Import?"
    }
  },
  descriptions: {
    close: {
      crawling:
        "This will stop the crawling process and close the dialog. The URLs discovered so far will still be available.",
      "jira-fetch-issues":
        "This will stop the fetching issues process and close the dialog. The issues fetched so far will still be available.",
      default: "This will stop the import process and close the dialog."
    },
    stop: {
      crawling:
        "This will stop the crawling process. The URLs discovered so far will still be available.",
      "jira-fetch-issues":
        "This will stop the fetching issues process. The issues fetched so far will still be available.",
      default: "This will stop the import process."
    }
  },
  buttonText: {
    stopping: "Stopping...",
    stop: {
      crawling: "Stop Crawling",
      "jira-fetch-issues": "Stop Fetching Issues",
      default: "Stop Import"
    }
  },
  continueText: {
    crawling: "Continue Crawling",
    "jira-fetch-issues": "Continue Fetching Issues",
    default: "Continue Import"
  }
};

const ProcessStopConfirmationDialog = ({
  isOpen,
  onOpenChange,
  onConfirm,
  isClosing,
  action,
  processType = "crawling" // can be "crawling", "jira", "sitemap"
}) => {
  const dialogTitle =
    (config.titles[action] && config.titles[action][processType]) ||
    config.titles[action]?.default ||
    "Default Title";
  const dialogDescription =
    (config.descriptions[action] && config.descriptions[action][processType]) ||
    config.descriptions[action]?.default ||
    "Default Description";
  const buttonText = isClosing
    ? config.buttonText.stopping
    : config.buttonText.stop[processType] ||
      config.buttonText.stop.default ||
      "Default Button Text";
  const continueText =
    config.continueText[processType] ||
    config.continueText.default ||
    "Default Continue Text";

  return (
    <AlertDialog open={isOpen} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-[400px] p-6 z-[200]">
        <AlertDialogHeader>
          <AlertDialogTitle className="text-base font-semibold text-center text-[#191919] font-inter">
            {dialogTitle}
          </AlertDialogTitle>
          <AlertDialogDescription className="text-[14px] text-[#6D6D6D] text-center font-inter font-normal">
            {dialogDescription}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="mt-6 flex flex-col gap-2">
          <Button
            className="h-12 px-6 justify-center items-center rounded-lg bg-[#DC2626] hover:bg-red-700 text-white"
            disabled={isClosing}
            onClick={onConfirm}>
            {buttonText}
          </Button>
          <Button
            className="h-12 px-4 justify-center items-center rounded-lg border border-[#1B242D] bg-white"
            variant="outline"
            disabled={isClosing}
            onClick={() => onOpenChange(false)}>
            {continueText}
          </Button>
        </div>
      </AlertDialogContent>
    </AlertDialog>
  );
};

export default ProcessStopConfirmationDialog;
