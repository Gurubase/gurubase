"use client";

import { useState } from "react";

import { createWidgetId } from "@/app/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function CreateWidgetModal({ onWidgetCreate, guruSlug }) {
  const [domain, setDomain] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const response = await createWidgetId(guruSlug, domain);

      if (response?.error) {
        setError(response.message);

        return;
      }
      if (response) {
        onWidgetCreate?.(response);
        setDomain("");
      }
    } catch (error) {
      setError(error.message || "Failed to create widget ID");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col">
      <div className="py-6 pr-4">
        <div className="flex items-center gap-3 pr-4 rounded-lg">
          <div className="flex items-center gap-3 w-[440px]">
            <div className="relative flex-1">
              <span className="absolute left-3 top-2 text-xs font-normal text-gray-500">
                Domain
              </span>
              <Input
                required
                aria-label="Domain input"
                className="pt-8 pb-2"
                disabled={isLoading}
                placeholder="URL link"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
              />
            </div>
            <Button
              className={`gap-2 rounded-lg transition-colors ${
                !domain ? "bg-[#6D6D6D] hover:bg-[#6D6D6D]" : ""
              }`}
              disabled={isLoading || !domain}
              size="action2"
              type="button"
              onClick={handleSubmit}>
              {isLoading ? "Generating..." : "Generate"}
            </Button>
          </div>
        </div>
        {error && <p className="text-red-500 text-sm mt-2 px-2">{error}</p>}
      </div>
    </div>
  );
}
