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
    times: payload.times || undefined // Only include times if it exists
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
      body: JSON.stringify(requestPayload) // Use the modified payload
    });
  } else if (authenticated) {
    response = await fetch(streamURL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(requestPayload), // Use the modified payload
      cache: "no-store"
    });
  } else {
    response = await fetch(streamURL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwtToken}`
      },
      body: JSON.stringify(requestPayload) // Use the modified payload
    });
  }

  return response;
}

// Analytics Functions
export async function getAnalyticsStats(guruType, interval) {
  "use client";
  const token = await getAuthTokenForStream();
  const authenticated = token ? token.trim().length > 0 : false;
  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";

  let response;
  const url = `${BACKEND_FETCH_URL}/analytics/${guruType}/stats?interval=${interval}`;

  if (isSelfHosted) {
    const headers = {
      "Content-Type": "application/json"
    };

    response = await fetch(url, {
      method: "GET",
      headers
    });
  } else if (authenticated) {
    response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      cache: "no-store"
    });
  } else {
    throw new Error("Authentication required");
  }

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const data = await response.json();

  return data.data;
}

export async function getAnalyticsHistogram(guruType, metricType, interval) {
  "use client";
  const token = await getAuthTokenForStream();
  const authenticated = token ? token.trim().length > 0 : false;
  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";

  let response;
  const url = `${BACKEND_FETCH_URL}/analytics/${guruType}/histogram?metric_type=${metricType}&interval=${interval}`;

  if (isSelfHosted) {
    const headers = {
      "Content-Type": "application/json"
    };

    response = await fetch(url, {
      method: "GET",
      headers
    });
  } else if (authenticated) {
    response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      cache: "no-store"
    });
  } else {
    throw new Error("Authentication required");
  }

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const data = await response.json();

  return data.data;
}

export async function getAnalyticsTable(
  guruType,
  metricType,
  interval,
  filterType,
  page,
  searchQuery = "",
  sortOrder = "desc",
  timeRange = null
) {
  "use client";
  const token = await getAuthTokenForStream();
  const authenticated = token ? token.trim().length > 0 : false;
  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";

  const startTime = timeRange ? timeRange.startTime : null;
  const endTime = timeRange ? timeRange.endTime : null;

  const params = new URLSearchParams({
    metric_type: metricType,
    interval,
    filter_type: filterType,
    page: page.toString(),
    search: searchQuery,
    sort_order: sortOrder
  });

  if (startTime) {
    params.append("start_time", startTime);
  }
  if (endTime) {
    params.append("end_time", endTime);
  }

  let response;
  const url = `${BACKEND_FETCH_URL}/analytics/${guruType}/table?${params}`;

  if (isSelfHosted) {
    const headers = {
      "Content-Type": "application/json"
    };

    response = await fetch(url, {
      method: "GET",
      headers
    });
  } else if (authenticated) {
    response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      cache: "no-store"
    });
  } else {
    throw new Error("Authentication required");
  }

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

export async function getAnalyticsDataSourceQuestions(
  guruType,
  url,
  filterType,
  interval,
  page,
  searchQuery = "",
  sortOrder = "desc"
) {
  "use client";
  const token = await getAuthTokenForStream();
  const authenticated = token ? token.trim().length > 0 : false;
  const isSelfHosted = process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";

  const params = new URLSearchParams({
    url: url,
    filter_type: filterType,
    interval: interval,
    page: page.toString(),
    search: searchQuery,
    sort_order: sortOrder
  });

  let response;
  const apiUrl = `${BACKEND_FETCH_URL}/analytics/${guruType}/data-source-questions?${params}`;

  if (isSelfHosted) {
    const headers = {
      "Content-Type": "application/json"
    };

    response = await fetch(apiUrl, {
      method: "GET",
      headers
    });
  } else if (authenticated) {
    response = await fetch(apiUrl, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      cache: "no-store"
    });
  } else {
    throw new Error("Authentication required");
  }

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}
