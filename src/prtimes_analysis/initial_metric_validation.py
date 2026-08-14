"""Pure DataFrame methods for descriptive product-metric validation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .statistics import safe_ratio, strict_historical_median


LIMITATION = (
    "DESCRIPTIVE_ONLY: cumulative snapshot values; release age differs; "
    "not PIT-safe and not usable for prediction or causal claims"
)


def build_release_metrics(raw: pd.DataFrame) -> pd.DataFrame:
    """Add time-safe self-history metrics to release-level observations."""
    required = {
        "company_id", "release_id", "created_at", "page_view", "unique_user"
    }
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"release metrics input missing columns: {sorted(missing)}")
    frame = raw.copy()
    frame["created_at"] = pd.to_datetime(frame["created_at"], errors="raise")
    frame = frame.sort_values(
        ["company_id", "created_at", "release_id"], kind="stable"
    ).reset_index(drop=True)
    grouped = frame.groupby("company_id", sort=False)
    frame["release_seq"] = grouped.cumcount() + 1
    frame["previous_release_at"] = grouped["created_at"].shift(1)
    frame["days_from_previous_release"] = (
        frame["created_at"] - frame["previous_release_at"]
    ).dt.total_seconds() / 86400.0
    frame["views_per_user"] = safe_ratio(frame["page_view"], frame["unique_user"])

    for source, public in (
        ("page_view", "pv"),
        ("unique_user", "uu"),
        ("views_per_user", "views_per_user"),
    ):
        median, count = strict_historical_median(frame, source)
        frame[f"historical_{public}_median_before"] = median
        frame[f"historical_{public}_count_before"] = count
        relative = safe_ratio(frame[source], median)
        frame[f"relative_{public}"] = relative.where(count.ge(2))
    return frame


def build_latest_metrics(
    frame: pd.DataFrame, release_type: pd.DataFrame
) -> pd.DataFrame:
    """Build one current continuity observation per eligible company."""
    grouped = frame.groupby("company_id", sort=False)
    company_gap = grouped["days_from_previous_release"].median().rename(
        "historical_median_gap"
    )
    latest = grouped.tail(1).copy().join(company_gap, on="company_id")
    latest = latest[
        latest["release_seq"].ge(3) & latest["historical_median_gap"].gt(0)
    ].copy()
    as_of = frame["created_at"].max()
    latest["days_since_latest"] = (
        as_of - latest["created_at"]
    ).dt.total_seconds() / 86400.0
    latest["current_gap_ratio"] = safe_ratio(
        latest["days_since_latest"], latest["historical_median_gap"]
    )
    latest["historical_release_count"] = latest["release_seq"] - 1
    latest = latest.merge(
        release_type,
        on="release_type_id",
        how="left",
        validate="many_to_one",
    )
    return latest.rename(
        columns={
            "release_id": "latest_release_id",
            "created_at": "latest_release_date",
            "release_seq": "release_count",
            "page_view": "pv",
            "unique_user": "uu",
            "release_type_name": "release_type",
        }
    )


def _summary_row(metric: str, values: pd.Series, universe_n: int) -> dict:
    finite = (
        pd.to_numeric(values, errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
    )
    return {
        "metric": metric,
        "eligible_n": int(len(finite)),
        "median": float(finite.median()) if len(finite) else np.nan,
        "p25": float(finite.quantile(0.25)) if len(finite) else np.nan,
        "p75": float(finite.quantile(0.75)) if len(finite) else np.nan,
        "above_1_rate": float(finite.gt(1).mean()) if len(finite) else np.nan,
        "unavailable_n": int(universe_n - len(finite)),
        "limitation": LIMITATION,
    }


def engagement_summary(frame: pd.DataFrame, latest: pd.DataFrame) -> pd.DataFrame:
    """Summarize relative PV, UU, and views-per-user distributions."""
    rows = []
    for label, values in (
        ("relative_pv_all", frame["relative_pv"]),
        ("relative_uu_all", frame["relative_uu"]),
        ("views_per_user_all", frame["views_per_user"]),
        ("relative_views_per_user_all", frame["relative_views_per_user"]),
    ):
        rows.append(_summary_row(label, values, len(frame)))
    for label, values in (
        ("relative_pv_latest", latest["relative_pv"]),
        ("relative_uu_latest", latest["relative_uu"]),
        ("views_per_user_latest", latest["views_per_user"]),
        ("relative_views_per_user_latest", latest["relative_views_per_user"]),
    ):
        rows.append(_summary_row(label, values, len(latest)))
    return pd.DataFrame(rows)


def continuity_table(latest: pd.DataFrame) -> pd.DataFrame:
    """Count companies by current gap-ratio bucket."""
    labels = ["<1.0", "1.0-1.5", "1.5-2.0", "2.0-4.0", ">=4.0"]
    bucket = pd.cut(
        latest["current_gap_ratio"],
        [-np.inf, 1, 1.5, 2, 4, np.inf],
        labels=labels,
        right=False,
    )
    result = (
        latest.assign(bucket=bucket)
        .groupby("bucket", observed=False)
        .agg(company_n=("company_id", "size"))
        .reindex(labels)
        .reset_index()
    )
    result["share"] = (
        result["company_n"] / len(latest) if len(latest) else np.nan
    )
    return result


def quadrant_counts(latest: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Cross relative response with current release rhythm."""
    valid = latest.dropna(subset=[metric, "current_gap_ratio"])
    labels = np.select(
        [
            valid[metric].ge(1) & valid["current_gap_ratio"].lt(1.5),
            valid[metric].ge(1) & valid["current_gap_ratio"].ge(1.5),
            valid[metric].lt(1) & valid["current_gap_ratio"].lt(1.5),
        ],
        [
            "A_good_response_normal_rhythm",
            "B_good_response_slow_rhythm",
            "C_low_response_normal_rhythm",
        ],
        default="D_low_response_slow_rhythm",
    )
    return (
        pd.Series(labels)
        .value_counts()
        .rename_axis("quadrant")
        .rename("company_n")
        .reset_index()
    )
