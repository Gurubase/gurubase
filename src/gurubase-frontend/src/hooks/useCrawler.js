import { useState, useEffect } from "react";
import { startCrawl, getCrawlStatus, stopCrawl } from "@/app/actions";
import { CustomToast } from "@/components/CustomToast";

export const useCrawler = (onUrlsDiscovered, guruSlug) => {
  const [isCrawling, setIsCrawling] = useState(false);
  const [crawlId, setCrawlId] = useState(null);
  const [discoveredUrls, setDiscoveredUrls] = useState(new Set());
  const [showCrawlInput, setShowCrawlInput] = useState(false);
  const [crawlUrl, setCrawlUrl] = useState("");

  useEffect(() => {
    let pollInterval;

    const pollCrawlStatus = async () => {
      if (!crawlId) return;

      try {
        const data = await getCrawlStatus(crawlId, guruSlug);

        // Filter out already discovered URLs
        if (data?.discovered_urls?.length > 0) {
          const newUrls = data.discovered_urls.filter(
            (url) => !discoveredUrls.has(url)
          );
          if (newUrls.length > 0) {
            // Update discovered URLs set
            newUrls.forEach((url) => discoveredUrls.add(url));
            setDiscoveredUrls(discoveredUrls);
            // Only pass new URLs to callback
            onUrlsDiscovered(newUrls);
          }
        }

        if (data.error) {
          throw new Error(data.message);
        }

        // Handle different status conditions
        if (data.status === "COMPLETED") {
          setIsCrawling(false);
          setCrawlId(null);
          clearInterval(pollInterval);
          setDiscoveredUrls(new Set()); // Reset discovered URLs
          setShowCrawlInput(false);
          setCrawlUrl("");

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
          setDiscoveredUrls(new Set()); // Reset discovered URLs
          setShowCrawlInput(false);
          setCrawlUrl("");
        } else if (data.status === "FAILED") {
          setIsCrawling(false);
          setCrawlId(null);
          clearInterval(pollInterval);
          setDiscoveredUrls(new Set()); // Reset discovered URLs
          setShowCrawlInput(false);
          setCrawlUrl("");

          CustomToast({
            message: data.error_message || "Crawling failed",
            variant: "error"
          });
        }
      } catch (error) {
        setIsCrawling(false);
        setCrawlId(null);
        clearInterval(pollInterval);
        setDiscoveredUrls(new Set()); // Reset discovered URLs

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
  }, [crawlId, onUrlsDiscovered, discoveredUrls]);

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
