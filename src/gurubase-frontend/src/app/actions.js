"use server";

import { getAccessToken, getSession } from "@auth0/nextjs-auth0";
import { redirect } from "next/navigation";

import HttpError from "@/utils/HttpError";

const shouldUsePublicRequest = () => {
  return process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted";
};

const getUserSession = async () => {
  if (process.env.NEXT_PUBLIC_NODE_ENV === "selfhosted") {
    return null;
  }

  return getSession();
};

// Helper function for handling errors
const handleRequestError = (error, context = {}) => {
  console.error("Request failed:", {
    error: error.message,
    stack: error.stack,
    ...context
  });

  if (error.message === "NEXT_REDIRECT") {
    throw error;
  }

  if (
    error.message === "AuthenticationExpired" ||
    error.message.includes("access token expired")
  ) {
    redirect("/api/auth/login", "replace");
  }

  if (error.message.includes("Unauthorized")) {
    return null;
  }

  const errorMessage = error.message.includes('"msg"')
    ? JSON.parse(error.message).msg
    : error.message;

  return { error: true, message: errorMessage };
};

// Helper function for authenticated requests
export const makeAuthenticatedRequest = async (
  url,
  options = {},
  decode = false
) => {
  // Early return for selfhosted mode
  if (shouldUsePublicRequest()) {
    return makePublicRequest(url, options, decode);
  }

  try {
    const session = await getUserSession();

    if (!session?.user) {
      redirect("/api/auth/login", "replace");
    }

    const { accessToken } = await getAccessToken();

    const headers = {
      Authorization: `Bearer ${accessToken}`,
      ...options.headers
    };

    // Extract cache configuration from options or use default no-store
    const { next, cache, ...restOptions } = options;
    const cacheConfig =
      next || (cache !== undefined ? { cache } : { cache: "no-store" });

    const response = await fetch(url, {
      ...restOptions,
      headers,
      ...cacheConfig
    });

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        redirect("/api/auth/login", "replace");
      }
      throw new Error(await response.text());
    }

    if (decode) {
      return await response.json();
    }

    return response;
  } catch (error) {
    if (error.message === "NEXT_REDIRECT") {
      redirect("/api/auth/login", "replace");
    }

    if (
      error.message === "AuthenticationExpired" ||
      error.message.includes("access token expired")
    ) {
      redirect("/api/auth/login", "replace");
    }
    throw error;
  }
};

// Helper for public API requests
export const makePublicRequest = async (url, options = {}, decode = false) => {
  const headers = {
    // "Content-Type": "application/json",
    Authorization: process.env.NEXT_PUBLIC_BACKEND_AUTH_TOKEN,
    ...options.headers
  };

  const response = await fetch(url, {
    ...options,
    headers
  });

  if (response.status === 429) {
    throw new HttpError("Server api rate limiting reached!", response.status);
  }

  if (response.status === 425) {
    throw new HttpError("Reranker model is not available!", response.status);
  }

  if (response.status === 490) {
    throw new HttpError("OpenAI API Key is not valid!", response.status);
  }

  if (!response.ok) {
    let errorDetails;

    try {
      errorDetails = await response.json();
    } catch (e) {
      errorDetails = response.statusText;
    }
    console.error("Error details for url", url, errorDetails, response.status);

    if (errorDetails && typeof errorDetails === "object" && errorDetails.msg) {
      throw new Error(errorDetails.msg);
    }

    throw new Error(`Request failed with status ${response.status}`);
  }

  if (decode) {
    return await response.json();
  }

  return response;
};

// Public API Actions
export async function getAnswerFromMyBackend(
  question,
  guruType,
  bingeId = null
) {
  try {
    const session = await getUserSession();
    const payload = { question };

    if (bingeId) {
      payload.binge_id = bingeId;
    }

    if (session?.user) {
      // Authenticated request
      const response = await makeAuthenticatedRequest(
        `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruType}/summary/`,
        {
          method: "POST",
          body: JSON.stringify(payload),
          headers: {
            "Content-Type": "application/json"
          }
        }
      );

      return await response.json();
    } else {
      // Public request
      const response = await makePublicRequest(
        `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruType}/summary/`,
        {
          method: "POST",
          body: JSON.stringify(payload),
          headers: {
            "Content-Type": "application/json"
          }
        }
      );

      return await response.json();
    }
  } catch (error) {
    return { error: true, message: error.message, status: error.status };
  }
}

