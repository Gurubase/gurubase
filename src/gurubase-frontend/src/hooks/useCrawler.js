import { useState, useEffect } from "react";
import { startCrawl, getCrawlStatus, stopCrawl } from "@/app/actions";
import { CustomToast } from "@/components/CustomToast";

export const useCrawler = (onUrlsDiscovered) => {
  const [isCrawling, setIsCrawling] = useState(false);
  const [crawlId, setCrawlId] = useState(null);

  useEffect(() => {
    let pollInterval;

    const pollCrawlStatus = async () => {
      if (!crawlId) return;

      try {
        const data = await getCrawlStatus(crawlId);
        console.log("crawl status data", data);

        if (data.error) {
          throw new Error(data.message);
        }

        // Update discovered URLs even while crawling is in progress
        if (data.discovered_urls?.length > 0) {
          onUrlsDiscovered(data.discovered_urls);
        }

        // Handle different status conditions
        if (data.status === "COMPLETED") {
          setIsCrawling(false);
          setCrawlId(null);
          clearInterval(pollInterval);

          if (data.discovered_urls?.length > 0) {
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
          setIsCrawling(false);
          setCrawlId(null);
          clearInterval(pollInterval);
        } else if (data.status === "FAILED") {
          setIsCrawling(false);
          setCrawlId(null);
          clearInterval(pollInterval);

          CustomToast({
            message: data.error_message || "Crawling failed",
            variant: "error"
          });
        }
      } catch (error) {
        console.error("Error polling crawl status:", error);
        setIsCrawling(false);
        setCrawlId(null);
        clearInterval(pollInterval);

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
  }, [crawlId, onUrlsDiscovered]);

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
      const data = await startCrawl(url);

      if (data.error) {
        CustomToast({
          message: data.message,
          variant: "error"
        });
        return;
      }

      setCrawlId(data.crawl_id);
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
      const data = await stopCrawl(crawlId);
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
    handleStopCrawl
  };
};
