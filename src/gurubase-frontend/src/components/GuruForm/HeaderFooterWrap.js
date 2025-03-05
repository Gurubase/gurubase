"use client";
import Footer from "@/components/Footer";
import Header from "@/components/Header/index";

import CommonContentLayout from "../CommonContentLayout";

export default function HeaderFooterWrap({ children }) {
  return (
    <div className="flex flex-col bg-white h-screen">
      <Header />
      <CommonContentLayout>{children}</CommonContentLayout>
      <Footer />
    </div>
  );
}
