import { getAuthTokenForStream } from "@/app/actions";

// Create a constant for the auth token at the top of the file
const BACKEND_AUTH_TOKEN =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_BACKEND_AUTH_TOKEN
    : "";
const BACKEND_FETCH_URL =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_BACKEND_FETCH_URL_CLIENT
    : "";
const PAGE_VISIT_MODULE =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_PAGE_VISIT_MODULE
    : "";

export async function recordVote(contentSlug, fingerprint, voteType, guruType) {
  const headers = {
    "Content-Type": "application/json",
    Authorization: BACKEND_AUTH_TOKEN
  };

  const response = await fetch(
    `${BACKEND_FETCH_URL}/${guruType}/record_vote/`,
    {
      method: "POST",
      headers: headers,
      body: JSON.stringify({
        content_slug: contentSlug,
        fingerprint: fingerprint,
        vote_type: voteType
      })
    }
  );

  // Check if the response status is not OK
  if (!response.ok) {
    throw new Error(
      `HTTP error! Status: ${response.status} ${response.statusText}`
    );
  }

  const contentLength = response.headers.get("content-length");

  if (contentLength === "0") {
    return { message: "No content in response" };
  }

  // Attempt to parse the response as JSON
  try {
    const result = await response.json();

    return result;
  } catch (error) {
    // If parsing fails, handle it gracefully
    throw new Error(
      "Failed to parse response as JSON. Response might be empty or invalid."
    );
  }
}

export async function recordVisit(guruType, contentSlug, fingerprint) {
  if (PAGE_VISIT_MODULE !== "true") {
    return { message: "Page visit module is disabled" };
  }

  const headers = {
    "Content-Type": "application/json",
    Authorization: BACKEND_AUTH_TOKEN
  };

  const response = await fetch(
    `${BACKEND_FETCH_URL}/${guruType}/record_visit/`,
    {
      method: "POST",
      headers: headers,
      body: JSON.stringify({
        content_slug: contentSlug,
        fingerprint: fingerprint
      })
    }
  );

  if (!response.ok) {
    throw new Error(
      `HTTP error! Status: ${response.status} ${response.statusText}`
    );
  }

  const contentLength = response.headers.get("content-length");

  if (contentLength === "0") {
    return { message: "No content in response" };
  }

  // Attempt to parse the response as JSON
  try {
    const result = await response.json();

    return result;
  } catch (error) {
    // If parsing fails, handle it gracefully
    throw new Error(
      "Failed to parse response as JSON. Response might be empty or invalid."
    );
  }
}

export async function getStream(payload, guruType, jwtToken = null) {
  "use client";

  const streamURL = `${BACKEND_FETCH_URL}/${guruType}/answer/`;
  // Get fresh token from server action
  const token = await getAuthTokenForStream();

  const authenticated = token ? token.trim().length > 0 : false;
  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";

  // Include times in the payload if it exists
  const requestPayload = {
    ...payload,
    times: payload.times || undefined  // Only include times if it exists
  };

  let response;

  if (isSelfHosted) {
    // Get CSRF token from cookies only for self-hosted environment
    const csrfToken = document.cookie
      .split("; ")
      .find((row) => row.startsWith("csrftoken="))
      ?.split("=")[1];

    const headers = {
      "Content-Type": "application/json",
      ...(csrfToken && { "X-CSRFToken": csrfToken })
    };

    response = await fetch(streamURL, {
      method: "POST",
      headers,
      body: JSON.stringify(requestPayload)  // Use the modified payload
    });
  } else if (authenticated) {
    response = await fetch(streamURL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(requestPayload),  // Use the modified payload
      cache: "no-store"
    });
  } else {
    response = await fetch(streamURL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwtToken}`
      },
      body: JSON.stringify(requestPayload)  // Use the modified payload
    });
  }

  return response;
}
