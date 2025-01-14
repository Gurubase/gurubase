"use client";
import React, { useEffect, useState } from "react";

import Footer from "@/components/Footer";
import GuruList from "@/components/GuruList";
import Header from "@/components/Header/index";

export default function HomePageClient({ allGuruTypes }) {
  // check the environment development or production
  const [env, setEnv] = useState("development");

  // check the environment development or production
  useEffect(() => {
    if (process.env.NEXT_PUBLIC_NODE_ENV === "production") {
      setEnv("production");
    }
  }, []);

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_MIXPANEL_TOKEN) {
      mixpanel.init(process.env.NEXT_PUBLIC_MIXPANEL_TOKEN, { debug: false });
    }
  }, []);

  return (
    <div
      className={`${
        process.env.NEXT_PUBLIC_NODE_ENV === "development"
          ? // ? "debug-screens"
            ""
          : "" // show debug screen in development mode
      } flex flex-col bg-white h-screen`}>
      <Header />
      <GuruList allGuruTypes={allGuruTypes} />
      <Footer />
    </div>
  );
}
