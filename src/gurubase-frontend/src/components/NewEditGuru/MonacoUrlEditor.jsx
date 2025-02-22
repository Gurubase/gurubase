import dynamic from "next/dynamic";
import { useState, useRef, useEffect } from "react";
import { Icon } from "@iconify/react";

import { SolarInfoCircleBold } from "@/components/Icons";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "@/components/ui/tooltip";
import { Input } from "@/components/ui/input";
import { LoaderCircle, Spider } from "lucide-react";
import { CustomToast } from "@/components/CustomToast";
import { parseSitemapUrls } from "@/app/actions";

// Add this dynamic import for MonacoEditor
const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false
});

const editorOptions = {
  minimap: { enabled: false },
  lineNumbers: "on",
  lineNumbersMinChars: 2,
  scrollBeyondLastLine: true,
  wordWrap: "on",
  automaticLayout: true,
  mouseWheelZoom: false,
  pinchZoom: false,
  scrollbar: {
    vertical: "hidden",
    horizontal: "hidden",
    useShadows: false
  },
  overviewRulerBorder: false,
  hideCursorInOverviewRuler: true,
  contextmenu: false,
  quickSuggestions: false,
  suggestOnTriggerCharacters: false,
  snippetSuggestions: "none",
  wordBasedSuggestions: false,
  parameterHints: {
    enabled: false
  },
  folding: false,
  renderLineHighlight: "none",
  matchBrackets: "never",
  selectionHighlight: false,
  occurrencesHighlight: false,
  links: false,
  colorDecorators: false,
  hover: {
    enabled: false
  },
  find: {
    addExtraSpaceOnTop: false,
    autoFindInSelection: "never",
    seedSearchStringFromSelection: false
  },
  lineDecorationsWidth: 15,
  glyphMargin: false
};

