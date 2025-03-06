"use client";
import { Check } from "lucide-react";
import { Highlight, themes } from "prism-react-renderer";
import { useState } from "react";

import { deleteWidgetId } from "@/app/actions";
import { SolarTrashBinTrashBold } from "@/components/Icons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from "@/components/ui/modal-dialog.jsx";
import { CustomToast } from "@/components/CustomToast";

export default function WidgetModal({
  widgetId,
  domainUrl,
  guruSlug,
  isLast,
  isFirst,
  onDelete
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";
  const widgetScript = `<!-- Gurubase Widget -->
<script async src="https://widget.gurubase.io/widget.latest.min.js" 
    data-widget-id="${widgetId}"
    data-text="Ask AI"
    data-margins='{"bottom": "1rem", "right": "1rem"}'
    data-light-mode="true"${isSelfHosted
      ? `
    data-baseUrl="http://localhost:8029/api/"  <!-- If you haven't changed it, this is the default Gurubase Self-Hosted backend URL. -->`
      : ""
    }
    id="guru-widget-id">
</script>`;

  const copyToClipboard = async (text, type) => {
    await navigator.clipboard.writeText(text);
    setCopied(type);
    setTimeout(() => setCopied(null), 2000);
  };

  const handleDeleteClick = () => {
    setShowDeleteDialog(true);
  };

  const handleConfirmDelete = async () => {
    setIsDeleting(true);
    try {
      const { success, message } = await deleteWidgetId(guruSlug, widgetId);

      if (!success) {
        CustomToast({
          message: message,
          variant: "error"
        });
      }

      // Call the onDelete callback after successful deletion
      onDelete?.();
    } catch (error) {
      // console.error("error", error);
    } finally {
      // First close the dialog
      setShowDeleteDialog(false);
      // Then after a small delay, reset the deleting state
      setTimeout(() => {
        setIsDeleting(false);
      }, 300); // 300ms matches the dialog's fade-out animation
    }
  };

  const CopyIcon = () => (
    <svg
      fill="none"
      height="17"
      viewBox="0 0 16 17"
      width="16"
      xmlns="http://www.w3.org/2000/svg">
      <path
        d="M10.16 1.83203H7.56389C6.38773 1.83202 5.45612 1.83201 4.72703 1.93043C3.97668 2.03172 3.36935 2.24513 2.8904 2.726C2.41144 3.20688 2.19889 3.81665 2.09801 4.57001C1.99998 5.30203 1.99999 6.23738 2 7.41826V11.3099C2 12.3154 2.6133 13.177 3.48478 13.5382C3.43992 12.9319 3.43996 12.0811 3.44 11.3734L3.44 8.09709L3.44 8.03364C3.43995 7.1792 3.43991 6.44299 3.51886 5.85344C3.60346 5.22162 3.79426 4.61598 4.28353 4.12474C4.77281 3.63349 5.37603 3.44193 6.00532 3.35699C6.59251 3.27772 7.32578 3.27776 8.1768 3.27781L8.24 3.27782H10.16L10.2232 3.27781C11.0742 3.27776 11.8059 3.27772 12.3931 3.35699C12.0418 2.46389 11.1744 1.83203 10.16 1.83203Z"
        fill="currentColor"
      />
      <path
        d="M4.40039 8.09761C4.40039 6.28015 4.40039 5.37141 4.96275 4.8068C5.5251 4.24219 6.4302 4.24219 8.24039 4.24219H10.1604C11.9706 4.24219 12.8757 4.24219 13.438 4.8068C14.0004 5.37141 14.0004 6.28015 14.0004 8.09761V11.3105C14.0004 13.1279 14.0004 14.0367 13.438 14.6013C12.8757 15.1659 11.9706 15.1659 10.1604 15.1659H8.24039C6.4302 15.1659 5.5251 15.1659 4.96275 14.6013C4.40039 14.0367 4.40039 13.1279 4.40039 11.3105V8.09761Z"
        fill="currentColor"
      />
    </svg>
  );

  return (
    <div className="flex flex-col">
      <div className={`${isFirst ? "pb-6" : "py-6"} flex items-center`}>
        <div className="flex items-center gap-3 w-[440px]">
          <div className="relative w-full md:w-[300px]">
            <span className="absolute left-3 top-2 text-xs font-normal text-gray-500">
              Domain
            </span>
            <Input
              readOnly
              className="bg-gray-50 pt-8 pb-2"
              value={domainUrl}
            />
          </div>
          <Button
            className="gap-2 rounded-lg"
            size="action2"
            type="button"
            variant="default"
            onClick={() => setIsOpen(true)}>
            <svg
              fill="none"
              height="20"
              viewBox="0 0 20 20"
              width="20"
              xmlns="http://www.w3.org/2000/svg">
              <path
                d="M8.12533 9.9987C8.12533 8.96316 8.96479 8.1237 10.0003 8.1237C11.0359 8.1237 11.8753 8.96316 11.8753 9.9987C11.8753 11.0342 11.0359 11.8737 10.0003 11.8737C8.96479 11.8737 8.12533 11.0342 8.12533 9.9987Z"
                fill="white"
              />
              <path
                clipRule="evenodd"
                d="M1.66699 9.9987C1.66699 11.3648 2.02113 11.8249 2.7294 12.7451C4.14363 14.5824 6.51542 16.6654 10.0003 16.6654C13.4852 16.6654 15.857 14.5824 17.2712 12.7451C17.9795 11.8249 18.3337 11.3648 18.3337 9.9987C18.3337 8.63255 17.9795 8.17247 17.2712 7.25231C15.857 5.415 13.4852 3.33203 10.0003 3.33203C6.51542 3.33203 4.14363 5.415 2.7294 7.25231C2.02113 8.17247 1.66699 8.63255 1.66699 9.9987ZM10.0003 6.8737C8.27444 6.8737 6.87533 8.27281 6.87533 9.9987C6.87533 11.7246 8.27444 13.1237 10.0003 13.1237C11.7262 13.1237 13.1253 11.7246 13.1253 9.9987C13.1253 8.27281 11.7262 6.8737 10.0003 6.8737Z"
                fill="white"
                fillRule="evenodd"
              />
            </svg>
            Show &lt;/&gt;
          </Button>
        </div>
        <Button
          className={`text-[#BABFC8] hover:text-[#DC2626] transition-colors hover:bg-transparent [display:revert] pl-2 ${isDeleting ? "opacity-50 cursor-not-allowed" : ""
            }`}
          disabled={isDeleting}
          size="icon"
          type="button"
          variant="ghost"
          onClick={handleDeleteClick}>
          <svg
            fill="none"
            height="24"
            viewBox="0 0 24 24"
            width="24"
            xmlns="http://www.w3.org/2000/svg">
            <path
              d="M3 6.38597C3 5.90152 3.34538 5.50879 3.77143 5.50879L6.43567 5.50832C6.96502 5.49306 7.43202 5.11033 7.61214 4.54412C7.61688 4.52923 7.62232 4.51087 7.64185 4.44424L7.75665 4.05256C7.8269 3.81241 7.8881 3.60318 7.97375 3.41617C8.31209 2.67736 8.93808 2.16432 9.66147 2.03297C9.84457 1.99972 10.0385 1.99986 10.2611 2.00002H13.7391C13.9617 1.99986 14.1556 1.99972 14.3387 2.03297C15.0621 2.16432 15.6881 2.67736 16.0264 3.41617C16.1121 3.60318 16.1733 3.81241 16.2435 4.05256L16.3583 4.44424C16.3778 4.51087 16.3833 4.52923 16.388 4.54412C16.5682 5.11033 17.1278 5.49353 17.6571 5.50879H20.2286C20.6546 5.50879 21 5.90152 21 6.38597C21 6.87043 20.6546 7.26316 20.2286 7.26316H3.77143C3.34538 7.26316 3 6.87043 3 6.38597Z"
              fill="currentColor"
            />
            <path
              clipRule="evenodd"
              d="M11.5956 22.0001H12.4044C15.1871 22.0001 16.5785 22.0001 17.4831 21.1142C18.3878 20.2283 18.4803 18.7751 18.6654 15.8686L18.9321 11.6807C19.0326 10.1037 19.0828 9.31524 18.6289 8.81558C18.1751 8.31592 17.4087 8.31592 15.876 8.31592H8.12404C6.59127 8.31592 5.82488 8.31592 5.37105 8.81558C4.91722 9.31524 4.96744 10.1037 5.06788 11.6807L5.33459 15.8686C5.5197 18.7751 5.61225 20.2283 6.51689 21.1142C7.42153 22.0001 8.81289 22.0001 11.5956 22.0001ZM10.2463 12.1886C10.2051 11.7548 9.83753 11.4382 9.42537 11.4816C9.01321 11.525 8.71251 11.9119 8.75372 12.3457L9.25372 17.6089C9.29494 18.0427 9.66247 18.3593 10.0746 18.3159C10.4868 18.2725 10.7875 17.8856 10.7463 17.4518L10.2463 12.1886ZM14.5746 11.4816C14.9868 11.525 15.2875 11.9119 15.2463 12.3457L14.7463 17.6089C14.7051 18.0427 14.3375 18.3593 13.9254 18.3159C13.5132 18.2725 13.2125 17.8856 13.2537 17.4518L13.7537 12.1886C13.7949 11.7548 14.1625 11.4382 14.5746 11.4816Z"
              fill="currentColor"
              fillRule="evenodd"
            />
          </svg>
        </Button>
      </div>
      {!isLast && <div className="border-b border-[#E2E2E2] w-[440px]" />}

      <Dialog modal={true} open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="sm:max-w-[700px] p-8 animate-in fade-in-0 zoom-in-95 duration-200">
          <DialogHeader className="mb-0">
            <DialogTitle className="text-[#191919] font-inter text-[20px] font-semibold">
              Add Widget
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-8">
            <p className="text-[#6D6D6D] font-inter text-[14px] font-normal">
              The Widget ID is a unique identifier for each domain. To add the
              widget, inject the Widget Script into your website. Here is the
              guide to{" "}
              <a
                className="text-blue-600 hover:underline"
                href="https://github.com/getanteon/gurubase-widget"
                rel="noreferrer"
                target="_blank">
                learn more
              </a>
              .
            </p>

            <div className="space-y-2">
              <h3 className="text-[#191919] font-inter text-[14px] font-semibold">
                Widget ID
              </h3>
              <div className="relative">
                <div className="bg-[#011727] text-white font-inter text-[12px] font-normal p-4 rounded-lg">
                  {widgetId}
                  <Button
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-[#FFFFFF]"
                    size="icon"
                    variant="link"
                    onClick={() => copyToClipboard(widgetId, "id")}>
                    {copied === "id" ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <CopyIcon />
                    )}
                  </Button>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <h3 className="text-[#191919] font-inter text-[14px] font-semibold">
                Widget Script
              </h3>
              <div className="relative">
                <div className="bg-[#011727] text-white font-inter text-[12px] font-normal p-4 rounded-lg">
                  <Highlight
                    code={widgetScript}
                    language="html"
                    theme={themes.nightOwl}>
                    {({
                      className,
                      style,
                      tokens,
                      getLineProps,
                      getTokenProps
                    }) => (
                      <pre
                        className={`${className} whitespace-pre-wrap break-all`}
                        style={style}>
                        {tokens.map((line, i) => (
                          <div key={i} {...getLineProps({ line })}>
                            {line.map((token, key) => (
                              <span key={key} {...getTokenProps({ token })} />
                            ))}
                          </div>
                        ))}
                      </pre>
                    )}
                  </Highlight>
                  <Button
                    className="absolute right-2 top-4 text-[#FFFFFF]"
                    size="icon"
                    variant="link"
                    onClick={() => copyToClipboard(widgetScript, "script")}>
                    {copied === "script" ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <CopyIcon />
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent className="max-w-[400px] p-0">
          <div className="p-6 text-center">
            <DialogHeader>
              <div className="mx-auto mb-4 h-[60px] w-[60px] rounded-full text-gray-600">
                <SolarTrashBinTrashBold className="h-full w-full" />
              </div>
              <DialogTitle className="text-base font-semibold text-center text-[#191919] font-inter">
                Delete Widget
              </DialogTitle>
              <DialogDescription className="text-[14px] text-[#6D6D6D] text-center font-inter font-normal">
                Are you sure you want to delete this widget?
              </DialogDescription>
            </DialogHeader>
            <div className="mt-6 flex flex-col gap-2">
              <Button
                className={`h-12 px-6 justify-center items-center rounded-lg bg-[#DC2626] hover:bg-red-700 text-white ${isDeleting ? "opacity-50 cursor-not-allowed" : ""
                  }`}
                disabled={isDeleting}
                onClick={handleConfirmDelete}>
                {isDeleting ? "Deleting..." : "Delete"}
              </Button>
              <Button
                className="h-12 px-4 justify-center items-center rounded-lg border border-[#1B242D] bg-white"
                disabled={isDeleting}
                variant="outline"
                onClick={() => setShowDeleteDialog(false)}>
                Cancel
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
