import type { SimilarPressRelease } from "@/lib/fastapi/types";

type SimilarPressReleaseCardProps = {
  release: SimilarPressRelease;
  rank: number;
  isSelected: boolean;
  onSelect: () => void;
};

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone: "Asia/Tokyo",
  }).format(date);
}

export function SimilarPressReleaseCard({
  release,
  rank,
  isSelected,
  onSelect,
}: SimilarPressReleaseCardProps) {
  return (
    <button
      type="button"
      className={`release-card${isSelected ? " is-selected" : ""}`}
      onClick={onSelect}
      aria-pressed={isSelected}
    >
      <span className="release-card__rank">{String(rank).padStart(2, "0")}</span>
      <span className="release-card__body">
        <span className="release-card__company">{release.company_name}</span>
        <strong>{release.title}</strong>
        <span className="release-card__meta">
          <span>{formatDate(release.created_at)}</span>
          {release.industry && <span>{release.industry}</span>}
        </span>
      </span>
      <span className="release-card__score">
        <span>類似度</span>
        <strong>{release.similarity_score.toFixed(3)}</strong>
      </span>
      <span className="release-card__arrow" aria-hidden="true">↗</span>
    </button>
  );
}
