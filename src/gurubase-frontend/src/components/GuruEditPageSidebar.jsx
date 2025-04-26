"use client";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Image from "next/image";
import { SidebarIcons } from "./Icons";
import clsx from "clsx";
import { IntegrationDivider } from "./Integrations/IntegrationShared";
import { useAppNavigation } from "@/lib/navigation";

const SidebarOption = ({ icon, label, isActive, onClick }) => (
  <Button
    variant="ghost"
    className={cn(
      "w-full justify-start gap-2 font-inter text-[14px] font-medium leading-[20px] transition-colors guru-sm:px-5 guru-sm:py-3",
      isActive
        ? "bg-[#EFF6FF] text-[#2563EB] hover:text-[#2563EB]"
        : "text-[#6D6D6D] hover:bg-[#FAFAFA]"
    )}
    onClick={onClick}>
    <SidebarIcons type={icon} color={isActive ? "#2563EB" : "#6D6D6D"} />
    <span>{label}</span>
  </Button>
);

export default function GuruEditPageSidebar({ guruData, hasDataSources }) {
  const router = useRouter();
  const pathname = usePathname();
  const navigation = useAppNavigation();

  let guruSlug = guruData?.slug;
  let guruName = guruData?.name;
  let guruLogo = guruData?.icon_url;

  const isSettingsActive = pathname === `/guru/${guruSlug}`;
  const isIntegrationsActive = pathname.includes(
    `/guru/${guruSlug}/integrations`
  );
  const isAnalyticsActive = pathname.includes(`/guru/${guruSlug}/analytics`);

  const handleNavigation = (path) => {
    if (!guruSlug) return;
    navigation.push(path);
  };

  if (!guruName) {
    return null;
  }

  return (
    <aside className="relative guru-sm:h-auto guru-sm:static h-full">
      <div className="sticky guru-sm:static top-[100px]">
        <nav className="flex flex-col items-center w-[250px] guru-sm:w-full guru-sm:mx-auto guru-sm:mb-5 mb-0 bg-white guru-sm:border-0 border rounded-lg border-[#E2E2E2]">
          {/* Guru Logo and Name */}
          <div className="flex items-center gap-2 w-full pb-3 pt-5 px-5 guru-sm:hidden">
            {guruLogo && (
              <div className="w-8 h-8 rounded-lg flex items-center justify-center overflow-hidden">
                <Image
                  src={guruLogo}
                  alt={`${guruName} logo`}
                  width={32}
                  height={32}
                  className="w-full h-full object-cover"
                />
              </div>
            )}
            <span className="font-inter text-[14px] font-medium leading-[20px] text-[#191919]">
              {guruName} Guru
            </span>
          </div>

          {/* Visit Guru Button */}
          {hasDataSources && (
            <div className="w-full px-5 pb-5 guru-sm:hidden">
              <Button
                variant="outline"
                size="smButtonLgText"
                className="w-full text-black hover:bg-gray-800 hover:text-white rounded-full"
                onClick={() =>
                  window.open(`/g/${guruSlug}`, "_blank", "noopener,noreferrer")
                }>
                <div className="inline-flex items-center gap-1">
                  <span>Visit Guru</span>
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg">
                    <path
                      fillRule="evenodd"
                      clipRule="evenodd"
                      d="M6 4.5C5.72386 4.5 5.5 4.27614 5.5 4C5.5 3.72386 5.72386 3.5 6 3.5H12C12.2761 3.5 12.5 3.72386 12.5 4V10C12.5 10.2761 12.2761 10.5 12 10.5C11.7239 10.5 11.5 10.2761 11.5 10V5.20711L4.35355 12.3536C4.15829 12.5488 3.84171 12.5488 3.64645 12.3536C3.45118 12.1583 3.45118 11.8417 3.64645 11.6464L10.7929 4.5H6Z"
                      fill="currentColor"
                    />
                  </svg>
                </div>
              </Button>
            </div>
          )}

          {/* Divider */}
          <div className="w-full h-px bg-[#E2E2E2] guru-sm:hidden" />

          {/* Navigation Items */}
          <div className="w-full p-2 guru-sm:px-4 guru-sm:pt-2 guru-sm:p-0 space-y-1">
            <SidebarOption
              icon="Settings"
              label="Settings"
              isActive={isSettingsActive}
              onClick={() => handleNavigation(`/guru/${guruSlug}`)}
            />

            <SidebarOption
              icon="Analytics"
              label="Analytics"
              isActive={isAnalyticsActive}
              onClick={() => handleNavigation(`/guru/${guruSlug}/analytics`)}
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
      <div className="guru-sm:block hidden">
        <IntegrationDivider />
      </div>
    </aside>
  );
}
