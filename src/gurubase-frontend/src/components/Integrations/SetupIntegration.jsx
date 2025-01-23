"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { DiscordIcon, SlackIcon } from "@/components/Icons";
import { cn } from "@/lib/utils";
import { getIntegrationDetails } from "@/app/actions";

const SetupIntegration = ({ type, customGuru }) => {
  const [integrationData, setIntegrationData] = useState(null);
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
    const fetchIntegrationData = async () => {
      try {
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
      } catch (err) {
        setError(err.message);
        setIntegrationData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchIntegrationData();
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
        <div className="flex items-center justify-between p-6">
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

export default SetupIntegration;
