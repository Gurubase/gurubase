"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { getIntegrationChannels, saveIntegrationChannels } from "@/app/actions";
import LoadingSkeleton from "@/components/Content/LoadingSkeleton";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { ChevronDownIcon, ExternalLinkIcon } from "@radix-ui/react-icons";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "@/components/ui/tooltip";

const RepositoriesComponent = ({
  guruData,
  type,
  integrationData,
  selfhosted,
  externalId,
  setInternalError
}) => {
  const [repositories, setRepositories] = useState([]);
  const [initialRepositories, setInitialRepositories] = useState([]);
  const [repositoriesLoading, setRepositoriesLoading] = useState(true);
  const [hasChanges, setHasChanges] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const fetchRepositories = async () => {
      try {
        const repositoriesData = await getIntegrationChannels(
          guruData?.slug,
          type.toUpperCase()
        );

        if (repositoriesData?.error) {
          setInternalError(
            repositoriesData?.message ||
              (selfhosted
                ? "Failed to fetch repositories. Please make sure your bot token is correct."
                : "Failed to fetch repositories.")
          );
        } else {
          // Ensure each repository has a mode value, defaulting to "auto" if not present
          const repositoriesWithMode =
            repositoriesData?.channels?.map((repo) => ({
              ...repo,
              mode: repo.mode || "auto"
            })) || [];
          setRepositories(repositoriesWithMode);
          setInitialRepositories(repositoriesWithMode);
          setInternalError(null);
        }
      } catch (err) {
        setInternalError(err.message);
      } finally {
        setRepositoriesLoading(false);
      }
    };

    fetchRepositories();
  }, [guruData?.slug, type, selfhosted]);

  useEffect(() => {
    // Compare current repositories with initial repositories to determine if there are changes
    const hasModeChanges = repositories.some(
      (repo, index) => repo.mode !== initialRepositories[index]?.mode
    );
    setHasChanges(hasModeChanges);
  }, [repositories, initialRepositories]);

  if (repositoriesLoading) {
    return (
      <div className="p-6 guru-xs:p-2">
        <LoadingSkeleton
          count={2}
          width="100%"
          className="max-w-[400px] guru-xs:max-w-[280px] md:w-1/2"
        />
      </div>
    );
  }

  const botSlug = selfhosted ? "@<github_app_slug>" : "@gurubase";

  return (
    <div className="">
      <div className="flex flex-col gap-2">
        <h3 className="text-lg font-medium">Repositories</h3>
        <p className="text-[#6D6D6D] font-inter text-[14px] font-normal">
          The following repositories are connected to your Guru. You can call
          the bot with <strong>{botSlug}</strong> in the repository issues.
        </p>
        <p className="text-[#6D6D6D] font-inter text-[14px] font-normal">
          Up to <strong>100</strong> repositories can be connected at a time.
        </p>
        <p className="text-[#6D6D6D] font-inter text-[14px] font-normal">
          "Auto" mode will automatically answer all new issues. "Manual" mode
          will require you to call the bot with <strong>{botSlug}</strong> in
          the issue comment to answer.
        </p>
      </div>
      {/* Repositories List */}
      <div className="space-y-4 guru-xs:mt-4 mt-5">
        {repositories.map((repo) => (
          <div
            key={repo.id}
            className="flex md:items-center md:flex-row flex-col guru-xs:gap-4 gap-3 guru-xs:pt-1">
            <div className="relative w-full guru-xs:w-full guru-sm:w-[450px] guru-md:w-[300px] xl:w-[450px]">
              <span className="absolute left-3 top-2 text-xs font-normal text-gray-500">
                Repository
              </span>
              <Input
                readOnly
                className="bg-gray-50 pt-8 pb-2"
                value={repo.name}
              />
            </div>
            <div className="flex items-center gap-3">
              <Select
                value={repo.mode}
                onValueChange={(value) => {
                  setRepositories(
                    repositories.map((r) =>
                      r.id === repo.id ? { ...r, mode: value } : r
                    )
                  );
                }}>
                <SelectTrigger className="w-[100px] flex items-center justify-center">
                  <SelectValue
                    placeholder="Select mode"
                    className="text-center"
                  />
                  <ChevronDownIcon className="h-4 w-4 opacity-50 ml-2" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto</SelectItem>
                  <SelectItem value="manual">Manual</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        ))}
      </div>
      <div className="guru-xs:mt-6 mt-4 flex gap-3">
        <Button
          disabled={!hasChanges || isSaving}
          className="inline-flex min-h-[48px] max-h-[48px] px-4 justify-center items-center gap-2 rounded-lg bg-[#1B242D] hover:bg-[#2a363f] text-white guru-xs:w-full md:w-auto"
          onClick={async () => {
            setIsSaving(true);
            try {
              const response = await saveIntegrationChannels(
                guruData?.slug,
                type.toUpperCase(),
                repositories
              );
              if (!response?.error) {
                setHasChanges(false);
                setInitialRepositories(repositories);
              }
            } catch (error) {
              setInternalError(error.message);
            } finally {
              setIsSaving(false);
            }
          }}>
          {isSaving ? (
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Saving...
            </div>
          ) : (
            "Save"
          )}
        </Button>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                className="inline-flex min-h-[48px] max-h-[48px] px-4 justify-center items-center gap-2 rounded-lg border border-[#E2E2E2] bg-white hover:bg-[#F3F4F6] active:bg-[#E2E2E2] text-[#191919] font-inter text-[14px] font-medium guru-xs:w-full md:w-auto"
                onClick={() =>
                  window.open(
                    `https://github.com/settings/installations/${externalId}`,
                    "_blank"
                  )
                }>
                Manage
                <ExternalLinkIcon className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>
                Manage your repositories on GitHub. All updates are then
                reflected to this page upon refresh.
              </p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>
  );
};

export default RepositoriesComponent;