const MonacoUrlEditor = ({
  title,
  tooltipText,
  value,
  onChange,
  placeholder,
  onStartCrawl,
  isCrawling,
  onStopCrawl,
  showCrawlInput,
  setShowCrawlInput,
  crawlUrl,
  setCrawlUrl
}) => {
  const editorRef = useRef(null);
  const [sitemapUrl, setSitemapUrl] = useState("");
  const [isLoadingSitemap, setIsLoadingSitemap] = useState(false);
  const [showSitemapInput, setShowSitemapInput] = useState(false);
  const [startingCrawl, setStartingCrawl] = useState(false);
  const [stoppingCrawl, setStoppingCrawl] = useState(false);
  const prevValueRef = useRef(value);

  // Update editor options to include readOnly based on isCrawling state
  const currentEditorOptions = {
    ...editorOptions,
    readOnly: isCrawling
  };

  // Effect to handle auto-scrolling when new URLs are added
  useEffect(() => {
    if (
      editorRef.current &&
      value &&
      value !== prevValueRef.current &&
      isCrawling
    ) {
      const editor = editorRef.current;
      const model = editor.getModel();
      if (model) {
        const lineCount = model.getLineCount();
        editor.revealLine(lineCount);
      }
    }
    prevValueRef.current = value;
  }, [value, isCrawling]);

  const handleSitemapParse = async () => {
    if (!sitemapUrl) {
      CustomToast({
        message: "Please enter a sitemap URL",
        variant: "error"
      });
      return;
    }

    if (!sitemapUrl.endsWith(".xml")) {
      CustomToast({
        message: "Sitemap URL must end with .xml",
        variant: "error"
      });
      return;
    }

    try {
      setIsLoadingSitemap(true);
      const response = await parseSitemapUrls(sitemapUrl);

      if (response.error || response.msg) {
        CustomToast({
          message: response.message || "Failed to parse sitemap",
          variant: response.urls ? "warning" : "error"
        });
        return;
      }

      const { urls, total_urls } = response;
      if (urls && urls.length > 0) {
        // Get current editor content
        const currentContent = value || "";
        const existingUrls = currentContent
          .split("\n")
          .filter((url) => url.trim());

        // Combine existing URLs with new ones and remove duplicates
        const allUrls = [...new Set([...existingUrls, ...urls])];

        // Update the editor content
        const newContent = allUrls.join("\n");
        onChange(newContent);

        // Clear the input field
        setSitemapUrl("");

        CustomToast({
          message: `Successfully added ${total_urls} URLs from sitemap`,
          variant: "success"
        });
      } else {
        CustomToast({
          message: response.msg || "No URLs found in the sitemap",
          variant: "warning"
        });
      }
      setShowSitemapInput(false);
    } catch (error) {
      CustomToast({
        message:
          error.message ||
          "An unexpected error occurred while parsing the sitemap",
        variant: "error"
      });
    } finally {
      setIsLoadingSitemap(false);
    }
  };

  const handleCrawlStart = async (url) => {
    setStartingCrawl(true);
    try {
      await onStartCrawl(url);
    } finally {
      setStartingCrawl(false);
    }
  };

  const handleCrawlStop = async () => {
    setStoppingCrawl(true);
    try {
      await onStopCrawl();
    } finally {
      setStoppingCrawl(false);
    }
  };

  const buttonContent = () => {
    if (!isCrawling) {
      return (
        <Button
          className="h-8 guru-sm:flex-1"
          disabled={!crawlUrl || startingCrawl}
          onClick={() => handleCrawlStart(crawlUrl)}
          variant="outline">
          Start Crawling
        </Button>
      );
    } else {
      if (stoppingCrawl) {
        return (
          <Button
            className="h-8 guru-sm:flex-1 bg-red-50 hover:bg-red-100 text-red-600 border-red-200"
            onClick={handleCrawlStop}
            disabled={stoppingCrawl}
            variant="outline">
            <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
            Stopping...
          </Button>
        );
      } else if (startingCrawl) {
        return (
          <Button
            className="h-8 guru-sm:flex-1"
            onClick={handleCrawlStop}
            disabled={stoppingCrawl}
            variant="outline">
            <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
            Starting...
          </Button>
        );
      } else {
        return (
          <Button
            className="h-8 guru-sm:flex-1 bg-red-50 hover:bg-red-100 text-red-600 border-red-200"
            onClick={handleCrawlStop}
            disabled={stoppingCrawl}
            variant="outline">
            <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
            Stop
          </Button>
        );
      }
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-none">
        <div
          className={`flex items-center justify-between h-8 mb-3 guru-sm:flex-col guru-sm:h-auto guru-sm:items-start gap-2 ${showSitemapInput || showCrawlInput ? "guru-sm:flex-col guru-sm:h-auto guru-sm:gap-2" : ""}`}>
          <div className="flex items-center space-x-1">
            <h3 className="text-sm font-semibold">{title}</h3>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div>
                    <SolarInfoCircleBold className="h-4 w-4 text-gray-200" />
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{tooltipText}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          {title === "Website Links" && (
            <div className={`flex items-center gap-2 guru-sm:w-full`}>
              {!showSitemapInput && !showCrawlInput ? (
                <div className="flex items-center gap-2 guru-sm:flex-col guru-sm:w-full">
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8 px-2 hover:bg-gray-100 flex items-center gap-1.5 guru-sm:w-full"
                          onClick={() => setShowSitemapInput(true)}>
                          <Icon icon="mdi:sitemap" className="h-4 w-4" />
                          <span className="text-sm">Import from Sitemap</span>
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Import URLs from your website's sitemap.xml file</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8 px-2 hover:bg-gray-100 flex items-center gap-1.5 guru-sm:w-full"
                          onClick={() => setShowCrawlInput(true)}>
                          <Icon icon="mdi:spider" className="h-4 w-4" />
                          <span className="text-sm">Crawl Website</span>
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent side="right">
                        <p>
                          Automatically discover and import URLs by crawling
                          your website
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              ) : showSitemapInput ? (
                <div className="flex items-center gap-2 animate-in slide-in-from-right-5 guru-sm:w-full guru-sm:flex-col">
                  <Input
                    className="w-[300px] h-8 guru-sm:w-full"
                    placeholder="https://example.com/sitemap.xml"
                    value={sitemapUrl}
                    onChange={(e) => setSitemapUrl(e.target.value)}
                  />
                  <div className="flex items-center gap-2 guru-sm:w-full">
                    <Button
                      className="h-8 guru-sm:flex-1"
                      disabled={isLoadingSitemap || !sitemapUrl}
                      onClick={handleSitemapParse}
                      variant="outline">
                      {isLoadingSitemap ? (
                        <>
                          <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                          Fetching...
                        </>
                      ) : (
                        "Parse Sitemap"
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 px-2 hover:bg-gray-100"
                      onClick={() => {
                        setShowSitemapInput(false);
                        setSitemapUrl("");
                      }}>
                      ✕
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2 animate-in slide-in-from-right-5 guru-sm:w-full guru-sm:flex-col">
                  <Input
                    className="w-[300px] h-8 guru-sm:w-full"
                    placeholder="https://example.com"
                    value={crawlUrl}
                    onChange={(e) => setCrawlUrl(e.target.value)}
                    disabled={isCrawling}
                  />
                  <div className="flex items-center gap-2 guru-sm:w-full">
                    {buttonContent()}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 px-2 hover:bg-gray-100"
                      onClick={() => {
                        setShowCrawlInput(false);
                        setCrawlUrl("");
                      }}
                      disabled={isCrawling}>
                      ✕
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      <div className="flex-1 min-h-0">
        <div className="border rounded-[8px] p-1 h-full relative">
          <MonacoEditor
            height="100%"
            language="plaintext"
            options={currentEditorOptions}
            theme="vs-light"
            value={value}
            onChange={onChange}
            onMount={(editor) => {
              editorRef.current = editor;
            }}
          />
          {!value && (
            <div className="monaco-placeholder absolute top-0 left-0 right-0 bottom-0 pointer-events-none">
              <div className="pl-[35px] pt-[3px] text-gray-400 text-[13px]">
                {placeholder}
              </div>
            </div>
          )}
          {isCrawling && (
            <div className="absolute top-0 left-0 right-0 bottom-0 bg-gray-50/50 flex items-center justify-center pointer-events-none">
              <div className="flex items-center gap-2 text-gray-500 bg-white px-4 py-2 rounded-lg shadow-sm">
                <LoaderCircle className="h-4 w-4 animate-spin" />
                <span>Crawling website...</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MonacoUrlEditor;
