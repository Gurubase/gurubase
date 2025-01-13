"use client";
import { env } from "next-runtime-env";
import posthog from "posthog-js";
import { PostHogProvider } from "posthog-js/react";

// Only initialize PostHog if not explicitly disabled
if (
  typeof window !== "undefined" &&
  (!env("NEXT_PUBLIC_TELEMETRY_ENABLED") ||
    env("NEXT_PUBLIC_TELEMETRY_ENABLED") !== "false") &&
  process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted"
) {
  posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST,
    person_profiles: "always"
  });
}

export function CSPostHogProvider({ children }) {
  // If PostHog is disabled, just render children without the provider
  if (env("NEXT_PUBLIC_TELEMETRY_ENABLED") === "false") {
    return children;
  }

  return <PostHogProvider client={posthog}>{children}</PostHogProvider>;
}
