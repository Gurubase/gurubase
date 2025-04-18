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
import {
  parseSitemapUrls,
  fetchYoutubePlaylist,
  fetchYoutubeChannel,
  fetchJiraIssues,
  fetchZendeskTickets,
  fetchZendeskArticles
} from "@/app/actions";

// Add this dynamic import for MonacoEditor
const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => <div>Loading editor...</div>
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
  setCrawlUrl,
  isLoadingSitemapRef,
  onSitemapLoadingChange,
  onStopSitemapLoading,
  sourceType,
  isYoutubeKeyValid,
  integrationId
}) => {
  const editorRef = useRef(null);
  const [sitemapUrl, setSitemapUrl] = useState("");
  const [showSitemapInput, setShowSitemapInput] = useState(false);
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [showYoutubeInput, setShowYoutubeInput] = useState(false);
  const [youtubeType, setYoutubeType] = useState("");
  const defaultJQL = `status in ("Done", "Closed")`;
  const [jiraQuery, setJiraQuery] = useState(defaultJQL);
  const [showJiraInput, setShowJiraInput] = useState(true);
  const [showZendeskButton, setShowZendeskButton] = useState(true);
  const [startingCrawl, setStartingCrawl] = useState(false);
  const [stoppingCrawl, setStoppingCrawl] = useState(false);
  const prevValueRef = useRef(value);
  const [loadingType, setLoadingType] = useState(null);

  // Update editor options to include readOnly based on isCrawling state
  const currentEditorOptions = {
    ...editorOptions,
    readOnly: isCrawling || isLoadingSitemapRef.current
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
      onSitemapLoadingChange(true);
      const response = await parseSitemapUrls(sitemapUrl);
      // If the sitemap loading state was reset (due to stop action), don't process the response
      if (!isLoadingSitemapRef.current) {
        return;
      }

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
      onSitemapLoadingChange(false);
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

  const handleYoutubeImport = async () => {
    if (!youtubeUrl) {
      CustomToast({
        message: "Please enter a YouTube URL",
        variant: "error"
      });
      return;
    }

    try {
      onSitemapLoadingChange(true);
      const response =
        youtubeType === "playlist"
          ? await fetchYoutubePlaylist(youtubeUrl)
          : await fetchYoutubeChannel(youtubeUrl);

      // If the loading state was reset (due to stop action), don't process the response
      if (!isLoadingSitemapRef.current) {
        return;
      }

      if (response.error || response.msg) {
        CustomToast({
          message: response.message || "Failed to import YouTube URLs",
          variant: response.urls ? "warning" : "error"
        });
        return;
      }

      const { videos, video_count } = response;
      if (videos && videos.length > 0) {
        // Get current editor content
        const currentContent = value || "";
        const existingUrls = currentContent
          .split("\n")
          .filter((url) => url.trim());

        // Combine existing URLs with new ones and remove duplicates
        const allUrls = [...new Set([...existingUrls, ...videos])];

        // Update the editor content
        const newContent = allUrls.join("\n");
        onChange(newContent);

        // Clear the input field
        setYoutubeUrl("");

        CustomToast({
          message: `Successfully added ${video_count} URLs from YouTube ${youtubeType}`,
          variant: "success"
        });
      } else {
        CustomToast({
          message: response.msg || "No URLs found in the YouTube source",
          variant: "warning"
        });
      }
      setShowYoutubeInput(false);
    } catch (error) {
      CustomToast({
        message:
          error.message ||
          "An unexpected error occurred while importing YouTube URLs",
        variant: "error"
      });
    } finally {
      onSitemapLoadingChange(false);
    }
  };

  const handleJiraFetch = async () => {
    try {
      onSitemapLoadingChange(true);
      const response = await fetchJiraIssues(integrationId, jiraQuery);

      if (!isLoadingSitemapRef.current) {
        return;
      }

      if (response.error || response.message || !response.issues) {
        CustomToast({
          message: response.message || "Failed to fetch Jira issues",
          variant: "error"
        });

        return;
      }

      const { issues, issue_count } = response;
      if (issues && issues.length > 0) {
        const fetchedUrls = issues.map((issue) => issue.link);
        const currentContent = value || "";
        const existingUrls = currentContent
          .split("\n")
          .filter((url) => url.trim());

        const allItems = [...new Set([...existingUrls, ...fetchedUrls])];

        const newContent = allItems.join("\n");
        onChange(newContent);

        // setJiraQuery(defaultJQL);

        CustomToast({
          message: `Successfully added ${issue_count || issues.length} issues from Jira`,
          variant: "success"
        });
        // setShowJiraInput(false);
      } else {
        CustomToast({
          message: response.message || "No issues found for the query",
          variant: "warning"
        });
        // setShowJiraInput(false);
      }
    } catch (error) {
      CustomToast({
        message:
          error.message ||
          "An unexpected error occurred while fetching Jira issues",
        variant: "error"
      });
    } finally {
      onSitemapLoadingChange(false);
    }
  };

  const handleZendeskTicketsFetch = async () => {
    try {
      onSitemapLoadingChange(true);
      setLoadingType("tickets");
      const response = await fetchZendeskTickets(integrationId);

      if (!isLoadingSitemapRef.current) {
        return;
      }

      if (response.error || response.message || !response.tickets) {
        CustomToast({
          message: response.message || "Failed to fetch Zendesk tickets",
          variant: "error"
        });
        return;
      }

      const { tickets, ticket_count } = response;
      if (tickets && tickets.length > 0) {
        const fetchedUrls = tickets.map((ticket) => ticket.link);
        const currentContent = value || "";
        const existingUrls = currentContent
          .split("\n")
          .filter((url) => url.trim());

        const allItems = [...new Set([...existingUrls, ...fetchedUrls])];
        const newContent = allItems.join("\n");
        onChange(newContent);

        CustomToast({
          message: `Successfully added ${ticket_count || tickets.length} tickets from Zendesk`,
          variant: "success"
        });
        // setShowZendeskButton(false); // Optionally hide button after fetch
      } else {
        CustomToast({
          message: response.message || "No tickets found in Zendesk",
          variant: "warning"
        });
      }
    } catch (error) {
      CustomToast({
        message:
          error.message ||
          "An unexpected error occurred while fetching Zendesk tickets",
        variant: "error"
      });
    } finally {
      onSitemapLoadingChange(false);
    }
  };

  const handleZendeskArticlesFetch = async () => {
    try {
      onSitemapLoadingChange(true);
      setLoadingType("articles");
      const response = await fetchZendeskArticles(integrationId);

      if (!isLoadingSitemapRef.current) {
        return;
      }

      if (response.error || response.message || !response.articles) {
        CustomToast({
          message: response.message || "Failed to fetch Zendesk articles",
          variant: "error"
        });
        return;
      }

      const { articles, article_count } = response;
      if (articles && articles.length > 0) {
        const fetchedUrls = articles.map((article) => article.link);
        const currentContent = value || "";
        const existingUrls = currentContent
          .split("\n")
          .filter((url) => url.trim());

        const allItems = [...new Set([...existingUrls, ...fetchedUrls])];
        const newContent = allItems.join("\n");
        onChange(newContent);

        CustomToast({
          message: `Successfully added ${article_count || articles.length} articles from Zendesk`,
          variant: "success"
        });
      } else {
        CustomToast({
          message: response.message || "No articles found in Zendesk",
          variant: "warning"
        });
      }
    } catch (error) {
      CustomToast({
        message:
          error.message ||
          "An unexpected error occurred while fetching Zendesk articles",
        variant: "error"
      });
    } finally {
      onSitemapLoadingChange(false);
      setLoadingType(null);
    }
  };

  const crawlButtonContent = () => {
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

  const sitemapButtonContent = () => {
    if (!isLoadingSitemapRef.current) {
      return (
        <Button
          className="h-8 guru-sm:flex-1"
          disabled={!sitemapUrl}
          onClick={handleSitemapParse}
          variant="outline">
          Parse Sitemap
        </Button>
      );
    } else {
      return (
        <Button
          className="h-8 guru-sm:flex-1 bg-red-50 hover:bg-red-100 text-red-600 border-red-200"
          onClick={() => onStopSitemapLoading()}
          disabled={!isLoadingSitemapRef.current}
          variant="outline">
          <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
          Stop
        </Button>
      );
    }
  };

  const youtubeButtonContent = () => {
    if (!isLoadingSitemapRef.current) {
      return (
        <Button
          className="h-8 guru-sm:flex-1"
          disabled={!youtubeUrl}
          onClick={handleYoutubeImport}
          variant="outline">
          Import {youtubeType === "playlist" ? "Playlist" : "Channel"}
        </Button>
      );
    } else {
      return (
        <Button
          className="h-8 guru-sm:flex-1 bg-red-50 hover:bg-red-100 text-red-600 border-red-200"
          onClick={() => onStopSitemapLoading()}
          disabled={!isLoadingSitemapRef.current}
          variant="outline">
          <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
          Stop
        </Button>
      );
    }
  };

  const jiraButtonContent = () => {
    if (!isLoadingSitemapRef.current) {
      return (
        <Button
          className="h-8 guru-sm:flex-1"
          disabled={isLoadingSitemapRef.current}
          onClick={handleJiraFetch}
          variant="outline">
          Fetch Issues
        </Button>
      );
    } else {
      return (
        <Button
          className="h-8 guru-sm:flex-1 bg-red-50 hover:bg-red-100 text-red-600 border-red-200"
          onClick={() => onStopSitemapLoading()}
          disabled={!isLoadingSitemapRef.current}
          variant="outline">
          <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
          Stop
        </Button>
      );
    }
  };

  const zendeskTicketsButtonContent = () => {
    if (!isLoadingSitemapRef.current) {
      return (
        <Button
          className="h-8 guru-sm:flex-1"
          disabled={isLoadingSitemapRef.current}
          onClick={handleZendeskTicketsFetch}
          variant="outline">
          Fetch Tickets
        </Button>
      );
    } else {
      // Show Stop button only if this specific fetch is loading
      if (loadingType === "tickets") {
        return (
          <Button
            className="h-8 guru-sm:flex-1 bg-red-50 hover:bg-red-100 text-red-600 border-red-200"
            onClick={() => onStopSitemapLoading()}
            disabled={!isLoadingSitemapRef.current}
            variant="outline">
            <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
            Stop
          </Button>
        );
      } else {
        // Otherwise, show the disabled Fetch button
        return (
          <Button
            className="h-8 guru-sm:flex-1"
            disabled={true}
            variant="outline">
            Fetch Tickets
          </Button>
        );
      }
    }
  };

  const zendeskArticlesButtonContent = () => {
    if (!isLoadingSitemapRef.current) {
      return (
        <Button
          className="h-8 guru-sm:flex-1"
          disabled={isLoadingSitemapRef.current}
          onClick={handleZendeskArticlesFetch}
          variant="outline">
          Fetch Articles
        </Button>
      );
    } else {
      // Show Stop button only if this specific fetch is loading
      if (loadingType === "articles") {
        return (
          <Button
            className="h-8 guru-sm:flex-1 bg-red-50 hover:bg-red-100 text-red-600 border-red-200"
            onClick={() => onStopSitemapLoading()} // Use the same stop mechanism
            disabled={!isLoadingSitemapRef.current}
            variant="outline">
            <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
            Stop
          </Button>
        );
      } else {
        // Otherwise, show the disabled Fetch button
        return (
          <Button
            className="h-8 guru-sm:flex-1"
            disabled={true}
            variant="outline">
            Fetch Articles
          </Button>
        );
      }
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-none">
        <div
          className={`flex items-center justify-between h-8 mb-3 guru-sm:flex-col guru-sm:h-auto guru-sm:items-start gap-2 ${showSitemapInput || showCrawlInput || showYoutubeInput || showJiraInput || showZendeskButton ? "guru-sm:flex-col guru-sm:h-auto guru-sm:gap-2" : ""}`}>
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
          {sourceType === "website" && (
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
                    {sitemapButtonContent()}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 px-2 hover:bg-gray-100"
                      disabled={isLoadingSitemapRef.current}
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
                    {crawlButtonContent()}
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
          {sourceType === "jira" && (
            <div className={`flex items-center gap-2 guru-sm:w-full`}>
              {!showJiraInput ? (
                <div className="flex items-center gap-2 guru-sm:flex-col guru-sm:w-full">
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8 px-2 hover:bg-gray-100 flex items-center gap-1.5 guru-sm:w-full"
                          onClick={() => setShowJiraInput(true)}>
                          <Icon icon="mdi:jira" className="h-4 w-4" />
                          <span className="text-sm">Fetch Issues</span>
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Fetch issues using a JQL query</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              ) : (
                <div className="flex items-center gap-2 animate-in slide-in-from-right-5 guru-sm:w-full guru-sm:flex-col">
                  <div className="relative w-full">
                    <span className="absolute left-3 top-2 text-xs font-normal text-gray-500">
                      JQL
                    </span>
                    <Input
                      className="w-[600px] h-10 guru-sm:w-full pt-6"
                      placeholder="Enter JQL Query (Optional)"
                      value={jiraQuery}
                      onChange={(e) => setJiraQuery(e.target.value)}
                      disabled={isLoadingSitemapRef.current}
                    />
                  </div>
                  <div className="flex items-center gap-2 guru-sm:w-full">
                    {jiraButtonContent()}
                    {/* <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 px-2 hover:bg-gray-100"
                      disabled={isLoadingSitemapRef.current}
                      onClick={() => {
                        setShowJiraInput(false);
                        setJiraQuery(defaultJQL);
                      }}>
                      ✕
                    </Button> */}
                  </div>
                </div>
              )}
            </div>
          )}
          {sourceType === "youtube" && (
            <div className={`flex items-center gap-2 guru-sm:w-full`}>
              {!showYoutubeInput ? (
                <div className="flex items-center gap-2 guru-sm:flex-col guru-sm:w-full">
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-8 px-2 hover:bg-gray-100 flex items-center gap-1.5 guru-sm:w-full"
                            onClick={() => {
                              setYoutubeType("playlist");
                              setShowYoutubeInput(true);
                            }}
                            disabled={!isYoutubeKeyValid}>
                            <Icon
                              icon="mdi:playlist-play"
                              className="h-4 w-4"
                            />
                            <span className="text-sm">Import Playlist</span>
                          </Button>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>
                          {isYoutubeKeyValid
                            ? "Import videos from a YouTube playlist"
                            : "YouTube API key is required for this functionality. You can add the API key on the Settings page."}
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-8 px-2 hover:bg-gray-100 flex items-center gap-1.5 guru-sm:w-full"
                            onClick={() => {
                              setYoutubeType("channel");
                              setShowYoutubeInput(true);
                            }}
                            disabled={!isYoutubeKeyValid}>
                            <Icon icon="mdi:youtube" className="h-4 w-4" />
                            <span className="text-sm">Import Channel</span>
                          </Button>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent side="right">
                        <p>
                          {isYoutubeKeyValid
                            ? "Import videos from a YouTube channel"
                            : "YouTube API key is required for this functionality. You can add the API key on the Settings page."}
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              ) : (
                <div className="flex items-center gap-2 animate-in slide-in-from-right-5 guru-sm:w-full guru-sm:flex-col">
                  <Input
                    className="w-[300px] h-8 guru-sm:w-full"
                    placeholder={
                      youtubeType === "playlist"
                        ? "https://www.youtube.com/playlist?list=..."
                        : "https://www.youtube.com/c/..."
                    }
                    value={youtubeUrl}
                    onChange={(e) => setYoutubeUrl(e.target.value)}
                    disabled={isLoadingSitemapRef.current}
                  />
                  <div className="flex items-center gap-2 guru-sm:w-full">
                    {youtubeButtonContent()}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 px-2 hover:bg-gray-100"
                      onClick={() => {
                        setShowYoutubeInput(false);
                        setYoutubeUrl("");
                      }}
                      disabled={isLoadingSitemapRef.current}>
                      ✕
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
          {sourceType === "zendesk" && (
            <div className={`flex items-center gap-2 guru-sm:w-full`}>
              {showZendeskButton && (
                <div className="flex items-center gap-2 animate-in slide-in-from-right-5 guru-sm:w-full guru-sm:flex-col">
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        {zendeskTicketsButtonContent()}
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Fetch tickets from your connected Zendesk account</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        {zendeskArticlesButtonContent()}
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>
                          Fetch articles from your connected Zendesk account
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
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
          {(isCrawling || isLoadingSitemapRef.current) && (
            <div className="absolute top-0 left-0 right-0 bottom-0 bg-gray-50/50 flex items-center justify-center pointer-events-none">
              <div className="flex items-center gap-2 text-gray-500 bg-white px-4 py-2 rounded-lg shadow-sm">
                <LoaderCircle className="h-4 w-4 animate-spin" />
                <span>
                  {isCrawling && "Crawling website..."}
                  {isLoadingSitemapRef.current &&
                    (sourceType === "website"
                      ? "Parsing sitemap..."
                      : sourceType === "youtube"
                        ? `Importing ${youtubeType}...`
                        : sourceType === "jira"
                          ? "Fetching Jira issues..."
                          : sourceType === "zendesk"
                            ? loadingType === "articles"
                              ? "Fetching Zendesk articles..."
                              : "Fetching Zendesk tickets..."
                            : "Loading...")}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MonacoUrlEditor;
