"""Pure continuation and right-censoring methods for release timelines."""

from __future__ import annotations

import pandas as pd


def add_continuation_flags(
    release: pd.DataFrame, window_days: int = 90
) -> pd.DataFrame:
    """Mark whether each release is observed and followed within the window."""
    required = {"company_id", "release_id", "created_at"}
    missing = required - set(release.columns)
    if missing:
        raise ValueError(f"release timeline missing columns: {sorted(missing)}")
    if window_days <= 0:
        raise ValueError("window_days must be positive")

    data = release.copy()
    data["created_at"] = pd.to_datetime(data["created_at"], errors="coerce")
    if data["created_at"].isna().any():
        raise ValueError("release timeline has unparseable created_at values")
    data = data.sort_values(
        ["company_id", "created_at", "release_id"], kind="stable"
    )
    data["next_release_at"] = data.groupby(
        "company_id", sort=False, dropna=False
    )["created_at"].shift(-1)
    max_date = data["created_at"].max()
    window = pd.Timedelta(days=window_days)
    data[f"continuation_eligible_{window_days}d"] = data["created_at"].le(
        max_date - window
    )
    data[f"continued_within_{window_days}d"] = (
        data[f"continuation_eligible_{window_days}d"]
        & data["next_release_at"].notna()
        & data["next_release_at"].sub(data["created_at"]).le(window)
    )
    return data
