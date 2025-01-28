"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
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
  deleteIntegration
} from "@/app/actions";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Trash2 } from "lucide-react";
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

const IntegrationContent = ({ type, customGuru, error }) => {
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

  const integrationConfig = {
    slack: {
      name: "Slack",
      description:
        "By connecting your account, you can easily share all your posts and invite your friends.",
      iconSize: "w-5 h-5",
      icon: SlackIcon,
      extraText: ""
    },
    discord: {
      name: "Discord",
      description:
        "Connect your Discord account to share content and interact with your community.",
      bgColor: "bg-[#5865F2]",
      iconSize: "w-5 h-5",
      url: `https://discord.com/oauth2/authorize?client_id=1331218460075757649&permissions=8&response_type=code&redirect_uri=https%3A%2F%2F7eaf-34-32-48-186.ngrok-free.app%2Fintegrations%2Fcreate&integration_type=0&scope=identify+bot`,
      icon: DiscordIcon,
      extraText: "To subscribe to a private channel and send test messages to it, you need to invite the bot to the channel. You can do so from the channel settings in the Discord app. This is not needed for public channels."
    }
  };
  const config = integrationConfig[type];

  const integrationUrl = config.url;

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch integration details
        const data = await getIntegrationDetails(
          customGuru,
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
          customGuru,
          type.toUpperCase()
        );
        if (channelsData?.error) {
          console.error("Failed to fetch channels:", channelsData.message);
        } else {
          setChannels(channelsData?.channels || []);
          setOriginalChannels(channelsData?.channels || []);
        }
      } catch (err) {
        console.error("Failed to fetch channels:", err);
      } finally {
        setChannelsLoading(false);
      }
    };

    fetchData();
  }, [customGuru, type]);

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

  if (internalError) {
    return (
      <div className="w-full">
        <IntegrationHeader text={`${name} Bot`} />
        <IntegrationDivider />
        <div className="p-6 text-red-500">{internalError}</div>
      </div>
    );
  }

  if (integrationData && !integrationData?.encoded_guru_slug) {
    return (
      <div className="w-full">
        <IntegrationHeader text={`${name} Bot`} />
        <IntegrationDivider />
        <div className="flex flex-col gap-6 p-6">
          <div className="flex md:items-center md:justify-between flex-col md:flex-row gap-4">
            <IntegrationIconContainer Icon={Icon} iconSize={config.iconSize}>
              <IntegrationInfo
                name={name}
                description="By connecting your account, you can easily share all your posts and invite your friends."
              />
            </IntegrationIconContainer>
            <div className="flex items-center justify-start w-full md:w-auto">
              <Button
                variant="outline"
                size="lgRounded"
                className="bg-white hover:bg-white text-[#232323] border border-neutral-200 rounded-full gap-2 guru-xs:w-full guru-xs:justify-center"
                onClick={() => setShowDeleteDialog(true)}>
                <ConnectedIntegrationIcon />
                Connected to {integrationData.workspace_name}
              </Button>
            </div>
          </div>
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
                <p className="text-[#6D6D6D] font-inter text-[14px] font-normal">
                  {config.extraText}
                </p>
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
                    .sort((a, b) => a.name.localeCompare(b.name))
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
                              "flex gap-2 border border-[#E2E2E2] bg-white hover:bg-white text-[#191919] font-inter text-[14px] font-medium whitespace-nowrap",
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
                                  console.error(
                                    "Failed to send test message:",
                                    response.message
                                  );
                                }
                              } catch (error) {
                                console.error(
                                  "Error sending test message:",
                                  error
                                );
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
                        <Select
                          key={channels.filter((c) => !c.allowed).length}
                          value=""
                          onValueChange={(value) => {
                            setChannels(
                              channels.map((c) =>
                                c.id === value ? { ...c, allowed: true } : c
                              )
                            );
                            setHasChanges(true);
                          }}>
                          <SelectTrigger
                            className="bg-white border border-[#E2E2E2] text-[14px] rounded-lg h-[48px] px-3 flex items-center gap-2 self-stretch"
                            arrow={false}>
                            <div className="flex flex-col items-start">
                              <span className="text-[12px] text-gray-500">
                                Channel
                              </span>
                              <SelectValue placeholder="Select a channel..." />
                            </div>
                            <svg
                              width="20"
                              height="20"
                              viewBox="0 0 20 20"
                              fill="none"
                              xmlns="http://www.w3.org/2000/svg">
                              <path
                                fill-rule="evenodd"
                                clip-rule="evenodd"
                                d="M3.69198 7.09327C3.91662 6.83119 4.31118 6.80084 4.57326 7.02548L9.99985 11.6768L15.4264 7.02548C15.6885 6.80084 16.0831 6.83119 16.3077 7.09327C16.5324 7.35535 16.502 7.74991 16.2399 7.97455L10.4066 12.9745C10.1725 13.1752 9.82716 13.1752 9.5931 12.9745L3.75977 7.97455C3.49769 7.74991 3.46734 7.35535 3.69198 7.09327Z"
                                fill="#6D6D6D"
                              />
                            </svg>
                          </SelectTrigger>
                          <SelectContent className="bg-white border border-[#E5E7EB] text-[14px] rounded-lg shadow-lg">
                            {channels
                              .filter((c) => !c.allowed)
                              .sort((a, b) => a.name.localeCompare(b.name))
                              .map((channel) => (
                                <SelectItem
                                  key={channel.id}
                                  value={channel.id}
                                  className="px-4 py-2 hover:bg-[#F3F4F6] cursor-pointer">
                                  {channel.name}
                                </SelectItem>
                              ))}
                          </SelectContent>
                        </Select>
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
                          customGuru,
                          type.toUpperCase(),
                          channels.filter((c) => c.allowed)
                        );
                        if (!response?.error) {
                          setHasChanges(false);
                          setOriginalChannels(channels);
                        }
                      } catch (error) {
                        console.error("Failed to save channels:", error);
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
                        customGuru,
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
      <div className="flex flex-row items-center justify-between p-6 guru-xs:flex-col guru-xs:items-start gap-4">
        <IntegrationIconContainer Icon={Icon} iconSize={config.iconSize}>
          <IntegrationInfo
            name={config.name}
            description={config.description}
          />
        </IntegrationIconContainer>
        <Button
          variant="default"
          size="lgRounded"
          className="bg-[#1a1a1a] text-white hover:bg-[#2a2a2a] guru-xs:w-full w-auto "
          onClick={() =>
            window.open(
              `${integrationUrl}&state=${JSON.stringify({
                type: type,
                guru_type: customGuru,
                encoded_guru_slug: integrationData?.encoded_guru_slug
              })}`,
              "_blank"
            )
          }>
          Connect
        </Button>
      </div>
      {error && <IntegrationError />}
    </div>
  );
};

export default IntegrationContent;
