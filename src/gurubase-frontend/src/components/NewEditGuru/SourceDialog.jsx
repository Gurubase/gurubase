import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import * as React from "react";

import MonacoUrlEditor from "@/components/NewEditGuru/MonacoUrlEditor";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { isValidUrl } from "@/utils/common";
import ProcessStopConfirmationDialog from "@/components/NewEditGuru/ProcessStopConfirmationDialog";

import { UrlTableContent } from "./UrlTableContent";

const Dialog = DialogPrimitive.Root;
const DialogPortal = DialogPrimitive.Portal;
const DialogClose = DialogPrimitive.Close;

const StyledDialogContent = React.forwardRef(
  ({ children, isMobile, ...props }, ref) => (
    <DialogPortal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
      <DialogPrimitive.Content
        ref={ref}
        className={cn(
          "fixed z-[100] bg-white shadow-lg transition ease-in-out data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:duration-300 data-[state=open]:duration-500",
          isMobile
            ? "inset-x-0 bottom-0 z-[100] h-[90vh] w-full rounded-t-[20px] data-[state=closed]:slide-out-to-bottom data-[state=open]:slide-in-from-bottom border border-gray-200 rounded-xl"
            : "right-0 top-0 z-[100] h-full w-full max-w-5xl data-[state=closed]:slide-out-to-right data-[state=open]:slide-in-from-right"
        )}
        {...props}>
        {children}
      </DialogPrimitive.Content>
    </DialogPortal>
  )
);

StyledDialogContent.displayName = "StyledDialogContent";

