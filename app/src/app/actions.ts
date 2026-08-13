"use server";

import {
  FastApiRequestError,
  searchPressReleases,
} from "@/lib/fastapi/client";
import type { SearchActionState } from "@/lib/fastapi/types";

const MAX_QUERY_LENGTH = 2000;

export async function searchPressReleaseAction(
  _previousState: SearchActionState,
  formData: FormData,
): Promise<SearchActionState> {
  const value = formData.get("query");
  const query = typeof value === "string" ? value : "";

  if (!query.trim()) {
    return {
      status: "error",
      message: "リード文を入力してください。",
      query,
    };
  }

  if (query.length > MAX_QUERY_LENGTH) {
    return {
      status: "error",
      message: "リード文は2,000文字以内で入力してください。",
      query,
    };
  }

  try {
    const response = await searchPressReleases(query.trim());
    return { status: "success", response };
  } catch (error) {
    if (error instanceof FastApiRequestError && error.kind === "validation") {
      return {
        status: "error",
        message: "入力内容を確認してください。",
        query,
      };
    }

    return {
      status: "error",
      message: "類似プレスリリースの検索に失敗しました。もう一度お試しください。",
      query,
    };
  }
}
