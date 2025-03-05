"use client";

import { useSearchParams } from "next/navigation";

import GuruForm from "@/components/GuruForm/GuruForm";
import HeaderFooterWrap from "@/components/GuruForm/HeaderFooterWrap";

export default function UserInfoPage() {
  const searchParams = useSearchParams();
  const source = searchParams.get("source") || "default";

  // Mock function to handle form submission
  const handleFormSubmit = async (data) => {
    // In a real application, you would send this data to your API
    console.log("Received form data:", data);
    console.log("Source:", source);

    // Simulate API call delay
    return new Promise((resolve) => setTimeout(resolve, 1000));
  };

  return (
    <HeaderFooterWrap>
      <GuruForm source={source} onSubmit={handleFormSubmit} />
    </HeaderFooterWrap>
  );
}
