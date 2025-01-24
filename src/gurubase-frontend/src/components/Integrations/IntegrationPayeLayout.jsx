"use client";

import CommonContentLayout from "@/components/CommonContentLayout";
import Footer from "@/components/Footer";
import GuruEditPageSidebar from "@/components/GuruEditPageSidebar";
import Header from "@/components/Header";
import IntegrationContent from "@/components/Integrations/IntegrationContent";

export const IntegrationPayeLayout = ({ customGuru, type, error }) => {
  return (
    <div className={`flex flex-col bg-white h-screen`}>
      <Header textPageHeader={true} />
      <CommonContentLayout
        sidebar={<GuruEditPageSidebar guruSlug={customGuru} />}>
        <div className="flex gap-6">
          <div className="flex-1">
            <IntegrationContent
              type={type}
              customGuru={customGuru}
              error={error}
            />
          </div>
        </div>
      </CommonContentLayout>
      <Footer />
    </div>
  );
};

export default IntegrationPayeLayout;
