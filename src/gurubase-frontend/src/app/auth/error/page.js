"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Link } from "@/components/Link";

export default function AuthErrorPage() {
  const searchParams = useSearchParams();
  const [isOpen, setIsOpen] = useState(false);
  const error = searchParams.get("error");
  const errorDescription = searchParams.get("error_description");

  useEffect(() => {
    if (error) {
      setIsOpen(true);
    }
  }, [error]);

  const handleClose = () => {
    setIsOpen(false);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 guru-sm:px-4">
      <div className="flex items-center space-x-3">
        {/* <SolarHomeBold className="text-error-base" height={42} width={42} /> */}
        <h1 className="text-4xl font-bold text-black-base">
          Authentication Error
        </h1>
      </div>
      <p className="mt-4 text-lg text-gray-600 mb-5">{errorDescription}</p>
      <Link href="/" prefetch={false}>
        <span className="px-4 py-2 text-white bg-blue-600 rounded hover:bg-blue-700">
          Return Home
        </span>
      </Link>
    </div>
  );
}
