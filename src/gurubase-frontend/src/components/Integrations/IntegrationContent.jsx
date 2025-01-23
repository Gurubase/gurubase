"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { DiscordIcon, SlackIcon } from "@/components/Icons";
import { cn } from "@/lib/utils";
import {
  getIntegrationDetails,
  getIntegrationChannels,
  saveIntegrationChannels
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

const IntegrationContent = ({ type, customGuru }) => {
  const [integrationData, setIntegrationData] = useState(null);
  const [channels, setChannels] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [channelsLoading, setChannelsLoading] = useState(true);
  const [hasChanges, setHasChanges] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const integrationConfig = {
    Slack: {
      name: "Slack",
      description:
        "By connecting your account, you can easily share all your posts and invite your friends.",
      iconSize: "w-5 h-5",
      url: `https://slack.com/oauth/v2/authorize?client_id=8327841447732.8318709976774&scope=channels:history,channels:join,channels:read,chat:write,groups:history,im:history,groups:read,mpim:read,im:read&user_scope=channels:history,chat:write,channels:read,groups:read,groups:history,im:history`
    },
    Discord: {
      name: "Discord",
      description:
        "Connect your Discord account to share content and interact with your community.",
      bgColor: "bg-[#5865F2]",
      iconSize: "w-5 h-5",
      url: `https://discord.com/oauth2/authorize?client_id=1331218460075757649&permissions=8&response_type=code&redirect_uri=https%3A%2F%2Fe306-34-32-48-186.ngrok-free.app%2FOAuth&integration_type=0&scope=identify+bot`
    }
  };

  const integrationUrl = integrationConfig[type].url;

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch integration details
        const data = await getIntegrationDetails(
          customGuru,
          type.toUpperCase()
        );

        // Case 1: 204 No Content - Show create content
        if (data?.status === 204) {
          setIntegrationData(null);
          setError(null);
          return;
        }

        // Case 2: Error response
        if (data?.error) {
          throw new Error(data.message || "Failed to fetch integration data");
        }

        // Case 3: Successful response with integration data
        setIntegrationData(data);
        setError(null);

        // Fetch channels separately
        fetchChannels();
      } catch (err) {
        setError(err.message);
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
        }
      } catch (err) {
        console.error("Failed to fetch channels:", err);
      } finally {
        setChannelsLoading(false);
      }
    };

    fetchData();
  }, [customGuru, type]);

  const config = integrationConfig[type];
  const Icon = type === "Discord" ? DiscordIcon : SlackIcon;

  if (loading) {
    return (
      <div className="w-full">
        <h2 className="text-xl font-semibold p-6">{type} Bot</h2>
        <div className="h-[1px] bg-neutral-200" />
        <div className="p-6">
          <LoadingSkeleton count={2} width={400} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full">
        <h2 className="text-xl font-semibold p-6">{type} Bot</h2>
        <div className="h-[1px] bg-neutral-200" />
        <div className="p-6 text-red-500">{error}</div>
      </div>
    );
  }
  console.log("channels", channels);

  if (integrationData) {
    return (
      <div className="w-full">
        <h2 className="text-xl font-semibold p-6">{type} Bot</h2>
        <div className="h-[1px] bg-neutral-200" />
        <div className="flex flex-col gap-6 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div
                className={cn(
                  "w-10 h-10 rounded-full flex items-center justify-center border border-neutral-200"
                )}>
                <Icon className={cn(config.iconSize, "text-white")} />
              </div>
              <div>
                <h3 className="font-medium">
                  Connected to {integrationData.workspace_name}
                </h3>
                <p className="text-sm text-muted-foreground">
                  Integration ID: {integrationData.id}
                  <br />
                  Last Updated:{" "}
                  {new Date(integrationData.date_updated).toLocaleDateString()}
                </p>
              </div>
            </div>
            <Button variant="destructive">Disconnect</Button>
          </div>
          <div className="mt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium">Channels</h3>
              <Button
                disabled={!hasChanges || isSaving}
                onClick={async () => {
                  setIsSaving(true);
                  try {
                    const response = await saveIntegrationChannels(
                      customGuru,
                      type.toUpperCase(),
                      channels
                    );
                    if (!response?.error) {
                      setHasChanges(false);
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
                  "Save Changes"
                )}
              </Button>
            </div>
            {/* Allowed Channels */}
            {channelsLoading ? (
              <div className="space-y-4">
                <LoadingSkeleton count={3} width={400} />
              </div>
            ) : (
              <>
                <div className="space-y-4 mb-6">
                  {channels
                    .filter((c) => c.allowed)
                    .map((channel) => (
                      <div key={channel.id} className="flex items-center gap-4">
                        <Select disabled value={channel.id}>
                          <SelectTrigger className="w-[200px]">
                            <SelectValue>{channel.name}</SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value={channel.id}>
                              {channel.name}
                            </SelectItem>
                          </SelectContent>
                        </Select>
                        <Button variant="outline" size="sm">
                          Send Test Message
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
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
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                </div>
                {/* Add New Channel */}
                <div className="mt-4">
                  <Select
                    onValueChange={(value) => {
                      setChannels(
                        channels.map((c) =>
                          c.id === value ? { ...c, allowed: true } : c
                        )
                      );
                      setHasChanges(true);
                    }}>
                    <SelectTrigger className="w-[200px]">
                      <SelectValue placeholder="Add channel..." />
                    </SelectTrigger>
                    <SelectContent>
                      {channels
                        .filter((c) => !c.allowed)
                        .map((channel) => (
                          <SelectItem key={channel.id} value={channel.id}>
                            {channel.name}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Default case: Show create content (204 or no integration)
  return (
    <div className="w-full">
      <h2 className="text-xl font-semibold p-6">{type} Bot</h2>
      <div className="h-[1px] bg-neutral-200" />
      <div className="flex items-center justify-between p-6">
        <div className="flex items-center gap-4">
          <div
            className={cn(
              "w-10 h-10 rounded-full flex items-center justify-center border border-neutral-200"
            )}>
            <Icon className={cn(config.iconSize, "text-white")} />
          </div>
          <div>
            <h3 className="font-medium">{config.name}</h3>
            <p className="text-sm text-muted-foreground">
              {config.description}
            </p>
          </div>
        </div>
        <Button
          variant="default"
          className="bg-[#1a1a1a] text-white hover:bg-[#2a2a2a]"
          onClick={() =>
            window.open(
              `${integrationUrl}&state={"type": "${type}", "guru_type": "${customGuru}"}`,
              "_blank"
            )
          }>
          Connect
        </Button>
      </div>
    </div>
  );
};

export default IntegrationContent;
