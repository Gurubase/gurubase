"use client";

import Header from "@/components/Header";
import Footer from "@/components/Footer";
import TermsOfUse from "./TermsOfUse";
import CommonContentLayout from "../CommonContentLayout";

export default function Page() {
  return (
    <div className={`flex flex-col bg-white guru-md:h-screen h-full`}>
      <Header textPageHeader={true} />
      <CommonContentLayout>
        <TermsOfUse />
      </CommonContentLayout>
      <Footer />
    </div>
  );
}
