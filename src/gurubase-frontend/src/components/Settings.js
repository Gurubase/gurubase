"use client";

import "react-loading-skeleton/dist/skeleton.css";

import Link from "next/link";
import { useEffect, useState } from "react";
import Skeleton from "react-loading-skeleton";

import { getSettings, updateSettings } from "@/app/actions";
import { CustomToast } from "@/components/CustomToast";
import SecretInput from "@/components/SecretInput";
import { Button } from "@/components/ui/button";

const Settings = () => {
  const [openAIKey, setOpenAIKey] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isKeyValid, setIsKeyValid] = useState(false);
  const [hasExistingKey, setHasExistingKey] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [scraperType, setScraperType] = useState("CRAWL4AI");
  const [firecrawlKey, setFirecrawlKey] = useState("");
  const [isFirecrawlKeyValid, setIsFirecrawlKeyValid] = useState(false);
  const [hasExistingFirecrawlKey, setHasExistingFirecrawlKey] = useState(false);
  const [isFirecrawlEditing, setIsFirecrawlEditing] = useState(false);
  const [maskedOpenAIKey, setMaskedOpenAIKey] = useState("");
  const [maskedFirecrawlKey, setMaskedFirecrawlKey] = useState("");
  const [youtubeApiKey, setYoutubeApiKey] = useState("");
  const [isYoutubeKeyValid, setIsYoutubeKeyValid] = useState(false);
  const [hasExistingYoutubeKey, setHasExistingYoutubeKey] = useState(false);
  const [isYoutubeEditing, setIsYoutubeEditing] = useState(false);
  const [maskedYoutubeKey, setMaskedYoutubeKey] = useState("");

  const fetchSettings = async (isInitial = false) => {
    if (isInitial) {
      setIsInitialLoading(true);
    }
    const settings = await getSettings();

    if (settings) {
      setOpenAIKey(settings.openai_api_key);
      setIsKeyValid(settings.is_openai_key_valid);
      setHasExistingKey(!!settings.openai_api_key);
      setMaskedOpenAIKey(settings.openai_api_key || "");

      // Set scraper settings
      if (settings.scrape_type) {
        setScraperType(settings.scrape_type);
      }

      setIsFirecrawlKeyValid(settings.is_firecrawl_key_valid);
      setHasExistingFirecrawlKey(!!settings.firecrawl_api_key);
      setFirecrawlKey(settings.firecrawl_api_key);
      setMaskedFirecrawlKey(settings.firecrawl_api_key || "");

      // Set YouTube API key settings
      setIsYoutubeKeyValid(settings.is_youtube_key_valid);
      setHasExistingYoutubeKey(!!settings.youtube_api_key);
      setYoutubeApiKey(settings.youtube_api_key);
      setMaskedYoutubeKey(settings.youtube_api_key || "");
    }
    if (isInitial) {
      setIsInitialLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings(true);
  }, []);

  const handleChange = (e) => {
    const value = e.target.value;

    setOpenAIKey(value);
  };

  const startEditing = () => {
    setIsEditing(true);
    setOpenAIKey("");
  };

  const startFirecrawlEditing = () => {
    setIsFirecrawlEditing(true);
    setFirecrawlKey("");
  };

  const startYoutubeEditing = () => {
    setIsYoutubeEditing(true);
    setYoutubeApiKey("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const formData = new FormData();

      if (isEditing) {
        formData.append("openai_api_key", openAIKey.trim());
        formData.append("openai_api_key_written", true);
      } else {
        formData.append("openai_api_key_written", false);
      }

      formData.append("scrape_type", scraperType);

      if (scraperType === "FIRECRAWL") {
        if (isFirecrawlEditing) {
          formData.append("firecrawl_api_key", firecrawlKey.trim());
          formData.append("firecrawl_api_key_written", true);
        } else {
          formData.append("firecrawl_api_key_written", false);
        }
      }

      if (isYoutubeEditing) {
        formData.append("youtube_api_key", youtubeApiKey.trim());
        formData.append("youtube_api_key_written", true);
      } else {
        formData.append("youtube_api_key_written", false);
      }

      const result = await updateSettings(formData);

      if (isEditing) setIsEditing(false);
      if (isFirecrawlEditing) setIsFirecrawlEditing(false);
      if (isYoutubeEditing) setIsYoutubeEditing(false);

      if (result) {
        if (result.is_openai_key_valid === false && result.openai_api_key) {
          CustomToast({
            message: "Invalid OpenAI API key",
            variant: "error"
          });

          return;
        }

        setOpenAIKey(result.openai_api_key);

        if (
          scraperType === "FIRECRAWL" &&
          result.is_firecrawl_key_valid === false &&
          result.firecrawl_api_key
        ) {
          CustomToast({
            message: "Invalid Firecrawl API key",
            variant: "error"
          });

          return;
        }

        setFirecrawlKey(result.firecrawl_api_key);

        if (result.is_youtube_key_valid === false && result.youtube_api_key) {
          CustomToast({
            message: "Invalid YouTube API key",
            variant: "error"
          });

          return;
        }

        setYoutubeApiKey(result.youtube_api_key);

        CustomToast({
          message: "Settings saved successfully",
          variant: "success"
        });
      }
    } catch (error) {
      CustomToast({
        message: "Failed to save settings",
        variant: "error"
      });
    } finally {
      setIsLoading(false);
      await fetchSettings(false);
    }
  };

  const handleFirecrawlChange = (e) => {
    setFirecrawlKey(e.target.value);
  };

  const handleYoutubeChange = (e) => {
    setYoutubeApiKey(e.target.value);
  };

  return (
    <main className="flex justify-center items-center px-16 guru-sm:px-0 w-full flex-grow guru-sm:max-w-full polygon-fill">
      <div className="guru-md:max-w-[870px] guru-lg:max-w-[1180px] w-full gap-4 h-full">
        <div className="grid grid-cols-1 h-full">
          <div className="bg-white shadow-md guru-sm:border-none border-l border-r guru-lg:border-r-0 border-solid border-neutral-200">
            <section className="bg-white border-gray-200">
              <div className="p-6">
                <div className="mb-8">
                  <h1 className="text-[20px] font-semibold text-[#191919] font-inter mb-2">
                    Settings
                  </h1>
                  <p className="text-[14px] font-normal text-[#6D6D6D] font-inter">
                    Configure your Gurubase Self-hosted instance settings.
                  </p>
                </div>

                <div className="max-w-[500px]">
                  <form autoComplete="off" onSubmit={handleSubmit}>
                    <div className="space-y-8">
                      {/* OpenAI API Key Section */}
                      <div className="space-y-8">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <label
                              className="text-[14px] font-medium text-[#191919] font-inter"
                              htmlFor="openai-key">
                              OpenAI API Key
                            </label>
                          </div>
                          <p className="text-[12px] font-normal text-[#6D6D6D] font-inter mb-2">
                            Used for text generation (GPT-4o, GPT-4o-mini) and
                            text embeddings.
                          </p>
                          {isInitialLoading ? (
                            <Skeleton className="h-12" />
                          ) : (
                            <SecretInput
                              hasExisting={hasExistingKey}
                              invalidMessage="OpenAI API key is invalid"
                              isEditing={isEditing}
                              isValid={isKeyValid}
                              maskedValue={maskedOpenAIKey}
                              placeholder="sk-..."
                              validMessage="OpenAI API key is valid"
                              value={openAIKey}
                              onChange={handleChange}
                              onStartEditing={startEditing}
                            />
                          )}
                        </div>
                      </div>

                      {/* Web Scraper Section */}
                      <div>
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <label className="text-[14px] font-medium text-[#191919] font-inter">
                              Web Scraper
                            </label>
                          </div>
                          <p className="text-[12px] font-normal text-[#6D6D6D] font-inter mb-2">
                            Choose between Crawl4AI (free) or Firecrawl
                            (requires API key but more robust).
                          </p>
                          {isInitialLoading ? (
                            <Skeleton className="h-12 w-[280px]" />
                          ) : (
                            <div className="space-y-2">
                              <label
                                className="flex items-center gap-3 cursor-pointer"
                                onClick={() => setScraperType("CRAWL4AI")}>
                                <div
                                  className={`w-6 h-6 rounded-[50px] border border-[#E2E2E2] bg-white flex items-center justify-center p-0.5`}>
                                  {scraperType === "CRAWL4AI" && (
                                    <div className="w-4 h-4 rounded-full bg-[#191919]" />
                                  )}
                                </div>
                                <div className="flex items-center">
                                  <span className="text-sm text-[#191919]">
                                    Crawl4AI
                                  </span>
                                </div>
                              </label>

                              <label
                                className="flex items-center gap-3 cursor-pointer"
                                onClick={() => setScraperType("FIRECRAWL")}>
                                <div
                                  className={`w-6 h-6 rounded-[50px] border border-[#E2E2E2] bg-white flex items-center justify-center p-0.5`}>
                                  {scraperType === "FIRECRAWL" && (
                                    <div className="w-4 h-4 rounded-full bg-[#191919]" />
                                  )}
                                </div>
                                <span className="text-sm text-[#191919]">
                                  Firecrawl
                                </span>
                              </label>
                            </div>
                          )}
                        </div>

                        {/* Firecrawl API Key */}
                        {scraperType === "FIRECRAWL" && (
                          <div className="relative mt-4">
                            {isInitialLoading ? (
                              <Skeleton className="h-12" />
                            ) : (
                              <SecretInput
                                hasExisting={hasExistingFirecrawlKey}
                                invalidMessage="Firecrawl API key is invalid"
                                isEditing={isFirecrawlEditing}
                                isValid={isFirecrawlKeyValid}
                                maskedValue={maskedFirecrawlKey}
                                placeholder="fc-..."
                                validMessage="Firecrawl API key is valid"
                                value={firecrawlKey}
                                onChange={handleFirecrawlChange}
                                onStartEditing={startFirecrawlEditing}
                              />
                            )}
                          </div>
                        )}
                      </div>

                      {/* YouTube API Key Section */}
                      <div>
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <label className="text-[14px] font-medium text-[#191919] font-inter">
                              YouTube API Key (Optional)
                            </label>
                          </div>
                          <p className="text-[12px] font-normal text-[#6D6D6D] font-inter mb-2">
                            Gurubase will use this API key to extract videos
                            from YouTube playlists and channels.
                          </p>
                          {isInitialLoading ? (
                            <Skeleton className="h-12" />
                          ) : (
                            <SecretInput
                              hasExisting={hasExistingYoutubeKey}
                              invalidMessage="YouTube API key is invalid"
                              isEditing={isYoutubeEditing}
                              isValid={isYoutubeKeyValid}
                              maskedValue={maskedYoutubeKey}
                              placeholder="AIza..."
                              validMessage="YouTube API key is valid"
                              value={youtubeApiKey}
                              onChange={handleYoutubeChange}
                              onStartEditing={startYoutubeEditing}
                            />
                          )}
                        </div>
                      </div>

                      {/* Submit Button Section */}
                      {isInitialLoading ? (
                        <Skeleton className="h-12" />
                      ) : (
                        <div className="flex space-x-3">
                          <Button
                            className="flex h-[48px] px-4 justify-center items-center gap-2 rounded-lg bg-gray-800 text-white hover:bg-gray-700"
                            disabled={isLoading}
                            size="lg"
                            type="submit">
                            {isLoading ? "Saving..." : "Save Settings"}
                          </Button>
                        </div>
                      )}
                    </div>
                  </form>

                  {/* Success CTA Section */}
                  {hasExistingKey &&
                    isKeyValid &&
                    !isInitialLoading &&
                    (scraperType === "CRAWL4AI" ||
                      (scraperType === "FIRECRAWL" && isFirecrawlKeyValid)) && (
                      <div className="mt-8 p-4 rounded-lg border-[0.5px] border-[#16A34A] bg-[#F8FCFA]">
                        <h3 className="text-[16px] font-semibold text-[#16A34A] font-inter mb-2">
                          🎉 Ready to Create a New Guru!
                        </h3>
                        <p className="text-[14px] font-normal text-[#16A34A] font-inter mb-4">
                          Create an AI-powered Q&A assistant by adding webpages,
                          PDFs, YouTube videos, or GitHub repositories.
                        </p>
                        <div className="flex flex-col gap-2">
                          <Link
                            className="inline-flex h-10 items-center justify-center rounded-lg bg-[#16A34A] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#15803D] focus:outline-none focus:ring-2 focus:ring-[#16A34A] focus:ring-offset-2"
                            href="/guru/new-12hsh25ksh2">
                            Create a New Guru →
                          </Link>
                        </div>
                      </div>
                    )}
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </main>
  );
};

export default Settings;
