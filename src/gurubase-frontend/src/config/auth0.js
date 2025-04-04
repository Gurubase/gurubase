import { initAuth0 } from "@auth0/nextjs-auth0";

export const auth0 = initAuth0({
  session: {
    // This config makes the session cookie to be valid for 3 days.
    // Each auth0 interaction will refresh the cookie for another 3 days, up to total 30 days.
    rolling: true,
    rollingDuration: 604800, // 7 days in seconds
    absoluteDuration: 2592000 // 30 days in seconds
  }
});
