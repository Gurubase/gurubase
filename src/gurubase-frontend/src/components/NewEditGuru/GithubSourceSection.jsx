import React from "react";
import { useFormContext } from "react-hook-form";
import {
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SolarTrashBinTrashBold } from "@/components/Icons";
import { HeaderTooltip } from "@/components/ui/header-tooltip";
import { cn } from "@/lib/utils";
import { AlertTriangle, Check, Clock } from "lucide-react";

const renderGithubBadge = (source) => {
  if (!source) return null;

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
      // Don't render badge if status is unknown or not provided
      return null;
    // badgeProps.className += " bg-gray-50 text-gray-700";
    // break;
  }

  return (
    <Badge {...badgeProps}>
      <badgeProps.icon className={cn("h-3 w-3", badgeProps.iconColor)} />
      {badgeProps.text}
    </Badge>
  );
};

export const GithubSourceSection = ({
  index_repo,
  isEditMode,
  githubRepoStatuses,
  githubRepoErrors,
  isSourcesProcessing,
  isProcessing,
  customGuruData
}) => {
  const { control, getValues, trigger, formState } = useFormContext();

  if (!index_repo && isEditMode) return null;

  // Get the repo limit from customGuruData
  const repoLimit =
    process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted"
      ? Infinity
      : customGuruData?.github_repo_limit || 1;

  return (
    <FormField
      control={control}
      name="githubRepos"
      render={({ field }) => {
        // Ensure we're always using the latest values from the form
        const repos = field.value || [];

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
                        value={repo || ""} // Ensure value is not undefined/null
                        className={cn(
                          "w-full pr-[110px]",
                          githubRepoStatuses[repo] === "NOT_PROCESSED" &&
                            "bg-gray-100 cursor-not-allowed",
                          formState.errors.githubRepos?.[index] &&
                            "border-red-500"
                        )}
                        type="url"
                        disabled={
                          isSourcesProcessing ||
                          isProcessing ||
                          formState.isSubmitting ||
                          githubRepoStatuses[repo] === "NOT_PROCESSED"
                        }
                        onChange={(e) => {
                          const newValue = [...repos];
                          newValue[index] = e.target.value;
                          field.onChange(newValue);
                          trigger("githubRepos"); // Trigger validation on change
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
                    <button
                      type="button"
                      disabled={isSourcesProcessing || formState.isSubmitting}
                      className={`${isSourcesProcessing || formState.isSubmitting ? "opacity-50 text-gray-300 pointer-events-none cursor-not-allowed" : "text-[#BABFC8] hover:text-[#DC2626]"} transition-colors group flex-shrink-0`}
                      onClick={() => {
                        const newValue = repos.filter((_, i) => i !== index);
                        field.onChange(newValue);
                      }}>
                      <SolarTrashBinTrashBold
                        className={`h-6 w-6 ${isSourcesProcessing || formState.isSubmitting ? "text-gray-300 opacity-50" : "text-[#BABFC8] group-hover:text-[#DC2626]"} transition-colors`}
                      />
                    </button>
                  </div>
                  {/* Show form validation error first, then indexing error */}
                  {formState.errors.githubRepos?.[index] && (
                    <FormMessage /> // Use FormMessage for built-in error display
                  )}
                  {repo &&
                    githubRepoErrors[repo] &&
                    !formState.errors.githubRepos?.[index] && (
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
                    formState.isSubmitting
                  }
                  className={`${
                    isSourcesProcessing ||
                    isProcessing ||
                    formState.isSubmitting
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
