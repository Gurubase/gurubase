"use client";

import Link from "next/link";
import { useEffect } from "react";
import { SolarHomeBold } from "@/components/Icons";
import { useAppSelector, useAppDispatch } from "@/redux/hooks";
import { setNotFoundContext } from "@/redux/slices/mainFormSlice";
import { reportErrorToSentry } from "@/utils/sentry";

export default function NotFound() {
  const dispatch = useAppDispatch();
  const notFoundContext = useAppSelector(
    (state) => state.mainForm.notFoundContext
  );

  useEffect(() => {
    const reportError = async () => {
      if (
        process.env.NEXT_PUBLIC_NODE_ENV === "production" &&
        notFoundContext
      ) {
        await reportErrorToSentry("404 - Page Not Found", notFoundContext);
        dispatch(setNotFoundContext(null));
      }
    };

    reportError();
  }, [notFoundContext, dispatch]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 guru-sm:px-4">
      <div className="flex items-center space-x-3">
        <SolarHomeBold className="text-error-base" height={42} width={42} />
        <h1 className="text-4xl font-bold text-black-base">
          404 - Page Not Found
        </h1>
      </div>
      <p className="mt-4 text-lg text-gray-600 mb-5">
        Sorry, the page you are looking for does not exist.
      </p>
      <Link href="/" prefetch={false}>
        <span className="px-4 py-2 text-white bg-blue-600 rounded hover:bg-blue-700">
          Return Home
        </span>
      </Link>
    </div>
  );
}