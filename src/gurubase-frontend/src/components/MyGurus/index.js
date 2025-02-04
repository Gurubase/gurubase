"use client";

import { useUser } from "@auth0/nextjs-auth0/client";
import { LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { getMyGurus } from "@/app/actions";
import Footer from "@/components/Footer";
import GuruList from "@/components/GuruList";
import Header from "@/components/Header";
import { useAppNavigation } from "@/lib/navigation";

export const MyGurusClient = () => {
  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";
  const { user, isLoading: authLoading } = isSelfHosted
    ? { user: true, isLoading: false }
    : useUser();
  const [myGurus, setMyGurus] = useState([]);
  const [error, setError] = useState(null);
  const [isLoadingGurus, setIsLoadingGurus] = useState(true);
  const navigation = useAppNavigation();

  useEffect(() => {
    if (!user && !authLoading) {
      navigation.push("/api/auth/login");

      return;
    }

    const fetchMyGurus = async () => {
      setIsLoadingGurus(true);
      try {
        const data = await getMyGurus();

        if (data === null) {
          throw new Error("Failed to fetch gurus");
        }
        setMyGurus(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoadingGurus(false);
      }
    };

    if (user) {
      fetchMyGurus();
    }
  }, [user, authLoading]);

  return (
    <div className="flex flex-col bg-white h-screen">
      <Header />
      {error && <div className="text-red-500 mb-4 px-4">Error: {error}</div>}
      {isLoadingGurus ? (
        <div className="flex flex-col items-center justify-center w-full max-w-4xl mx-auto px-4 h-[100vh]">
          <LoaderCircle className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : myGurus?.length === 0 && !isSelfHosted ? (
        <div className="text-gray-500 text-center flex flex-col items-center justify-center w-full max-w-4xl mx-auto px-4 h-[100vh]">
          You haven&apos;t been granted access to any gurus yet. Please check
          out the{" "}
          <a
            href="https://github.com/Gurubase/gurubase?tab=readme-ov-file#how-to-claim-a-guru"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-500 hover:underline">
            How to Claim a Guru
          </a>
        </div>
      ) : (
        <GuruList allGuruTypes={myGurus} title="My Gurus" />
      )}
      <Footer />
    </div>
  );
};
