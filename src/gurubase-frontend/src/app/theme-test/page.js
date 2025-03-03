"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

import { ThemeToggle } from "@/components/ui/theme-toggle";

export default function ThemeTestPage() {
  const { theme, resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div>Loading...</div>;
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8 bg-white dark:bg-black">
      <div className="max-w-md w-full bg-gray-50 dark:bg-gray-800 p-8 rounded-lg shadow-lg">
        <h1 className="text-2xl font-bold mb-4 text-black dark:text-white">
          Theme Test Page
        </h1>

        <div className="mb-6 space-y-2">
          <p className="text-gray-700 dark:text-gray-300">
            Current theme: <span className="font-bold">{theme}</span>
          </p>
          <p className="text-gray-700 dark:text-gray-300">
            Resolved theme: <span className="font-bold">{resolvedTheme}</span>
          </p>
          <p className="text-gray-700 dark:text-gray-300">
            Dark class on HTML:
            <span className="font-bold">
              {document.documentElement.classList.contains("dark")
                ? "Yes"
                : "No"}
            </span>
          </p>
        </div>

        <div className="flex flex-col space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-gray-700 dark:text-gray-300">
              Toggle Theme:
            </span>
            <ThemeToggle />
          </div>

          <div className="grid grid-cols-3 gap-2">
            <button
              className="px-4 py-2 bg-white text-black border border-gray-300 rounded hover:bg-gray-100"
              onClick={() => setTheme("light")}>
              Light
            </button>
            <button
              className="px-4 py-2 bg-gray-800 text-white border border-gray-700 rounded hover:bg-gray-700"
              onClick={() => setTheme("dark")}>
              Dark
            </button>
            <button
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              onClick={() => setTheme("system")}>
              System
            </button>
          </div>
        </div>

        <div className="mt-8 space-y-4">
          <div className="p-4 bg-white dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-black dark:text-white mb-2">
              Light/Dark Demo
            </h2>
            <p className="text-gray-700 dark:text-gray-300">
              This box should change colors based on the theme.
            </p>
          </div>

          <div className="p-4 bg-blue-100 dark:bg-blue-900 rounded border border-blue-200 dark:border-blue-800">
            <h2 className="text-lg font-semibold text-blue-800 dark:text-blue-100 mb-2">
              Colored Box
            </h2>
            <p className="text-blue-700 dark:text-blue-300">
              This colored box should also adapt to the theme.
            </p>
          </div>
        </div>

        <div className="mt-6">
          <a className="text-blue-500 hover:underline" href="/">
            Back to Home
          </a>
        </div>
      </div>
    </div>
  );
}
