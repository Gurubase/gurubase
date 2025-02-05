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

export default function GuruEditPageSidebar({ guruSlug, guruTypes }) {
  const router = useRouter();
  const pathname = usePathname();
  const navigation = useAppNavigation();

  const isSettingsActive = pathname === `/guru/${guruSlug}`;
  const isIntegrationsActive = pathname.includes(
    `/guru/${guruSlug}/integrations`
  );

  const handleNavigation = (path) => {
    if (!guruSlug) return;
    navigation.push(path);
  };

  let guruName = guruTypes?.find((type) => type.slug === guruSlug)?.name;
  let guruLogo = guruTypes?.find((type) => type.slug === guruSlug)?.icon_url;

  if (!guruName) {
    return null;
  }

  return (
    <aside className="relative guru-sm:h-auto guru-sm:static h-full">
      <div className="sticky guru-sm:static top-[100px]">
        <nav className="flex flex-col items-center w-[250px] guru-sm:w-full guru-sm:mx-auto guru-sm:mb-5 mb-0 bg-white guru-sm:border-0 border rounded-lg border-[#E2E2E2]">
          {/* Guru Logo and Name */}
          <div className="flex items-center gap-2 w-full p-5 guru-sm:hidden">
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
