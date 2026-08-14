"""Small deterministic DataFrame fixture for examples and local tests."""

from __future__ import annotations

import pandas as pd

from .providers.base import AnalysisInputs


def synthetic_inputs() -> AnalysisInputs:
    companies = pd.DataFrame({
        "company_id": list(range(1, 23)),
        "company_name": [f"Synthetic {number}" for number in range(1, 23)],
        "industry_id": [1] * 22,
    })
    releases: list[tuple[int, int, str, int, str]] = []
    statistics: list[tuple[int, int, int, int, int, int, float, float]] = []
    media: list[tuple[int, int, str]] = []
    for company_id in range(1, 23):
        for ordinal, date in enumerate(("2025-01-01", "2025-02-01", "2025-03-01")):
            release_id = company_id * 100 + ordinal
            releases.append((company_id, release_id, date, 1, f"release {company_id}-{ordinal}"))
            statistics.append((company_id, release_id, company_id * 10 + ordinal, company_id + ordinal, ordinal + 1, ordinal + 2, 0.6, 0.4))
            media.append((company_id, release_id, f"media-{ordinal % 2}"))
    return AnalysisInputs(
        company=companies,
        release=pd.DataFrame(releases, columns=["company_id", "release_id", "created_at", "release_type_id", "title"]),
        release_statistics=pd.DataFrame(statistics, columns=["company_id", "release_id", "page_view", "unique_user", "media_count", "referral_site_count", "pc_share", "smartphone_share"]),
        industry=pd.DataFrame({"industry_id": [1], "industry_name": ["Synthetic industry"]}),
        release_type=pd.DataFrame({"release_type_id": [1], "release_type_name": ["News"]}),
        repost_media=pd.DataFrame(media, columns=["company_id", "release_id", "media_name"]),
    )
