import Image from "next/image";
import { Button } from "@/components/ui/button";

const SetupIntegration = ({ type }) => {
  const integrationConfig = {
    Slack: {
      name: "Slack",
      description:
        "By connecting your account, you can easily share all your posts and invite your friends.",
      icon: "/slack-icon.svg"
    },
    Discord: {
      name: "Discord",
      description:
        "Connect your Discord account to share content and interact with your community.",
      icon: "/discord-icon.svg"
    }
  };

  const config = integrationConfig[type];

  return (
    <div className="w-full border rounded-lg p-6">
      <h2 className="text-xl font-semibold mb-6">{type} Bot</h2>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 relative">
            <Image
              src={config.icon}
              alt={`${type} icon`}
              fill
              className="object-contain"
            />
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
