"use client"; // Error components must be Client Components

import { ExclamationCircleIcon } from "@/components/Icons";

export default function Error() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 text-black-base">
      <div className="flex items-center space-x-3">
        <ExclamationCircleIcon className="h-12 w-12 text-red-500" />
        <h1 className="text-4xl font-bold text-gray-800">
          404 - Page Not Found
        </h1>
      </div>
      <p className="mt-4 text-lg text-gray-600 mb-5">
        Sorry, the page you are looking for does not exist.
      </p>
      <a
        className="px-4 py-2 text-white bg-blue-600 rounded hover:bg-blue-700"
        href="/">
        Return Home
      </a>
    </div>
  );
}
