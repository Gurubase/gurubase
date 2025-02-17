"use client";

import { useEffect, useState } from "react";
import { CustomToast } from "@/components/CustomToast";
import { Button } from "@/components/ui/button";
import {
  DiscordIcon,
  SlackIcon,
  SendTestMessageIcon,
  SolarTrashBinTrashBold,
  ConnectedIntegrationIcon
} from "@/components/Icons";
import { cn } from "@/lib/utils";
import {
  getIntegrationDetails,
  getIntegrationChannels,
  saveIntegrationChannels,
  sendIntegrationTestMessage,
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
import {
  Command,
  CommandInput,
  CommandEmpty,
  CommandGroup,
  CommandItem
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger
} from "@/components/ui/popover";
import Link from "next/link";

const IntegrationContent = ({ type, guruData, error, selfhosted }) => {
  const [integrationData, setIntegrationData] = useState(null);
  const [channels, setChannels] = useState([]);
  const [originalChannels, setOriginalChannels] = useState([]);
  const [internalError, setInternalError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [channelsLoading, setChannelsLoading] = useState(true);
  const [hasChanges, setHasChanges] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [open, setOpen] = useState(false);
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
      extraText:
        'To subscribe to a <strong>private channel</strong> and send test messages to it, you need to invite the bot to the channel. You can do so from the Slack app using the <strong>"Add apps to this channel"</strong> command. This is not needed for public channels.',
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
      extraText:
        "To subscribe to a <strong>private channel</strong> and send test messages to it, you need to invite the bot to the channel. You can do so from the channel settings in the Discord app. This is not needed for public channels.",
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

        // Fetch channels separately
        fetchChannels();
      } catch (err) {
        setInternalError(err.message);
        setIntegrationData(null);
      } finally {
        setLoading(false);
      }
    };

    const fetchChannels = async () => {
      try {
        const channelsData = await getIntegrationChannels(
          guruData?.slug,
          type.toUpperCase()
        );
        if (channelsData?.error) {
          setInternalError(
            selfhosted
              ? "Failed to fetch channels. Please make sure your bot token is correct."
              : "Failed to fetch channels."
          );
        } else {
          setChannels(channelsData?.channels || []);
          setOriginalChannels(channelsData?.channels || []);
          setInternalError(null);
        }
      } catch (err) {
        setInternalError(err.message);
      } finally {
        setChannelsLoading(false);
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
          <div className="">
            <div className="flex flex-col gap-2">
              <h3 className="text-lg font-medium">Channels</h3>
              <p className="text-[#6D6D6D] font-inter text-[14px] font-normal">
                Select the channels you want, click <strong>Save</strong>, then
                test the connection for each channel using{" "}
                <strong>Send test message</strong>, and call the bot with{" "}
                <strong>@gurubase</strong>.
              </p>
              {config.extraText && (
                <p
                  className="text-[#6D6D6D] font-inter text-[14px] font-normal"
                  dangerouslySetInnerHTML={{ __html: config.extraText }}
                />
              )}
            </div>
            {/* Allowed Channels */}
            {channelsLoading ? (
              <div className="p-6 guru-xs:p-2">
                <LoadingSkeleton
                  count={2}
                  width="100%"
                  className="max-w-[400px] guru-xs:max-w-[280px] md:w-1/2"
                />
              </div>
            ) : (
              <>
                <div className="space-y-4 guru-xs:mt-4 mt-5">
                  {channels
                    .filter((c) => c.allowed)
                    .map((channel) => (
                      <div
                        key={channel.id}
                        className="flex md:items-center md:flex-row flex-col guru-xs:gap-4 gap-3 guru-xs:pt-1">
                        <div className="relative w-full guru-xs:w-full guru-sm:w-[450px] guru-md:w-[300px] xl:w-[450px]">
                          <span className="absolute left-3 top-2 text-xs font-normal text-gray-500">
                            Channel
                          </span>
                          <Input
                            readOnly
                            className="bg-gray-50 pt-8 pb-2"
                            value={channel.name}
                          />
                        </div>
                        <div className="flex flex-row gap-3 w-full md:w-auto">
                          <Button
                            variant="outline"
                            disabled={
                              !originalChannels.find(
                                (c) => c.id === channel.id && c.allowed
                              )
                            }
                            size="lgRounded"
                            className={cn(
                              "flex gap-2 border border-[#E2E2E2] bg-white hover:bg-[#F3F4F6] active:bg-[#E2E2E2] text-[#191919] font-inter text-[14px] font-medium whitespace-nowrap transition-all",
                              !originalChannels.find(
                                (c) => c.id === channel.id && c.allowed
                              ) && "opacity-50 cursor-not-allowed"
                            )}
                            onClick={async () => {
                              try {
                                const response =
                                  await sendIntegrationTestMessage(
                                    integrationData.id,
                                    channel.id
                                  );
                                if (response?.error) {
                                  CustomToast({
                                    message: "Failed to send test message.",
                                    variant: "error"
                                  });
                                } else {
                                  CustomToast({
                                    message: "Test message sent successfully!",
                                    variant: "success"
                                  });
                                }
                              } catch (error) {
                                CustomToast({
                                  message: "Failed to send test message.",
                                  variant: "error"
                                });
                              }
                            }}>
                            <SendTestMessageIcon />
                            Send Test Message
                          </Button>
                          <div className="flex items-center md:justify-start justify-center">
                            <button
                              className="text-[#BABFC8] hover:text-[#DC2626] transition-colors group"
                              onClick={() => {
                                setChannels(
                                  channels.map((c) =>
                                    c.id === channel.id
                                      ? { ...c, allowed: false }
                                      : c
                                  )
                                );
                                setHasChanges(true);
                              }}>
                              <SolarTrashBinTrashBold className="h-6 w-6 text-[#BABFC8] group-hover:text-[#DC2626] transition-colors" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
                {/* Add New Channel */}
                {channels.filter((c) => !c.allowed).length > 0 && (
                  <div className="guru-xs:mt-5 mt-4">
                    <div className="flex items-center gap-3">
                      <div className="relative w-full guru-xs:w-full guru-sm:w-[450px] guru-md:w-[300px] xl:w-[450px]">
                        <Popover open={open} onOpenChange={setOpen}>
                          <PopoverTrigger asChild>
                            <Button
                              variant="outline"
                              size="lgRounded"
                              className="bg-white border border-[#E2E2E2] text-[14px] rounded-lg h-[48px] px-3 flex items-center gap-2 self-stretch w-full justify-between font-inter font-medium text-[#191919]">
                              <div className="flex flex-col items-start">
                                <span className="text-[12px] text-gray-500">
                                  Channel
                                </span>
                                <span className="text-[14px] text-[#6D6D6D]">
                                  Select a channel...
                                </span>
                              </div>
                              <svg
                                width="20"
                                height="20"
                                viewBox="0 0 20 20"
                                fill="none"
                                xmlns="http://www.w3.org/2000/svg">
                                <path
                                  fillRule="evenodd"
                                  clipRule="evenodd"
                                  d="M3.69198 7.09327C3.91662 6.83119 4.31118 6.80084 4.57326 7.02548L9.99985 11.6768L15.4264 7.02548C15.6885 6.80084 16.0831 6.83119 16.3077 7.09327C16.5324 7.35535 16.502 7.74991 16.2399 7.97455L10.4066 12.9745C10.1725 13.1752 9.82716 13.1752 9.5931 12.9745L3.75977 7.97455C3.49769 7.74991 3.46734 7.35535 3.69198 7.09327Z"
                                  fill="#6D6D6D"
                                />
                              </svg>
                            </Button>
                          </PopoverTrigger>
                          <PopoverContent className="w-[450px] p-0 border border-[#E2E2E2] rounded-lg shadow-lg">
                            <Command className="rounded-lg">
                              <CommandInput
                                placeholder="Search channels..."
                                className="h-[48px] border-0 border-b border-[#E2E2E2] focus:ring-0 px-3 text-[14px] font-normal"
                              />
                              <CommandEmpty className="px-4 py-3 text-[14px] text-[#6D6D6D]">
                                No channels found.
                              </CommandEmpty>
                              <CommandGroup className="max-h-[200px] overflow-auto p-1">
                                {channels
                                  .filter((c) => !c.allowed)
                                  .sort((a, b) => a.name.localeCompare(b.name))
                                  .map((channel) => (
                                    <CommandItem
                                      key={channel.id}
                                      value={channel.name}
                                      onSelect={() => {
                                        const updatedChannels = [
                                          ...channels.filter(
                                            (c) => c.id !== channel.id
                                          ),
                                          { ...channel, allowed: true }
                                        ];
                                        setChannels(updatedChannels);
                                        setHasChanges(true);
                                        setOpen(false);
                                      }}
                                      className="px-3 py-2 text-[14px] hover:bg-[#F3F4F6] cursor-pointer rounded-md">
                                      {channel.name}
                                    </CommandItem>
                                  ))}
                              </CommandGroup>
                            </Command>
                          </PopoverContent>
                        </Popover>
                      </div>
                    </div>
                  </div>
                )}
                <div className="guru-xs:mt-6 mt-4">
                  <Button
                    disabled={!hasChanges || isSaving}
                    className="inline-flex min-h-[48px] max-h-[48px] px-4 justify-center items-center gap-2 rounded-lg bg-[#1B242D] hover:bg-[#2a363f] text-white guru-xs:w-full md:w-auto"
                    onClick={async () => {
                      setIsSaving(true);
                      try {
                        const response = await saveIntegrationChannels(
                          guruData?.slug,
                          type.toUpperCase(),
                          channels.filter((c) => c.allowed)
                        );
                        if (!response?.error) {
                          setHasChanges(false);
                          setOriginalChannels(channels);
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
                </div>
              </>
            )}
          </div>
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
                window.open(
                  `${integrationUrl}&state=${JSON.stringify({
                    type: type,
                    guru_type: guruData?.slug,
                    encoded_guru_slug: integrationData?.encoded_guru_slug
                  })}`,
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
