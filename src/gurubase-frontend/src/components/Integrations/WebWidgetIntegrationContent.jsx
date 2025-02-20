"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getMyGuru } from "@/app/actions";
import CreateWidgetModal from "@/components/CreateWidgetModal";
import WidgetId from "@/components/WidgetId";
import { Button } from "@/components/ui/button";
import {
  IntegrationHeader,
  IntegrationDivider,
  IntegrationIconContainer,
  IntegrationInfo
} from "./IntegrationShared";
import { WebWidgetIcon } from "@/components/Icons";

export const WebWidgetIntegrationContent = ({ guruData }) => {
  const router = useRouter();
  const [isWidgetModalVisible, setIsWidgetModalVisible] = useState(false);
  const [isGeneratingWidget, setIsGeneratingWidget] = useState(false);
  const [widgetIds, setWidgetIds] = useState(guruData?.widget_ids || []);

  const refreshGuruData = async () => {
    const updatedGuruData = await getMyGuru(guruData.slug);
    setWidgetIds(updatedGuruData?.widget_ids || []);
  };

  const handleAddWidget = () => {
    setIsWidgetModalVisible(true);
    setIsGeneratingWidget(true);
  };

  const handleWidgetCreate = async (response) => {
    setIsWidgetModalVisible(false);
    setIsGeneratingWidget(false);
    if (response?.error) return;

    await refreshGuruData();
  };

  const handleWidgetDelete = async (deletedWidgetId) => {
    await refreshGuruData();
  };

  return (
    <div className="w-full">
      <IntegrationHeader text="Web Widget" />
      <IntegrationDivider />
      <div className="flex flex-col gap-6 p-6">
        <div>
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-lg font-medium">Widget IDs</h3>
          </div>
          <p className="text-[#6D6D6D] font-inter text-[14px] font-normal mb-6">
            Add {guruData?.name} Guru directly to your website. Here's the guide
            to{" "}
            <Link
              className="text-blue-500 hover:text-blue-600"
              href="https://github.com/getanteon/gurubase-widget"
              target="_blank">
              learn more
            </Link>
            .
          </p>
          <div className="flex flex-col">
            {widgetIds.map((widget, index) => (
              <WidgetId
                key={widget.key}
                domainUrl={widget.domain_url}
                guruSlug={guruData?.slug}
                isFirst={index === 0}
                isLast={!isWidgetModalVisible && index === widgetIds.length - 1}
                widgetId={widget.key}
                onDelete={() => handleWidgetDelete(widget.key)}
              />
            ))}

            {!isGeneratingWidget && (
              <div className="flex justify-start">
                <Button
                  className="text-black-600"
                  size="action3"
                  type="button"
                  variant="ghostNoSpace"
                  onClick={handleAddWidget}>
                  <span className="flex items-center text-md">
                    <svg
                      className="w-4 h-4 mr-2"
                      fill="none"
                      viewBox="0 0 24 24"
                      xmlns="http://www.w3.org/2000/svg">
                      <path
                        d="M12 4V20M20 12L4 12"
                        stroke="currentColor"
                        strokeLinecap="round"
                        strokeWidth="2"
                      />
                    </svg>
                    New Widget ID
                  </span>
                </Button>
              </div>
            )}

            {isWidgetModalVisible && (
              <CreateWidgetModal
                guruSlug={guruData?.slug}
                onWidgetCreate={handleWidgetCreate}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default WebWidgetIntegrationContent;
