"use client";

import { useSearchParams } from "next/navigation";
import { submitGuruCreationForm, getCurrentUserEmail } from "@/app/actions";
import GuruForm from "@/components/GuruForm/GuruForm";
import HeaderFooterWrap from "@/components/GuruForm/HeaderFooterWrap";
import { useEffect, useState } from "react";

export default function UserInfoPage() {
  const searchParams = useSearchParams();
  const source = searchParams.get("source") || "unknown";
  const [userEmail, setUserEmail] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchUserEmail = async () => {
      try {
        const email = await getCurrentUserEmail();
        setUserEmail(email);
      } finally {
        setIsLoading(false);
      }
    };

    fetchUserEmail();
  }, []);

  // Mock function to handle form submission
  const handleFormSubmit = async (data) => {
    try {
      const formData = new FormData();
      formData.append("email", data.email);
      formData.append("github_repo", data.githubLink);
      formData.append("docs_url", data.docsRootUrl);
      formData.append("use_case", data.useCase);
      formData.append("source", data.source);

      const response = await submitGuruCreationForm(formData);

      if (response?.error) {
        throw new Error(response.message);
      }

      return response;
    } catch (error) {
      console.error("Error submitting form:", error);
      throw error;
    }
  };

  return (
    <HeaderFooterWrap>
      <GuruForm
        source={source}
        onSubmit={handleFormSubmit}
        defaultEmail={userEmail}
        isLoading={isLoading}
      />
    </HeaderFooterWrap>
  );
}