export async function fetchDefaultQuestion(guruType) {
  try {
    const response = await makePublicRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruType}/default_questions/`,
      {
        next: { revalidate: 3600 }
      }
    );

    return await response.json();
  } catch (error) {
    return { error: true, message: error.message, status: error.status };
  }
}

// Do not use makePublicRequest for this, it can break the question generation stream
export async function getDataForSlugDetails(
  slug,
  guruType,
  bingeId = null,
  question = ""
) {
  try {
    const session = await getUserSession();
    let url = `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruType}/question/${slug}`;

    // Only add question parameter if it's not empty
    if (question) {
      url += `?question=${question}`;
    }

    // Add bingeId as a query parameter, considering if question was already added
    if (bingeId) {
      url += `${question ? "&" : "?"}binge_id=${bingeId}`;
    }

    if (session?.user) {
      // Authenticated request
      const response = await makeAuthenticatedRequest(url, {
        next: { revalidate: 10 }
      });

      if (!response.ok) {
        const data = await response.json();

        throw new Error(data.msg);
      }

      const data = await response.json();

      return JSON.stringify(data, null, 2);
    } else {
      // Public request
      const response = await makePublicRequest(url, {
        next: { revalidate: 10 }
      });

      if (!response.ok) {
        const data = await response.json();

        throw new Error(data.msg);
      }

      const data = await response.json();

      return JSON.stringify(data, null, 2);
    }
  } catch (error) {
    const errorResponse = { msg: error.message };

    return JSON.stringify(errorResponse, null, 2);
  }
}

export async function getGurutypeResources(guruType) {
  try {
    const response = await makePublicRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruType}/resources/`,
      { next: { revalidate: 3600 } }
    );

    return await response.json();
  } catch (error) {
    return { error: true, message: error.message, status: error.status };
  }
}

export async function getGuruTypes() {
  try {
    const cacheConfig = shouldUsePublicRequest()
      ? { cache: "no-store" }
      : { next: { revalidate: 3600 } };

    const response = await makePublicRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/guru_types/`,
      cacheConfig
    );

    return await response.json();
  } catch (error) {
    return { error: true, message: error.message, status: error.status };
  }
}

export async function getGuruType(slug) {
  try {
    const cacheConfig = shouldUsePublicRequest()
      ? { cache: "no-store" }
      : { next: { revalidate: 3600 } };

    const response = await makePublicRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/guru_type/${slug}/`,
      cacheConfig
    );

    return await response.json();
  } catch (error) {
    return { error: true, message: error.message, status: error.status };
  }
}

export async function checkGuruReadiness(guruName) {
  try {
    const response = await makePublicRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/guru_types/status/${guruName}/`,
      { cache: "no-store" }
    );
    const data = await response.json();

    return data?.ready || false;
  } catch (error) {
    return false;
  }
}

// Authenticated API Actions
export async function getMyGurus() {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/my_gurus/`
    );

    if (!response) return null;
    const data = await response.json();

    return data;
  } catch (error) {
    return handleRequestError(error, {
      url: `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/my_gurus/`
    });
  }
}

export async function getMyGuru(guruSlug) {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/my_gurus/${guruSlug}/`
    );

    if (!response) return null;
    const data = await response.json();

    return data;
  } catch (error) {
    return handleRequestError(error, {
      url: `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/my_gurus/${guruSlug}/`
    });
  }
}

export async function createWidgetId(guruSlug, domainUrl) {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruSlug}/widget_ids/`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain_url: domainUrl })
      }
    );

    if (!response) return null;

    return await response.json();
  } catch (error) {
    return handleRequestError(error, { domainUrl });
  }
}

