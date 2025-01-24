"use client";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Image from "next/image";
import { SidebarIcons } from "./Icons";

const SidebarOption = ({ icon, label, isActive, onClick }) => (
  <Button
    variant="ghost"
    className={cn(
      "w-full justify-start gap-2 p-3 font-inter text-[14px] font-medium leading-[20px] transition-colors",
      isActive
        ? "bg-[#EFF6FF] text-[#2563EB] hover:text-[#2563EB]"
        : "text-[#6D6D6D] hover:bg-[#FAFAFA]"
    )}
    onClick={onClick}>
    <SidebarIcons type={icon} color={isActive ? "#2563EB" : "#6D6D6D"} />
    <span>{label}</span>
  </Button>
);

export default function GuruEditPageSidebar({ guruSlug, guruTypes }) {
  const router = useRouter();
  const pathname = usePathname();

  const isSettingsActive = pathname === `/guru/${guruSlug}`;
  const isIntegrationsActive = pathname === `/guru/${guruSlug}/integrations`;

  const handleNavigation = (path) => {
    if (!guruSlug) return;
    router.push(path);
  };

  const guruName = guruTypes.find((type) => type.slug === guruSlug)?.name;
  const guruLogo = guruTypes.find((type) => type.slug === guruSlug)?.icon_url;

  return (
    <aside className="relative h-full min-h-screen">
      <div className="sticky top-[110px]">
        <nav className="flex flex-col items-center w-[250px] bg-white border rounded-lg border-[#E2E2E2]">
          {/* Guru Logo and Name */}
          <div className="flex items-center gap-2 w-full p-5">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center overflow-hidden">
              {guruLogo ? (
                <Image
                  src={guruLogo}
                  alt={`${guruName} logo`}
                  width={32}
                  height={32}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full bg-gray-200" />
              )}
            </div>
            <span className="font-inter text-[14px] font-medium leading-[20px] text-[#191919]">
              {guruName} Guru
            </span>
          </div>

          {/* Divider */}
          <div className="w-full h-px bg-[#E2E2E2]" />

          {/* Navigation Items */}
          <div className="w-full p-2 space-y-1">
            <SidebarOption
              icon="Settings"
              label="Settings"
              isActive={isSettingsActive}
              onClick={() => handleNavigation(`/guru/${guruSlug}`)}
            />

            <SidebarOption
              icon="Integrations"
              label="Integrations"
              isActive={isIntegrationsActive}
              onClick={() => handleNavigation(`/guru/${guruSlug}/integrations`)}
            />
          </div>
        </nav>
      </div>
    </aside>
  );
}
