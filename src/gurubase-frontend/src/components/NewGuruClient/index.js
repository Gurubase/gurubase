"use client";
import Footer from "@/components/Footer";
import GuruEditPageSidebar from "@/components/GuruEditPageSidebar";
import Header from "@/components/Header";

import CommonContentLayout from "../CommonContentLayout";
import NewGuruContent from "./NewGuruContent";

export const NewGuruClient = ({ guruData, isProcessing }) => {
  return (
    <div className={`flex flex-col bg-white h-screen`}>
      <Header sidebarExists={true} />
      <CommonContentLayout
        sidebar={<GuruEditPageSidebar guruData={guruData} />}>
        <NewGuruContent guruData={guruData} isProcessing={isProcessing} />
      </CommonContentLayout>
      <Footer sidebarExists={true} />
    </div>
  );
};
