"""In-memory DataFrame contract for release analysis."""

from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True)
class AnalysisInputs:
    company: pd.DataFrame
    release: pd.DataFrame
    release_statistics: pd.DataFrame
    industry: pd.DataFrame | None = None
    ipo_type: pd.DataFrame | None = None
    release_type: pd.DataFrame | None = None
    # Optional release-to-media detail at company/release grain.
    repost_media: pd.DataFrame | None = None
