"use client";

import { useActionState, useMemo } from "react";
import { generateMetricExplanationAction } from "@/app/actions";
import type {
  MetricExplanationActionState,
  MetricKey,
  SimilarPressRelease,
} from "@/lib/fastapi/types";
import { METRIC_LABELS } from "./MetricSelector";

type MetricExplanationProps = {
  releases: SimilarPressRelease[];
  metric: MetricKey;
};

const INITIAL_STATE: MetricExplanationActionState = { status: "idle" };

function SparkIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2.8c.4 5.3 3 8 8.2 8.4-5.2.4-7.8 3.1-8.2 8.4-.4-5.3-3-8-8.2-8.4C9 10.8 11.6 8.1 12 2.8Z" />
      <path d="M19.2 16.4c.1 2.1 1.1 3.1 3.1 3.3-2 .2-3 1.2-3.1 3.3-.2-2.1-1.2-3.1-3.2-3.3 2-.2 3-1.2 3.2-3.3Z" />
    </svg>
  );
}

export function MetricExplanation({
  releases,
  metric,
}: MetricExplanationProps) {
  const [state, formAction, isPending] = useActionState(
    generateMetricExplanationAction,
    INITIAL_STATE,
  );
  const context = useMemo(
    () =>
      JSON.stringify({
        metric,
        releases: releases.map((release) => ({
          createdAt: release.created_at,
          value: release[metric],
        })),
      }),
    [metric, releases],
  );
  const currentState =
    state.status !== "idle" && state.requestKey === context ? state : INITIAL_STATE;
  const hasExplanation = currentState.status === "success";

  return (
    <section className="metric-explanation" aria-labelledby="explanation-title">
      <div className="metric-explanation__header">
        <div className="metric-explanation__identity">
          <span className="metric-explanation__icon"><SparkIcon /></span>
          <div>
            <span className="metric-explanation__eyebrow">
              ENGINEERING INSIGHT <span>AI生成</span>
            </span>
            <h4 id="explanation-title">数値の読み解きメモ</h4>
          </div>
        </div>

        <form action={formAction}>
          <input type="hidden" name="context" value={context} />
          <button
            type="submit"
            className="explanation-button"
            disabled={isPending}
          >
            {isPending ? (
              <>
                <span className="spinner" aria-hidden="true" />
                読み解いています…
              </>
            ) : (
              <>
                {hasExplanation ? "もう一度生成" : "この比較を読み解く"}
                <span aria-hidden="true">↗</span>
              </>
            )}
          </button>
        </form>
      </div>

      {isPending ? (
        <div className="explanation-loading" role="status" aria-live="polite">
          <span />
          <span />
          <span />
          <p>公開日時と{METRIC_LABELS[metric]}の関係を整理しています</p>
        </div>
      ) : currentState.status === "success" ? (
        <div className="explanation-copy" aria-live="polite">
          {currentState.content}
        </div>
      ) : currentState.status === "error" ? (
        <div className="explanation-error" role="alert">
          <span aria-hidden="true">!</span>
          <p>{currentState.message}</p>
        </div>
      ) : (
        <div className="explanation-empty">
          <p>
            上のグラフを、数字に詳しくない人にも伝わる言葉へ変換します。
            公開日時による条件の違いにも触れながら、数値から言える範囲を整理します。
          </p>
          <div className="explanation-flow" aria-label="解説に使う情報">
            <span>公開日時</span>
            <i aria-hidden="true">＋</i>
            <span>{METRIC_LABELS[metric]}</span>
            <i aria-hidden="true">＋</i>
            <span>指標の値</span>
            <i aria-hidden="true">→</i>
            <strong>やさしい解説</strong>
          </div>
        </div>
      )}

      <p className="metric-explanation__note">
        入力された比較データのみをもとに生成します。数値は原因や成果を断定するものではありません。
      </p>
    </section>
  );
}
