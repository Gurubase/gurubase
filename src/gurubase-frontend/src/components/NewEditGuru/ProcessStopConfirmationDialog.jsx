import {
  Dialog as AlertDialog,
  DialogContent as AlertDialogContent,
  DialogDescription as AlertDialogDescription,
  DialogHeader as AlertDialogHeader,
  DialogTitle as AlertDialogTitle
} from "@/components/ui/modal-dialog";
import { Button } from "@/components/ui/button";

// Create a new component for the confirmation dialog

const ProcessStopConfirmationDialog = ({
  isOpen,
  onOpenChange,
  onConfirm,
  isClosing,
  action,
  processType = "crawling" // can be "crawling" or "sitemap"
}) => {
  const dialogTitle =
    action === "close"
      ? `Close While ${processType === "crawling" ? "Crawling" : "Importing"}?`
      : processType === "crawling"
        ? "Stop Crawling?"
        : "Stop Import?";

  const dialogDescription =
    action === "close"
      ? `This will stop the ${processType.charAt(0).toUpperCase() + processType.slice(1)} process and close the dialog. ${
          processType === "crawling"
            ? "The URLs discovered so far will still be available."
            : ""
        }`
      : `This will stop the ${
          processType.charAt(0).toUpperCase() + processType.slice(1)
        } process. ${
          processType === "crawling"
            ? "The URLs discovered so far will still be available."
            : ""
        }`;

  const buttonText = isClosing
    ? "Stopping..."
    : `Stop ${processType === "crawling" ? "Crawling" : "Import"}`;

  const continueText = `Continue ${
    processType === "crawling" ? "Crawling" : "Import"
  }`;

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
