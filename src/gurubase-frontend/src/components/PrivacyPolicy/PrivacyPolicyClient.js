"use client";

import Header from "@/components/Header";
import Footer from "@/components/Footer";
import PrivacyPolicy from "./PrivacyPolicy";
import CommonContentLayout from "../CommonContentLayout";

export default function Page() {
  return (
    <div className={`flex flex-col bg-white h-screen`}>
      <Header textPageHeader={true} />
      <CommonContentLayout>
        <PrivacyPolicy />
      </CommonContentLayout>
      <Footer />
    </div>
  );
}
