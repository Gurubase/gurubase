"use client";
import { useState } from "react";

import Footer from "@/components/Footer";
import GuruEditPageSidebar from "@/components/GuruEditPageSidebar";
import Header from "@/components/Header";

import CommonContentLayout from "../CommonContentLayout";
import NewGuruContent from "./NewGuruContent";

export const NewGuruClient = ({ guruData, isProcessing }) => {
  const [hasDataSources, setHasDataSources] = useState(false);

  return (
    <div className={`flex flex-col bg-white h-screen`}>
      <Header sidebarExists={true} />
      <CommonContentLayout
        sidebar={
          <GuruEditPageSidebar
            guruData={guruData}
            hasDataSources={hasDataSources}
          />
        }>
        <NewGuruContent
          guruData={guruData}
          hasDataSources={hasDataSources}
          isProcessing={isProcessing}
          setHasDataSources={setHasDataSources}
        />
      </CommonContentLayout>
      <Footer sidebarExists={true} />
    </div>
  );
};
