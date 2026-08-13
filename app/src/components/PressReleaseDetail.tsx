import type { SimilarPressRelease } from "@/lib/fastapi/types";

type PressReleaseDetailProps = {
  release: SimilarPressRelease;
};

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "Asia/Tokyo",
  }).format(date);
}

function StatIcon({ type }: { type: "view" | "user" | "like" }) {
  if (type === "view") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" />
        <circle cx="12" cy="12" r="2.7" />
      </svg>
    );
  }
  if (type === "user") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="8" r="3.3" />
        <path d="M5.5 20c.5-4 2.7-6 6.5-6s6 2 6.5 6" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 20S4 15.5 4 9.5C4 6.8 5.8 5 8.3 5c1.6 0 3 1 3.7 2.2C12.7 6 14.1 5 15.7 5 18.2 5 20 6.8 20 9.5 20 15.5 12 20 12 20Z" />
    </svg>
  );
}

export function PressReleaseDetail({ release }: PressReleaseDetailProps) {
  return (
    <article className="detail-panel" aria-labelledby="detail-title">
      <div className="detail-panel__heading">
        <div>
          <span className="panel-heading__label">SELECTED RELEASE</span>
          <h3 id="detail-title">選択したPRの詳細</h3>
        </div>
        <span className="detail-panel__date">{formatDate(release.created_at)}</span>
      </div>

      <div className="detail-panel__content">
        <div className="detail-lead">
          <div className="detail-lead__company">
            <span>{release.company_name}</span>
            {release.industry && <span>{release.industry}</span>}
          </div>
          <h4>{release.title}</h4>
          {release.subtitle && <p className="detail-subtitle">{release.subtitle}</p>}
          <div className="detail-divider" />
          <p className="detail-copy">{release.lead_paragraph}</p>
        </div>

        <aside className="detail-side">
          <div className="detail-stats">
            <div>
              <span className="stat-icon"><StatIcon type="view" /></span>
              <span>ページ閲覧数</span>
              <strong>{release.page_view.toLocaleString("ja-JP")}</strong>
            </div>
            <div>
              <span className="stat-icon"><StatIcon type="user" /></span>
              <span>ユニークユーザー数</span>
              <strong>{release.unique_user.toLocaleString("ja-JP")}</strong>
            </div>
            <div>
              <span className="stat-icon"><StatIcon type="like" /></span>
              <span>Like数</span>
              <strong>{release.like_count.toLocaleString("ja-JP")}</strong>
            </div>
          </div>

          {release.business_categories.length > 0 && (
            <div className="tag-section">
              <span className="tag-section__label">事業カテゴリ</span>
              <div className="tags">
                {release.business_categories.map((category) => (
                  <span key={category}>{category}</span>
                ))}
              </div>
            </div>
          )}

          {release.keywords.length > 0 && (
            <div className="tag-section">
              <span className="tag-section__label">キーワード</span>
              <div className="tags tags--outline">
                {release.keywords.map((keyword) => (
                  <span key={keyword}>#{keyword}</span>
                ))}
              </div>
            </div>
          )}
        </aside>
      </div>
    </article>
  );
}
