"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { DiscordIcon, SlackIcon } from "@/components/Icons";
import { cn } from "@/lib/utils";
import { getIntegrationDetails, getIntegrationChannels } from "@/app/actions";
import { Checkbox } from "@/components/ui/checkbox";

const IntegrationContent = ({ type, customGuru }) => {
  const [integrationData, setIntegrationData] = useState(null);
  const [channels, setChannels] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const integrationConfig = {
    Slack: {
      name: "Slack",
      description:
        "By connecting your account, you can easily share all your posts and invite your friends.",
      iconSize: "w-5 h-5"
    },
    Discord: {
      name: "Discord",
      description:
        "Connect your Discord account to share content and interact with your community.",
      bgColor: "bg-[#5865F2]",
      iconSize: "w-5 h-5"
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch integration details
        const data = await getIntegrationDetails(
          customGuru,
          type.toUpperCase()
        );

        console.log("data", data);

        // Case 1: 204 No Content - Show create content
        if (data?.status === 204) {
          setIntegrationData(null);
          setError(null);
          return;
        }

        console.log("no 204");

        // Case 2: Error response
        if (data?.error) {
          throw new Error(data.message || "Failed to fetch integration data");
        }

        console.log("no data");

        // Case 3: Successful response with integration data
        setIntegrationData(data);
        setError(null);

        console.log("fetching channels");

        // If integration exists, fetch channels
        const channelsData = await getIntegrationChannels(
          customGuru,
          type.toUpperCase()
        );
        console.log("channelsData", channelsData);
        if (channelsData?.error) {
          console.error("Failed to fetch channels:", channelsData.message);
        } else {
          setChannels(channelsData || []);
        }
      } catch (err) {
        setError(err.message);
        setIntegrationData(null);
      } finally {
        setLoading(false);
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
        <div className="p-6">Loading...</div>
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

          {channels.length > 0 && (
            <div className="mt-6">
              <h3 className="text-lg font-medium mb-4">Available Channels</h3>
              <div className="space-y-4">
                {channels.map((channel) => (
                  <div key={channel.id} className="flex items-center gap-2">
                    <Checkbox id={channel.id} checked={channel.allowed} />
                    <label htmlFor={channel.id} className="text-sm font-medium">
                      {channel.name}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          )}
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
          className="bg-[#1a1a1a] text-white hover:bg-[#2a2a2a]">
          Connect
        </Button>
      </div>
    </div>
  );
};

export default IntegrationContent;
