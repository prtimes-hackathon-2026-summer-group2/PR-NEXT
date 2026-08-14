"use server";

import {
  FastApiRequestError,
  generateLlmCompletion,
  searchPressReleases,
} from "@/lib/fastapi/client";
import type {
  MetricExplanationActionState,
  MetricKey,
  SearchActionState,
} from "@/lib/fastapi/types";

const MAX_QUERY_LENGTH = 2000;
const MAX_EXPLANATION_CONTEXT_LENGTH = 4000;
const METRIC_DETAILS: Record<
  MetricKey,
  { label: string; unit: string; description: string }
> = {
  page_view: {
    label: "ページ閲覧数",
    unit: "回",
    description:
      "ページが表示された延べ回数です。同じ人が複数回見た場合は、その分も数えられるため、見た人数そのものではありません",
  },
  unique_user: {
    label: "ユニークユーザー数",
    unit: "人",
    description:
      "同じ人による複数回の閲覧を原則として1人と数えた、ページを見た人数の目安です",
  },
  like_count: {
    label: "Like数",
    unit: "回",
    description:
      "読者がLikeボタンで反応した回数です。閲覧者全体の満足度や支持率そのものではありません",
  },
};

type MetricExplanationContext = {
  metric: MetricKey;
  releases: Array<{
    createdAt: string;
    value: number;
  }>;
};

function isMetricExplanationContext(
  value: unknown,
): value is MetricExplanationContext {
  if (!value || typeof value !== "object") return false;

  const context = value as Partial<MetricExplanationContext>;
  if (
    !context.metric ||
    !Object.prototype.hasOwnProperty.call(METRIC_DETAILS, context.metric) ||
    !Array.isArray(context.releases) ||
    context.releases.length < 1 ||
    context.releases.length > 5
  ) {
    return false;
  }

  return context.releases.every(
    (release) =>
      release &&
      typeof release === "object" &&
      typeof release.createdAt === "string" &&
      release.createdAt.trim().length > 0 &&
      release.createdAt.length <= 100 &&
      !Number.isNaN(Date.parse(release.createdAt)) &&
      typeof release.value === "number" &&
      Number.isSafeInteger(release.value) &&
      release.value >= 0,
  );
}

function buildMetricExplanationMessages(context: MetricExplanationContext) {
  const metric = METRIC_DETAILS[context.metric];
  const data = context.releases
    .map(
      (release, index) =>
        `事例${index + 1}｜公開日時: ${release.createdAt}｜${metric.label}: ${release.value.toLocaleString("ja-JP")}${metric.unit}`,
    )
    .join("\n");

  return [
    {
      role: "system" as const,
      content: [
        "あなたは、広報の数値を、データや統計の知識がない一般の読者に説明する案内役です。",
        "目的は、読者が指標の意味、今回の値が示す事実、数値だけでは判断できないことを区別して理解できるようにすることです。",
        "入力された指標の説明と比較データだけを根拠にしてください。外部の平均値、評価基準、背景情報は補わないでください。",
        "最初に、指標が何を数えたものかを日常語で説明してください。人数と延べ回数を混同せず、値の単位も示してください。",
        "事例が複数ある場合は、最大と最小の事例と値を示し、差を実数で説明してください。すべて同じ値なら、大小の差がないと伝えてください。必要なら他の目立つ違いにも1つだけ触れてください。各事例の名前は入力どおり『事例1』のように表してください。",
        "『高い』『低い』は今回の事例同士の比較に限って使い、一般的な水準より高い・低いとは評価しないでください。割合や点数に変換しないでください。",
        "値が大きい理由、施策の効果、プレスリリースの良し悪し、公開日時との因果関係を推測・断定しないでください。",
        "公開日時が異なる場合は、集計期間などの測定条件が同じとは限らず、公平な成果比較や時系列の傾向判断はできないと、やさしく説明してください。",
        "出力は『この指標は何？』『今回の数値を読むと』『読み取れないこと・注意点』の順に、見出しと本文だけで構成してください。全体は320〜450文字を目安にします。",
        "中学生でも一度で理解できる短い文を使ってください。Markdown記号、箇条書き、表、前置き、総括は使わないでください。専門用語は避け、必要な場合は直後に意味を添えてください。",
      ].join("\n"),
    },
    {
      role: "user" as const,
      content: [
        `指標: ${metric.label}`,
        `単位: ${metric.unit}`,
        `指標の意味: ${metric.description}。`,
        "<比較データ>",
        data,
        "</比較データ>",
        "上記の指標と値が何を意味するかを、指定された読者と形式に沿って解説してください。",
      ].join("\n"),
    },
  ];
}

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

export async function generateMetricExplanationAction(
  _previousState: MetricExplanationActionState,
  formData: FormData,
): Promise<MetricExplanationActionState> {
  const value = formData.get("context");
  const requestKey = typeof value === "string" ? value : "";

  if (!requestKey || requestKey.length > MAX_EXPLANATION_CONTEXT_LENGTH) {
    return {
      status: "error",
      message: "比較データを確認できませんでした。もう一度お試しください。",
      requestKey,
    };
  }

  let context: unknown;
  try {
    context = JSON.parse(requestKey);
  } catch {
    return {
      status: "error",
      message: "比較データの形式が正しくありません。",
      requestKey,
    };
  }

  if (!isMetricExplanationContext(context)) {
    return {
      status: "error",
      message: "解説に必要な日時または指標の値を確認できませんでした。",
      requestKey,
    };
  }

  try {
    const response = await generateLlmCompletion(
      buildMetricExplanationMessages(context),
    );
    return {
      status: "success",
      content: response.content.trim(),
      requestKey,
    };
  } catch (error) {
    const message =
      error instanceof FastApiRequestError && error.kind === "validation"
        ? "解説用データをAPIが受け付けられませんでした。"
        : "解説の生成に失敗しました。時間をおいてもう一度お試しください。";

    return { status: "error", message, requestKey };
  }
}
