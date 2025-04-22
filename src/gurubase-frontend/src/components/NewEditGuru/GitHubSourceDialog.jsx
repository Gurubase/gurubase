import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { isValidUrl } from "@/utils/common";
import { Checkbox } from "@/components/ui/checkbox";

const Dialog = DialogPrimitive.Root;
const DialogPortal = DialogPrimitive.Portal;

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

const GitHubSourceDialog = React.memo(
  ({
    isOpen,
    onOpenChange,
    repoUrl,
    globPattern,
    onRepoUrlChange,
    onGlobPatternChange,
    onAddGithubRepo,
    isMobile,
    isProcessing,
    isEditingRepo,
    editingRepo
  }) => {
    const [isClosing, setIsClosing] = React.useState(false);
    const [urlError, setUrlError] = React.useState("");
    const [includeGlobPattern, setIncludeGlobPattern] = React.useState(false);

    // Reset state when dialog is opened
    React.useEffect(() => {
      if (isOpen) {
        setUrlError("");
        // Only reset include pattern if we're not editing
        if (!isEditingRepo) {
          setIncludeGlobPattern(false);
        }
      }
    }, [isOpen, isEditingRepo]);

    // When editing, populate the form with existing data
    React.useEffect(() => {
      if (isEditingRepo && editingRepo) {
        // If we're in edit mode, set the includeGlobPattern based on the repo settings
        setIncludeGlobPattern(!!editingRepo.include_glob);
      }
    }, [isEditingRepo, editingRepo]);

    const handleClose = React.useCallback(() => {
      setTimeout(() => {
        document.body.style.pointerEvents = "";
      }, 500);
      onOpenChange(false);
    }, [onOpenChange]);

    const handleDialogClose = React.useCallback(
      (e) => {
        e?.preventDefault();
        handleClose();
      },
      [handleClose]
    );

    const validateUrl = React.useCallback((url) => {
      if (!url) {
        setUrlError("Repository URL is required");
        return false;
      }

      if (!isValidUrl(url)) {
        setUrlError("Please enter a valid URL");
        return false;
      }

      // Check if it's a GitHub URL
      if (!url.includes("github.com")) {
        setUrlError("URL must be from github.com");
        return false;
      }

      setUrlError("");
      return true;
    }, []);

    const handleSubmit = React.useCallback(
      (e) => {
        e.preventDefault();

        if (validateUrl(repoUrl)) {
          // Only include glob pattern if it's enabled
          const finalGlobPattern = globPattern || "";
          onAddGithubRepo(
            repoUrl,
            finalGlobPattern,
            includeGlobPattern,
            isEditingRepo ? editingRepo.id : null
          );
          handleClose();
        }
      },
      [
        repoUrl,
        globPattern,
        includeGlobPattern,
        onAddGithubRepo,
        handleClose,
        validateUrl,
        isEditingRepo,
        editingRepo
      ]
    );

    return (
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
                  {isEditingRepo
                    ? "Edit GitHub Repository"
                    : "Add GitHub Repository"}
                </h2>
                <p className="text-sm text-gray-500">
                  {isEditingRepo
                    ? "Update glob pattern for this repository"
                    : "Add a GitHub repository to index its code for your guru"}
                </p>
              </div>
              <Button
                size="icon"
                variant="ghost"
                disabled={isClosing || isProcessing}
                onClick={handleDialogClose}>
                <X className="h-6 w-6 text-gray-400" />
                <span className="sr-only">Close</span>
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="repoUrl">
                    Repository URL <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="repoUrl"
                    placeholder="https://github.com/username/repository"
                    value={repoUrl}
                    onChange={(e) => onRepoUrlChange(e.target.value)}
                    className={urlError ? "border-red-500" : ""}
                    required
                    readOnly={isEditingRepo}
                    disabled={isEditingRepo}
                  />
                  {urlError ? (
                    <p className="text-xs text-red-500">{urlError}</p>
                  ) : (
                    <p className="text-xs text-gray-500">
                      Enter the full URL to the GitHub repository
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="globPattern">Glob Pattern (Optional)</Label>
                  <Input
                    id="globPattern"
                    placeholder="e.g., *.md, docs/**/*.js"
                    value={globPattern}
                    onChange={(e) => onGlobPatternChange(e.target.value)}
                  />

                  {globPattern && (
                    <div className="">
                      <div className="flex items-center space-x-3">
                        <div className="flex h-6 items-center space-x-2 mt-2">
                          <Checkbox
                            id="includePattern"
                            checked={includeGlobPattern}
                            onCheckedChange={setIncludeGlobPattern}
                            className="h-5 w-5 border-2"
                          />
                          <Label
                            htmlFor="includePattern"
                            className="font-regular cursor-pointer text-base">
                            Include/Exclude
                          </Label>
                        </div>
                      </div>
                      <p className="mt-1 text-sm text-gray-600">
                        {includeGlobPattern
                          ? "Files matching the pattern will be included."
                          : "Files matching the pattern will be excluded."}
                      </p>
                    </div>
                  )}

                  {!globPattern && (
                    <p className="text-xs text-gray-500 mt-1">
                      Specify file patterns to include. Leave empty to include
                      all files.
                    </p>
                  )}
                </div>

                <div className="flex justify-end gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleDialogClose}
                    disabled={isProcessing}>
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    disabled={!repoUrl || !!urlError || isProcessing}>
                    {isProcessing ? (
                      <>
                        <span className="mr-2">⧗</span>
                        Processing...
                      </>
                    ) : isEditingRepo ? (
                      "Update Repository"
                    ) : (
                      "Add Repository"
                    )}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        </StyledDialogContent>
      </Dialog>
    );
  }
);

GitHubSourceDialog.displayName = "GitHubSourceDialog";

export default GitHubSourceDialog;
