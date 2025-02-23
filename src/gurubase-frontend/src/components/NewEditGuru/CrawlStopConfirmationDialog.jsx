import {
  Dialog as AlertDialog,
  DialogContent as AlertDialogContent,
  DialogDescription as AlertDialogDescription,
  DialogHeader as AlertDialogHeader,
  DialogTitle as AlertDialogTitle
} from "@/components/ui/modal-dialog";
import { Button } from "@/components/ui/button";

// Create a new component for the confirmation dialog

const CrawlStopConfirmationDialog = ({
  isOpen,
  onOpenChange,
  onConfirm,
  isClosing,
  action
}) => {
  const dialogTitle =
    action === "close" ? "Close While Crawling?" : "Stop Crawling?";

  const dialogDescription =
    action === "close"
      ? "This will stop the crawling process and close the dialog. The URLs discovered so far will still be available."
      : "This will stop the crawling process. The URLs discovered so far will still be available.";

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
            {isClosing ? "Stopping..." : "Stop Crawling"}
          </Button>
          <Button
            className="h-12 px-4 justify-center items-center rounded-lg border border-[#1B242D] bg-white"
            variant="outline"
            disabled={isClosing}
            onClick={() => onOpenChange(false)}>
            Continue Crawling
          </Button>
        </div>
      </AlertDialogContent>
    </AlertDialog>
  );
};

export default CrawlStopConfirmationDialog;
