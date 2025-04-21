import {
  LinkIcon,
  Upload
  // Edit, // Keep for potential future use if needed directly
  // RotateCw, // Keep for potential future use if needed directly
} from "lucide-react";

import {
  GitHubIcon,
  JiraIcon,
  LogosYoutubeIcon,
  SolarFileTextBold,
  // SolarTrashBinTrashBold, // Keep for potential future use if needed directly
  SolarVideoLibraryBold,
  ZendeskIcon
} from "@/components/Icons"; // Assuming Icons barrel file exists or adjust path

// Check if beta features are enabled via environment variable
const isBetaFeaturesEnabled = process.env.NEXT_PUBLIC_BETA_FEAT_ON === "true";

// Central configuration for data source types
const baseSourceTypesConfig = {
  WEBSITE: {
    id: "website",
    apiType: "WEBSITE", // Matches backend/API expected type
    displayName: "Website", // User-facing name in filters/UI
    displaySourceText: "Website", // Text shown in the table 'Type' column
    icon: LinkIcon, // Icon for the table row
    actionButtonIcon: LinkIcon, // Icon for the 'Add' button
    actionButtonText: "Website",
    sidebarStateSetterName: "setIsUrlSidebarOpen", // Name of the state setter in NewGuru
    formField: "websiteUrls", // Corresponding field in the form schema
    canReindex: true, // Can this source type be reindexed?
    canEdit: true, // Can this source type be edited (open sidebar)?
    requiresIntegrationCheck: false, // Does adding require an integration check?
    filterValue: "website", // Value used in the filter dropdown
    willGroup: true // Group by domain
  },
  YOUTUBE: {
    id: "youtube",
    apiType: "YOUTUBE",
    displayName: "YouTube",
    displaySourceText: "Video",
    icon: SolarVideoLibraryBold,
    actionButtonIcon: LogosYoutubeIcon,
    actionButtonText: "YouTube",
    sidebarStateSetterName: "setIsYoutubeSidebarOpen",
    formField: "youtubeLinks",
    canReindex: false,
    canEdit: true,
    requiresIntegrationCheck: false,
    filterValue: "youtube",
    willGroup: true // Group by domain
  },
  PDF: {
    id: "pdf",
    apiType: "PDF",
    displayName: "Files",
    displaySourceText: "File",
    icon: SolarFileTextBold,
    actionButtonIcon: Upload,
    actionButtonText: "PDFs",
    sidebarStateSetterName: null, // PDFs don't open a sidebar for editing content
    formField: "uploadedFiles",
    canReindex: false,
    canEdit: false, // No 'Edit' option like URLs
    requiresIntegrationCheck: false,
    hasPrivacyToggle: true, // Specific to PDF
    actionHandlerName: "onUploadPdfClick", // Specific handler for PDF upload trigger
    willGroup: false, // Do not group PDFs
    filterValue: "pdf"
  },
  GITHUB: {
    id: "github_repo",
    apiType: "GITHUB_REPO",
    displayName: "GitHub",
    displaySourceText: "GitHub",
    icon: GitHubIcon,
    actionButtonIcon: GitHubIcon,
    actionButtonText: "GitHub",
    sidebarStateSetterName: "setIsGithubSidebarOpen",
    formField: "githubRepos",
    canReindex: true,
    canEdit: false,
    requiresIntegrationCheck: false,
    filterValue: "github_repo",
    willGroup: false // Do not group GitHub repos
  }
};

// Conditionally add beta source types
if (isBetaFeaturesEnabled) {
  baseSourceTypesConfig.JIRA = {
    id: "jira",
    apiType: "JIRA",
    displayName: "Jira",
    displaySourceText: "Jira",
    icon: JiraIcon,
    actionButtonIcon: JiraIcon,
    actionButtonText: "Jira Issues",
    sidebarStateSetterName: "setIsJiraSidebarOpen",
    formField: "jiraIssues",
    canReindex: true,
    canEdit: true,
    requiresIntegrationCheck: true, // Specific to Jira
    integrationCheckProp: "jiraIntegration", // Prop name in parent for integration status
    integrationLoadingProp: "isLoadingIntegration", // Prop name for loading status
    integrationModalSetterName: "setShowJiraIntegrationModal", // State setter for the integration modal
    filterValue: "jira",
    willGroup: true // Group Jira issues by domain (project?)
  };
  baseSourceTypesConfig.ZENDESK = {
    id: "zendesk",
    apiType: "ZENDESK",
    displayName: "Zendesk",
    displaySourceText: "Zendesk",
    icon: ZendeskIcon, // Placeholder
    actionButtonIcon: ZendeskIcon, // Placeholder
    actionButtonText: "Zendesk Data",
    sidebarStateSetterName: "setIsZendeskSidebarOpen", // Assuming a similar pattern
    formField: "zendeskTickets", // Assuming a form field name
    canReindex: true,
    canEdit: true,
    requiresIntegrationCheck: true, // Assuming integration is needed
    integrationCheckProp: "zendeskIntegration", // Prop name for integration status
    integrationLoadingProp: "isLoadingIntegration", // Prop name for loading status
    integrationModalSetterName: "setShowZendeskIntegrationModal", // State setter for the integration modal
    filterValue: "zendesk",
    willGroup: true // Group Zendesk tickets by domain
  };
}

export const SOURCE_TYPES_CONFIG = baseSourceTypesConfig;

// Helper function to get config by id (case-insensitive)
export const getSourceTypeConfigById = (typeId) => {
  if (!typeId) return null;
  const upperCaseTypeId = typeId.toUpperCase();

  // Find the config entry where the apiType matches (more robust than key matching if keys differ)
  return (
    Object.values(SOURCE_TYPES_CONFIG).find(
      (config) => config.apiType === upperCaseTypeId
    ) || null
  );
};

// Helper function to get config by filter value
export const getSourceTypeConfigByFilterValue = (filterValue) => {
  if (!filterValue || filterValue === "all") return null;

  return (
    Object.values(SOURCE_TYPES_CONFIG).find(
      (config) => config.filterValue === filterValue
    ) || null
  );
};

// Get all configs as an array
export const getAllSourceTypeConfigs = () => {
  return Object.values(SOURCE_TYPES_CONFIG);
};

// Get dropdown menu items for the filter
export const getSourceFilterItems = () => {
  return [
    { value: "all", label: "All" },
    ...getAllSourceTypeConfigs().map((config) => ({
      value: config.filterValue,
      label: config.displayName
    }))
  ];
};
