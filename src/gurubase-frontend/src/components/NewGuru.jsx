"use client";
import { useAppNavigation } from "@/lib/navigation";
import { useUser } from "@auth0/nextjs-auth0/client";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  AlertTriangle,
  Info,
  LinkIcon,
  LoaderCircle,
  Lock,
  Unlock
} from "lucide-react";
import { redirect } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import * as React from "react";
import { useForm } from "react-hook-form";
import * as z from "zod";
import Link from "next/link";

import {
  addGuruSources,
  checkGuruReadiness,
  createGuru,
  deleteGuru,
  deleteGuruSources,
  getGuruDataSources,
  reindexGuruSources,
  updateGuru,
  updateGuruDataSourcesPrivacy,
  getSettings,
  getMyGuru,
  getIntegrationDetails // <-- Import getIntegrationDetails
} from "@/app/actions";
import { CustomToast } from "@/components/CustomToast";
import { LucideSquareArrowOutUpRight } from "@/components/Icons";
// Import the new component
import SourceDialog from "@/components/NewEditGuru/SourceDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Form } from "@/components/ui/form";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { cn } from "@/lib/utils";
import {
  determineInitialTab,
  getNormalizedDomain,
  isValidUrl
} from "@/utils/common";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "./ui/tooltip";
import { useCrawler } from "@/hooks/useCrawler";
import { DeleteConfirmationModal } from "@/components/NewEditGuru/DeleteConfirmationModal";
import { LongUpdatesIndicator } from "@/components/NewEditGuru/LongUpdatesIndicator";
import { JiraIntegrationModal } from "@/components/NewEditGuru/JiraIntegrationModal";
import { PendingChangesIndicator } from "@/components/NewEditGuru/PendingChangesIndicator";
import { GithubSourceSection } from "@/components/NewEditGuru/GithubSourceSection";
import { GuruDetailsSection } from "@/components/NewEditGuru/GuruDetailsSection"; // Import new component
import { SourcesTableSection } from "@/components/NewEditGuru/SourcesTableSection"; // Import new component

const formSchema = z.object({
  guruName: z
    .string()
    .min(2, { message: "Guru name must be at least 2 characters." })
    .max(18, { message: "Guru name must be at most 18 characters." }),
  guruLogo: z
    .union([z.instanceof(File), z.string()])
    .refine((value) => value !== null && value !== "", {
      message: "Guru logo is required."
    }),
  guruContext: z
    .string()
    .min(10, { message: "Guru context must be at least 10 characters." })
    .max(100, { message: "Guru context must not exceed 100 characters." }),
  githubRepos: z
    .array(
      z
        .string()
        .refine((value) => !value || value.startsWith("https://github.com"), {
          message: "Must be a valid GitHub repository URL."
        })
    )
    .default([])
    .optional(),
  uploadedFiles: z
    .array(
      z.object({
        file: z.any(),
        name: z.string(),
        size: z.union([z.number(), z.string(), z.undefined()])
      })
    )
    .optional(),
  youtubeLinks: z.array(z.string()).optional(),
  websiteUrls: z.array(z.string()).optional(),
  jiraIssues: z.array(z.string()).optional()
});

