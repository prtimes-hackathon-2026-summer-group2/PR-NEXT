import type { MetricKey, SimilarPressRelease } from "@/lib/fastapi/types";
import { METRIC_LABELS } from "./MetricSelector";

type MetricComparisonProps = {
  releases: SimilarPressRelease[];
  metric: MetricKey;
};

export function MetricComparison({ releases, metric }: MetricComparisonProps) {
  const maximum = Math.max(...releases.map((release) => release[metric]), 0);

  return (
    <div className="metric-chart">
      <div className="metric-chart__axis">
        <span>{METRIC_LABELS[metric]}</span>
        <span>Top 5 comparison</span>
      </div>
      <div className="metric-chart__rows">
        {releases.map((release, index) => {
          const value = release[metric];
          const width = maximum > 0 ? (value / maximum) * 100 : 0;
          return (
            <div className="metric-row" key={`${release.company_id}:${release.release_id}`}>
              <div className="metric-row__label">
                <span>#{index + 1}</span>
                <span title={release.title}>{release.company_name}</span>
              </div>
              <div className="metric-row__visual">
                <div className="metric-row__track">
                  <span
                    className="metric-row__bar"
                    style={{ width: `${width}%` }}
                  />
                </div>
                <strong>{value.toLocaleString("ja-JP")}</strong>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
