"use client";

import { useActionState, useState } from "react";
import { searchPressReleaseAction } from "@/app/actions";
import type { SearchActionState } from "@/lib/fastapi/types";
import { SearchResults } from "./SearchResults";

const MAX_LENGTH = 2000;
const INITIAL_STATE: SearchActionState = { status: "idle" };

export function DraftForm() {
  const [query, setQuery] = useState("");
  const [state, formAction, isPending] = useActionState(
    searchPressReleaseAction,
    INITIAL_STATE,
  );
  const canSubmit = query.trim().length > 0 && !isPending;

  return (
    <>
      <section className="search-card" aria-labelledby="search-heading">
        <form action={formAction}>
          <div className="search-card__header">
            <div>
              <span className="section-index">01 / SEARCH</span>
              <h2 id="search-heading">類似プレスリリースを探す</h2>
            </div>
            <p>
              リード文の内容が具体的であるほど、
              <br />
              より近い事例を見つけやすくなります。
            </p>
          </div>

          <div className="field-group">
            <label htmlFor="lead-query">作成中のリード文</label>
            <textarea
              id="lead-query"
              name="query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              maxLength={MAX_LENGTH}
              rows={7}
              placeholder="例）株式会社〇〇は、新しい働き方を支援する法人向けサービスを本日より提供開始します…"
              aria-describedby="query-help query-count"
              aria-invalid={state.status === "error"}
              disabled={isPending}
            />
            <div className="field-meta">
              <span id="query-help">最大2,000文字まで入力できます</span>
              <span
                id="query-count"
                className={query.length >= 1900 ? "character-count is-near-limit" : "character-count"}
                aria-live="polite"
              >
                <strong>{query.length.toLocaleString("ja-JP")}</strong> / 2,000
              </span>
            </div>
          </div>

          {state.status === "error" && (
            <div className="error-message" role="alert">
              <span className="error-message__icon" aria-hidden="true">!</span>
              <div>
                <strong>検索できませんでした</strong>
                <span>{state.message}</span>
              </div>
            </div>
          )}

          <div className="form-submit-row">
            <span className="form-note">
              入力内容は類似検索にのみ使用されます
            </span>
            <button className="search-button" type="submit" disabled={!canSubmit}>
              {isPending ? (
                <>
                  <span className="spinner" aria-hidden="true" />
                  検索しています…
                </>
              ) : (
                <>
                  類似プレスリリースを検索
                  <svg viewBox="0 0 20 20" aria-hidden="true">
                    <path d="M4 10h11M11 5l5 5-5 5" />
                  </svg>
                </>
              )}
            </button>
          </div>
        </form>
      </section>

      {isPending && (
        <div className="searching-status" role="status" aria-live="polite">
          <span className="searching-status__pulse" />
          <span>過去のプレスリリースから、意味の近い事例を探しています</span>
        </div>
      )}

      {!isPending && state.status === "success" ? (
        <SearchResults
          key={`${state.response.query}-${state.response.data.length}`}
          response={state.response}
        />
      ) : (
        !isPending && state.status === "idle" && <InitialGuide />
      )}
    </>
  );
}

function InitialGuide() {
  return (
    <section className="initial-guide" aria-label="利用の流れ">
      <div className="initial-guide__intro">
        <span className="section-index">HOW IT WORKS</span>
        <h2>過去の成功事例を、<br />次の一手に。</h2>
      </div>
      <ol>
        <li>
          <span className="guide-number">01</span>
          <div>
            <h3>リード文を入力</h3>
            <p>作成中の原稿をそのまま貼り付けます。</p>
          </div>
        </li>
        <li>
          <span className="guide-number">02</span>
          <div>
            <h3>類似事例を発見</h3>
            <p>意味の近いプレスリリースを5件表示します。</p>
          </div>
        </li>
        <li>
          <span className="guide-number">03</span>
          <div>
            <h3>反響を比較</h3>
            <p>閲覧数・ユーザー数・Like数を見比べられます。</p>
          </div>
        </li>
      </ol>
    </section>
  );
}
