"use client";
import { useAppNavigation } from "@/lib/navigation";
import { useUser } from "@auth0/nextjs-auth0/client";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  AlertTriangle,
  Clock,
  Edit,
  Info,
  LinkIcon,
  LoaderCircle,
  Lock,
  MoreVertical,
  RotateCw,
  Unlock,
  Upload,
  Check
} from "lucide-react";
import Image from "next/image";
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
  getMyGuru
} from "@/app/actions";
import { CustomToast } from "@/components/CustomToast";
import {
  LogosYoutubeIcon,
  LucideSquareArrowOutUpRight,
  SolarFileTextBold,
  SolarGalleryAddBold,
  SolarInfoCircleBold,
  SolarTrashBinTrashBold,
  SolarVideoLibraryBold
} from "@/components/Icons";
// Import the new component
import SourceDialog from "@/components/NewEditGuru/SourceDialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from "@/components/ui/modal-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
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
import { HeaderTooltip } from "@/components/ui/header-tooltip";
import { useCrawler } from "@/hooks/useCrawler";

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
  websiteUrls: z.array(z.string()).optional()
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

  // First, add a state to track the GitHub repository source status
  const [githubRepoStatuses, setGithubRepoStatuses] = useState({});
  const [githubRepoErrors, setGithubRepoErrors] = useState({});

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
      websiteUrls: []
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
    const newSources = files.map((file) => ({
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

    if (sourceType !== "website" && sourceType !== "youtube") return;

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
      sourceType === "youtube" ? setIsYoutubeSidebarOpen : setIsUrlSidebarOpen;

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

  const onSubmit = async (data) => {
    try {
      // Check data source limits first
      // Calculate current and potential new data sources
      if (customGuruData) {
        // Get current counts and limits
        const youtubeCount = sources.filter(
          (s) => s.type.toLowerCase() === "youtube" && !s.deleted
        ).length;
        const websiteCount = sources.filter(
          (s) => s.type.toLowerCase() === "website" && !s.deleted
        ).length;

        // Calculate PDF size
        let currentPdfSize = sources
          .filter(
            (s) =>
              s.type.toLowerCase() === "pdf" && !s.deleted && !s.newAddedSource
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
          return;
        }

        if (websiteCount > websiteLimit) {
          CustomToast({
            message: `You have exceeded the website source limit (${websiteLimit}).`,
            variant: "error"
          });
          return;
        }

        if (pdfSizeMb > pdfSizeLimitMb) {
          CustomToast({
            message: `You have exceeded the PDF size limit (${pdfSizeLimitMb} MB).`,
            variant: "error"
          });
          return;
        }
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
        (data.uploadedFiles && data.uploadedFiles.length > 0) ||
        (data.youtubeLinks && data.youtubeLinks.length > 0) ||
        (data.websiteUrls && data.websiteUrls.length > 0);

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

      // Add YouTube and website URLs
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
        websiteUrls: data.websiteUrls || []
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
      const isDeleted = dirtyChanges.sources.some(
        (s) => s.deleted && s.url === url
      );
      const isAdded = dirtyChanges.sources.some(
        (s) => s.newAddedSource && s.url === url
      );

      if (isDeleted && isAdded) {
        acc.add(url);
      }

      return acc;
    }, new Set());

    // If we found any URLs that are both deleted and added, remove them from both states
    if (duplicateUrls.size > 0) {
      setDirtyChanges((prev) => ({
        ...prev,
        sources: prev.sources.filter((source) => !duplicateUrls.has(source.url))
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

  // Modify hasFormChanged to be a pure function
  const hasFormChanged = useCallback(() => {
    // Check for changes in sources
    if (redirectingRef.current) return false;
    if (dirtyChanges.sources.length > 0) return true;
    if (dirtyChanges.guruUpdated) return true;

    if (!initialFormValues) return false;

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
      return (
        JSON.stringify([...arr1].sort()) !== JSON.stringify([...arr2].sort())
      );
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

    return basicFieldsChanged || sourcesChanged || logoChanged;
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

  // Add this near the top of the component where other useEffects are
  // Leave site? Changes you made may not be saved.
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (hasFormChanged()) {
        e.preventDefault();
        e.returnValue = ""; // Required for Chrome
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [hasFormChanged]);

  // Update the PendingChangesIndicator component
  const PendingChangesIndicator = () => {
    // Count non-processed newly added sources
    const newSources = dirtyChanges.sources.filter(
      (source) => source.newAddedSource && !source.deleted
    );
    const newSourcesCount = newSources.length;

    // Get deleted sources directly from dirtyChanges
    const deletedSources = dirtyChanges.sources.filter(
      (source) => source.deleted
    );
    const deletedSourcesCount = deletedSources.length;

    // Find original sources that are being deleted
    const getDeletedSourceDetails = (sourceIds) => {
      return sources
        .filter((source) =>
          Array.isArray(sourceIds)
            ? sourceIds.includes(source.id)
            : source.id === sourceIds
        )
        .map((source) => source.url || source.name);
    };

    // Only show counts if there are any
    const hasChanges = newSourcesCount > 0 || deletedSourcesCount > 0;

    const tooltipContent = hasChanges ? (
      <div className="space-y-2">
        {newSourcesCount > 0 && (
          <div>
            <p className="font-medium text-warning-base">
              Pending addition: {newSourcesCount}
            </p>
            <div className="mt-1 space-y-1">
              {newSources.map((source, index) => (
                <p key={source.id} className="text-sm text-gray-500">
                  {index + 1}. {source.url || source.name}
                </p>
              ))}
            </div>
          </div>
        )}
        {deletedSourcesCount > 0 && (
          <div>
            <p className="font-medium text-error-base">
              Pending deletion: {deletedSourcesCount}
            </p>
            <div className="mt-1 space-y-1">
              {deletedSources.map((source) => {
                const deletedUrls = getDeletedSourceDetails(source.id);

                return deletedUrls.map((url, urlIndex) => (
                  <p
                    key={`${source.id}-${urlIndex}`}
                    className="text-sm text-gray-500">
                    {urlIndex + 1}. {url}
                  </p>
                ));
              })}
            </div>
          </div>
        )}
      </div>
    ) : (
      <p>Other changes pending</p>
    );

    return (
      <Alert className="w-full" variant="warning">
        <div className="flex items-center gap-2">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <AlertTriangle className="h-4 w-4" />
              </TooltipTrigger>
              <TooltipContent>{tooltipContent}</TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <AlertDescription>
            You have pending changes. Click &quot;Update Guru&quot; to save
            them.
          </AlertDescription>
        </div>
      </Alert>
    );
  };

  const LongUpdatesIndicator = () => {
    return (
      <Alert className="w-full">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4" />
          <AlertDescription>
            Updates can take seconds to minutes, depending on the size of the
            data sources. You can leave and return to check later.
          </AlertDescription>
        </div>
      </Alert>
    );
  };

  // First, let's modify the renderBadges function to handle badge clicks

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

  const renderGithubBadge = (source) => {
    return (
      <div className="absolute right-2 top-1/2 -translate-y-1/2">
        {(() => {
          let badgeProps = {
            className:
              "flex items-center rounded-full gap-1 px-2 text-body4 font-medium pointer-events-none",
            icon: Clock,
            iconColor: "text-gray-500",
            text: "Not Indexed"
          };

          switch (source.status) {
            case "SUCCESS":
              badgeProps.icon = Check;
              badgeProps.iconColor = "text-green-700";
              badgeProps.text = "Indexed";
              badgeProps.className += " bg-green-50 text-green-700";
              break;
            case "FAIL":
              badgeProps.icon = AlertTriangle;
              badgeProps.iconColor = "text-red-700";
              badgeProps.text = "Failed";
              badgeProps.className += " bg-red-50 text-red-700";
              break;
            case "NOT_PROCESSED":
              badgeProps.icon = Clock;
              badgeProps.iconColor = "text-yellow-700";
              badgeProps.text = "Processing";
              badgeProps.className += " bg-yellow-50 text-yellow-700";
              break;
            default:
              return null;
              badgeProps.className += " bg-gray-50 text-gray-700";
              break;
          }

          return (
            <Badge {...badgeProps}>
              <badgeProps.icon
                className={cn("h-3 w-3", badgeProps.iconColor)}
              />
              {badgeProps.text}
            </Badge>
          );
        })()}
      </div>
    );
  };

  // Update the renderBadges function to include the click handler
  const renderBadges = (source) => {
    // For PDF files (existing code)
    if (source?.type?.toLowerCase() === "pdf") {
      return (
        <div className="flex items-center gap-1">
          {(() => {
            let badgeProps = {
              className: cn(
                "flex items-center rounded-full gap-1 px-2 py-1 text-body4 font-medium cursor-pointer",
                isSourcesProcessing && "pointer-events-none opacity-50"
              ),
              variant: "secondary"
            };

            switch (source.private) {
              case true:
                badgeProps.icon = Lock;
                badgeProps.iconColor = "text-gray-500";
                badgeProps.text = "Private";
                break;
              default:
                badgeProps.icon = Unlock;
                badgeProps.iconColor = "text-blue-base";
                badgeProps.text = "Public";
                break;
            }

            return (
              <div className="flex items-center gap-1">
                <div
                  key={source.id}
                  role="button"
                  tabIndex={0}
                  onClick={(e) => handlePrivacyBadgeClick(e, source)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      handlePrivacyBadgeClick(e, source);
                    }
                  }}>
                  <Badge {...badgeProps}>
                    <badgeProps.icon
                      className={cn("h-3 w-3", badgeProps.iconColor)}
                    />
                    {badgeProps.text}
                  </Badge>
                </div>
                <div className="relative flex items-center">
                  <TooltipProvider>
                    <Tooltip delayDuration={0}>
                      <TooltipTrigger className="cursor-pointer hover:text-gray-600 transition-colors flex items-center">
                        <Info className="h-3.5 w-3.5 text-gray-400" />
                      </TooltipTrigger>
                      <TooltipContent
                        align="center"
                        className="rounded-lg shadow-lg border p-3 md:bg-[#1B242D] md:text-white bg-background"
                        side="top"
                        sideOffset={8}>
                        <div
                          className="absolute w-4 h-4 border-l border-t md:bg-[#1B242D] bg-background"
                          style={{
                            bottom: "-8px",
                            left: "50%",
                            transform: "translateX(-50%) rotate(225deg)",
                            borderColor: "inherit"
                          }}
                        />
                        <p className="text-center relative font-inter px-2 text-xs font-medium">
                          {source.private
                            ? "This resource will be listed but not linked as a question reference."
                            : "This resource will be listed and linked as a question reference."}
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </div>
            );
          })()}
        </div>
      );
    }

    // Group URLs by status
    const statusGroups = source?.domains?.reduce((acc, domain) => {
      const status =
        domain.status === "NOT_PROCESSED"
          ? "NOT_PROCESSED"
          : domain.status?.toLowerCase() === "fail"
            ? "FAIL"
            : "SUCCESS";

      acc[status] = (acc[status] || 0) + 1;

      return acc;
    }, {});

    const handleBadgeClick = (e, status, source) => {
      if (isSourcesProcessing) return;
      e.preventDefault();
      e.stopPropagation();

      // Set the initial tab first
      const tabValue =
        status === "SUCCESS"
          ? "success"
          : status === "NOT_PROCESSED"
            ? "not_processed"
            : "failed";

      setInitialActiveTab(tabValue);

      // Small delay to ensure state is updated before opening dialog
      setTimeout(() => {
        handleEditSource(source, tabValue);
      }, 0);
    };

    return (
      <div className="flex items-center space-x-2">
        {Object.entries(statusGroups).map(([status, count]) => {
          if (count === 0) return null;

          let badgeProps = {
            className:
              "flex items-center rounded-full gap-1 px-2 py-1 text-body4 font-medium cursor-pointer",
            variant: "secondary",
            text: `${count} URL${count > 1 ? "s" : ""}`
          };

          switch (status) {
            case "SUCCESS":
              badgeProps = {
                ...badgeProps,
                icon: LinkIcon,
                iconColor: "text-blue-base",
                className: `${badgeProps.className} hover:bg-blue-50`
              };
              break;
            case "NOT_PROCESSED":
              badgeProps = {
                ...badgeProps,
                icon: AlertTriangle,
                iconColor: "text-warning-base",
                className: `${badgeProps.className} hover:bg-warning-50`
              };
              break;
            case "FAIL":
              badgeProps = {
                ...badgeProps,
                icon: AlertTriangle,
                iconColor: "text-error-base",
                className: `${badgeProps.className} hover:bg-error-50`
              };
              break;
            default:
              return null;
          }

          return (
            <div
              key={status}
              className={cn(
                "cursor-pointer",
                isSourcesProcessing && "pointer-events-none opacity-50"
              )}
              role="button"
              tabIndex={0}
              onClick={(e) => handleBadgeClick(e, status, source)}>
              <Badge {...badgeProps} />
            </div>
          );
        })}
      </div>
    );
  };

  // Add cleanup when closing dialogs
  useEffect(() => {
    if (!isUrlSidebarOpen && !isYoutubeSidebarOpen) {
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

    const youtubeUrls = youtubeEditorContent
      .split("\n")
      .map((url) => url.trim())
      .filter((url) => url && isValidUrl(url));

    const websiteUrls = urlEditorContent
      .split("\n")
      .map((url) => url.trim())
      .filter((url) => url && isValidUrl(url));

    const uniqueYoutubeUrls = [...new Set(youtubeUrls)];
    const uniqueWebsiteUrls = [...new Set(websiteUrls)];

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
  }, [isUrlSidebarOpen, isYoutubeSidebarOpen]);

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

  // Only show GitHub-related UI and logic if index_repo is true
  const renderCodebaseIndexing = () => {
    if (!index_repo && isEditMode) return null;

    // Find GitHub repository sources and their errors if they exist
    const githubSources =
      dataSources?.results?.filter(
        (source) => source.url && source.url.startsWith("https://github.com")
      ) || [];

    // Get the repo limit from customGuruData
    const repoLimit =
      process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted"
        ? Infinity
        : customGuruData?.github_repo_limit || 1;

    // Always get the current githubRepos values directly from the form
    const currentGithubRepos = form.getValues("githubRepos") || [];

    return (
      <FormField
        control={form.control}
        name="githubRepos"
        render={({ field }) => {
          // Ensure we're always using the latest values from the form
          const repos = field.value;

          return (
            <FormItem className="flex-1">
              <div className="flex items-center space-x-2">
                <FormLabel>Codebase Indexing</FormLabel>
                <HeaderTooltip
                  text={
                    "Provide links to GitHub repositories to index their codebases. The Guru can then use these codebases to generate answers based on them."
                  }
                />
              </div>
              <div className="space-y-2">
                {repos.map((repo, index) => (
                  <div key={index} className="flex flex-col gap-2">
                    <div className="relative flex gap-2">
                      <FormControl>
                        <Input
                          placeholder="https://github.com/username/repository"
                          value={repo}
                          className={cn(
                            "w-full pr-[110px]",
                            githubRepoStatuses[repo] === "NOT_PROCESSED" &&
                              "bg-gray-100 cursor-not-allowed",
                            form.formState.errors.githubRepos?.[index] &&
                              "border-red-500"
                          )}
                          type="url"
                          disabled={
                            isSourcesProcessing ||
                            isProcessing ||
                            form.formState.isSubmitting ||
                            githubRepoStatuses[repo] === "NOT_PROCESSED"
                          }
                          onChange={(e) => {
                            const newValue = [...repos];
                            newValue[index] = e.target.value;
                            field.onChange(newValue);
                            form.trigger("githubRepos");
                          }}
                        />
                      </FormControl>

                      {repo && (
                        <div className="absolute right-8 top-1/2 -translate-y-1/2">
                          {renderGithubBadge({
                            url: repo,
                            status: githubRepoStatuses[repo]
                          })}
                        </div>
                      )}
                      <div className="flex items-center gap-2">
                        {
                          <button
                            type="button"
                            disabled={
                              isSourcesProcessing || form.formState.isSubmitting
                            }
                            className={`${isSourcesProcessing || form.formState.isSubmitting ? "opacity-50 text-gray-300 pointer-events-none cursor-not-allowed" : "text-[#BABFC8] hover:text-[#DC2626]"} transition-colors group flex-shrink-0`}
                            onClick={() => {
                              const newValue = repos.filter(
                                (_, i) => i !== index
                              );
                              field.onChange(newValue);
                            }}>
                            <SolarTrashBinTrashBold
                              className={`h-6 w-6 ${isSourcesProcessing || form.formState.isSubmitting ? "text-gray-300 opacity-50" : "text-[#BABFC8] group-hover:text-[#DC2626]"} transition-colors`}
                            />
                          </button>
                        }
                      </div>
                    </div>
                    {/* Show form validation error first, then indexing error */}
                    {form.formState.errors.githubRepos?.[index] && (
                      <div className="text-sm text-red-600 pl-1">
                        {form.formState.errors.githubRepos[index].message}
                      </div>
                    )}
                    {repo &&
                      githubRepoErrors[repo] &&
                      !form.formState.errors.githubRepos?.[index] && (
                        <div className="text-sm text-red-600 pl-1">
                          {githubRepoErrors[repo]}
                        </div>
                      )}
                  </div>
                ))}
                {repos.length < repoLimit && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      field.onChange([...repos, ""]);
                    }}
                    disabled={
                      isSourcesProcessing ||
                      isProcessing ||
                      form.formState.isSubmitting
                    }
                    className={`w-full ${
                      isSourcesProcessing ||
                      isProcessing ||
                      form.formState.isSubmitting
                        ? "opacity-50 cursor-not-allowed"
                        : ""
                    }`}>
                    Add Repository
                  </Button>
                )}
              </div>
            </FormItem>
          );
        }}
      />
    );
  };

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
            <div className="max-w-md">
              <FormField
                control={form.control}
                name="guruName"
                render={({ field }) => (
                  <FormItem>
                    <div className="flex items-center space-x-2">
                      <FormLabel>
                        Guru Name <span className="text-red-500">*</span>
                      </FormLabel>
                      <HeaderTooltip
                        text={
                          isEditMode
                            ? "Guru name cannot be changed"
                            : "Enter the name of your AI guru"
                        }
                      />
                    </div>
                    <FormControl>
                      <Input
                        placeholder="Enter a guru name"
                        {...field}
                        className={
                          isEditMode ||
                          isProcessing ||
                          form.formState.isSubmitting
                            ? "bg-gray-100 cursor-not-allowed"
                            : ""
                        }
                        disabled={
                          isEditMode ||
                          isProcessing ||
                          form.formState.isSubmitting
                        }
                        onBlur={() => form.trigger("guruName")}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="guruLogo"
                render={({ field: { value, onChange, ...rest } }) => (
                  <FormItem>
                    <div className="flex items-center space-x-2">
                      <FormLabel>
                        Guru Logo <span className="text-red-500">*</span>
                      </FormLabel>
                      <HeaderTooltip text={"Guru logo"} />
                    </div>
                    <FormControl>
                      <div className="flex items-center space-x-4">
                        <div className="w-16 h-16 bg-gray-900 rounded-lg border-[0.5px] border-gray-85 flex items-center justify-center overflow-hidden">
                          {iconUrl ? (
                            <Image
                              alt="Guru logo"
                              className="w-full h-full object-cover"
                              height={64}
                              src={iconUrl}
                              width={64}
                            />
                          ) : selectedFile ? (
                            <Image
                              alt="Selected logo"
                              className="w-full h-full object-cover"
                              height={64}
                              src={URL.createObjectURL(selectedFile)}
                              width={64}
                            />
                          ) : (
                            <div>
                              <SolarGalleryAddBold
                                className="text-gray-500"
                                height={26.66}
                                width={26.66}
                              />
                            </div>
                          )}
                        </div>
                        <div>
                          <Input
                            accept="image/png, image/jpeg"
                            className="hidden"
                            id="logo-upload"
                            type="file"
                            onChange={(e) => {
                              const file = e.target.files?.[0];

                              if (file) {
                                setSelectedFile(file);
                                setIconUrl(null);
                                onChange(file);
                                // Mark form as dirty when logo changes
                                setDirtyChanges((prev) => ({
                                  ...prev,
                                  guruUpdated: true
                                }));
                              }
                            }}
                            {...rest}
                            value="" // Always keep the value empty for file inputs
                          />
                          <Button
                            className="text-gray-600 hover:text-gray-700 mb-2"
                            disabled={
                              isProcessing || form.formState.isSubmitting
                            }
                            type="button"
                            variant="outline"
                            onClick={() =>
                              document.getElementById("logo-upload").click()
                            }>
                            <Upload className="mr-2 h-4 w-4" />{" "}
                            {isEditMode ? "Change Logo" : "Upload Logo"}
                          </Button>
                          <FormDescription>
                            We support PNG, JPEG under 1MB.
                          </FormDescription>
                        </div>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="guruContext"
                render={({ field }) => (
                  <FormItem>
                    <div className="flex items-center space-x-2">
                      <FormLabel>
                        Topics <span className="text-red-500">*</span>
                      </FormLabel>
                      <HeaderTooltip
                        text={
                          'Add comma-separated topics related to this Guru, e.g., "programming, microservices, containers". This helps the AI understand the Guru\'s expertise and context.'
                        }
                      />
                    </div>
                    <FormControl>
                      <Input
                        placeholder="Enter topics, separated by commas"
                        {...field}
                        className="w-full"
                        disabled={
                          isSourcesProcessing ||
                          isProcessing ||
                          form.formState.isSubmitting
                        }
                        onBlur={() => form.trigger("guruContext")}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="flex items-center space-x-4">
                {renderCodebaseIndexing()}
              </div>
            </div>

            {/* Table Area */}
            <div className="max-w-full">
              <div className="flex flex-col mb-5">
                <h3 className="text-lg font-semibold mb-1">Sources</h3>
                <div className="flex items-center justify-between">
                  <p className="text-body2 text-gray-400">
                    Your guru will answer questions based on the sources you
                    provided below
                  </p>
                </div>
              </div>

              {/* Table Header Actions */}
              <div className="flex items-center justify-between space-x-4 mb-3">
                {sources.length > 0 && (
                  <Select
                    disabled={
                      isSourcesProcessing ||
                      isProcessing ||
                      form.formState.isSubmitting
                    }
                    onValueChange={(value) => setFilterType(value)}>
                    <SelectTrigger className="guru-sm:w-[100px] guru-md:w-[180px] guru-lg:w-[180px]">
                      <SelectValue placeholder="All" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="website">Website</SelectItem>
                      <SelectItem value="youtube">Video</SelectItem>
                      <SelectItem value="pdf">Files</SelectItem>
                    </SelectContent>
                  </Select>
                )}
                <div className="flex items-center justify-end space-x-2">
                  <Button
                    className="text-black-600"
                    disabled={
                      isProcessing ||
                      form.formState.isSubmitting ||
                      isSourcesProcessing
                    }
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setClickedSource([]);
                      setIsYoutubeSidebarOpen(true);
                    }}>
                    <LogosYoutubeIcon className="guru-sm:mr-0 guru-md:mr-2 guru-lg:mr-2 h-4 w-4" />
                    <span className="guru-sm:hidden guru-md:block guru-lg:block">
                      Add YouTube
                    </span>
                  </Button>
                  <Button
                    className="text-black-600"
                    disabled={
                      isProcessing ||
                      form.formState.isSubmitting ||
                      isSourcesProcessing
                    }
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setClickedSource([]);
                      setIsUrlSidebarOpen(true);
                    }}>
                    <LinkIcon className="guru-sm:mr-0 guru-md:mr-2 guru-lg:mr-2 h-4 w-4" />
                    <span className="guru-sm:hidden guru-md:block guru-lg:block">
                      Add Website
                    </span>
                  </Button>
                  <Button
                    className="text-black-600"
                    disabled={
                      isProcessing ||
                      form.formState.isSubmitting ||
                      isSourcesProcessing
                    }
                    type="button"
                    variant="outline"
                    onClick={() => fileInputRef.current.click()}>
                    <Upload className="guru-sm:mr-0 guru-md:mr-2 guru-lg:mr-2 h-4 w-4" />
                    <span className="guru-sm:hidden guru-md:block guru-lg:block">
                      Upload PDFs
                    </span>
                  </Button>
                </div>
              </div>

              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[20%]">Type</TableHead>
                    <TableHead className="w-[50%]">Name</TableHead>
                    <TableHead className="w-[30%]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sources.length === 0 ? (
                    <TableRow>
                      <TableCell className="text-center" colSpan={3}>
                        No sources added
                      </TableCell>
                    </TableRow>
                  ) : (
                    (() => {
                      const filteredSources =
                        filterType === "all"
                          ? sources
                          : sources.filter(
                              (source) =>
                                source.type.toLowerCase() ===
                                filterType.toLowerCase()
                            );

                      const urlSources = filteredSources.filter(
                        (source) =>
                          source.type.toLowerCase() === "youtube" ||
                          source.type.toLowerCase() === "website"
                      );
                      const fileSources = filteredSources.filter(
                        (source) => source.type.toLowerCase() === "pdf"
                      );

                      const groupedSources = urlSources.reduce(
                        (acc, source) => {
                          const domain = getNormalizedDomain(source.url);

                          if (!domain) return acc;

                          const existingSource = acc.find(
                            (item) => item.domain === domain
                          );

                          if (existingSource) {
                            existingSource.count += 1;
                            existingSource.domains.push(source);
                          } else {
                            acc.push({
                              ...source,
                              count: 1,
                              domains: [source],
                              domain: domain
                            });
                          }

                          return acc;
                        },
                        []
                      );

                      const displaySources = [
                        ...groupedSources,
                        ...fileSources
                      ];

                      return displaySources.map((source) => (
                        <TableRow key={source.id}>
                          <TableCell className="font-medium">
                            <div className="flex items-center">
                              {source.type?.toLowerCase() === "website" && (
                                <LinkIcon className="mr-2 h-4 w-4" />
                              )}
                              {source.type?.toLowerCase() === "youtube" && (
                                <SolarVideoLibraryBold className="mr-2 h-4 w-4" />
                              )}
                              {source.type?.toLowerCase() === "pdf" && (
                                <SolarFileTextBold className="mr-2 h-4 w-4" />
                              )}
                              <span>{source.sources}</span>
                            </div>
                          </TableCell>

                          <TableCell>
                            {isSourceProcessing(source) &&
                            isSourcesProcessing ? (
                              <div className="flex items-center gap-2 text-gray-500">
                                <LoaderCircle className="h-4 w-4 animate-spin" />
                                <span className="text-sm">
                                  Processing source...
                                </span>
                              </div>
                            ) : source?.domain?.length > 50 ||
                              source?.name?.length > 50 ? (
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <span>
                                      {source?.type?.toLowerCase() === "pdf"
                                        ? source?.name?.slice(0, 50)
                                        : source?.domain?.slice(0, 50)}
                                    </span>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>
                                      {source?.type?.toLowerCase() === "pdf"
                                        ? source?.name
                                        : source?.domain}
                                    </p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            ) : (
                              <span>
                                {source?.type?.toLowerCase() === "pdf"
                                  ? source?.name
                                  : source?.domain}
                              </span>
                            )}
                          </TableCell>

                          <TableCell className="">
                            <div className="flex items-center space-x-2 justify-end">
                              {renderBadges(source)}
                              <span>
                                <DropdownMenu>
                                  <DropdownMenuTrigger asChild>
                                    <Button
                                      className="h-8 w-8 p-0"
                                      disabled={isSourcesProcessing}
                                      size="icon"
                                      variant="ghost">
                                      <span className="sr-only">Open menu</span>
                                      <MoreVertical className="h-4 w-4" />
                                    </Button>
                                  </DropdownMenuTrigger>
                                  <DropdownMenuContent align="end">
                                    {(source.type.toLowerCase() === "website" ||
                                      source.type.toLowerCase() ===
                                        "youtube") && (
                                      <DropdownMenuItem
                                        disabled={isSourcesProcessing}
                                        onClick={() =>
                                          handleEditSource(source)
                                        }>
                                        <Edit className="mr-2 h-3 w-3" />
                                        Edit
                                      </DropdownMenuItem>
                                    )}
                                    {source.type.toLowerCase() ===
                                      "website" && (
                                      <DropdownMenuItem
                                        disabled={isSourcesProcessing}
                                        onClick={() =>
                                          handleReindexSource(source)
                                        }>
                                        <RotateCw className="mr-2 h-3 w-3" />
                                        Reindex
                                      </DropdownMenuItem>
                                    )}
                                    <DropdownMenuItem
                                      disabled={isSourcesProcessing}
                                      onClick={() =>
                                        handleDeleteSource(source)
                                      }>
                                      <SolarTrashBinTrashBold className="mr-2 h-3 w-3" />
                                      Delete
                                    </DropdownMenuItem>
                                  </DropdownMenuContent>
                                </DropdownMenu>
                              </span>
                            </div>
                          </TableCell>
                        </TableRow>
                      ));
                    })()
                  )}
                </TableBody>
              </Table>
            </div>
            <div className="w-full">
              {hasFormChanged() && isEditMode && !isUpdating && (
                <PendingChangesIndicator />
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
                  (customGuru && !hasFormChanged())
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
      <DeleteConfirmationModal
        isOpen={showDeleteModal}
        onDelete={handleDeleteGuru}
        onOpenChange={setShowDeleteModal}
      />
    </>
  );
}

const DeleteConfirmationModal = ({ isOpen, onOpenChange, onDelete }) => {
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[400px] p-0">
        <div className="p-6 text-center">
          <DialogHeader>
            <div className="mx-auto mb-4 h-[60px] w-[60px] rounded-full text-gray-600">
              <SolarTrashBinTrashBold className="h-full w-full" />
            </div>
            <DialogTitle className="text-base font-semibold text-center text-[#191919] font-inter">
              You are about to remove the Guru
            </DialogTitle>
            <DialogDescription className="text-[14px] text-[#6D6D6D] text-center font-inter font-normal">
              If you confirm, the Guru will be removed.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-6 flex flex-col gap-2">
            <Button
              className="h-12 px-6 justify-center items-center rounded-lg bg-[#DC2626] hover:bg-red-700 text-white"
              onClick={onDelete}>
              Delete
            </Button>
            <Button
              className="h-12 px-4 justify-center items-center rounded-lg border border-[#1B242D] bg-white"
              variant="outline"
              onClick={() => onOpenChange(false)}>
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
