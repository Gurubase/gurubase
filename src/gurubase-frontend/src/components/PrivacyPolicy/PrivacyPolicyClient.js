"use client";

import Footer from "@/components/Footer";
import Header from "@/components/Header";

import CommonContentLayout from "../CommonContentLayout";
import PrivacyPolicy from "./PrivacyPolicy";

export default function Page() {
  return (
    <div className={`flex flex-col bg-white h-screen`}>
      <Header />
      <CommonContentLayout>
        <PrivacyPolicy />
      </CommonContentLayout>
      <Footer />
    </div>
  );
}
