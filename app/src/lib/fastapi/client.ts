import "server-only";

import type {
  LlmCompletionMessage,
  LlmCompletionResponse,
  PressReleaseSearchResponse,
} from "./types";

const SEARCH_PATH = "/press-release/search";
const LLM_COMPLETION_PATH = "/llm/completion";
const TOP_N = 5;

export class FastApiRequestError extends Error {
  constructor(
    public readonly kind: "validation" | "request",
    message: string,
  ) {
    super(message);
    this.name = "FastApiRequestError";
  }
}

function isSearchResponse(value: unknown): value is PressReleaseSearchResponse {
  if (!value || typeof value !== "object") return false;

  const response = value as Partial<PressReleaseSearchResponse>;
  return (
    typeof response.query === "string" &&
    typeof response.top_n === "number" &&
    typeof response.hits === "number" &&
    Array.isArray(response.data)
  );
}

function isLlmCompletionResponse(
  value: unknown,
): value is LlmCompletionResponse {
  if (!value || typeof value !== "object") return false;

  const response = value as Partial<LlmCompletionResponse>;
  return (
    typeof response.content === "string" && response.content.trim().length > 0
  );
}

function createEndpoint(path: string) {
  const baseUrl = process.env.FASTAPI_URL;

  if (!baseUrl) {
    throw new FastApiRequestError(
      "request",
      "FASTAPI_URL is not configured.",
    );
  }

  try {
    return new URL(path, baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`);
  } catch {
    throw new FastApiRequestError("request", "FASTAPI_URL is invalid.");
  }
}

export async function searchPressReleases(
  query: string,
): Promise<PressReleaseSearchResponse> {
  const endpoint = createEndpoint(SEARCH_PATH);

  endpoint.search = new URLSearchParams({
    query,
    top_n: String(TOP_N),
  }).toString();

  let response: Response;
  try {
    response = await fetch(endpoint, {
      method: "GET",
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
  } catch {
    throw new FastApiRequestError("request", "FastAPI request failed.");
  }

  if (response.status === 422) {
    throw new FastApiRequestError("validation", "FastAPI validation failed.");
  }

  if (!response.ok) {
    throw new FastApiRequestError("request", `FastAPI returned ${response.status}.`);
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new FastApiRequestError("request", "FastAPI returned invalid JSON.");
  }

  if (!isSearchResponse(body)) {
    throw new FastApiRequestError("request", "FastAPI response shape is invalid.");
  }

  return body;
}

export async function generateLlmCompletion(
  messages: LlmCompletionMessage[],
): Promise<LlmCompletionResponse> {
  const endpoint = createEndpoint(LLM_COMPLETION_PATH);

  let response: Response;
  try {
    response = await fetch(endpoint, {
      method: "POST",
      cache: "no-store",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        messages,
        generation_params: {
          reasoning_effort: null,
          temperature: null,
          top_p: null,
          max_tokens: null,
        },
      }),
    });
  } catch {
    throw new FastApiRequestError("request", "LLM request failed.");
  }

  if (response.status === 422) {
    throw new FastApiRequestError("validation", "LLM validation failed.");
  }

  if (!response.ok) {
    throw new FastApiRequestError("request", `FastAPI returned ${response.status}.`);
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new FastApiRequestError("request", "FastAPI returned invalid JSON.");
  }

  if (!isLlmCompletionResponse(body)) {
    throw new FastApiRequestError("request", "LLM response shape is invalid.");
  }

  return body;
}
