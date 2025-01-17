"use client";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import NewGuruContent from "./NewGuruContent";
import CommonContentLayout from "../CommonContentLayout";

export const NewGuruClient = ({
  guruTypes,
  dataSources,
  customGuru,
  isProcessing
}) => {
  return (
    <div className={`flex flex-col bg-white h-screen`}>
      <Header textPageHeader={true} />
      <CommonContentLayout>
        <NewGuruContent
          guruTypes={guruTypes}
          dataSources={dataSources}
          customGuru={customGuru}
          isProcessing={isProcessing}
        />
      </CommonContentLayout>
      <Footer />
    </div>
  );
};
