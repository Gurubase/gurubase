"use client";
import Footer from "@/components/Footer";
import GuruEditPageSidebar from "@/components/GuruEditPageSidebar";
import Header from "@/components/Header";

import CommonContentLayout from "../CommonContentLayout";
import NewGuruContent from "./NewGuruContent";

export const NewGuruClient = ({
  customGuru,
  dataSources,
  guruTypes,
  isProcessing
}) => {
  return (
    <div className={`flex flex-col bg-white h-screen`}>
      <Header />
      <CommonContentLayout
        sidebar={
          <GuruEditPageSidebar guruSlug={customGuru} guruTypes={guruTypes} />
        }>
        <NewGuruContent
          customGuru={customGuru}
          dataSources={dataSources}
          guruTypes={guruTypes}
          isProcessing={isProcessing}
        />
      </CommonContentLayout>
      <Footer />
    </div>
  );
};
