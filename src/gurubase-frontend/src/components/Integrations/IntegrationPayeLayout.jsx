"use client";

import CommonContentLayout from "@/components/CommonContentLayout";
import Footer from "@/components/Footer";
import GuruEditPageSidebar from "@/components/GuruEditPageSidebar";
import Header from "@/components/Header";
import SetupIntegration from "@/components/Integrations/SetupIntegration";

export const IntegrationPayeLayout = ({ customGuru, type }) => {
  return (
    <div className={`flex flex-col bg-white h-screen`}>
      <Header textPageHeader={true} />
      <CommonContentLayout
        sidebar={<GuruEditPageSidebar guruSlug={customGuru} />}>
        <div className="flex gap-6">
          <div className="flex-1">
            <SetupIntegration type={type} customGuru={customGuru} />
          </div>
        </div>
      </CommonContentLayout>
      <Footer />
    </div>
  );
};

export default IntegrationPayeLayout;