export async function deleteWidgetId(guruSlug, widgetId) {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruSlug}/widget_ids/`,
      {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ widget_id: widgetId })
      }
    );

    if (!response)
      return {
        success: false,
        message: response.msg || "No response from server"
      };

    if (response.ok) {
      return {
        success: true,
        message: "Widget ID deleted successfully"
      };
    }

    return {
      success: false,
      message: response.msg || "Failed to delete widget ID"
    };
  } catch (error) {
    return handleRequestError(error, { widgetId });
  }
}

export async function getGuruDataSources(customGuru, page = 1) {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${customGuru}/resources/detailed/?page=${page}`
    );

    if (!response) return null;

    return await response.json();
  } catch (error) {
    return handleRequestError(error, { customGuru, page });
  }
}

export async function createGuru(formData) {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/guru_types/create_frontend/`,
      {
        method: "POST",
        body: formData
      }
    );

    if (!response) return null;

    return await response.json();
  } catch (error) {
    return handleRequestError(error);
  }
}

export async function updateGuru(guruSlug, formData) {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/guru_types/update/${guruSlug}/`,
      {
        method: "PUT",
        body: formData
      }
    );

    if (!response) return null;

    return await response.json();
  } catch (error) {
    return handleRequestError(error, { guruSlug });
  }
}

export async function deleteGuru(guruSlug) {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/guru_types/delete/${guruSlug}/`,
      {
        method: "DELETE",
        headers: { "Content-Type": "application/json" }
      }
    );

    if (!response) return null;

    return await response.json();
  } catch (error) {
    return handleRequestError(error, { guruSlug });
  }
}

export async function deleteGuruSources(guruSlug, sourceIds) {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruSlug}/data_sources_frontend/`,
      {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: sourceIds })
      }
    );

    if (!response) return null;

    return { success: true };
  } catch (error) {
    return handleRequestError(error, { guruSlug, sourceIds });
  }
}

export async function reindexGuruSources(guruSlug, sourceIds) {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruSlug}/data_sources_reindex/`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: sourceIds })
      }
    );

    if (!response) return null;

    return { success: true };
  } catch (error) {
    return handleRequestError(error, { guruSlug, sourceIds });
  }
}

export async function addGuruSources(guruSlug, formData) {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruSlug}/data_sources_frontend/`,
      {
        method: "POST",
        body: formData
      }
    );

    if (!response) return null;

    return await response.json();
  } catch (error) {
    return handleRequestError(error, { guruSlug });
  }
}

export async function getSitemapData(slug) {
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${slug}`,
    {
      next: { revalidate: 3600 }
    }
  );

  const data = await res.text();

  return data;
}

export async function getExampleQuestions(
  guruType,
  bingeId,
  slug,
  questionText
) {
  if (!slug) return [];

  try {
    const session = await getUserSession();
    const endpoint = `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruType}/follow_up/examples/`;
    const payload = {
      binge_id: bingeId,
      question_slug: slug,
      question_text: questionText
    };

    const response = session?.user
      ? await makeAuthenticatedRequest(endpoint, {
          cache: "no-store",
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        })
      : await makePublicRequest(endpoint, {
          cache: "no-store",
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

    if (!response || !response.ok) return [];

    const data = await response.json();

    // Ensure we return a valid array of strings
    return Array.isArray(data) ? data : [];
  } catch (error) {
    // console.error("Error fetching example questions:", error);

    return [];
  }
}

export async function createBinge({ guruType, rootSlug }) {
  try {
    const response = await makeAuthenticatedRequest(
      // const response = await makePublicRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruType}/follow_up/binge/`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          root_slug: rootSlug
        })
      }
    );

    if (!response.ok) {
      throw new Error("Failed to initialize binge session");
    }

    const data = await response.json();

    return data.id;
  } catch (error) {
    // console.error("Error initializing binge session:", error);
    return null;
  }
}

export async function getBingeData(guruType, bingeId) {
  try {
    const session = await getUserSession();
    const url = `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruType}/follow_up/graph/?binge_id=${bingeId}`;

    if (session?.user) {
      // Authenticated request
      const response = await makeAuthenticatedRequest(url);
      if (!response) return null;
      return await response.json();
    } else {
      // Public request
      const response = await makePublicRequest(url);
      if (!response) return null;
      return await response.json();
    }
  } catch (error) {
    return handleRequestError(error, { guruType, bingeId });
  }
}

