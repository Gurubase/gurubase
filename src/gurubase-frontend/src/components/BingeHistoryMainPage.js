"use client";
import Header from "@/components/Header/index";
import Footer from "@/components/Footer";
import BingeHistory from "@/components/BingeHistory";

const BingeHistoryMainPage = ({ guruTypes }) => {
  return (
    <div className="flex flex-col bg-white h-screen">
      <Header />
      <BingeHistory guruTypes={guruTypes} />
      <Footer />
    </div>
  );
};

export default BingeHistoryMainPage;
