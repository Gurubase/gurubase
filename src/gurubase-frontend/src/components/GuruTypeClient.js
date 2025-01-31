"use client";
import mixpanel from "mixpanel-browser";
import React, { useEffect, useState } from "react";

import Content from "@/components/Content";
import Footer from "@/components/Footer";
import Header from "@/components/Header";
import { useAppDispatch } from "@/redux/hooks";
import { setBingeInfo } from "@/redux/slices/mainFormSlice";

export default function Home({
  guruType,
  allGuruTypes,
  defaultQuestions,
  resources
}) {
  const dispatch = useAppDispatch();

  // check the environment development or production
  const [env, setEnv] = useState("development");

  // check the environment development or production
  useEffect(() => {
    if (process.env.NEXT_PUBLIC_NODE_ENV === "production") {
      setEnv("production");
    }
  }, []);

  useEffect(() => {
    dispatch(setBingeInfo({ treeData: null, bingeOutdated: false }));
  }, []);

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_MIXPANEL_TOKEN) {
      mixpanel.init(process.env.NEXT_PUBLIC_MIXPANEL_TOKEN, { debug: false });
    }
  }, []);

  return (
    <div className="flex flex-col bg-white h-screen">
      <Header
        allGuruTypes={allGuruTypes}
        guruType={guruType}
        sidebarExists={true}
      />
      <Content
        allGuruTypes={allGuruTypes}
        defaultQuestions={defaultQuestions}
        guruType={guruType}
        resources={resources}
      />
      <Footer guruType={guruType} sidebarExists={true} />
    </div>
  );
}