export async function getBingeHistory(page = 1, query = "") {
  try {
    const response = await makeAuthenticatedRequest(
      process.env.NEXT_PUBLIC_BACKEND_FETCH_URL +
        "/binge-history/?page_num=" +
        page +
        "&search_query=" +
        query
    );

    if (response.status === 429) {
      throw new HttpError("Server api rate limitig reached!", response.status);
    }

    if (!response.ok) {
      throw new HttpError(
        `HTTP error! status: ${response.status}`,
        response.status
      );
    }

    const data = await response.json();

    return data;
  } catch (error) {
    return { error: true, message: error.message, status: error.status };
  }
}

export async function getAuthTokenForStream() {
  "use server";
  try {
    const session = await getUserSession();

    if (!session?.user) {
      return null;
    }
    const { accessToken } = await getAccessToken();

    return accessToken;
  } catch (error) {
    console.error("Error getting auth token:", error);

    return null;
  }
}
export const updateGuruDataSourcesPrivacy = async (guruSlug, payload) => {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruSlug}/data_sources/update/`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }
    );

    if (!response.ok) {
      throw new Error("Failed to update data sources privacy");
    }

    return await response.json();
  } catch (error) {
    console.error("Error updating data sources privacy:", error);
  }
};

export async function getApiKeys() {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/api_keys/`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      }
    );

    if (!response) return null;
    return await response.json();
  } catch (error) {
    return handleRequestError(error, {
      context: "getApiKeys"
    });
  }
}

export async function getIntegrationDetails(guruType, integrationType) {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruType}/integrations/${integrationType}/`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      }
    );

    if (!response) return { error: true, message: "No response from server" };

    // Case 1: 202 Accepted - Integration doesn't exist but encoded guru slug is provided
    if (response.status === 202) {
      const data = await response.json();
      return { status: 202, encoded_guru_slug: data.encoded_guru_slug };
    }

    // Case 2: 200 Success - Integration exists
    if (response.ok) {
      return await response.json();
    }

    // Case 3: Any other status - Error
    const errorData = await response.json();
    return {
      error: true,
      message: errorData.msg || "Failed to fetch integration data",
      status: response.status
    };
  } catch (error) {
    return handleRequestError(error, {
      context: "getIntegrationDetails",
      guruType,
      integrationType
    });
  }
}

export async function createApiKey(formData) {
  try {
    const name = formData.get("name");
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/api_keys/`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name })
      }
    );

    if (!response) return null;
    return await response.json();
  } catch (error) {
    return handleRequestError(error, {
      context: "createApiKey",
      name: formData.get("name")
    });
  }
}

export async function deleteApiKey(formData) {
  try {
    const id = formData.get("id");
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/api_keys/`,
      {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: id })
      }
    );

    if (!response) return null;
    return await response.json();
  } catch (error) {
    return handleRequestError(error, {
      context: "deleteApiKey",
      id: formData.get("id")
    });
  }
}

export async function getIntegrationChannels(guruType, integrationType) {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruType}/integrations/${integrationType}/channels/`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      }
    );

    if (!response) return { error: true, message: "No response from server" };

    if (!response.ok) {
      const errorData = await response.json();
      return {
        error: true,
        message: errorData.msg || "Failed to fetch channels",
        status: response.status
      };
    }

    return await response.json();
  } catch (error) {
    return handleRequestError(error, {
      context: "getIntegrationChannels",
      guruType,
      integrationType
    });
  }
}

