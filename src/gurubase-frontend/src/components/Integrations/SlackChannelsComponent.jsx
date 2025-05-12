"use client";

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
  sendIntegrationTestMessage
} from "@/app/actions";
import LoadingSkeleton from "@/components/Content/LoadingSkeleton";
import { useEffect } from "react";
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

    setHasChanges(channelsChanged);
  }, [channels, originalChannels]);

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

    if (channelsLoading) {
      fetchChannels();
    }
  }, [guruData?.slug, type, channelsLoading]);

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

  return (
    <div className="">
      <div className="flex flex-col gap-2">
        <h3 className="text-lg font-medium">Channels</h3>
        <p className="text-[#6D6D6D] font-inter text-[14px] font-normal">
          Select the channels you want, click <strong>Save</strong>, then test
          the connection for each channel using{" "}
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
        {type === "slack" && (
          <p className="text-[#6D6D6D] font-inter text-[14px] font-normal">
            To subscribe to a <strong>private channel</strong> and send test
            messages to it, you need to invite the bot to the channel. You can
            do so from the Slack app using the{" "}
            <strong>"Add apps to this channel"</strong> command. This is not
            needed for public channels.
          </p>
        )}
        {type === "discord" && (
          <p className="text-[#6D6D6D] font-inter text-[14px] font-normal">
            To subscribe to a <strong>private channel</strong> and send test
            messages to it, you need to invite the bot to the channel. You can
            do so from the channel settings in the Discord app. This is not
            needed for public channels.
          </p>
        )}
      </div>
      {/* Allowed Channels */}
      <div className="space-y-4 guru-xs:mt-4 mt-5">
        {type === "slack" && (
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
        )}
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
                      <span className="text-[12px] text-gray-500">Channel</span>
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
                                ...channels.filter((c) => c.id !== channel.id),
                                { ...channel, allowed: true }
                              ];
                              setChannels(updatedChannels);
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
                type === "slack"
                  ? {
                      channels: channels.filter((c) => c.allowed),
                      direct_messages: directMessages
                    }
                  : channels.filter((c) => c.allowed)
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
    </div>
  );
};

export default ChannelsComponent;
