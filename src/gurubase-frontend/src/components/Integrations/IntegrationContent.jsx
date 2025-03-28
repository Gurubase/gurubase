"use client";

import { useEffect, useState } from "react";
import { CustomToast } from "@/components/CustomToast";
import { Button } from "@/components/ui/button";
import {
  DiscordIcon,
  SlackIcon,
  SendTestMessageIcon,
  SolarTrashBinTrashBold,
  ConnectedIntegrationIcon,
  GitHubIcon
} from "@/components/Icons";
import { cn } from "@/lib/utils";
import {
  getIntegrationDetails,
  deleteIntegration,
  createSelfhostedIntegration
} from "@/app/actions";
import LoadingSkeleton from "@/components/Content/LoadingSkeleton";
import { Input } from "@/components/ui/input";
import {
  IntegrationHeader,
  IntegrationDivider,
  IntegrationIconContainer,
  IntegrationInfo,
  IntegrationError
} from "./IntegrationShared";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from "@/components/ui/modal-dialog.jsx";
import Link from "next/link";
import ChannelsComponent from "./ChannelsComponent";
import RepositoriesComponent from "./RepositoriesComponent";

const IntegrationContent = ({ type, guruData, error, selfhosted }) => {
  const [integrationData, setIntegrationData] = useState(null);
  const [internalError, setInternalError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [workspaceName, setWorkspaceName] = useState("");
  const [externalId, setExternalId] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [isConnecting, setIsConnecting] = useState(false);

  const integrationConfig = {
    slack: {
      name: "Slack",
      description: (
        <>
          By connecting your account, you can ask your Guru directly in Slack.
          Here is the guide to{" "}
          <Link
            href="https://docs.gurubase.io/integrations/slack-bot"
            className="text-blue-500 hover:text-blue-600"
            target="_blank">
            learn more
          </Link>
          .
        </>
      ),
      iconSize: "w-5 h-5",
      url: process.env.NEXT_PUBLIC_SLACK_INTEGRATION_URL,
      icon: SlackIcon,
      showChannels: true,
      accessTokenLabel: "Bot Token",
      selfhostedDescription: (
        <>
          To use the Slack integration on Self-hosted, you need to set up a
          Slack bot. Learn how to do so in our{" "}
          <Link
            href="https://docs.gurubase.ai/integrations/slack-bot#slack-app-setup-for-self-hosted-version"
            className="text-blue-500 hover:text-blue-600"
            target="_blank">
            documentation
          </Link>
          .
        </>
      )
    },
    discord: {
      name: "Discord",
      description: (
        <>
          By connecting your account, you can ask your Guru directly in Discord.
          Here is the guide to{" "}
          <Link
            href="https://docs.gurubase.io/integrations/discord-bot"
            className="text-blue-500 hover:text-blue-600"
            target="_blank">
            learn more
          </Link>
          .
        </>
      ),
      bgColor: "bg-[#5865F2]",
      iconSize: "w-5 h-5",
      url: process.env.NEXT_PUBLIC_DISCORD_INTEGRATION_URL,
      icon: DiscordIcon,
      showChannels: true,
      accessTokenLabel: "Bot Token",
      selfhostedDescription: (
        <>
          To use the Discord integration on Self-hosted, you need to set up a
          Discord bot. Learn how to do so in our{" "}
          <Link
            href="https://docs.gurubase.ai/integrations/discord-bot#discord-app-setup-for-self-hosted-version"
            className="text-blue-500 hover:text-blue-600"
            target="_blank">
            documentation
          </Link>
          .
        </>
      )
    },
    github: {
      name: "GitHub",
      description: "Connect your GitHub repositories to your Guru.",
      iconSize: "w-5 h-5",
      url: process.env.NEXT_PUBLIC_GITHUB_INTEGRATION_URL,
      icon: GitHubIcon,
      showChannels: false,
      accessTokenLabel: "Bot Token",
      selfhostedDescription: (
        <>
          To use the GitHub integration on Self-hosted, you need to set up a
          GitHub app. Learn how to do so in our{" "}
          <Link
            href="https://docs.gurubase.ai/integrations/github-bot#github-app-setup-for-self-hosted-version"
            className="text-blue-500 hover:text-blue-600"
            target="_blank">
            documentation
          </Link>
          .
        </>
      )
    }
  };
  const config = integrationConfig[type];

  const integrationUrl = config.url;

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch integration details
        const data = await getIntegrationDetails(
          guruData?.slug,
          type.toUpperCase()
        );

        // Case 1: 202 Accepted - Show create content
        if (data?.status === 202) {
          setIntegrationData(data);
          setInternalError(null);
          return;
        }

        // Case 2: Error response
        if (data?.error) {
          throw new Error(data.message || "Failed to fetch integration data");
        }

        // Case 3: Successful response with integration data
        setIntegrationData(data);
        setInternalError(null);
      } catch (err) {
        setInternalError(err.message);
        setIntegrationData(null);
      } finally {
        setLoading(false);
      }
    };

    if (loading) {
      fetchData();
    }
  }, [guruData?.slug, type, loading]);

  const Icon = config.icon;
  const name = config.name;

  if (loading) {
    return (
      <div className="w-full">
        <IntegrationHeader text={`${name} Bot`} />
        <IntegrationDivider />
        <div className="p-6 guru-xs:p-2">
          <LoadingSkeleton
            count={2}
            width="100%"
            className="max-w-[400px] guru-xs:max-w-[280px] md:w-1/2"
          />
        </div>
      </div>
    );
  }

  if (integrationData && !integrationData?.encoded_guru_slug) {
    return (
      <div className="w-full">
        <IntegrationHeader text={`${name} Bot`} />
        <IntegrationDivider />
        {/* Show error if present */}
        {internalError && <IntegrationError message={internalError} />}
        {error && <IntegrationError message={error} />}
        <div className="flex flex-col gap-6 p-6">
          <div className="flex md:items-center md:justify-between flex-col md:flex-row gap-4">
            <IntegrationIconContainer Icon={Icon} iconSize={config.iconSize}>
              <IntegrationInfo name={name} description={config.description} />
            </IntegrationIconContainer>
            <div className="flex items-center justify-start w-full md:w-auto">
              <Button
                variant="outline"
                size="lgRounded"
                className="bg-white hover:bg-white text-[#232323] border border-neutral-200 rounded-full gap-2 guru-xs:w-full guru-xs:justify-center hover:bg-[#F3F4F6] active:bg-[#E2E2E2]"
                onClick={() => {
                  setShowDeleteDialog(true);
                }}>
                <ConnectedIntegrationIcon />
                Connected to {integrationData.workspace_name}
              </Button>
            </div>
          </div>
          {selfhosted ? (
            <div className="space-y-8">
              <div>
                <div className="flex flex-col gap-2">
                  <h3 className="text-lg font-medium">
                    {config.accessTokenLabel}
                  </h3>
                  <p className="text-[#6D6D6D] font-inter text-[14px] font-normal">
                    {config.selfhostedDescription}
                  </p>
                </div>
                <div className="relative w-full guru-xs:w-full guru-sm:w-[450px] guru-md:w-[300px] xl:w-[450px] mt-4">
                  <Input
                    readOnly={!!integrationData?.access_token}
                    className={cn(
                      "h-12 px-3 py-2 border border-[#E2E2E2] rounded-lg text-[14px] font-normal text-[#191919]",
                      integrationData?.access_token ? "bg-gray-50" : "bg-white"
                    )}
                    value={integrationData?.access_token || accessToken}
                    onChange={
                      !integrationData?.access_token
                        ? (e) => setAccessToken(e.target.value)
                        : undefined
                    }
                    placeholder={
                      !integrationData?.access_token
                        ? type === "discord"
                          ? "Enter Discord bot token..."
                          : "Enter Slack bot token..."
                        : undefined
                    }
                  />
                </div>
              </div>
            </div>
          ) : null}
          {config.showChannels && type !== "github" && (
            <ChannelsComponent
              guruData={guruData}
              type={type}
              integrationData={integrationData}
              selfhosted={selfhosted}
            />
          )}
          {type === "github" && (
            <RepositoriesComponent
              guruData={guruData}
              type={type}
              integrationData={integrationData}
              selfhosted={selfhosted}
            />
          )}
        </div>

        <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
          <DialogContent className="max-w-[400px] p-0">
            <div className="p-6 text-center">
              <DialogHeader>
                <DialogTitle className="text-base font-semibold text-center text-[#191919] font-inter">
                  Disconnect {name}
                </DialogTitle>
                <DialogDescription className="text-[14px] text-[#6D6D6D] text-center font-inter font-normal">
                  Are you sure you want to disconnect this integration?
                </DialogDescription>
              </DialogHeader>
              <div className="mt-6 flex flex-col gap-2">
                <Button
                  className={`h-12 px-6 justify-center items-center rounded-lg bg-[#DC2626] hover:bg-red-700 text-white ${
                    isDisconnecting ? "opacity-50 cursor-not-allowed" : ""
                  }`}
                  disabled={isDisconnecting}
                  onClick={async () => {
                    setIsDisconnecting(true);
                    try {
                      const response = await deleteIntegration(
                        guruData?.slug,
                        type.toUpperCase()
                      );
                      if (!response?.error) {
                        setIntegrationData(response);
                        setInternalError(null);
                      } else {
                        setInternalError(
                          response.message || "Failed to disconnect integration"
                        );
                      }
                    } catch (error) {
                      setInternalError(error.message);
                    } finally {
                      setIsDisconnecting(false);
                      setShowDeleteDialog(false);
                    }
                  }}>
                  {isDisconnecting ? "Disconnecting..." : "Disconnect"}
                </Button>
                <Button
                  className="h-12 px-4 justify-center items-center rounded-lg border border-[#1B242D] bg-white"
                  disabled={isDisconnecting}
                  variant="outline"
                  onClick={() => setShowDeleteDialog(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    );
  }

  // Default case: Show create content (204 or no integration)
  return (
    <div className="w-full">
      <IntegrationHeader text={`${name} Bot`} />
      <IntegrationDivider />
      {internalError && <IntegrationError message={internalError} />}
      {error && <IntegrationError message={error} />}
      <div
        className={cn(
          "flex p-6 gap-4",
          selfhosted
            ? "flex-col"
            : "flex-row items-center justify-between guru-xs:flex-col guru-xs:items-start"
        )}>
        <IntegrationIconContainer Icon={Icon} iconSize={config.iconSize}>
          <IntegrationInfo
            name={config.name}
            description={config.description}
          />
        </IntegrationIconContainer>
        <div
          className={cn(
            "flex flex-col gap-4 mt-2",
            selfhosted ? "w-full md:" : "w-full md:w-auto"
          )}>
          {selfhosted ? (
            <>
              <div className="space-y-8">
                <div>
                  <div className="flex flex-col gap-2">
                    <h3 className="text-lg font-medium">
                      {config.accessTokenLabel}
                    </h3>
                    <p className="text-[#6D6D6D] font-inter text-[14px] font-normal">
                      {config.selfhostedDescription}
                    </p>
                  </div>
                  <div className="relative w-full guru-xs:w-full guru-sm:w-[450px] guru-md:w-[300px] xl:w-[450px] mt-4">
                    <Input
                      readOnly={!!integrationData?.access_token}
                      className={cn(
                        "h-12 px-3 py-2 border border-[#E2E2E2] rounded-lg text-[14px] font-normal text-[#191919]",
                        integrationData?.access_token
                          ? "bg-gray-50"
                          : "bg-white"
                      )}
                      value={integrationData?.access_token || accessToken}
                      onChange={
                        !integrationData?.access_token
                          ? (e) => setAccessToken(e.target.value)
                          : undefined
                      }
                      placeholder={
                        !integrationData?.access_token
                          ? type === "discord"
                            ? "Enter Discord bot token..."
                            : "Enter Slack bot token..."
                          : undefined
                      }
                    />
                  </div>
                </div>
              </div>
            </>
          ) : null}
          <Button
            variant="default"
            size="lgRounded"
            className={cn(
              "bg-[#1a1a1a] text-white hover:bg-[#2a2a2a]",
              selfhosted
                ? "w-full guru-xs:w-full guru-sm:w-[450px] guru-md:w-[300px] xl:w-[450px]"
                : "guru-xs:w-full w-auto"
            )}
            disabled={isConnecting}
            onClick={async () => {
              if (selfhosted) {
                setIsConnecting(true);
                try {
                  const response = await createSelfhostedIntegration(
                    guruData?.slug,
                    type.toUpperCase(),
                    {
                      workspaceName,
                      externalId,
                      accessToken
                    }
                  );

                  if (!response?.error) {
                    setLoading(true);
                    setIntegrationData(response);
                    setInternalError(null);
                  } else {
                    setInternalError(
                      "Failed to create integration. Please make sure your bot token is correct."
                    );
                  }
                } catch (error) {
                  setInternalError(error.message);
                } finally {
                  setIsConnecting(false);
                }
              } else {
                const queryParamExists = window.location.search.includes("?");
                window.open(
                  `${integrationUrl}${queryParamExists ? "&" : "?"}state=${JSON.stringify(
                    {
                      type: type,
                      guru_type: guruData?.slug,
                      encoded_guru_slug: integrationData?.encoded_guru_slug
                    }
                  )}`,
                  "_blank"
                );
              }
            }}>
            {isConnecting ? (
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Connecting...
              </div>
            ) : (
              "Connect"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default IntegrationContent;
