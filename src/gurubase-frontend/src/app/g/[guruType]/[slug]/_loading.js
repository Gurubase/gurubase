"use client";
import { useParams } from "next/navigation";
import { useEffect } from "react";

import Content from "@/components/Content";
import LoadingSkeleton from "@/components/Content/LoadingSkeleton";
import Footer from "@/components/Footer";
import Header from "@/components/Header";
import { useAppDispatch } from "@/redux/hooks";
import { setIsLoading } from "@/redux/slices/mainFormSlice";

export default function Loading() {
  const dispatch = useAppDispatch();

  useEffect(() => {
    dispatch(setIsLoading(true)); // to give loading skeleton
  }, [dispatch]);

  const { guruType } = useParams(); // Use useParams to get the dynamic route parameters

  // You can add any UI inside Loading, including a Skeleton.
  return (
    // Keep same UI while getting data from the server for instant questions
    <main className="flex flex-col bg-white h-screen">
      <Header guruType={guruType} sidebarExists={true} />
      <main className="z-10 flex justify-center items-center px-16 xs:px-0 w-full flex-grow xs:max-w-full polygon-fill">
        <section className="container mx-auto max-w-[1180px] shadow-md bg-white h-full xs:border-none border-l border-r border-solid border-neutral-200">
          <section className="flex flex-col flex-grow w-full xs:ml-0">
            <LoadingSkeleton />
          </section>
        </section>
      </main>
      <Footer sidebarExists={true} />
    </main>
  );
}
