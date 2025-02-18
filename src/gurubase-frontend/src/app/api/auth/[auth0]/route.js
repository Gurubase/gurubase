import { handleAuth, handleCallback } from "@auth0/nextjs-auth0";
import { redirect } from "next/navigation";

const authHandler = handleAuth();

export const GET = async (req, ctx) => {
  if (process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted") {
    return redirect("/not-found");
  }

  const { searchParams } = new URL(req.url);
  const error = searchParams.get("error");
  const errorDescription = searchParams.get("error_description");

  // If this is a callback request with an error, redirect to show error modal
  if (ctx.params.auth0 === "callback" && error) {
    const errorParams = new URLSearchParams({
      error,
      error_description: errorDescription || ""
    }).toString();
    return redirect(`/auth/error?${errorParams}`);
  }

  return authHandler(req, ctx);
};
