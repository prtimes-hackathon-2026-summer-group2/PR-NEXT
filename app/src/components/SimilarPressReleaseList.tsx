import type { SimilarPressRelease } from "@/lib/fastapi/types";
import { SimilarPressReleaseCard } from "./SimilarPressReleaseCard";

type SimilarPressReleaseListProps = {
  releases: SimilarPressRelease[];
  selectedKey: string;
  onSelect: (key: string) => void;
};

export function SimilarPressReleaseList({
  releases,
  selectedKey,
  onSelect,
}: SimilarPressReleaseListProps) {
  return (
    <aside className="release-list-panel" aria-labelledby="similar-list-title">
      <div className="release-list-panel__heading">
        <div>
          <span className="panel-heading__label">SIMILAR RELEASES</span>
          <h3 id="similar-list-title">類似PR Top {releases.length}</h3>
        </div>
        <span className="select-hint">選択して詳細を表示</span>
      </div>
      <div className="release-list">
        {releases.map((release, index) => {
          const releaseKey = `${release.company_id}:${release.release_id}`;
          return (
            <SimilarPressReleaseCard
              key={releaseKey}
              release={release}
              rank={index + 1}
              isSelected={releaseKey === selectedKey}
              onSelect={() => onSelect(releaseKey)}
            />
          );
        })}
      </div>
    </aside>
  );
}
