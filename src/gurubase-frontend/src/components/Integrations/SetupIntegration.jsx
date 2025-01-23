import Image from "next/image";
import { Button } from "@/components/ui/button";
import { DiscordIcon, SlackIcon } from "@/components/Icons";
import { cn } from "@/lib/utils";

const SetupIntegration = ({ type }) => {
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

  const config = integrationConfig[type];

  const Icon = type === "Discord" ? DiscordIcon : SlackIcon;

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
