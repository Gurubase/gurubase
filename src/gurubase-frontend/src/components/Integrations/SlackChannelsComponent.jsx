"use client";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "@/components/ui/tooltip";
import { SolarInfoCircleBold } from "@/components/Icons";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  SendTestMessageIcon,
  SolarTrashBinTrashBold
} from "@/components/Icons";
import { cn } from "@/lib/utils";
import {
  getIntegrationChannels,
  saveIntegrationChannels,
  sendIntegrationTestMessage,
  addSlackChannels
} from "@/app/actions";
import LoadingSkeleton from "@/components/Content/LoadingSkeleton";
import { useEffect } from "react";
import { CustomToast } from "@/components/CustomToast";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { ChevronDownIcon } from "@radix-ui/react-icons";

const ChannelsComponent = ({
  guruData,
  type,
  integrationData,
  selfhosted,
  setInternalError
}) => {
  const [channels, setChannels] = useState([]);
  const [originalChannels, setOriginalChannels] = useState([]);
  const [channelsLoading, setChannelsLoading] = useState(true);
  const [hasChanges, setHasChanges] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [open, setOpen] = useState(false);
  const [directMessages, setDirectMessages] = useState(false);
  const [newChannelId, setNewChannelId] = useState("");
  const [newChannels, setNewChannels] = useState([]);
  const [reFetch, setReFetch] = useState(false);

  useEffect(() => {
    // Compare current repositories with initial repositories to determine if there are changes
    const channelsChanged = channels.some((channel) => {
      const originalChannel = originalChannels.find((c) => c.id === channel.id);
      return (
        !originalChannel ||
        channel.allowed !== originalChannel.allowed ||
        channel.mode !== originalChannel.mode
      );
    });

    setHasChanges(channelsChanged || newChannels.length > 0);
  }, [channels, originalChannels, newChannels]);

  useEffect(() => {
    const fetchChannels = async () => {
      try {
        const channelsData = await getIntegrationChannels(
          guruData?.slug,
          type.toUpperCase()
        );
        if (channelsData?.error) {
          setInternalError(
            channelsData?.message ||
              (selfhosted
                ? "Failed to fetch channels. Please make sure your bot token is correct."
                : "Failed to fetch channels.")
          );
        } else {
          const channelsWithMode =
            channelsData?.channels?.map((channel) => ({
              ...channel,
              mode: channel.mode || "auto"
            })) || [];
          setChannels(channelsWithMode);
          setOriginalChannels(channelsWithMode);
          setDirectMessages(channelsData?.allow_dm || false);
          setInternalError(null);
        }
      } catch (err) {
        setInternalError(err.message);
      } finally {
        setChannelsLoading(false);
      }
    };

    if (channelsLoading || reFetch) {
      fetchChannels();
    }

    if (reFetch) {
      setReFetch(false);
    }
  }, [guruData?.slug, type, channelsLoading, reFetch]);

  if (channelsLoading) {
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

  const handleAddNewChannel = () => {
    if (newChannelId.trim()) {
      const existingInNewChannels = newChannels.find(
        (c) => c.id === newChannelId.trim()
      );
      const existingInChannels = channels.find(
        (c) => c.id === newChannelId.trim()
      );
      if (existingInNewChannels) {
        CustomToast({
          message: "Channel already exists",
          variant: "error"
        });
      } else if (existingInChannels) {
        const channelName = existingInChannels.name;
        CustomToast({
          message: `Channel ${channelName} already exists`,
          variant: "error"
        });
      } else {
        setNewChannels([
          ...newChannels,
          { id: newChannelId.trim(), mode: "manual" }
        ]);
        setNewChannelId("");
      }
    }
  };

  const handleRemoveNewChannel = (channelId) => {
    setNewChannels(newChannels.filter((c) => c.id !== channelId));
  };

  return (
    <div className="">
      <div className="flex flex-col gap-2">
        <h3 className="text-lg font-medium">Channels</h3>
        <p className="text-[#6D6D6D] font-inter text-[14px] font-normal">
          Enter channel IDs you want to add, click <strong>Save</strong>, then
          test the connection for each channel using{" "}
          <strong>Send test message</strong>, and call the bot with{" "}
          <strong>@Gurubase.io</strong>.
        </p>
        <p className="text-[#6D6D6D] font-inter text-[14px] font-normal">
          In <strong>Auto</strong> mode, the bot replies to new messages
          automatically, but follow-up messages require a mention.
          <br />
          In <strong>Manual</strong> mode, all replies require mentioning the
          bot.
        </p>
        <p className="text-[#6D6D6D] font-inter text-[14px] font-normal">
          To subscribe to a <strong>private channel</strong> and send test
          messages to it, you need to invite the bot to the channel. You can do
          so from the Slack app using the{" "}
          <strong>"Add apps to this channel"</strong> command. This is not
          needed for public channels.
        </p>
      </div>
      {/* Allowed Channels */}
      <div className="space-y-4 guru-xs:mt-4 mt-5">
        <div className="flex items-center gap-2 mb-4">
          <input
            type="checkbox"
            id="direct_messages"
            checked={directMessages}
            onChange={(e) => {
              setDirectMessages(e.target.checked);
              setHasChanges(true);
            }}
            className="h-4 w-4 rounded border-gray-300"
          />
          <label htmlFor="direct_messages" className="text-sm text-gray-700">
            Enable Direct Messages
          </label>
        </div>
        {channels
          .filter((c) => c.allowed)
          .map((channel) => (
            <div
              key={channel.id}
              className="flex md:items-center md:flex-row flex-col guru-xs:gap-4 gap-3 guru-xs:pt-1">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div>
                      <SolarInfoCircleBold className="h-4 w-4 text-gray-200" />
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>
                      <a
                        href="https://docs.gurubase.io/integrations/slack-bot#finding-out-channel-ids"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:text-blue-600">
                        Here
                      </a>{" "}
                      is a guide to find out how to get the channel ID.
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
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
              <div className="flex items-center gap-3">
                <Select
                  value={channel.mode || "manual"}
                  onValueChange={(value) => {
                    setChannels(
                      channels.map((c) =>
                        c.id === channel.id ? { ...c, mode: value } : c
                      )
                    );
                  }}>
                  <SelectTrigger className="w-[100px] flex items-center justify-center">
                    <SelectValue placeholder="Mode" className="text-center" />
                    <ChevronDownIcon className="h-4 w-4 opacity-50 ml-2" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">Auto</SelectItem>
                    <SelectItem value="manual">Manual</SelectItem>
                  </SelectContent>
                </Select>
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
                      const response = await sendIntegrationTestMessage(
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
                          c.id === channel.id ? { ...c, allowed: false } : c
                        )
                      );
                    }}>
                    <SolarTrashBinTrashBold className="h-6 w-6 text-[#BABFC8] group-hover:text-[#DC2626] transition-colors" />
                  </button>
                </div>
              </div>
            </div>
          ))}

        {/* New Channels */}
        {newChannels.map((channel) => (
          <div
            key={channel.id}
            className="flex md:items-center md:flex-row flex-col guru-xs:gap-4 gap-3 guru-xs:pt-1">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div>
                    <SolarInfoCircleBold className="h-4 w-4 text-gray-200" />
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>
                    <a
                      href="https://docs.gurubase.io/integrations/slack-bot#finding-out-channel-ids"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-500 hover:text-blue-600">
                      Here
                    </a>{" "}
                    is a guide to find out how to get the channel ID.
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <div className="relative w-full guru-xs:w-full guru-sm:w-[450px] guru-md:w-[300px] xl:w-[450px]">
              <span className="absolute left-3 top-2 text-xs font-normal text-gray-500">
                New Channel ID
              </span>
              <Input
                readOnly
                className="bg-gray-50 pt-8 pb-2"
                value={channel.id}
              />
            </div>
            <div className="flex items-center gap-3">
              <Select
                value={channel.mode}
                onValueChange={(value) => {
                  setNewChannels(
                    newChannels.map((c) =>
                      c.id === channel.id ? { ...c, mode: value } : c
                    )
                  );
                }}>
                <SelectTrigger className="w-[100px] flex items-center justify-center">
                  <SelectValue placeholder="Mode" className="text-center" />
                  <ChevronDownIcon className="h-4 w-4 opacity-50 ml-2" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto</SelectItem>
                  <SelectItem value="manual">Manual</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center md:justify-start justify-center">
              <button
                className="text-[#BABFC8] hover:text-[#DC2626] transition-colors group"
                onClick={() => handleRemoveNewChannel(channel.id)}>
                <SolarTrashBinTrashBold className="h-6 w-6 text-[#BABFC8] group-hover:text-[#DC2626] transition-colors" />
              </button>
            </div>
          </div>
        ))}

        {/* Add New Channel Input */}
        <div className="flex items-center gap-3">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div>
                  <SolarInfoCircleBold className="h-4 w-4 text-gray-200" />
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>
                  <a
                    href="https://docs.gurubase.io/integrations/slack-bot#finding-out-channel-ids"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-500 hover:text-blue-600">
                    Here
                  </a>{" "}
                  is a guide to find out how to get the channel ID.
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <div className="relative w-full guru-xs:w-full guru-sm:w-[450px] guru-md:w-[300px] xl:w-[450px]">
            <span className="absolute left-3 top-2 text-xs font-normal text-gray-500">
              Channel ID
            </span>
            <Input
              className="pt-8 pb-2"
              placeholder="Enter channel ID..."
              value={newChannelId}
              onChange={(e) => setNewChannelId(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleAddNewChannel();
                }
              }}
            />
          </div>
          <Button
            variant="outline"
            size="lgRounded"
            className="flex gap-2 border border-[#E2E2E2] bg-white hover:bg-[#F3F4F6] active:bg-[#E2E2E2] text-[#191919] font-inter text-[14px] font-medium whitespace-nowrap transition-all"
            onClick={handleAddNewChannel}>
            Add Channel
          </Button>
        </div>
      </div>

      <div className="guru-xs:mt-6 mt-4">
        <Button
          disabled={!hasChanges || isSaving}
          className="inline-flex min-h-[48px] max-h-[48px] px-4 justify-center items-center gap-2 rounded-lg bg-[#1B242D] hover:bg-[#2a363f] text-white guru-xs:w-full md:w-auto"
          onClick={async () => {
            setIsSaving(true);
            try {
              // Handle updates
              const response = await saveIntegrationChannels(
                guruData?.slug,
                type.toUpperCase(),
                {
                  channels: channels.filter((c) => c.allowed),
                  direct_messages: directMessages
                }
              );

              const failed = [];
              const existing = [];
              // Handle new channels
              if (newChannels.length > 0) {
                const response = await addSlackChannels(
                  guruData?.slug,
                  newChannels.map((c) => ({
                    id: c.id,
                    mode: c.mode
                  }))
                );

                if (response?.error) {
                  throw new Error(response.message);
                }

                if (response?.failed) {
                  failed.push(...response.failed.map((c) => c.id));
                }

                if (response?.existing) {
                  existing.push(...response.existing.map((c) => c.name));
                }
              }

              if (failed.length > 0) {
                CustomToast({
                  message: `Failed to add channels: ${failed.join(", ")}. Please check the channel IDs and try again.`,
                  variant: "error"
                });
              }

              if (existing.length > 0) {
                CustomToast({
                  message: `Existing channels: ${existing.join(", ")}`,
                  variant: "error"
                });
              }

              setNewChannels([]);
            } catch (error) {
              setInternalError(error.message);
            } finally {
              setIsSaving(false);
              setReFetch(true);
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
    </div>
  );
};

export default ChannelsComponent;
