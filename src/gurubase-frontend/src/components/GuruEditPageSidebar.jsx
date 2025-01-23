"use client";

import { Settings, Link } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger
} from "@/components/ui/collapsible";
import { useState } from "react";
import { useRouter, usePathname } from "next/navigation";

export default function GuruEditPageSidebar({ guruSlug }) {
  const [isOpen, setIsOpen] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const isSettingsActive = pathname.endsWith(`/guru/${guruSlug}`);
  const isSlackActive = pathname.includes("/integrations/slack");
  const isDiscordActive = pathname.includes("/integrations/discord");

  const handleNavigation = (path) => {
    if (!guruSlug) return;
    router.push(path);
  };

  return (
    <nav className="w-64 p-4 space-y-2 bg-white border rounded-lg border-neutral-200">
      <Button
        variant="ghost"
        className={cn(
          "w-full justify-start gap-2 font-normal",
          isSettingsActive ? "bg-gray-50" : "hover:bg-gray-50"
        )}
        onClick={() => handleNavigation(`/guru/${guruSlug}`)}>
        <Settings className="w-5 h-5 text-gray-500" />
        <span className="text-gray-600">Settings</span>
      </Button>
      {/* 
      <Button
        variant="ghost"
        className="w-full justify-start gap-2 font-normal hover:bg-gray-50">
        <FileText className="w-5 h-5 text-gray-500" />
        <span className="text-gray-600">Data Sources</span>
      </Button> */}

      {/* <Button
        variant="ghost"
        className="w-full justify-start gap-2 font-normal hover:bg-gray-50">
        <BarChart2 className="w-5 h-5 text-gray-500" />
        <span className="text-gray-600">Analytics</span>
      </Button> */}

      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className={cn(
              "w-full justify-start gap-2 font-normal hover:bg-gray-50",
              (isSlackActive || isDiscordActive) && "bg-gray-50"
            )}>
            <Link className="w-5 h-5 text-gray-500" />
            <span className="text-gray-600">Integrations</span>
            <svg
              className={cn(
                "ml-auto h-4 w-4 shrink-0 text-gray-500 transition-transform duration-200",
                isOpen && "rotate-180"
              )}
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24">
              <path
                fill="none"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="m6 9 6 6 6-6"
              />
            </svg>
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="space-y-2">
          {/* <Button
            variant="ghost"
            className="w-full justify-start pl-11 font-normal text-gray-600 hover:bg-gray-50">
            Web Widget
          </Button> */}
          <Button
            variant="ghost"
            className={cn(
              "w-full justify-start pl-11 font-normal",
              isSlackActive
                ? "text-blue-600 bg-blue-50 hover:bg-blue-100"
                : "text-gray-600 hover:bg-gray-50"
            )}
            onClick={() =>
              handleNavigation(`/guru/${guruSlug}/integrations/slack`)
            }>
            Slack Bot
          </Button>
          <Button
            variant="ghost"
            className={cn(
              "w-full justify-start pl-11 font-normal",
              isDiscordActive
                ? "text-blue-600 bg-blue-50 hover:bg-blue-100"
                : "text-gray-600 hover:bg-gray-50"
            )}
            onClick={() =>
              handleNavigation(`/guru/${guruSlug}/integrations/discord`)
            }>
            Discord Bot
          </Button>
        </CollapsibleContent>
      </Collapsible>
    </nav>
  );
}
