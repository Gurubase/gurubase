"use client";

import Footer from "@/components/Footer";
import Header from "@/components/Header/index";
import Settings from "@/components/Settings";

const SettingsMainPage = () => {
  return (
    <div className="flex flex-col bg-white h-screen">
      <Header />
      <Settings />
      <Footer />
    </div>
  );
};

export default SettingsMainPage;