const SourceDialog = React.memo(
  ({
    isOpen,
    onOpenChange,
    title,
    sourceType,
    editorContent,
    onEditorChange,
    clickedSource,
    initialActiveTab,
    selectedUrls,
    setSelectedUrls,
    onAddUrls,
    form,
    isMobile,
    setDirtyChanges,
    setClickedSource,
    setSources,
    handleDeleteUrls,
    readOnly = false,
    onStartCrawl,
    isCrawling,
    onStopCrawl,
    showCrawlInput,
    setShowCrawlInput,
    crawlUrl,
    setCrawlUrl
  }) => {
    const [showStopConfirmation, setShowStopConfirmation] =
      React.useState(false);
    const [isClosing, setIsClosing] = React.useState(false);
    const [stopAction, setStopAction] = React.useState(null);
    const [processType, setProcessType] = React.useState("crawling");
    const [isLoadingSitemap, setIsLoadingSitemap] = React.useState(false);
    const isLoadingSitemapRef = React.useRef(false);

    const handleProcessStop = React.useCallback((action, type) => {
      setStopAction(action);
      setProcessType(type);
      setShowStopConfirmation(true);
    }, []);

    // Create a wrapper function to update both state and ref
    const updateSitemapLoadingState = React.useCallback((loading) => {
      setIsLoadingSitemap(loading);
      isLoadingSitemapRef.current = loading;
    }, []);

    const handleClose = React.useCallback(async () => {
      if (isCrawling) {
        handleProcessStop("close", "crawling");
        return;
      }

      if (isLoadingSitemap) {
        handleProcessStop(
          "close",
          sourceType === "website" ? "sitemap" : "youtube"
        );
        return;
      }

      if (editorContent.trim()) {
        const urls = editorContent
          .split("\n")
          .map((url) => url.trim())
          .filter((url) => url && isValidUrl(url));

        const uniqueUrls = [...new Set(urls)];

        if (uniqueUrls.length > 0) {
          const newUrls = uniqueUrls.map((url) => ({
            id: url,
            type: sourceType,
            url: url,
            status: "NOT_PROCESSED",
            newAddedSource: true
          }));

          onAddUrls(newUrls);
          form.setValue(`${sourceType}Links`, [
            ...(form.getValues(`${sourceType}Links`) || []),
            ...newUrls.map((url) => url.url)
          ]);
        } else {
          onAddUrls([]);
          form.setValue(`${sourceType}Links`, []);
        }
      } else {
        onAddUrls([]);
        form.setValue(`${sourceType}Links`, []);
      }

      // Reset showCrawlInput when closing
      if (showCrawlInput) {
        setShowCrawlInput(false);
        setCrawlUrl("");
      }

      setTimeout(() => {
        document.body.style.pointerEvents = "";
      }, 500);
      onOpenChange(false);
    }, [
      editorContent,
      form,
      isCrawling,
      isLoadingSitemap,
      onAddUrls,
      onOpenChange,
      sourceType,
      setShowCrawlInput
    ]);

    const handleConfirmStop = React.useCallback(async () => {
      if (isClosing) return;
      setIsClosing(true);

      try {
        if (processType === "crawling") {
          await onStopCrawl();
        } else {
          // Reset loading state for both sitemap and youtube
          updateSitemapLoadingState(false);
        }

        await new Promise((resolve) => setTimeout(resolve, 100));
        setShowStopConfirmation(false);

        if (stopAction === "close") {
          // Reset states before closing
          if (processType === "crawling") {
            setShowCrawlInput(false);
            setCrawlUrl("");
          }
          onOpenChange(false);
        }
      } finally {
        setIsClosing(false);
        setStopAction(null);
        setProcessType("crawling");
      }
    }, [
      onStopCrawl,
      onOpenChange,
      stopAction,
      processType,
      setShowCrawlInput,
      updateSitemapLoadingState
    ]);

    const handleDialogClose = React.useCallback(
      (e) => {
        e?.preventDefault();
        handleClose();
      },
      [handleClose]
    );

    return (
      <>
        <Dialog
          open={isOpen}
          onOpenChange={(open) => {
            if (!open && !isClosing) {
              handleClose();
            } else if (open) {
              document.body.style.pointerEvents = "none";
            }
          }}>
          <StyledDialogContent isMobile={isMobile}>
            <div className="flex flex-col h-full overflow-hidden">
              <div className="guru-sm:hidden guru-md:flex guru-lg:flex px-5 py-6 items-center gap-5 border-b border-gray-85 bg-gray-25 sticky top-0 z-10">
                <div className="flex-grow">
                  <h2 className="text-h5 font-semibold mb-1">
                    {clickedSource?.length > 0
                      ? `Edit ${title}`
                      : `Add ${title}`}
                  </h2>
                </div>
                <Button
                  size="icon"
                  variant="ghost"
                  disabled={isClosing}
                  onClick={handleDialogClose}>
                  <X className="h-6 w-6 text-gray-400" />
                  <span className="sr-only">Close</span>
                </Button>
              </div>

              <div className="flex-1 overflow-hidden p-4">
                {clickedSource?.length === 0 ? (
                  <MonacoUrlEditor
                    placeholder={`Add multiple ${title} with a new line`}
                    title={`${title}`}
                    tooltipText={`Add multiple ${title} with a new line`}
                    value={editorContent}
                    onChange={onEditorChange}
                    sourceType={sourceType}
                    onStartCrawl={onStartCrawl}
                    isCrawling={isCrawling}
                    onStopCrawl={() => handleProcessStop("stop", "crawling")}
                    showCrawlInput={showCrawlInput}
                    setShowCrawlInput={setShowCrawlInput}
                    crawlUrl={crawlUrl}
                    setCrawlUrl={setCrawlUrl}
                    isLoadingSitemapRef={isLoadingSitemapRef}
                    onSitemapLoadingChange={updateSitemapLoadingState}
                    onStopSitemapLoading={() =>
                      handleProcessStop(
                        "stop",
                        sourceType === "website" ? "sitemap" : "youtube"
                      )
                    }
                  />
                ) : (
                  <div className="h-full">
                    <UrlTableContent
                      clickedSource={clickedSource}
                      initialActiveTab={initialActiveTab}
                      selectedUrls={selectedUrls}
                      setSelectedUrls={setSelectedUrls}
                      onDeleteUrls={(urls) => {
                        handleDeleteUrls({
                          urlIds: urls,
                          sourceType,
                          setSources,
                          setDirtyChanges,
                          clickedSource,
                          setClickedSource,
                          onOpenChange,
                          form
                        });
                      }}
                    />
                  </div>
                )}
              </div>
            </div>
          </StyledDialogContent>
        </Dialog>

        <ProcessStopConfirmationDialog
          isOpen={showStopConfirmation}
          onOpenChange={setShowStopConfirmation}
          onConfirm={handleConfirmStop}
          isClosing={isClosing}
          action={stopAction}
          processType={processType}
        />
      </>
    );
  }
);

SourceDialog.displayName = "SourceDialog";

export default SourceDialog;
