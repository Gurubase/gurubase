"use client";
import APIKeys from "@/components/APIKeys";
import Footer from "@/components/Footer";
import Header from "@/components/Header/index";

const APIKeysMainPage = ({ apiKeys }) => {
  return (
    <div className="flex flex-col bg-white h-screen">
      <Header />
      <APIKeys initialApiKeys={apiKeys} />
      <Footer />
    </div>
  );
};

export default APIKeysMainPage;
