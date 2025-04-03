import { initAuth0 } from "@auth0/nextjs-auth0";
import { redirect } from "next/navigation";

const auth0 = initAuth0({
  session: {
    // This config makes the session cookie to be valid for 3 days.
    // Each auth0 interaction will refresh the cookie for another 3 days, up to total 30 days.
    rolling: true,
    rollingDuration: 259200, // 3 days in seconds
    absoluteDuration: 2592000 // 30 days in seconds
  }
});

const authHandler = auth0.handleAuth({
  // Add prompt=login parameter to prevent Auth0 to use the previous session.
  // Could have also used federated=True while logging out, but this logs the user out from their own identity provider.
  login: auth0.handleLogin({ authorizationParams: { prompt: "login" } })
});

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
