import type { MetricKey } from "@/lib/fastapi/types";

export const METRIC_LABELS: Record<MetricKey, string> = {
  page_view: "ページ閲覧数",
  unique_user: "ユニークユーザー数",
  like_count: "Like数",
};

type MetricSelectorProps = {
  selectedMetric: MetricKey;
  onChange: (metric: MetricKey) => void;
};

export function MetricSelector({
  selectedMetric,
  onChange,
}: MetricSelectorProps) {
  return (
    <div className="metric-selector" aria-label="比較指標">
      {(Object.keys(METRIC_LABELS) as MetricKey[]).map((metric) => (
        <button
          key={metric}
          type="button"
          className={selectedMetric === metric ? "is-active" : ""}
          onClick={() => onChange(metric)}
          aria-pressed={selectedMetric === metric}
        >
          {METRIC_LABELS[metric]}
        </button>
      ))}
    </div>
  );
}
