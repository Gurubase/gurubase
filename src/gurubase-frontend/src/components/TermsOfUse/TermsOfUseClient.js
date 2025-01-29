"use client";

import Footer from "@/components/Footer";
import Header from "@/components/Header";

import CommonContentLayout from "../CommonContentLayout";
import TermsOfUse from "./TermsOfUse";

export default function Page() {
  return (
    <div className={`flex flex-col bg-white guru-md:h-screen h-full`}>
      <Header />
      <CommonContentLayout>
        <TermsOfUse />
      </CommonContentLayout>
      <Footer />
    </div>
  );
}
