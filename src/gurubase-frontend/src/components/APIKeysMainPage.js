"use client";
import APIKeys from "@/components/APIKeys";
import Footer from "@/components/Footer";
import Header from "@/components/Header/index";

const APIKeysMainPage = () => {
  return (
    <div className="flex flex-col bg-white h-screen">
      <Header />
      <APIKeys />
      <Footer />
    </div>
  );
};

export default APIKeysMainPage;