export default function NewGuru({ guruData, isProcessing }) {
  const navigation = useAppNavigation();
  const redirectingRef = useRef(false);
  // Add useCrawler here with other hooks
  const {
    isCrawling,
    handleStartCrawl,
    handleStopCrawl,
    showCrawlInput,
    setShowCrawlInput,
    crawlUrl,
    setCrawlUrl
  } = useCrawler((newUrls) => {
    // Use functional update to ensure we're working with the latest state
    setUrlEditorContent((prevContent) => {
      const prevContent_trimmed = prevContent || "";
      const currentUrls = prevContent_trimmed
        .split("\n")
        .filter((url) => url.trim());

      // Filter out URLs that already exist in the editor
      const filteredNewUrls = newUrls.filter(
        (url) => !currentUrls.includes(url)
      );

      // Only proceed if there are new unique URLs to add
      if (filteredNewUrls.length === 0) {
        return prevContent_trimmed;
      }

      // Add new URLs line by line, preserving existing URLs
      const updatedContent =
        prevContent_trimmed +
        (prevContent_trimmed ? "\n" : "") +
        filteredNewUrls.join("\n");

      // Update form value with all unique URLs
      const allUrls = [...currentUrls, ...filteredNewUrls];
      form.setValue("websiteUrls", allUrls);

      return updatedContent;
    });
  }, guruData?.slug || null);

  // Only initialize Auth0 hooks if in selfhosted mode
  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";
  const { user, isLoading: authLoading } = isSelfHosted
    ? { user: true, isLoading: false }
    : useUser();

  const [isWidgetModalVisible, setIsWidgetModalVisible] = useState(false);
  const [dataSources, setDataSources] = useState(null);
  const [customGuruData, setCustomGuruData] = useState(guruData);

  const [isApiKeyValid, setIsApiKeyValid] = useState(true);
  const [isCheckingApiKey, setIsCheckingApiKey] = useState(true);
  const [isYoutubeKeyValid, setIsYoutubeKeyValid] = useState(true);

  // Add function to fetch guru data
  const fetchGuruData = useCallback(async (guruSlug) => {
    try {
      const data = await getMyGuru(guruSlug);
      if (data.error) {
        notFound();
      }
      setCustomGuruData(data);
      return data;
    } catch (error) {
      return null;
    }
  }, []);

  // Add function to fetch data sources
  const fetchDataSources = useCallback(async (guruSlug) => {
    try {
      // console.log("Fetching data sources");
      const sources = await getGuruDataSources(guruSlug);
      if (!sources) {
        redirect("/not-found");
      }
      setDataSources(sources);
      return sources;
    } catch (error) {
      // console.error("Error fetching data sources:", error);
      return null;
    }
  }, []);

  // Add effect to fetch data sources initially
  useEffect(() => {
    if (customGuruData?.slug) {
      fetchDataSources(customGuruData.slug);
    }
  }, [customGuruData?.slug, fetchDataSources]);

  // Add effect to check API key validity
  useEffect(() => {
    const checkApiKey = async () => {
      if (!isSelfHosted) {
        setIsCheckingApiKey(false);
        return;
      }

      try {
        const settings = await getSettings();
        setIsApiKeyValid(settings?.is_openai_key_valid ?? false);
        setIsYoutubeKeyValid(settings?.is_youtube_key_valid ?? false);
      } catch (error) {
        setIsApiKeyValid(false);
      } finally {
        setIsCheckingApiKey(false);
      }
    };

    checkApiKey();
  }, [isSelfHosted]);

  // Add helper function here at the top level

  const handleAddWidget = () => {
    setIsWidgetModalVisible(true);
  };

  const handleWidgetCreate = (response) => {
    setIsWidgetModalVisible(false);
  };

  // Modify the auth check effect
  useEffect(() => {
    if (!isSelfHosted && !user && !authLoading) {
      navigation.push("/api/auth/login");

      return;
    }
  }, [user, authLoading]);

  const [initialActiveTab, setInitialActiveTab] = useState("success");
  const [isPublishing, setIsPublishing] = useState(false);

  const customGuru = customGuruData?.slug;
  const isEditMode = !!customGuru;
  const [selectedFile, setSelectedFile] = useState(null);
  const [iconUrl, setIconUrl] = useState(customGuruData?.icon_url || null);
  const [index_repo, setIndexRepo] = useState(
    customGuruData?.index_repo || false
  );
  const [sources, setSources] = useState([]);
  const fileInputRef = useRef(null);
  const [isSourcesProcessing, setIsSourcesProcessing] = useState(isProcessing);
  const [filterType, setFilterType] = useState("all");
  const [clickedSource, setClickedSource] = useState([]);
  const [isUpdating, setIsUpdating] = useState(false);
  const [initialFormValues, setInitialFormValues] = useState(null);
  const [processingSources, setProcessingSources] = useState([]);
  const [dirtyChanges, setDirtyChanges] = useState({
    sources: [],
    guruUpdated: false
  });
  const isPollingRef = useRef(false);

  const [selectedUrls, setSelectedUrls] = useState([]);
  const [isUrlSidebarOpen, setIsUrlSidebarOpen] = useState(false);
  const [urlEditorContent, setUrlEditorContent] = useState("");
  const [isYoutubeSidebarOpen, setIsYoutubeSidebarOpen] = useState(false);
  const [youtubeEditorContent, setYoutubeEditorContent] = useState("");
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isJiraSidebarOpen, setIsJiraSidebarOpen] = useState(false); // <-- New state for Jira sidebar
  const [jiraEditorContent, setJiraEditorContent] = useState(""); // <-- New state for Jira editor

  // First, add a state to track the GitHub repository source status
  const [githubRepoStatuses, setGithubRepoStatuses] = useState({});
  const [githubRepoErrors, setGithubRepoErrors] = useState({});

  const [jiraIntegration, setJiraIntegration] = useState(null); // <-- State for Jira integration details
  const [isLoadingIntegration, setIsLoadingIntegration] = useState(true); // <-- State for loading integration
  const [showJiraIntegrationModal, setShowJiraIntegrationModal] =
    useState(false); // <-- State for integration prompt modal

  useEffect(() => {
    const fetchIntegration = async () => {
      const integration = await getIntegrationDetails(customGuru, "JIRA");
      if (integration.status === 202) {
        setJiraIntegration(null);
      } else {
        setJiraIntegration(integration);
      }
      setIsLoadingIntegration(false);
    };
    fetchIntegration();
  }, []);

  const isSourceProcessing = (source) => {
    if (typeof source.id === "string") {
      return false;
    }

    // For sources with domains (website/youtube), check if any domain is not processed
    if (source.domains) {
      return source.domains.some((domain) => domain.status === "NOT_PROCESSED");
    }

    // For single sources (PDF), check its own status
    return source.status === "NOT_PROCESSED";
  };

  const form = useForm({
    resolver: zodResolver(formSchema),
    defaultValues: {
      guruName: customGuruData?.name || "",
      guruLogo: customGuruData?.icon_url || "",
      guruContext: customGuruData?.domain_knowledge || "",
      githubRepos: customGuruData?.github_repos || [],
      uploadedFiles: [],
      youtubeLinks: [],
      websiteUrls: [],
      jiraIssues: []
    }
  });

  // Add effect to check for unprocessed sources on load - at the top level
  useEffect(() => {
    if (customGuru && sources.length > 0) {
      const hasUnprocessedSources = sources.some((source) =>
        isSourceProcessing(source)
      );
      if (hasUnprocessedSources) {
        setIsSourcesProcessing(true);
        pollForGuruReadiness(customGuru);
      }
    }
  }, [customGuru, sources]);

  const updateEditorContent = useCallback((sources, type) => {
    // Filter sources by type and status
    const notProcessedSources = sources
      .filter(
        (source) =>
          source.type.toLowerCase() === type &&
          !source.deleted &&
          (source.newAddedSource || source.status === "NOT_PROCESSED")
      )
      .map((source) => source.url)
      .join("\n");

    // Update the appropriate editor content
    if (type === "youtube") {
      setYoutubeEditorContent(notProcessedSources);
    } else if (type === "website") {
      setUrlEditorContent(notProcessedSources);
    } else if (type === "jira") {
      setJiraEditorContent(notProcessedSources);
    }
  }, []);

  const handleDeleteUrls = useCallback(
    ({
      urlIds,
      sourceType,
      setSources,
      setDirtyChanges,
      clickedSource,
      setClickedSource,
      onOpenChange,
      form
    }) => {
      // Update sources state
      setSources((prevSources) => {
        const updatedSources = prevSources
          .filter((source) => !urlIds.includes(source.id))
          .map((source) => {
            if (source.domains) {
              return {
                ...source,
                domains: source.domains.filter(
                  (domain) => !urlIds.includes(domain.id)
                )
              };
            }

            return source;
          });

        // Update editor content after sources are updated
        updateEditorContent(updatedSources, sourceType);

        return updatedSources;
      });

      // Get sources being deleted with all their details
      const deletedSources = clickedSource
        .filter((source) => urlIds.includes(source.id))
        .map((source) => ({
          id: source.id,
          type: source.type,
          url: source.url,
          name: source.url,
          deleted: true
        }));

      // Update dirty changes - add each deleted source as a separate entry
      setDirtyChanges((prev) => ({
        ...prev,
        sources: [
          ...prev.sources.filter(
            (s) =>
              // Keep all non-deleted sources and deleted sources of different types
              !(s.deleted && s.type === sourceType && urlIds.includes(s.id))
          ),
          ...deletedSources
        ]
      }));

      // Update clicked source state
      const remainingUrls = clickedSource.filter(
        (url) => !urlIds.includes(url.id)
      );

      if (remainingUrls.length === 0) {
        onOpenChange(false);
      } else {
        setClickedSource(remainingUrls);
      }

      // Update form values
      const formField = `${sourceType}Links`;
      const currentLinks = form.getValues(formField) || [];
      const deletedUrls = deletedSources.map((source) => source.url);

      form.setValue(
        formField,
        currentLinks.filter((url) => !deletedUrls.includes(url))
      );
    },
    [updateEditorContent]
  );

  const handleDeleteGuru = async () => {
    setShowDeleteModal(false);
    const response = await deleteGuru(customGuru);

    if (response) {
      navigation.push("/my-gurus");
    }
  };

  const handleReindexSources = useCallback(async (sourceIds, sourceUrls) => {
    // Add reindex changes to dirtyChanges
    setDirtyChanges((prev) => ({
      ...prev,
      sources: [
        ...prev.sources,
        ...sourceIds.map((id, index) => ({
          id,
          reindexed: true,
          url: sourceUrls[index]
        }))
      ]
    }));
  }, []);

  const isMobile = useMediaQuery("(max-width: 915px)");

  useEffect(() => {
    setIsSourcesProcessing(isProcessing);
  }, [isProcessing]);

  // Add this useEffect to handle polling on page load
  useEffect(() => {
    if (isSourcesProcessing && customGuru) {
      pollForGuruReadiness(customGuru);
    }
  }, [isSourcesProcessing, customGuru]);

  // Update the useEffect where we process dataSources to find and set GitHub repo status
  useEffect(() => {
    if (customGuruData && dataSources?.results) {
      const newSources = dataSources.results.map((source) => ({
        id: source.id,
        sources:
          source.type === "YOUTUBE"
            ? "Video"
            : source.type === "PDF"
              ? "File"
              : source.type === "JIRA"
                ? "Jira"
                : "Website",
        name: source.title,
        type: source.type.toLowerCase(),
        size: source.type === "PDF" ? source.size : "N/A",
        url: source.url || "",
        status: source.status,
        last_reindex_date: source.last_reindex_date || "",
        error: source.error || "",
        private: source.type === "PDF" ? !!source.private : undefined
      }));

      // Find GitHub repository source status
      if (customGuruData?.github_repos) {
        const githubSources = dataSources.results.filter(
          (source) => source.url && source.url.startsWith("https://github.com")
        );

        if (githubSources.length > 0) {
          const newStatuses = {};
          const newErrors = {};
          let hasUnprocessed = false;

          githubSources.forEach((source) => {
            newStatuses[source.url] = source.status;
            newErrors[source.url] = source.error || null;
            if (source.status === "NOT_PROCESSED") {
              hasUnprocessed = true;
            }
          });

          setGithubRepoStatuses(newStatuses);
          setGithubRepoErrors(newErrors);

          if (hasUnprocessed) {
            setIsSourcesProcessing(true);
            pollForGuruReadiness(customGuru);
          }
        }
      }

      setSources(newSources);
      form.setValue(
        "youtubeLinks",
        newSources.filter((s) => s.type === "youtube").map((s) => s.url)
      );
      form.setValue(
        "websiteUrls",
        newSources.filter((s) => s.type === "website").map((s) => s.url)
      );
      form.setValue(
        "jiraIssues",
        newSources.filter((s) => s.type === "jira").map((s) => s.url)
      );
      form.setValue(
        "uploadedFiles",
        newSources
          .filter((s) => s.type === "pdf")
          .map((s) => ({
            file: null,
            name: s.name,
            size: s.size
          }))
      );
    }
  }, [customGuruData, dataSources, customGuru]); // Added customGuru to dependencies

  // Watch all form fields
  // const formValues = form.watch();

  useEffect(() => {
    // if there is a error in the youtubeLinks or websiteUrls, then show the error message
    if (
      form.formState.errors.youtubeLinks ||
      form.formState.errors.websiteUrls
    ) {
      CustomToast({
        message: `Please enter a valid ${form.formState.errors.youtubeLinks ? "YouTube" : "website"} link.`,
        variant: "error"
      });
    }
  }, [form.formState.errors]);

  const handleFileUpload = (event) => {
    const files = Array.from(event.target.files);
    const newSources = files
      .filter((file) => !sources.some((s) => s.name === file.name))
      .map((file) => ({
        id: Date.now() + Math.random(),
        sources: "File",
        name: file.name,
        type: "pdf",
        size: file.size,
        file: file,
        newAddedSource: true
      }));

    setSources((prevSources) => [...prevSources, ...newSources]);

    setDirtyChanges((prev) => ({
      ...prev,
      sources: [
        ...prev.sources,
        ...newSources.map((source) => ({
          id: source.id,
          type: "pdf",
          file: source.file,
          name: source.name,
          size: source.size,
          newAddedSource: true,
          private: false
        }))
      ]
    }));

    const currentUploadedFiles = form.getValues("uploadedFiles") || [];
    const newUploadedFiles = newSources.map((source) => ({
      file: source.file,
      name: source.name,
      size: source.size
    }));

    form.setValue(
      "uploadedFiles",
      [...currentUploadedFiles, ...newUploadedFiles],
      {
        shouldValidate: true,
        shouldDirty: true
      }
    );

    // Clear the file input's value to allow uploading the same file again
    event.target.value = "";
  };

  const handleAddUrls = useCallback(
    (links, sourceType) => {
      setSources((prevSources) => {
        // Get the editor content based on sourceType
        const editorContent =
          sourceType === "youtube" ? youtubeEditorContent : urlEditorContent;
        const currentUrls = editorContent.split("\n").filter(Boolean);

        // Keep existing sources that are already processed
        const existingProcessedSources = prevSources.filter(
          (source) =>
            source.type.toLowerCase() !== sourceType ||
            source.status === "SUCCESS" ||
            source.status === "FAIL"
        );

        // Create new source objects for each URL in the editor
        const newSources = currentUrls.map((url) => ({
          id: url,
          type: sourceType,
          sources: sourceType === "youtube" ? "Video" : "Website",
          url: url,
          status: "NOT_PROCESSED",
          error: null,
          newAddedSource: true,
          domain: getNormalizedDomain(url)
        }));

        // Remove duplicates from newSources by itself and check for duplicates with existing processed sources
        const newSourcesWithoutDuplicates = newSources.filter(
          (source, index, self) =>
            index === self.findIndex((t) => t.url === source.url) &&
            !existingProcessedSources.some((s) => s.url === source.url)
        );

        // Combine existing processed sources with new sources
        const updatedSources = [
          ...existingProcessedSources,
          ...newSourcesWithoutDuplicates
        ];

        // Update the form's URL fields to match editor content
        const formField =
          sourceType === "youtube" ? "youtubeLinks" : "websiteUrls";

        // Get all URLs of this type, including both processed and new ones
        const allTypeUrls = updatedSources
          .filter((source) => source.type.toLowerCase() === sourceType)
          .map((source) => source.url);

        form.setValue(formField, allTypeUrls);

        return updatedSources;
      });

      // Update dirtyChanges to reflect only the new URLs
      setDirtyChanges((prev) => {
        const editorContent =
          sourceType === "youtube" ? youtubeEditorContent : urlEditorContent;
        const currentUrls = editorContent.split("\n").filter(Boolean);

        // Keep existing deleted sources and sources of other types
        const filteredSources = prev.sources.filter(
          (source) => source.type !== sourceType || source.deleted
        );

        // Add only new entries from editor content that aren't already in sources
        const newEntries = currentUrls
          .filter((url) => {
            // Check if this URL is new (not in existing sources)
            const isNewUrl = !sources.some(
              (source) =>
                source.url === url && source.status !== "NOT_PROCESSED"
            );

            return isNewUrl;
          })
          .map((url) => ({
            id: url,
            type: sourceType,
            url: url,
            name: url,
            error: null,
            newAddedSource: true
          }));

        return {
          ...prev,
          sources: [...filteredSources, ...newEntries]
        };
      });
    },
    [form, youtubeEditorContent, urlEditorContent, sources]
  );

  const handleDeleteSource = (source) => {
    const sourceIds = source.domains
      ? source.domains.map((domain) => domain.id)
      : [source.id];

    handleDeleteUrls({
      urlIds: sourceIds,
      sourceType: source.type.toLowerCase(),
      setSources,
      setDirtyChanges,
      clickedSource: source.domains || [source],
      setClickedSource,
      onOpenChange: () => {}, // No-op since we don't need to close any dialog
      form
    });
  };

  const handleReindexSource = (source) => {
    const sourceIds = source.domains?.map((domain) => domain.id) || [source.id];
    const sourceUrls = source.domains?.map((domain) => domain.url) || [
      source.url
    ];

    handleReindexSources(sourceIds, sourceUrls);
  };

  // Update handleEditSource
  const handleEditSource = (source, tabValue) => {
    const sourceType = source.type.toLowerCase();

    if (
      sourceType !== "website" &&
      sourceType !== "youtube" &&
      sourceType !== "jira"
    )
      return;

    const domains = source.domains?.map((d) => ({
      ...d,
      type: sourceType.toUpperCase()
    })) || [
      {
        id: source.id,
        url: source.url,
        type: sourceType.toUpperCase(),
        status: source.status || "SUCCESS",
        error: source.error || null
      }
    ];

    const newTabValue = tabValue || determineInitialTab(domains);

    setInitialActiveTab(newTabValue);
    setClickedSource(domains);

    // Set the appropriate sidebar state
    const setSidebar =
      sourceType === "youtube"
        ? setIsYoutubeSidebarOpen
        : sourceType === "jira"
          ? setIsJiraSidebarOpen
          : setIsUrlSidebarOpen;

    setSidebar(true);
  };

  const pollForGuruReadiness = async (guruSlug) => {
    // If already polling, return early
    if (isPollingRef.current) {
      return;
    }

    // Set polling flag
    isPollingRef.current = true;
    const pollInterval = 3000;
    const maxAttempts = 100;
    let attempts = 0;

    const poll = async () => {
      attempts++;
      try {
        const isReady = await checkGuruReadiness(guruSlug);

        if (isReady) {
          // Fetch the latest sources data
          const latestSources = await fetchDataSources(guruSlug);
          if (!latestSources) {
            redirect("/not-found");
          }

          if (latestSources?.results) {
            // Check GitHub repository status if it exists
            if (customGuruData?.github_repos) {
              const githubSources = latestSources.results.filter(
                (source) =>
                  source.url && source.url.startsWith("https://github.com")
              );

              if (githubSources.length > 0) {
                const newStatuses = {};
                const newErrors = {};
                let hasUnprocessed = false;

                githubSources.forEach((source) => {
                  newStatuses[source.url] = source.status;
                  newErrors[source.url] = source.error || null;
                  if (source.status === "NOT_PROCESSED") {
                    hasUnprocessed = true;
                  }
                });

                setGithubRepoStatuses(newStatuses);
                setGithubRepoErrors(newErrors);
              }
            }

            // Create a map of existing privacy settings
            const existingPrivacySettings = sources.reduce((acc, source) => {
              if (source.type?.toLowerCase() === "pdf") {
                acc[source.id] = source.private;
              }

              return acc;
            }, {});

            // Update sources state while preserving privacy settings
            const updatedSources = latestSources.results.map((source) => ({
              id: source.id,
              sources:
                source.type === "YOUTUBE"
                  ? "Video"
                  : source.type === "PDF"
                    ? "File"
                    : source.type === "JIRA"
                      ? "Jira"
                      : "Website",
              name: source.title,
              type: source.type.toLowerCase(),
              size: source.type === "PDF" ? source.size : "N/A",
              url: source.url || "",
              status: source.status,
              error: source.error || "",
              // Preserve existing privacy setting or use the one from backend
              private:
                source.type === "PDF"
                  ? existingPrivacySettings[source.id] !== undefined
                    ? existingPrivacySettings[source.id]
                    : !!source.private
                  : undefined
            }));

            setSources(updatedSources);

            // Update form values and reset states
            const newFormValues = {
              ...form.getValues(),
              youtubeLinks: updatedSources
                .filter((s) => s.type === "youtube")
                .map((s) => s.url),
              websiteUrls: updatedSources
                .filter((s) => s.type === "website")
                .map((s) => s.url),
              jiraIssues: updatedSources
                .filter((s) => s.type === "jira")
                .map((s) => s.url),
              uploadedFiles: updatedSources
                .filter((s) => s.type === "pdf")
                .map((s) => ({
                  file: null,
                  name: s.name,
                  size: s.size
                }))
            };

            form.reset(newFormValues);
            setInitialFormValues(newFormValues);
            setDirtyChanges({ sources: [], guruUpdated: false });
            setUrlEditorContent("");
            setYoutubeEditorContent("");
            setProcessingSources([]);

            setIsSourcesProcessing(false);
            // Reset polling flag before returning
            isPollingRef.current = false;
            return true; // Indicate successful completion
          }
        } else if (attempts < maxAttempts) {
          await new Promise((resolve) => setTimeout(resolve, pollInterval));
          return await poll();
        } else {
          setIsSourcesProcessing(false);
          CustomToast({
            message:
              "Sources are being processed in the background. You can continue using the guru.",
            variant: "info"
          });
          // Reset polling flag before returning
          isPollingRef.current = false;
          return false; // Indicate timeout
        }
      } catch (error) {
        // console.error("Error in polling:", error);
        if (attempts < maxAttempts) {
          await new Promise((resolve) => setTimeout(resolve, pollInterval));
          return await poll();
        } else {
          setIsSourcesProcessing(false);
          CustomToast({
            message:
              "An error occurred while processing sources. Please try again.",
            variant: "error"
          });
          // Reset polling flag before returning
          isPollingRef.current = false;
          return false; // Indicate error
        }
      }
    };

    return await poll();
  };

  const validateSourceLimits = (sources, dirtyChanges, customGuruData) => {
    if (!customGuruData) return true;

    if (isSelfHosted) return true;

    // Get current counts and limits
    const youtubeCount = sources.filter(
      (s) => s.type.toLowerCase() === "youtube" && !s.deleted
    ).length;
    const websiteCount = sources.filter(
      (s) => s.type.toLowerCase() === "website" && !s.deleted
    ).length;
    const jiraCount = sources.filter(
      (s) => s.type.toLowerCase() === "jira" && !s.deleted
    ).length;

    // Calculate PDF size
    let currentPdfSize = sources
      .filter(
        (s) => s.type.toLowerCase() === "pdf" && !s.deleted && !s.newAddedSource
      )
      .reduce((total, pdf) => total + (pdf.size || 0), 0);

    // Add new PDF sizes
    const newPdfSize = dirtyChanges.sources
      .filter((s) => s.type === "pdf" && s.newAddedSource && !s.deleted)
      .reduce((total, pdf) => total + (pdf.size || 0), 0);

    const pdfSizeMb = (currentPdfSize + newPdfSize) / 1024 / 1024;

    // Check against limits
    const youtubeLimit =
      customGuruData.youtube_limit === undefined
        ? Infinity
        : customGuruData.youtube_limit;
    const websiteLimit =
      customGuruData.website_limit === undefined
        ? Infinity
        : customGuruData.website_limit;
    const jiraLimit =
      customGuruData.jira_limit === undefined
        ? Infinity
        : customGuruData.jira_limit;
    const pdfSizeLimitMb =
      customGuruData.pdf_size_limit_mb === undefined
        ? Infinity
        : customGuruData.pdf_size_limit_mb;

    // Validate limits
    if (youtubeCount > youtubeLimit) {
      CustomToast({
        message: `You have exceeded the YouTube source limit (${youtubeLimit}).`,
        variant: "error"
      });
      return false;
    }

    if (websiteCount > websiteLimit) {
      CustomToast({
        message: `You have exceeded the website source limit (${websiteLimit}).`,
        variant: "error"
      });
      return false;
    }

    if (pdfSizeMb > pdfSizeLimitMb) {
      CustomToast({
        message: `You have exceeded the PDF size limit (${pdfSizeLimitMb} MB).`,
        variant: "error"
      });
      return false;
    }

    if (jiraCount > jiraLimit) {
      CustomToast({
        message: `You have exceeded the Jira issue limit (${jiraLimit}).`,
        variant: "error"
      });
      return false;
    }

    return true;
  };

  const onSubmit = async (data) => {
    try {
      // Check data source limits first
      if (!validateSourceLimits(sources, dirtyChanges, customGuruData)) {
        return;
      }

      // Only validate files if there are new files being added
      const newFiles = dirtyChanges.sources.filter(
        (source) =>
          source.type === "pdf" && source.newAddedSource && !source.deleted
      );

      if (newFiles.length > 0) {
        const validFiles = newFiles.every(
          (file) =>
            file.name &&
            (typeof file.size === "number" || typeof file.size === "string")
        );

        if (!validFiles) {
          CustomToast({
            message: "Invalid file data. Please try uploading the files again.",
            variant: "error"
          });

          return;
        }
      }

      if (!data.guruContext) {
        return;
      }

      if (!isEditMode) {
        setIsPublishing(true);
      } else {
        setIsUpdating(true);
      }

      // Find the hasResources check and update it like this:
      const hasResources =
        data.uploadedFiles?.length > 0 ||
        data.youtubeLinks?.length > 0 ||
        data.websiteUrls?.length > 0 ||
        data.jiraIssues?.length > 0;

      // Add check for GitHub repo changes
      const hasGithubChanges = isEditMode
        ? (data.githubRepos || []) !== (customGuruData?.github_repos || [])
        : !!data.githubRepos;

      if (
        (!hasResources && (!index_repo || !hasGithubChanges) && !isEditMode) ||
        (sources.length === 0 &&
          (!index_repo || !hasGithubChanges) &&
          isEditMode)
      ) {
        CustomToast({
          message: index_repo
            ? "At least one resource (PDF, YouTube link, website URL) must be added, or GitHub repository settings must be changed."
            : "At least one resource (PDF, YouTube link, website URL) must be added.",
          variant: "error"
        });

        return;
      }

      // Track if any changes were made that require polling
      let hasChanges = false;

      // First handle guru update/create
      const formData = new FormData();

      if (!isEditMode) {
        formData.append("name", data.guruName);
      }
      formData.append("domain_knowledge", data.guruContext);
      formData.append(
        "github_repos",
        JSON.stringify(data.githubRepos.filter(Boolean))
      );

      // Handle guruLogo
      if (data.guruLogo instanceof File) {
        formData.append("icon_image", data.guruLogo);
      } else if (
        typeof data.guruLogo === "string" &&
        data.guruLogo.startsWith("http")
      ) {
        formData.append("existing_guru_logo", data.guruLogo);
      }

      const guruResponse = isEditMode
        ? await updateGuru(customGuru, formData)
        : await createGuru(formData);

      if (guruResponse.error) {
        throw new Error(guruResponse.message);
      }

      if (data.guruLogo instanceof File) {
        setSelectedFile(null);
        setIconUrl(guruResponse.icon_url || customGuruData?.icon_url);
      }

      const guruSlug = isEditMode ? customGuru : guruResponse.slug;

      // Fetch updated guru data after create/update
      await fetchGuruData(guruSlug);

      // If there are GitHub-related changes, mark for polling
      if (index_repo && hasGithubChanges) {
        hasChanges = true;
        await fetchDataSources(guruSlug);
      }

      // Handle deleted sources
      if (isEditMode && dirtyChanges.sources.some((source) => source.deleted)) {
        const deletedSourceIds = dirtyChanges.sources
          .filter((source) => source.deleted)
          .flatMap((source) =>
            Array.isArray(source.id) ? source.id : [source.id]
          );

        if (deletedSourceIds.length > 0) {
          hasChanges = true;
          const deleteResponse = await deleteGuruSources(
            guruSlug,
            deletedSourceIds
          );

          if (deleteResponse.error) {
            throw new Error(deleteResponse.message);
          }

          // Fetch updated sources after deletion
          await fetchDataSources(guruSlug);
        }
      }

      // Handle privacy changes
      const existingPdfPrivacyChanges = dirtyChanges.sources
        .filter(
          (source) =>
            source.type === "pdf" &&
            source.privacyToggled &&
            !source.newAddedSource
        )
        .map((source) => ({
          id: source.id,
          private: source.private
        }));

      if (existingPdfPrivacyChanges.length > 0) {
        hasChanges = true;
        await updateGuruDataSourcesPrivacy(guruSlug, {
          data_sources: existingPdfPrivacyChanges
        });

        // Fetch updated sources after privacy changes
        await fetchDataSources(guruSlug);
      }

      // Handle reindexed sources
      if (
        isEditMode &&
        dirtyChanges.sources.some((source) => source.reindexed)
      ) {
        const reindexedSourceIds = dirtyChanges.sources
          .filter((source) => source.reindexed)
          .flatMap((source) =>
            Array.isArray(source.id) ? source.id : [source.id]
          );

        if (reindexedSourceIds.length > 0) {
          hasChanges = true;
          const reindexResponse = await reindexGuruSources(
            guruSlug,
            reindexedSourceIds
          );

          if (reindexResponse.error) {
            throw new Error(reindexResponse.message);
          }

          // Fetch updated sources after reindexing
          await fetchDataSources(guruSlug);
        }
      }

      // Handle new sources
      const newSourcesFormData = new FormData();
      let hasNewSources = false;

      // Add PDF files from dirtyChanges
      const pdfSources = dirtyChanges.sources.filter(
        (source) =>
          source.type === "pdf" && source.newAddedSource && !source.deleted
      );

      if (pdfSources.length > 0) {
        pdfSources.forEach((source) => {
          if (source.file instanceof File) {
            newSourcesFormData.append("pdf_files", source.file);
            hasNewSources = true;
          }
        });

        const pdfPrivacies = pdfSources.map(
          (source) => source.private || false
        );

        newSourcesFormData.append(
          "pdf_privacies",
          JSON.stringify(pdfPrivacies)
        );
      }

      // Add YouTube URLs
      const youtubeSources = dirtyChanges.sources
        .filter(
          (source) =>
            source.type === "youtube" &&
            source.newAddedSource &&
            !source.deleted
        )
        .map((source) => source.url);

      if (youtubeSources.length > 0) {
        newSourcesFormData.append(
          "youtube_urls",
          JSON.stringify(youtubeSources)
        );
        hasNewSources = true;
      }

      // Add Website URLs
      const websiteSources = dirtyChanges.sources
        .filter(
          (source) =>
            source.type === "website" &&
            source.newAddedSource &&
            !source.deleted
        )
        .map((source) => source.url);

      if (websiteSources.length > 0) {
        newSourcesFormData.append(
          "website_urls",
          JSON.stringify(websiteSources)
        );
        hasNewSources = true;
      }

      // Add Jira issues
      const jiraSources = dirtyChanges.sources
        .filter(
          (source) =>
            source.type === "jira" && source.newAddedSource && !source.deleted
        )
        .map((source) => source.url);

      if (jiraSources.length > 0) {
        newSourcesFormData.append("jira_urls", JSON.stringify(jiraSources));
        hasNewSources = true;
      }

      if (hasNewSources) {
        hasChanges = true;
        setIsSourcesProcessing(true);

        // Get all source IDs including those from the same domain groups
        const processingIds = sources.reduce((ids, source) => {
          if (source.domains) {
            // For grouped domains (website/youtube), add all domain IDs
            const domainUrls = source.domains.map((d) => d.url);
            const matchingNewSources = dirtyChanges.sources.some(
              (newSource) =>
                newSource.newAddedSource &&
                !newSource.deleted &&
                domainUrls.includes(newSource.url)
            );

            if (matchingNewSources) {
              ids.push(source.id); // Add the group ID
              source.domains.forEach((domain) => ids.push(domain.id)); // Add all domain IDs
            }
          } else if (
            dirtyChanges.sources.some(
              (newSource) =>
                newSource.newAddedSource &&
                !newSource.deleted &&
                newSource.id === source.id
            )
          ) {
            // For PDFs, use the file name instead of the temporary ID
            if (source.type?.toLowerCase() === "pdf") {
              ids.push(source.name);
            } else {
              ids.push(source.id);
            }
          }

          return ids;
        }, []);

        setProcessingSources((prev) => [...prev, ...processingIds]);

        const sourcesResponse = await addGuruSources(
          guruSlug,
          newSourcesFormData
        );

        if (sourcesResponse.error) {
          throw new Error(sourcesResponse.message);
        }

        // Fetch updated sources after adding new sources
        await fetchDataSources(guruSlug);
      }

      // If not in edit mode, redirect immediately after guru creation
      if (!isEditMode) {
        redirectingRef.current = true;
        window.location.href = `/guru/${guruSlug}`;
        return;
      }

      // Poll for readiness only if there were changes
      if (hasChanges) {
        const pollingSuccessful = await pollForGuruReadiness(guruSlug);
        if (pollingSuccessful) {
          // Fetch final guru data after all operations
          await fetchGuruData(guruSlug);
          CustomToast({
            message: "Guru updated successfully!",
            variant: "success"
          });
        }
      } else if (isEditMode) {
        // If no changes required polling but guru was updated
        CustomToast({
          message: "Guru updated successfully!",
          variant: "success"
        });
      }

      // Reset states after all updates are complete
      setInitialFormValues({
        ...data,
        guruLogo: guruResponse.icon_url || data.guruLogo,
        uploadedFiles: data.uploadedFiles || [],
        youtubeLinks: data.youtubeLinks || [],
        websiteUrls: data.websiteUrls || [],
        jiraIssues: data.jiraIssues || []
      });

      fetchDataSources(guruSlug);
      setDirtyChanges({ sources: [], guruUpdated: false });
    } catch (error) {
      CustomToast({
        message: `Error ${isEditMode ? "updating" : "creating"} guru: ${error.message}`,
        variant: "error"
      });
    } finally {
      setIsUpdating(false);
      setIsPublishing(false);
      setIsSourcesProcessing(false);
      setProcessingSources([]);
    }
  };

  useEffect(() => {
    // Find URLs that are both in deleted and added states
    const duplicateUrls = dirtyChanges.sources.reduce((acc, source) => {
      const url = source.url;
      const id = source.id;
      const isDeleted = dirtyChanges.sources.some(
        (s) => s.deleted && (s.type === "pdf" ? s.id === id : s.url === url)
      );
      const isAdded = dirtyChanges.sources.some(
        (s) =>
          s.newAddedSource && (s.type === "pdf" ? s.id === id : s.url === url)
      );

      if (isDeleted && isAdded) {
        if (source.type === "pdf") {
          acc.add(id);
        } else {
          acc.add(url);
        }
      }

      return acc;
    }, new Set());

    // If we found any URLs that are both deleted and added, remove them from both states
    if (duplicateUrls.size > 0) {
      setDirtyChanges((prev) => ({
        ...prev,
        sources: prev.sources.filter((source) => {
          if (source.type === "pdf") {
            return !duplicateUrls.has(source.id);
          } else {
            return !duplicateUrls.has(source.url);
          }
        })
      }));

      return;
    }

    // Only deduplicate URL sources, keep all PDF sources
    const uniqueSources = dirtyChanges.sources.filter(
      (source, index, self) =>
        source.type?.toLowerCase() === "pdf"
          ? true // Keep all PDF sources
          : index === self.findIndex((t) => t.url === source.url) // Deduplicate URLs
    );

    if (uniqueSources.length !== dirtyChanges.sources.length) {
      setDirtyChanges((prev) => ({
        ...prev,
        sources: uniqueSources
      }));
    }

    // if the dirtyChanges length is 0, reset form to initial values and set SourceDialog content to empty
    if (dirtyChanges.sources.length === 0 && initialFormValues) {
      // Set each field individually
      Object.entries(initialFormValues).forEach(([fieldName, value]) => {
        form.setValue(fieldName, value);
      });

      setUrlEditorContent("");
      setYoutubeEditorContent("");
    }
  }, [dirtyChanges.sources, initialFormValues, form.setValue]);

  const [hasFormChanged, setHasFormChanged] = useState(false);

  // Modify hasFormChanged to be a pure function
  useEffect(() => {
    if (!isEditMode || isPublishing) {
      setHasFormChanged(false);
      return;
    }
    // Check for changes in sources
    if (redirectingRef.current) {
      setHasFormChanged(false);
      return;
    }
    if (dirtyChanges.sources.length > 0) {
      setHasFormChanged(true);
      return;
    }
    if (dirtyChanges.guruUpdated) {
      setHasFormChanged(true);
      return;
    }

    if (!initialFormValues) {
      setHasFormChanged(false);
      return;
    }

    const currentValues = form.getValues();
    // Check for changes in basic fields
    const basicFieldsChanged =
      currentValues.guruContext !== initialFormValues.guruContext ||
      (currentValues.githubRepos || []).some(
        (repo) => !initialFormValues.githubRepos.includes(repo)
      ) ||
      (currentValues.githubRepos || []).length !==
        (initialFormValues.githubRepos || []).length;

    // Check for changes in arrays (files, links, urls)
    const compareArrays = (arr1 = [], arr2 = []) => {
      if (
        JSON.stringify([...arr1].sort()) !== JSON.stringify([...arr2].sort())
      ) {
        setHasFormChanged(true);
        return;
      }
    };

    const sourcesChanged =
      compareArrays(
        currentValues.uploadedFiles?.map((f) => f.name),
        initialFormValues.uploadedFiles?.map((f) => f.name)
      ) ||
      compareArrays(
        currentValues.youtubeLinks,
        initialFormValues.youtubeLinks
      ) ||
      compareArrays(currentValues.websiteUrls, initialFormValues.websiteUrls);

    const logoChanged = selectedFile !== null;

    setHasFormChanged(basicFieldsChanged || sourcesChanged || logoChanged);
  }, [dirtyChanges, initialFormValues, selectedFile, form]);

  // Update form onChange to track guru info changes
  useEffect(() => {
    const subscription = form.watch((value, { name, type }) => {
      if (type === "change" && initialFormValues) {
        const initialValue = initialFormValues[name];
        const currentValue = value[name];

        if (JSON.stringify(initialValue) !== JSON.stringify(currentValue)) {
          setDirtyChanges((prev) => ({
            ...prev,
            guruUpdated: true
          }));
        }
      }
    });

    return () => subscription.unsubscribe();
  }, [form, initialFormValues]);

  // Add useEffect to initialize initialFormValues
  useEffect(() => {
    if (customGuruData && dataSources?.results) {
      const initialValues = {
        guruName: customGuruData.name || "",
        guruLogo: customGuruData.icon_url || "",
        guruContext: customGuruData.domain_knowledge || "",
        githubRepos: customGuruData.github_repos || [],
        uploadedFiles: dataSources.results
          .filter((s) => s.type.toLowerCase() === "pdf")
          .map((s) => ({ name: s.title })),
        youtubeLinks: dataSources.results
          .filter((s) => s.type.toLowerCase() === "youtube")
          .map((s) => s.url),
        websiteUrls: dataSources.results
          .filter((s) => s.type.toLowerCase() === "website")
          .map((s) => s.url)
      };

      setInitialFormValues(initialValues);
    }
  }, [customGuruData, dataSources]);

  // Add this near the top of the component
  useEffect(() => {
    // Cleanup function to ensure pointer-events is restored when component unmounts
    return () => {
      document.body.style.pointerEvents = "";
    };
  }, []);

  // URL sidebar handlers
  const handleUrlEditorChange = useCallback((newValue) => {
    setUrlEditorContent(newValue);
  }, []);

  // Simplify handleYoutubeEditorChange to only update state
  const handleYoutubeEditorChange = useCallback((newValue) => {
    setYoutubeEditorContent(newValue);
  }, []);

  // Placeholder handlers for Jira
  const handleJiraEditorChange = useCallback((newValue) => {
    setJiraEditorContent(newValue);
  }, []);

  // Placeholder - Needs actual implementation for adding Jira links
  const handleAddJiraUrls = useCallback(
    (links) => {
      setSources((prevSources) => {
        // Get the current Jira issues from editor content
        const currentIssues = jiraEditorContent.split("\n").filter(Boolean);

        // Keep existing sources that are already processed (excluding unprocessed Jira issues)
        const existingProcessedSources = prevSources.filter(
          (source) =>
            source.type.toLowerCase() !== "jira" ||
            source.status === "SUCCESS" ||
            source.status === "FAIL"
        );

        // Create new source objects for each Jira issue in the editor
        const newSources = currentIssues.map((issue) => ({
          id: issue,
          type: "jira",
          sources: "Jira",
          url: issue,
          status: "NOT_PROCESSED",
          error: null,
          newAddedSource: true,
          issueKey: issue.split("/").pop() // Extract issue key from URL
        }));

        // Remove duplicates from newSources and check for duplicates with existing processed sources
        const newSourcesWithoutDuplicates = newSources.filter(
          (source, index, self) =>
            index === self.findIndex((t) => t.url === source.url) &&
            !existingProcessedSources.some((s) => s.url === source.url)
        );

        // Combine existing processed sources with new sources
        const updatedSources = [
          ...existingProcessedSources,
          ...newSourcesWithoutDuplicates
        ];

        // Update the form's Jira fields to match editor content
        const formField = "jiraIssues";

        // Get all Jira issues, including both processed and new ones
        const allJiraIssues = updatedSources
          .filter((source) => source.type.toLowerCase() === "jira")
          .map((source) => source.url);

        form.setValue(formField, allJiraIssues);

        return updatedSources;
      });

      // Update dirtyChanges to reflect only the new Jira issues
      setDirtyChanges((prev) => {
        const currentIssues = jiraEditorContent.split("\n").filter(Boolean);

        // Keep existing deleted sources and sources of other types
        const filteredSources = prev.sources.filter(
          (source) => source.type !== "jira" || source.deleted
        );

        // Add only new entries from editor content that aren't already in sources
        const newEntries = currentIssues
          .filter((issue) => {
            // Check if this issue is new (not in existing sources)
            const isNewIssue = !sources.some(
              (source) =>
                source.url === issue && source.status !== "NOT_PROCESSED"
            );

            return isNewIssue;
          })
          .map((issue) => ({
            id: issue,
            type: "jira",
            url: issue,
            name: issue,
            error: null,
            newAddedSource: true
          }));

        return {
          ...prev,
          sources: [...filteredSources, ...newEntries]
        };
      });
    },
    [form, jiraEditorContent, sources]
  );

  // Add this near the top of the component where other useEffects are
  // Leave site? Changes you made may not be saved.
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (hasFormChanged) {
        e.preventDefault();
        e.returnValue = ""; // Required for Chrome
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [hasFormChanged]);

  const handlePrivacyBadgeClick = (e, source) => {
    e.preventDefault();
    e.stopPropagation();

    if (isSourcesProcessing) return;

    // Toggle the private status in sources state
    setSources((prevSources) =>
      prevSources.map((s) => {
        if (s.id === source.id) {
          return {
            ...s,
            private: !s.private
          };
        }

        return s;
      })
    );
    // Update dirtyChanges to track the toggle
    setDirtyChanges((prev) => {
      const existingChangeIndex = prev.sources.findIndex(
        (s) => s.id === source.id
      );

      if (existingChangeIndex !== -1) {
        // If source is newly added, update its privacy in dirtyChanges
        if (prev.sources[existingChangeIndex].newAddedSource) {
          return {
            ...prev,
            sources: prev.sources.map((s, i) =>
              i === existingChangeIndex ? { ...s, private: !s.private } : s
            )
          };
        }

        // If this source was already toggled, check if it's back to original state
        const currentSource = sources.find((s) => s.id === source.id);

        if (currentSource.private === source.private) {
          // Remove from dirty changes if back to original
          return {
            ...prev,
            sources: prev.sources.filter((_, i) => i !== existingChangeIndex)
          };
        }

        return prev; // Keep existing change if still different from original
      }

      // Add new privacy toggle to dirty changes
      return {
        ...prev,
        sources: [
          ...prev.sources,
          {
            id: source.id,
            type: "pdf",
            privacyToggled: true,
            private: !source.private,
            name: source.name,
            url: source.url
          }
        ]
      };
    });
  };

  // Add cleanup when closing dialogs
  useEffect(() => {
    if (!isUrlSidebarOpen && !isYoutubeSidebarOpen && !isJiraSidebarOpen) {
      setClickedSource([]);
      setSelectedUrls([]);
    }

    // if youtubeEditorContent is empty and newAddedSource is true, clear the dirtyChanges that is a youtube source
    if (
      youtubeEditorContent === "" &&
      dirtyChanges.sources.some(
        (source) => source.newAddedSource && source.type === "youtube"
      )
    ) {
      setDirtyChanges((prev) => ({
        ...prev,
        sources: prev.sources.filter((source) => source.type !== "youtube")
      }));
    }

    if (
      urlEditorContent === "" &&
      dirtyChanges.sources.some(
        (source) => source.newAddedSource && source.type === "website"
      )
    ) {
      setDirtyChanges((prev) => ({
        ...prev,
        sources: prev.sources.filter((source) => source.type !== "website")
      }));
    }

    if (
      jiraEditorContent === "" &&
      dirtyChanges.sources.some(
        (source) => source.newAddedSource && source.type === "jira"
      )
    ) {
      setDirtyChanges((prev) => ({
        ...prev,
        sources: prev.sources.filter((source) => source.type !== "jira")
      }));
    }

    const youtubeUrls = youtubeEditorContent
      .split("\n")
      .map((url) => url.trim())
      .filter((url) => url && isValidUrl(url));

    const websiteUrls = urlEditorContent
      .split("\n")
      .map((url) => url.trim())
      .filter((url) => url && isValidUrl(url));

    const jiraUrls = jiraEditorContent
      .split("\n")
      .map((url) => url.trim())
      .filter((url) => url && isValidUrl(url));

    const uniqueYoutubeUrls = [...new Set(youtubeUrls)];
    const uniqueWebsiteUrls = [...new Set(websiteUrls)];
    const uniqueJiraUrls = [...new Set(jiraUrls)];

    if (uniqueYoutubeUrls.length > 0) {
      const newYoutubeUrls = uniqueYoutubeUrls.map((url) => ({
        id: url,
        type: "youtube",
        url: url,
        status: "NOT_PROCESSED",
        newAddedSource: true
      }));

      handleAddUrls(newYoutubeUrls, "youtube");
    }

    if (uniqueWebsiteUrls.length > 0) {
      const newWebsiteUrls = uniqueWebsiteUrls.map((url) => ({
        id: url,
        type: "website",
        url: url,
        status: "NOT_PROCESSED",
        newAddedSource: true
      }));

      handleAddUrls(newWebsiteUrls, "website");
    }

    if (uniqueJiraUrls.length > 0) {
      const newJiraUrls = uniqueJiraUrls.map((url) => ({
        id: url,
        type: "jira",
        url: url,
        status: "NOT_PROCESSED",
        newAddedSource: true
      }));

      handleAddJiraUrls(newJiraUrls);
    }
  }, [isUrlSidebarOpen, isYoutubeSidebarOpen, isJiraSidebarOpen]);

  // useEffect(() => {
  //   console.log("dirtyChanges useeffect", dirtyChanges);
  // }, [dirtyChanges]);

  // useEffect(() => {
  //   console.log("isProcessing useeffect", isProcessing);
  // }, [isProcessing]);

  // useEffect(() => {
  //   console.log("isUpdating useeffect", isUpdating);
  // }, [isUpdating]);

  // useEffect(() => {
  //   console.log("sources", sources);
  // }, [sources]);

  // If still loading auth or no user, show loading state
  if (!isSelfHosted && (authLoading || (!user && !authLoading))) {
    return (
      <div className="flex flex-col items-center justify-center w-full h-[50vh]">
        <LoaderCircle className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (isSelfHosted && isCheckingApiKey) {
    return (
      <div className="flex flex-col items-center justify-center w-full h-[50vh]">
        <LoaderCircle className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  // Modify the form component
  return (
    <>
      {" "}
      {isSelfHosted && !isCheckingApiKey && !isApiKeyValid && (
        <div className="w-full border-b border-red-200 bg-red-50">
          <div className="flex items-center gap-3 px-6 py-3">
            <AlertTriangle className="h-5 w-5 flex-shrink-0 text-red-600" />
            <div className="flex-1">
              <p className="text-sm font-medium text-red-900">
                Configure a valid OpenAI API Key to create a Guru.
              </p>
            </div>
            <Link
              href="/settings"
              className="flex-shrink-0 rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-offset-2">
              Configure API Key →
            </Link>
          </div>
        </div>
      )}
      <section className="flex flex-col w-full p-6 border-b border-[#E5E7EB]">
        <h1 className="text-h5 font-semibold text-black-600">
          {isEditMode ? "Edit Guru" : "New Guru"}
        </h1>
      </section>
      <div className="p-6 pt-0">
        <Form {...form}>
          <form
            className={cn(
              "space-y-8",
              isSelfHosted && !isApiKeyValid && "opacity-50 pointer-events-none"
            )}
            onSubmit={(e) => {
              e.preventDefault();
              form.trigger().then((isValid) => {
                if (isValid) {
                  form.handleSubmit(onSubmit)(e);
                }
              });
            }}>
            {/* Use GuruDetailsSection component */}
            <GuruDetailsSection
              form={form}
              isEditMode={isEditMode}
              isProcessing={isProcessing}
              isSubmitting={form.formState.isSubmitting}
              isSourcesProcessing={isSourcesProcessing}
              iconUrl={iconUrl}
              selectedFile={selectedFile}
              setSelectedFile={setSelectedFile}
              setIconUrl={setIconUrl}
              setDirtyChanges={setDirtyChanges}
            />

            <div className="max-w-3xl">
              <div className="flex items-center space-x-4">
                <GithubSourceSection
                  index_repo={index_repo}
                  isEditMode={isEditMode}
                  githubRepoStatuses={githubRepoStatuses}
                  githubRepoErrors={githubRepoErrors}
                  isSourcesProcessing={isSourcesProcessing}
                  isProcessing={isProcessing}
                  customGuruData={customGuruData}
                />
              </div>
            </div>

            {/* Use SourcesTableSection component */}
            <SourcesTableSection
              sources={sources}
              isProcessing={isProcessing}
              isSourcesProcessing={isSourcesProcessing}
              isSubmitting={form.formState.isSubmitting}
              isLoadingIntegration={isLoadingIntegration}
              jiraIntegration={jiraIntegration}
              fileInputRef={fileInputRef}
              handleEditSource={handleEditSource}
              handleDeleteSource={handleDeleteSource}
              handleReindexSource={handleReindexSource}
              handlePrivacyBadgeClick={handlePrivacyBadgeClick}
              setClickedSource={setClickedSource} // Pass needed setters
              setIsYoutubeSidebarOpen={setIsYoutubeSidebarOpen}
              setIsJiraSidebarOpen={setIsJiraSidebarOpen}
              setIsUrlSidebarOpen={setIsUrlSidebarOpen}
              setShowJiraIntegrationModal={setShowJiraIntegrationModal}
              // isSourceProcessing={isSourceProcessing} // Pass isSourceProcessing
            />

            <div className="w-full">
              {hasFormChanged && isEditMode && !isUpdating && (
                <PendingChangesIndicator
                  dirtyChanges={dirtyChanges}
                  sources={sources}
                />
              )}
              {(isUpdating || isPublishing || isSourcesProcessing) && (
                <LongUpdatesIndicator />
              )}
            </div>
            {/* Replace the bottom buttons section with this */}
            <div className="flex guru-sm:flex-col guru-md:flex-row guru-lg:flex-row gap-4 items-center">
              {customGuru && (
                <Button
                  className="guru-sm:w-full guru-md:w-auto guru-lg:w-auto rounded-lg bg-white hover:bg-gray-50 text-gray-800 border border-gray-200"
                  disabled={
                    isSourcesProcessing ||
                    isProcessing ||
                    form.formState.isSubmitting
                  }
                  size="lg"
                  type="button"
                  onClick={() =>
                    window.open(
                      `/g/${customGuru}`,
                      "_blank",
                      "noopener,noreferrer"
                    )
                  }>
                  <LucideSquareArrowOutUpRight className="mr-2 h-4 w-4" />
                  Visit Guru
                </Button>
              )}

              <Button
                className={cn(
                  "guru-sm:w-full guru-md:w-auto guru-lg:w-auto rounded-lg",
                  "bg-gray-800 text-white hover:bg-gray-700",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                  customGuru ? "min-w-[140px]" : "min-w-[180px]"
                )}
                disabled={
                  isProcessing ||
                  form.formState.isSubmitting ||
                  isUpdating ||
                  isPublishing ||
                  isSourcesProcessing ||
                  (customGuru && !hasFormChanged)
                }
                size="lg"
                type="submit">
                {isUpdating || isSourcesProcessing ? (
                  <div className="flex items-center gap-2">
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                    <span>Updating...</span>
                  </div>
                ) : isPublishing ? (
                  <div className="flex items-center gap-2">
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                    <span>Publishing...</span>
                  </div>
                ) : customGuru ? (
                  "Update Guru"
                ) : (
                  "Publish Guru"
                )}
              </Button>

              {customGuru && isSelfHosted && (
                <Button
                  className="guru-sm:w-full guru-md:w-auto guru-lg:w-auto rounded-lg bg-[#DC2626] hover:bg-red-700 text-white ml-auto"
                  disabled={
                    isSourcesProcessing ||
                    isProcessing ||
                    form.formState.isSubmitting
                  }
                  size="lg"
                  type="button"
                  onClick={() => setShowDeleteModal(true)}>
                  Delete Guru
                </Button>
              )}
            </div>
          </form>
        </Form>
      </div>
      <input
        ref={fileInputRef}
        multiple
        accept=".pdf"
        className="hidden"
        type="file"
        onChange={handleFileUpload}
      />
      <SourceDialog
        clickedSource={clickedSource}
        editorContent={urlEditorContent}
        form={form}
        handleDeleteUrls={handleDeleteUrls}
        initialActiveTab={initialActiveTab}
        isMobile={isMobile}
        isOpen={isUrlSidebarOpen}
        selectedUrls={selectedUrls}
        setClickedSource={setClickedSource}
        setDirtyChanges={setDirtyChanges}
        setSelectedUrls={setSelectedUrls}
        setSources={setSources}
        sourceType="website"
        title="Website Links"
        onAddUrls={(links) => handleAddUrls(links, "website")}
        onEditorChange={handleUrlEditorChange}
        onOpenChange={setIsUrlSidebarOpen}
        onStartCrawl={handleStartCrawl}
        onStopCrawl={handleStopCrawl}
        isCrawling={isCrawling}
        showCrawlInput={showCrawlInput}
        setShowCrawlInput={setShowCrawlInput}
        crawlUrl={crawlUrl}
        setCrawlUrl={setCrawlUrl}
        isYoutubeKeyValid={isYoutubeKeyValid}
      />
      <SourceDialog
        clickedSource={clickedSource}
        editorContent={youtubeEditorContent}
        form={form}
        handleDeleteUrls={handleDeleteUrls}
        initialActiveTab={initialActiveTab}
        isMobile={isMobile}
        isOpen={isYoutubeSidebarOpen}
        selectedUrls={selectedUrls}
        setClickedSource={setClickedSource}
        setDirtyChanges={setDirtyChanges}
        setSelectedUrls={setSelectedUrls}
        setSources={setSources}
        sourceType="youtube"
        title="YouTube Links"
        onAddUrls={(links) => handleAddUrls(links, "youtube")}
        onEditorChange={handleYoutubeEditorChange}
        onOpenChange={setIsYoutubeSidebarOpen}
        isYoutubeKeyValid={isYoutubeKeyValid}
      />
      <SourceDialog
        clickedSource={clickedSource} // Might need adjustment for Jira specifics later
        editorContent={jiraEditorContent}
        form={form} // Pass form if needed for validation/updates
        handleDeleteUrls={handleDeleteUrls} // Needs adjustment for Jira deletion
        initialActiveTab={initialActiveTab} // May need adjustment
        isMobile={isMobile}
        isOpen={isJiraSidebarOpen}
        selectedUrls={selectedUrls} // Needs adjustment for Jira selection
        setClickedSource={setClickedSource}
        setDirtyChanges={setDirtyChanges}
        setSelectedUrls={setSelectedUrls} // Needs adjustment for Jira selection
        setSources={setSources}
        sourceType="jira" // Set source type
        title="Jira Issues" // Set title
        onAddUrls={handleAddJiraUrls} // Use Jira handler
        onEditorChange={handleJiraEditorChange} // Use Jira handler
        onOpenChange={setIsJiraSidebarOpen}
        isYoutubeKeyValid={isYoutubeKeyValid} // Pass this prop, although likely not relevant for Jira
        // Add any other Jira specific props if SourceDialog is extended
      />
      <DeleteConfirmationModal
        isOpen={showDeleteModal}
        onDelete={handleDeleteGuru}
        onOpenChange={setShowDeleteModal}
      />
      <JiraIntegrationModal
        isOpen={showJiraIntegrationModal}
        onOpenChange={setShowJiraIntegrationModal}
        guruSlug={customGuru}
      />
    </>
  );
}
