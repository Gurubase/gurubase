"use client";

import React, { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { createIntegration } from "@/app/actions";
import { useRouter } from "next/navigation";
import { useAppNavigation } from "@/lib/navigation";

const LoadingSpinner = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-gray-800 border-r-transparent motion-reduce:animate-[spin_1.5s_linear_infinite]" />
  </div>
);

const OAuthCallback = () => {
  const [error, setError] = useState(null);
  const searchParams = useSearchParams();
  const navigation = useAppNavigation();

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get("code");
      const state = searchParams.get("state");

      if (!code || !state) {
        setError("Missing required parameters");
        navigation.push(`/`);
      }

      try {
        const stateData = JSON.parse(state);
        const response = await createIntegration(code, state);

        const { guru_type, type } = stateData;
        const url = `/guru/${guru_type}/integrations/${type.toLowerCase()}`;

        if (response.error) {
          setError(response.message);
          navigation.push(`${url}?error=true`);
        } else {
          navigation.push(url);
        }
      } catch (err) {
        setError(err.message || "Failed to create integration");
      }
    };

    handleCallback();
  }, [searchParams]);

  // if (error) {
  //   return (
  //     <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
  //       <div className="p-8 bg-white rounded-lg shadow-md">
  //         <h1 className="text-2xl font-bold text-red-600 mb-4">Error</h1>
  //         <p className="text-gray-700">{error}</p>
  //       </div>
  //     </div>
  //   );
  // }

  return <LoadingSpinner />;
};

export default OAuthCallback;
