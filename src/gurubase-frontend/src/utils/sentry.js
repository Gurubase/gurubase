import * as Sentry from "@sentry/nextjs";

export const reportErrorToSentry = async (error, context) => {
  try {
    const errorObject = new Error(error);

    Sentry.captureException(errorObject, {
      tags: {
        ...context,
        environment: process.env.NEXT_PUBLIC_NODE_ENV
      }
    });
  } catch (error) {
    // console.error("[Sentry] Failed to report error:", error);
  }
};
