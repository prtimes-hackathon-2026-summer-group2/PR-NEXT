"use client";

import { useMemo, useState } from "react";
import type {
  MetricKey,
  PressReleaseSearchResponse,
} from "@/lib/fastapi/types";
import { MetricComparison } from "./MetricComparison";
import { MetricExplanation } from "./MetricExplanation";
import { MetricSelector } from "./MetricSelector";
import { PressReleaseDetail } from "./PressReleaseDetail";
import { SimilarPressReleaseList } from "./SimilarPressReleaseList";

type SearchResultsProps = {
  response: PressReleaseSearchResponse;
};

export function SearchResults({ response }: SearchResultsProps) {
  const releases = useMemo(() => response.data.slice(0, 5), [response.data]);
  const [selectedKey, setSelectedKey] = useState(() =>
    releases[0] ? `${releases[0].company_id}:${releases[0].release_id}` : "",
  );
  const [selectedMetric, setSelectedMetric] = useState<MetricKey>("page_view");

  const selectedRelease =
    releases.find(
      (release) => `${release.company_id}:${release.release_id}` === selectedKey,
    ) ?? releases[0];

  return (
    <section className="results" aria-labelledby="results-heading">
      <div className="results__heading">
        <div>
          <span className="section-index">02 / RESULTS</span>
          <h2 id="results-heading">検索結果</h2>
        </div>
        <div className="results__summary">
          <strong>{response.hits.toLocaleString("ja-JP")}</strong>
          <span>件の類似事例を取得</span>
        </div>
      </div>

      {releases.length === 0 ? (
        <div className="empty-result">
          <span className="empty-result__mark" aria-hidden="true">0</span>
          <div>
            <h3>類似するプレスリリースが見つかりませんでした</h3>
            <p>入力内容を変えて、もう一度検索してください。</p>
          </div>
        </div>
      ) : (
        <div className="dashboard">
          <SimilarPressReleaseList
            releases={releases}
            selectedKey={selectedKey}
            onSelect={setSelectedKey}
          />

          <div className="dashboard__main">
            <section className="metric-panel" aria-labelledby="metric-title">
              <div className="panel-heading">
                <div>
                  <span className="panel-heading__label">METRIC COMPARISON</span>
                  <h3 id="metric-title">指標比較</h3>
                </div>
                <MetricSelector
                  selectedMetric={selectedMetric}
                  onChange={setSelectedMetric}
                />
              </div>
              <MetricComparison releases={releases} metric={selectedMetric} />
              <MetricExplanation releases={releases} metric={selectedMetric} />
            </section>

            {selectedRelease && (
              <PressReleaseDetail release={selectedRelease} />
            )}
          </div>
        </div>
      )}
    </section>
  );
}
