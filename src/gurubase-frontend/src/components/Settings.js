"use client";

import "react-loading-skeleton/dist/skeleton.css";

import Link from "next/link";
import { useEffect, useState } from "react";
import Skeleton from "react-loading-skeleton";

import {
  getSettings,
  updateSettings,
  validateOllamaUrlRequest
} from "@/app/actions";
import { CustomToast } from "@/components/CustomToast";
import { CheckCircleIcon, CloseCircleIcon } from "@/components/Icons";
import SecretInput from "@/components/SecretInput";
import { Button } from "@/components/ui/button";
import { HeaderTooltip } from "@/components/ui/header-tooltip";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from "@/components/ui/modal-dialog";

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

  // New state variables for AI Model Provider
  const [aiModelProvider, setAiModelProvider] = useState("OPENAI");
  const [ollamaUrl, setOllamaUrl] = useState("");
  const [isOllamaUrlValid, setIsOllamaUrlValid] = useState(false);
  const [ollamaEmbeddingModel, setOllamaEmbeddingModel] =
    useState("nomic-embed-text");
  const [ollamaBaseModel, setOllamaBaseModel] = useState("llama2");
  const [isValidatingOllama, setIsValidatingOllama] = useState(false);
  const [ollamaUrlError, setOllamaUrlError] = useState("");

  const [isEmbeddingModelValid, setIsEmbeddingModelValid] = useState(false);
  const [isBaseModelValid, setIsBaseModelValid] = useState(false);
  const [dataSourcesExist, setDataSourcesExist] = useState(false);
  const [showEmbeddingChangeModal, setShowEmbeddingChangeModal] =
    useState(false);
  const [hasEmbeddingChanged, setHasEmbeddingChanged] = useState(false);
  const [oldAiModelProvider, setOldAiModelProvider] = useState("");

  const fetchSettings = async (isInitial = false, keepFields = false) => {
    // keepFields only works for non-api key inputs as they are masked.
    if (isInitial) {
      setIsInitialLoading(true);
    }
    const settings = await getSettings();

    if (settings) {
      setOpenAIKey(settings.openai_api_key);
      setIsKeyValid(settings.is_openai_key_valid);
      setHasExistingKey(!!settings.openai_api_key);
      setMaskedOpenAIKey(settings.openai_api_key || "");
      setDataSourcesExist(settings.data_sources_exist);

      // Set AI Model Provider settings
      if (!keepFields && settings.ai_model_provider) {
        setAiModelProvider(settings.ai_model_provider);
        setOldAiModelProvider(settings.ai_model_provider);
      }
      if (settings.ollama_url) {
        if (!keepFields) {
          setOllamaUrl(settings.ollama_url);
        }
        setIsOllamaUrlValid(settings.is_ollama_url_valid);
      }
      if (settings.ollama_embedding_model) {
        if (!keepFields) {
          setOllamaEmbeddingModel(settings.ollama_embedding_model);
        }
        setIsEmbeddingModelValid(settings.is_ollama_embedding_model_valid);
      }
      if (settings.ollama_base_model) {
        if (!keepFields) {
          setOllamaBaseModel(settings.ollama_base_model);
        }
        setIsBaseModelValid(settings.is_ollama_base_model_valid);
      }

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
    if (oldAiModelProvider && aiModelProvider !== oldAiModelProvider) {
      setHasEmbeddingChanged(true);
    }
  }, [aiModelProvider]);

  useEffect(() => {
    fetchSettings(true, false);
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
    // Clear previous errors
    setOllamaUrlError("");

    let error = false;
    let requestSent = false;

    try {
      // Validate Ollama settings if Ollama is selected
      if (aiModelProvider === "OLLAMA") {
        if (!ollamaUrl.trim()) {
          error = true;
          CustomToast({
            message: "Ollama URL is required",
            variant: "error"
          });
          setIsLoading(false);

          return;
        }

        if (!isOllamaUrlValid) {
          error = true;
          CustomToast({
            message: "Please validate the Ollama URL first",
            variant: "error"
          });
          setIsLoading(false);

          return;
        }

        if (!ollamaEmbeddingModel.trim()) {
          error = true;
          CustomToast({
            message: "Embedding model is required",
            variant: "error"
          });
          setIsLoading(false);
        }

        if (!ollamaBaseModel.trim()) {
          error = true;
          CustomToast({
            message: "Language model is required",
            variant: "error"
          });
          setIsLoading(false);
        }
      }

      if (error) {
        setIsLoading(false);

        return;
      }

      const formData = new FormData();

      // Add AI Model Provider settings
      formData.append("ai_model_provider", aiModelProvider);
      if (aiModelProvider === "OLLAMA") {
        formData.append("ollama_url", ollamaUrl.trim());
        formData.append("ollama_embedding_model", ollamaEmbeddingModel.trim());
        formData.append("ollama_base_model", ollamaBaseModel.trim());
      }

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

      // Show confirmation modal if embedding has changed and data sources exist
      if (hasEmbeddingChanged && dataSourcesExist) {
        setShowEmbeddingChangeModal(true);
        setIsLoading(false);

        return;
      }

      const result = await updateSettings(formData);

      requestSent = true;

      if (isEditing) setIsEditing(false);
      if (isFirecrawlEditing) setIsFirecrawlEditing(false);
      if (isYoutubeEditing) setIsYoutubeEditing(false);

      if (result) {
        let error = false;

        if (aiModelProvider === "OLLAMA") {
          if (result.is_ollama_url_valid === false && result.ollama_url) {
            error = true;
            CustomToast({
              message: "Invalid Ollama URL",
              variant: "error"
            });
          }

          if (
            result.is_ollama_embedding_model_valid === false &&
            result.ollama_embedding_model
          ) {
            error = true;
            CustomToast({
              message: "Invalid Ollama embedding model",
              variant: "error"
            });
          }

          if (
            result.is_ollama_base_model_valid === false &&
            result.ollama_base_model
          ) {
            error = true;
            CustomToast({
              message: "Invalid language model",
              variant: "error"
            });
          }
        }

        if (
          result.is_openai_key_valid === false &&
          result.openai_api_key &&
          aiModelProvider === "OPENAI"
        ) {
          error = true;
          CustomToast({
            message: "Invalid OpenAI API key",
            variant: "error"
          });
        }

        if (
          scraperType === "FIRECRAWL" &&
          result.is_firecrawl_key_valid === false &&
          result.firecrawl_api_key
        ) {
          error = true;
          CustomToast({
            message: "Invalid Firecrawl API key",
            variant: "error"
          });
        }

        setFirecrawlKey(result.firecrawl_api_key);

        if (result.is_youtube_key_valid === false && result.youtube_api_key) {
          error = true;
          CustomToast({
            message: "Invalid YouTube API key",
            variant: "error"
          });
        }

        setYoutubeApiKey(result.youtube_api_key);

        // Update Ollama settings
        if (result.ollama_url) {
          setOllamaUrl(result.ollama_url);
          setIsOllamaUrlValid(result.is_ollama_url_valid);
        }
        if (result.ollama_embedding_model) {
          setOllamaEmbeddingModel(result.ollama_embedding_model);
        }
        if (result.ollama_base_model) {
          setOllamaBaseModel(result.ollama_base_model);
        }
        if (result.ai_model_provider) {
          setAiModelProvider(result.ai_model_provider);
          setOldAiModelProvider(result.ai_model_provider);
        }

        if (!error) {
          CustomToast({
            message: "Settings saved successfully",
            variant: "success"
          });
        }
      }
    } catch (error) {
      CustomToast({
        message: "Failed to save settings",
        variant: "error"
      });
    } finally {
      setIsLoading(false);
      if (requestSent) {
        await fetchSettings(false, error);
      }
    }
  };

  const handleFirecrawlChange = (e) => {
    setFirecrawlKey(e.target.value);
  };

  const handleYoutubeChange = (e) => {
    setYoutubeApiKey(e.target.value);
  };

  const validateOllamaUrl = async () => {
    if (!ollamaUrl.trim()) {
      setIsOllamaUrlValid(false);
      setOllamaUrlError("Ollama URL is required");

      return;
    }

    setIsValidatingOllama(true);
    setOllamaUrlError("");

    try {
      const result = await validateOllamaUrlRequest(ollamaUrl.trim());

      if (result.error) {
        setIsOllamaUrlValid(false);
        setOllamaUrlError("Invalid Ollama URL or server not responding");
      } else {
        setIsOllamaUrlValid(true);
        setOllamaUrlError("");
      }
    } catch (error) {
      setIsOllamaUrlValid(false);
      setOllamaUrlError("Failed to connect to Ollama server");
    } finally {
      setIsValidatingOllama(false);
    }
  };

  const handleConfirmEmbeddingChange = async () => {
    setIsLoading(true);
    try {
      const formData = new FormData();

      formData.append("ai_model_provider", aiModelProvider);
      if (aiModelProvider === "OLLAMA") {
        formData.append("ollama_url", ollamaUrl.trim());
        formData.append("ollama_embedding_model", ollamaEmbeddingModel.trim());
        formData.append("ollama_base_model", ollamaBaseModel.trim());
      }
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

      if (result) {
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
      setShowEmbeddingChangeModal(false);
      setHasEmbeddingChanged(false);
      await fetchSettings(false, false);
    }
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
                      {/* AI Model Provider Section */}
                      <div className="space-y-4">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <label className="text-[14px] font-medium text-[#191919] font-inter">
                              AI Model Provider
                            </label>
                            <HeaderTooltip
                              text={
                                "Choose between OpenAI's cloud services or self-hosted Ollama for AI capabilities"
                              }
                            />
                          </div>
                          <p className="text-[12px] font-normal text-[#6D6D6D] font-inter mb-2">
                            Configure your Gurubase Self-hosted instance
                            settings.
                          </p>
                          {isInitialLoading ? (
                            <Skeleton className="h-12" />
                          ) : (
                            <div className="space-y-2">
                              <label
                                className="flex items-center gap-3 cursor-pointer"
                                onClick={() => setAiModelProvider("OPENAI")}>
                                <div
                                  className={`w-6 h-6 rounded-[50px] border border-[#E2E2E2] bg-white flex items-center justify-center p-0.5`}>
                                  {aiModelProvider === "OPENAI" && (
                                    <div className="w-4 h-4 rounded-full bg-[#191919]" />
                                  )}
                                </div>
                                <div className="flex items-center">
                                  <span className="text-sm text-[#191919]">
                                    OpenAI
                                  </span>
                                </div>
                              </label>

                              <label
                                className="flex items-center gap-3 cursor-pointer"
                                onClick={() => setAiModelProvider("OLLAMA")}>
                                <div
                                  className={`w-6 h-6 rounded-[50px] border border-[#E2E2E2] bg-white flex items-center justify-center p-0.5`}>
                                  {aiModelProvider === "OLLAMA" && (
                                    <div className="w-4 h-4 rounded-full bg-[#191919]" />
                                  )}
                                </div>
                                <span className="text-sm text-[#191919]">
                                  Ollama
                                </span>
                              </label>
                            </div>
                          )}
                        </div>

                        {/* OpenAI API Key Section */}
                        {!isInitialLoading && aiModelProvider === "OPENAI" && (
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <label
                                className="text-[14px] font-medium text-[#6D6D6D] font-inter"
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
                        )}

                        {/* Ollama Settings Section */}
                        {aiModelProvider === "OLLAMA" && (
                          <div className="space-y-4">
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <label
                                  className="text-[14px] font-medium text-[#6D6D6D] font-inter"
                                  htmlFor="ollama-url">
                                  Ollama URL
                                </label>
                                <HeaderTooltip
                                  text={"Add your Ollama server endpoint."}
                                />
                              </div>
                              <p className="text-[12px] font-normal text-[#6D6D6D] font-inter mb-2">
                                Add your Ollama server endpoint. Learn more
                                about{" "}
                                <a
                                  href="https://github.com/ollama/ollama/"
                                  rel="noopener noreferrer"
                                  target="_blank">
                                  Ollama
                                </a>
                                .
                              </p>
                              {isInitialLoading ? (
                                <Skeleton className="h-12" />
                              ) : (
                                <div className="relative">
                                  <input
                                    className="w-full h-12 px-4 rounded-lg border border-[#E2E2E2] focus:outline-none focus:ring-2 focus:ring-[#191919] focus:border-transparent"
                                    id="ollama-url"
                                    placeholder="http://host.docker.internal:11434"
                                    type="text"
                                    value={ollamaUrl}
                                    onBlur={validateOllamaUrl}
                                    onChange={(e) => {
                                      setOllamaUrl(e.target.value);
                                      setHasEmbeddingChanged(true);
                                    }}
                                  />
                                  {isValidatingOllama && (
                                    <div className="absolute right-3 top-1/2 -translate-y-1/2">
                                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900" />
                                    </div>
                                  )}
                                </div>
                              )}
                              {(ollamaUrlError || !isOllamaUrlValid) && (
                                <div className="flex items-center gap-1 mt-2">
                                  <CloseCircleIcon className="text-[#DC2626]" />
                                  <span className="text-[12px] font-inter font-normal text-[#DC2626]">
                                    Unable to access the Ollama server at this
                                    address.
                                  </span>
                                </div>
                              )}
                              {isOllamaUrlValid && !ollamaUrlError && (
                                <div className="flex items-center gap-1 mt-2">
                                  <CheckCircleIcon />
                                  <span className="text-[12px] font-normal text-[#16A34A] font-inter">
                                    Ollama is accessible.
                                  </span>
                                </div>
                              )}
                            </div>

                            {isOllamaUrlValid && (
                              <div className="space-y-4">
                                <div>
                                  <div className="flex items-center gap-2 mb-1">
                                    <label className="text-[16px] font-semibold text-[#6D6D6D] font-inter">
                                      Model Selection
                                    </label>
                                    <HeaderTooltip
                                      text={
                                        "Configure the embedding and language models for your Ollama setup"
                                      }
                                    />
                                  </div>
                                  <p className="text-[12px] font-normal text-[#6D6D6D] font-inter mb-4">
                                    Configure your Gurubase Self-hosted instance
                                    settings.
                                  </p>
                                </div>

                                <div>
                                  {isInitialLoading ? (
                                    <Skeleton className="h-12" />
                                  ) : (
                                    <>
                                      <div className="flex items-center gap-2 mb-1">
                                        <label
                                          className="text-[14px] font-medium text-[#6D6D6D] font-inter"
                                          htmlFor="ollama-embedding-model">
                                          Embedding Model
                                        </label>
                                      </div>
                                      <p className="text-[12px] font-normal text-[#6D6D6D] font-inter mb-2">
                                        This model will be used to convert text
                                        into vector embeddings for search
                                      </p>
                                      <input
                                        className="w-full h-12 px-4 rounded-lg border border-[#E2E2E2] focus:outline-none focus:ring-2 focus:ring-[#191919] focus:border-transparent"
                                        id="ollama-embedding-model"
                                        placeholder="Embedding Model"
                                        type="text"
                                        value={ollamaEmbeddingModel}
                                        onChange={(e) => {
                                          setOllamaEmbeddingModel(
                                            e.target.value
                                          );
                                          setHasEmbeddingChanged(true);
                                        }}
                                      />
                                    </>
                                  )}
                                  {!isEmbeddingModelValid && (
                                    <div className="flex items-center gap-1 mt-2">
                                      <CloseCircleIcon className="text-[#DC2626]" />
                                      <span className="text-[12px] font-inter font-normal text-[#DC2626]">
                                        Either the model name is incorrect, the
                                        model does not exist on the specified
                                        Ollama server, or it does not support
                                        embedding.
                                      </span>
                                    </div>
                                  )}
                                  {isEmbeddingModelValid && (
                                    <div className="flex items-center gap-1 mt-2">
                                      <CheckCircleIcon />
                                      <span className="text-[12px] font-normal text-[#16A34A] font-inter">
                                        Embedding model is valid
                                      </span>
                                    </div>
                                  )}
                                </div>

                                <div>
                                  {isInitialLoading ? (
                                    <Skeleton className="h-12" />
                                  ) : (
                                    <>
                                      <div className="flex items-center gap-2 mb-1">
                                        <label
                                          className="text-[14px] font-medium text-[#6D6D6D] font-inter"
                                          htmlFor="ollama-base-model">
                                          Language Model
                                        </label>
                                      </div>
                                      <p className="text-[12px] font-normal text-[#6D6D6D] font-inter mb-2">
                                        Model for generating responses (e.g.,
                                        llama3, gemma3:latest, or gemma3:12b)
                                      </p>
                                      <input
                                        className="w-full h-12 px-4 rounded-lg border border-[#E2E2E2] focus:outline-none focus:ring-2 focus:ring-[#191919] focus:border-transparent"
                                        id="ollama-base-model"
                                        placeholder="Language Model"
                                        type="text"
                                        value={ollamaBaseModel}
                                        onChange={(e) =>
                                          setOllamaBaseModel(e.target.value)
                                        }
                                      />
                                    </>
                                  )}
                                  {!isBaseModelValid && (
                                    <div className="flex items-center gap-1 mt-2">
                                      <CloseCircleIcon className="text-[#DC2626]" />
                                      <span className="text-[12px] font-inter font-normal text-[#DC2626]">
                                        Either the model name is incorrect, or
                                        the model does not exist on the
                                        specified Ollama server.
                                      </span>
                                    </div>
                                  )}
                                  {isBaseModelValid && (
                                    <div className="flex items-center gap-1 mt-2">
                                      <CheckCircleIcon />
                                      <span className="text-[12px] font-normal text-[#16A34A] font-inter">
                                        Language model is valid
                                      </span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
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
                  {!isInitialLoading &&
                    ((aiModelProvider === "OPENAI" &&
                      hasExistingKey &&
                      isKeyValid) ||
                      (aiModelProvider === "OLLAMA" &&
                        ollamaUrl &&
                        isOllamaUrlValid &&
                        ollamaEmbeddingModel &&
                        ollamaBaseModel &&
                        isEmbeddingModelValid &&
                        isBaseModelValid)) &&
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

      <Dialog
        open={showEmbeddingChangeModal}
        onOpenChange={setShowEmbeddingChangeModal}>
        <DialogContent className="max-w-[400px] p-6 z-[200]">
          <div className="p-6 text-center">
            <DialogHeader>
              <DialogTitle className="text-base font-semibold text-center text-[#191919] font-inter">
                Change Embedding Model
              </DialogTitle>
              <DialogDescription className="text-[14px] text-[#6D6D6D] text-center font-inter font-normal">
                You are about to change the embedding model, which will require
                reprocessing all data sources with the new model. You can track
                the processing status of the data sources on the Guru Edit
                pages.
              </DialogDescription>
            </DialogHeader>
            <div className="mt-6 flex flex-col gap-2">
              <Button
                className="h-12 px-6 justify-center items-center rounded-lg bg-[#DC2626] hover:bg-red-700 text-white"
                disabled={isLoading}
                onClick={handleConfirmEmbeddingChange}>
                {isLoading ? "Saving..." : "Continue"}
              </Button>
              <Button
                className="h-12 px-4 justify-center items-center rounded-lg border border-[#1B242D] bg-white"
                disabled={isLoading}
                variant="outline"
                onClick={() => setShowEmbeddingChangeModal(false)}>
                Cancel
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </main>
  );
};

export default Settings;
