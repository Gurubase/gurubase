import { useCallback, useEffect, useState } from "react";

import { getCrawlStatus, startCrawl, stopCrawl } from "@/app/actions";
import { CustomToast } from "@/components/CustomToast";

export const useCrawler = (onUrlsDiscovered, guruSlug) => {
  const [isCrawling, setIsCrawling] = useState(false);
  const [crawlId, setCrawlId] = useState(null);
  const [discoveredUrls, setDiscoveredUrls] = useState(new Set());
  const [showCrawlInput, setShowCrawlInput] = useState(false);
  const [crawlUrl, setCrawlUrl] = useState("");

  // Process new URLs in a race-condition safe way
  const processNewUrls = useCallback(
    (allDiscoveredUrls) => {
      if (!allDiscoveredUrls || !Array.isArray(allDiscoveredUrls)) return [];

      // Use functional update to ensure we're working with the latest state
      setDiscoveredUrls((prevUrls) => {
        const newUrlSet = new Set(prevUrls);
        const newUrls = [];

        // Find truly new URLs that haven't been processed yet
        allDiscoveredUrls.forEach((url) => {
          if (!newUrlSet.has(url)) {
            newUrlSet.add(url);
            newUrls.push(url);
          }
        });

        // Only notify if we have new URLs
        if (newUrls.length > 0 && onUrlsDiscovered) {
          onUrlsDiscovered(newUrls);
        }

        return newUrlSet;
      });
    },
    [onUrlsDiscovered]
  );

  // Reset crawler state
  const resetCrawlerState = useCallback(() => {
    setIsCrawling(false);
    setCrawlId(null);
    setDiscoveredUrls(new Set());
    setShowCrawlInput(false);
    setCrawlUrl("");
  }, []);

  useEffect(() => {
    let pollInterval;

    const pollCrawlStatus = async () => {
      if (!crawlId) return;

      try {
        const data = await getCrawlStatus(crawlId, guruSlug);

        // Process any discovered URLs
        if (data && data.discovered_urls && data.discovered_urls.length > 0) {
          processNewUrls(data.discovered_urls);
        }

        if (data.error) {
          throw new Error(data.message);
        }

        // Handle different status conditions
        if (data.status === "COMPLETED") {
          clearInterval(pollInterval);
          resetCrawlerState();

          if (data.discovered_urls && data.discovered_urls.length > 0) {
            CustomToast({
              message: `Successfully crawled ${data.discovered_urls.length} URL(s)`,
              variant: "success"
            });
          } else {
            CustomToast({
              message: "No URLs were discovered during crawling",
              variant: "warning"
            });
          }
        } else if (data.status === "STOPPED") {
          clearInterval(pollInterval);
          resetCrawlerState();
        } else if (data.status === "FAILED") {
          clearInterval(pollInterval);
          resetCrawlerState();

          CustomToast({
            message: data.error_message || "Crawling failed",
            variant: "error"
          });
        }
      } catch (error) {
        clearInterval(pollInterval);
        resetCrawlerState();

        CustomToast({
          message: "Error checking crawl status",
          variant: "error"
        });
      }
    };

    if (crawlId) {
      pollInterval = setInterval(pollCrawlStatus, 3000);
      // Initial poll
      pollCrawlStatus();
    }

    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [crawlId, guruSlug, processNewUrls, resetCrawlerState]);

  const handleStartCrawl = async (url) => {
    if (!url) {
      CustomToast({
        message: "Please enter a URL to crawl",
        variant: "error"
      });

      return;
    }

    try {
      setIsCrawling(true);
      const data = await startCrawl(url, guruSlug);

      if (data.error) {
        CustomToast({
          message: data.message,
          variant: "error"
        });
        setIsCrawling(false);

        return;
      }

      setCrawlId(data.id);
    } catch (error) {
      setIsCrawling(false);
      CustomToast({
        message: error.message || "Failed to start crawling",
        variant: "error"
      });
    }
  };

  const handleStopCrawl = async () => {
    if (!crawlId) return;

    try {
      const data = await stopCrawl(crawlId, guruSlug);

      if (data.error) {
        throw new Error(data.message);
      }

      setIsCrawling(false);
      setCrawlId(null);
    } catch (error) {
      CustomToast({
        message: error.message || "Failed to stop crawling",
        variant: "error"
      });
    }
  };

  return {
    isCrawling,
    handleStartCrawl,
    handleStopCrawl,
    showCrawlInput,
    setShowCrawlInput,
    crawlUrl,
    setCrawlUrl
  };
};