export async function saveIntegrationChannels(
  guruType,
  integrationType,
  channels
) {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruType}/integrations/${integrationType}/channels/`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channels })
      }
    );

    if (!response) return { error: true, message: "No response from server" };

    if (!response.ok) {
      const errorData = await response.json();
      return {
        error: true,
        message: errorData.msg || "Failed to save channels",
        status: response.status
      };
    }

    return await response.json();
  } catch (error) {
    return handleRequestError(error, {
      context: "saveIntegrationChannels",
      guruType,
      integrationType
    });
  }
}

export async function createIntegration(code, state) {
  try {
    const response = await makePublicRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/integrations/create/?code=${code}&state=${state}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      }
    );

    if (!response) return { error: true, message: "No response from server" };

    if (!response.ok) {
      const errorData = await response.json();
      return {
        error: true,
        message: errorData.msg || "Failed to create integration",
        status: response.status
      };
    }

    return await response.json();
  } catch (error) {
    return handleRequestError(error, {
      context: "createIntegration",
      code,
      state
    });
  }
}

export async function sendIntegrationTestMessage(integrationId, channelId) {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/integrations/test_message/`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          integration_id: integrationId,
          channel_id: channelId
        })
      }
    );

    if (!response) return { error: true, message: "No response from server" };

    if (!response.ok) {
      const errorData = await response.json();
      return {
        error: true,
        message: errorData.msg || "Failed to send test message",
        status: response.status
      };
    }

    return await response.json();
  } catch (error) {
    return handleRequestError(error, {
      context: "sendIntegrationTestMessage",
      integrationId,
      channelId
    });
  }
}

export async function deleteIntegration(guruType, integrationType) {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruType}/integrations/${integrationType}/`,
      {
        method: "DELETE",
        headers: { "Content-Type": "application/json" }
      }
    );

    if (!response) return { error: true, message: "No response from server" };

    if (!response.ok) {
      const errorData = await response.json();
      return {
        error: true,
        message: errorData.msg || "Failed to create integration",
        status: response.status
      };
    }

    return await response.json();
  } catch (error) {
    return handleRequestError(error, {
      context: "deleteIntegration",
      guruType,
      integrationType
    });
  }
}

export async function getIntegrationsList(guruType) {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruType}/integrations/`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      }
    );

    if (!response) return { error: true, message: "No response from server" };

    if (!response.ok) {
      const errorData = await response.json();
      return {
        error: true,
        message: errorData.msg || "Failed to fetch integrations list",
        status: response.status
      };
    }

    return await response.json();
  } catch (error) {
    return handleRequestError(error, {
      context: "getIntegrationsList",
      guruType
    });
  }
}

export async function createSelfhostedIntegration(
  guruType,
  integrationType,
  data
) {
  try {
    const response = await makePublicRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/${guruType}/integrations/${integrationType}/`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workspace_name: data.workspaceName,
          external_id: data.externalId,
          access_token: data.accessToken
        })
      }
    );

    if (!response) return { error: true, message: "No response from server" };

    if (response.ok) {
      return await response.json();
    }

    const errorData = await response.json();
    return {
      error: true,
      message: errorData.msg || "Failed to create integration",
      status: response.status
    };
  } catch (error) {
    return handleRequestError(error, {
      context: "createSelfhostedIntegration",
      guruType,
      data
    });
  }
}

export async function getSettings() {
  try {
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/settings/`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      }
    );

    if (!response) return null;
    return await response.json();
  } catch (error) {
    return handleRequestError(error, {
      context: "getSettings"
    });
  }
}

export async function updateSettings(formData) {
  try {
    const openai_api_key = formData.get("openai_api_key");
    const firecrawl_api_key = formData.get("firecrawl_api_key");
    const scrape_type = formData.get("scrape_type");
    const response = await makeAuthenticatedRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/settings/`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          openai_api_key,
          firecrawl_api_key,
          scrape_type
        })
      }
    );

    if (!response) return null;
    return await response.json();
  } catch (error) {
    return handleRequestError(error, {
      context: "updateSettings"
    });
  }
}

export async function parseSitemapUrls(sitemapUrl) {
  try {
    const response = await makePublicRequest(
      `${process.env.NEXT_PUBLIC_BACKEND_FETCH_URL}/parse_sitemap/`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sitemap_url: sitemapUrl })
      }
    );

    if (!response) return { error: true, message: "No response from server" };

    const data = await response.json();
    return data;
  } catch (error) {
    return handleRequestError(error, {
      context: "parseSitemapUrls",
      sitemapUrl
    });
  }
}
