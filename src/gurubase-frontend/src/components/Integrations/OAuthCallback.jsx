"use client";

import React, { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { createIntegration } from "@/app/actions";

const OAuthCallback = () => {
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const searchParams = useSearchParams();

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get("code");
      const state = searchParams.get("state");

      if (!code || !state) {
        setError("Missing required parameters");
        return;
      }

      try {
        // Parse state to get integration type and guru type
        const stateData = JSON.parse(state);

        const response = await createIntegration(code, state);

        if (response.error) {
          setError(response.message);
          return;
        }

        setSuccess(true);
      } catch (err) {
        setError(err.message || "Failed to create integration");
      }
    };

    handleCallback();
  }, [searchParams]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        <div className="p-8 bg-white rounded-lg shadow-md">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Error</h1>
          <p className="text-gray-700">{error}</p>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        <div className="p-8 bg-white rounded-lg shadow-md">
          <h1 className="text-2xl font-bold text-green-600 mb-4">Success!</h1>
          <p className="text-gray-700">
            Integration successful, you can now close this page and refresh your
            integration configuration
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <div className="p-8 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-gray-800 mb-4">
          Setting up your integration...
        </h1>
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>
    </div>
  );
};

export default OAuthCallback;
