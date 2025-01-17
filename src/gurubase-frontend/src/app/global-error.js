"use client";

import * as Sentry from "@sentry/nextjs";
import Error from "next/error";
import { useEffect } from "react";

export default function GlobalError({ error }) {
  let statusCode = error.statusCode;
  let errorMessage = "An unexpected error occurred";

  if (
    statusCode === 500 ||
    (error instanceof SyntaxError &&
      error.message.includes("is not valid JSON"))
  ) {
    statusCode = 404;
    errorMessage = "Bad Request: Invalid JSON received";
  }

  useEffect(() => {
    if (
      process.env.NEXT_PUBLIC_SENTRY_AUTH_TOKEN &&
      process.env.NEXT_PUBLIC_NODE_ENV === "production"
    ) {
      Sentry.captureException(error);
    }
  }, [error]);

  return (
    <html>
      <body>
        <Error statusCode={statusCode} title={errorMessage} />
      </body>
    </html>
  );
}
