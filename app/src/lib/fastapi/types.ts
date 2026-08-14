export type PressReleaseSearchResponse = {
  query: string;
  top_n: number;
  hits: number;
  data: SimilarPressRelease[];
};

export type SimilarPressRelease = {
  company_id: number;
  release_id: number;
  similarity_score: number;
  title: string;
  subtitle: string;
  lead_paragraph: string;
  created_at: string;
  company_name: string;
  industry: string;
  page_view: number;
  unique_user: number;
  like_count: number;
  business_categories: string[];
  keywords: string[];
};

export type ValidationErrorResponse = {
  detail: {
    loc: Array<string | number>;
    msg: string;
    type: string;
    input?: unknown;
    ctx?: Record<string, unknown>;
  }[];
};

export type LlmCompletionMessage = {
  role: "system" | "user";
  content: string;
};

export type LlmCompletionResponse = {
  content: string;
  usage?: {
    model?: string;
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
};

export type MetricKey = "page_view" | "unique_user" | "like_count";

export type SearchActionState =
  | { status: "idle" }
  | { status: "success"; response: PressReleaseSearchResponse }
  | { status: "error"; message: string; query: string };

export type MetricExplanationActionState =
  | { status: "idle" }
  | { status: "success"; content: string; requestKey: string }
  | { status: "error"; message: string; requestKey: string };
