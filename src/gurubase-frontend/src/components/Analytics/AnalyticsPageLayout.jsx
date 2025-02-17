"use client";

import CommonContentLayout from "@/components/CommonContentLayout";
import Footer from "@/components/Footer";
import GuruEditPageSidebar from "@/components/GuruEditPageSidebar";
import Header from "@/components/Header";
import AnalyticsContent from "./AnalyticsContent";

// TODO: This can be merged with IntegrationPageLayout

export const AnalyticsPageLayout = ({ guruData, initialInterval }) => {
  return (
    <div className={`flex flex-col bg-white h-screen`}>
      <Header sidebarExists={true} />
      <CommonContentLayout
        sidebar={<GuruEditPageSidebar guruData={guruData} />}>
        <div className="flex gap-6">
          <div className="flex-1">
            <AnalyticsContent
              guruData={guruData}
              initialInterval={initialInterval}
            />
          </div>
        </div>
      </CommonContentLayout>
      <Footer />
    </div>
  );
};

export default AnalyticsPageLayout;
