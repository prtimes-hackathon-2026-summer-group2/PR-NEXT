"""Storage-independent descriptive habit-formation analysis.

Only release timestamps and company/release identifiers are used. Future
releases are outcomes only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .statistics import safe_ratio, strict_historical_median


def build_timeline(release: pd.DataFrame) -> pd.DataFrame:
    """Derive strictly historical gaps and future outcomes from a DataFrame."""
    required = {"company_id", "release_id", "created_at"}
    missing = required - set(release.columns)
    if missing:
        raise ValueError(f"release timeline missing columns: {sorted(missing)}")
    frame = release.copy()
    frame["created_at"] = pd.to_datetime(frame["created_at"], errors="raise")
    frame = frame.sort_values(
        ["company_id", "created_at", "release_id"], kind="stable"
    ).reset_index(drop=True)
    grouped = frame.groupby("company_id", sort=False)
    frame["release_count"] = grouped.cumcount() + 1
    frame["previous_at"] = grouped["created_at"].shift(1)
    frame["previous_gap_days"] = (
        frame["created_at"] - frame["previous_at"]
    ).dt.total_seconds() / 86400.0
    median, count = strict_historical_median(frame, "previous_gap_days")
    frame["historical_median_gap_before"] = median
    frame["historical_gap_count_before"] = count
    frame["gap_ratio"] = safe_ratio(
        frame["previous_gap_days"], frame["historical_median_gap_before"]
    )
    frame["next_at"] = grouped["created_at"].shift(-1)
    frame["next_release_days"] = (
        frame["next_at"] - frame["created_at"]
    ).dt.total_seconds() / 86400.0
    for offset in range(2, 6):
        frame[f"next_{offset}_at"] = grouped["created_at"].shift(-offset)
    frame["gap_ratio_m1"] = grouped["gap_ratio"].shift(1)
    frame["gap_ratio_m2"] = grouped["gap_ratio"].shift(2)
    for offset in range(1, 5):
        frame[f"gap_ratio_after_{offset}"] = grouped["gap_ratio"].shift(-offset)
    return frame


def retention_curve(frame: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    rows = []
    previous_90 = np.nan
    for count in range(3, 16):
        row: dict[str, float | int] = {"release_count": count}
        for days in (30, 60, 90, 180):
            eligible = frame[
                frame["release_count"].eq(count)
                & frame["created_at"].le(as_of - pd.Timedelta(days=days))
            ]
            outcome = eligible["next_at"].notna() & eligible["next_release_days"].le(days)
            row[f"eligible_{days}d_n"] = int(len(eligible))
            row[f"retention_{days}d"] = float(outcome.mean())
        row["improvement_90d_pp"] = (
            np.nan if np.isnan(previous_90) else (row["retention_90d"] - previous_90) * 100
        )
        previous_90 = float(row["retention_90d"])
        rows.append(row)
    return pd.DataFrame(rows)


def rhythm_stability(frame: pd.DataFrame, as_of: pd.Timestamp) -> tuple[pd.DataFrame, float]:
    candidates = frame[
        frame["created_at"].le(as_of - pd.Timedelta(days=365))
        & frame[["gap_ratio_m2", "gap_ratio_m1", "gap_ratio"]].notna().all(axis=1)
    ]
    anchors = candidates.groupby("company_id", sort=False).tail(1).copy()
    recent = anchors[["gap_ratio_m2", "gap_ratio_m1", "gap_ratio"]]
    stable = recent.ge(0.5).all(axis=1) & recent.le(1.5).all(axis=1)
    highly = recent.gt(2.0).any(axis=1)
    anchors["rhythm_group"] = np.select(
        [stable, highly], ["stable", "highly_irregular"], default="mildly_irregular"
    )
    rows = []
    for label, group in anchors.groupby("rhythm_group", sort=False):
        row = {"rhythm_group": label, "company_n": int(len(group))}
        for days in (90, 180, 365):
            continued = group["next_at"].notna() & group["next_release_days"].le(days)
            row[f"retention_{days}d"] = float(continued.mean())
        rows.append(row)
    result = pd.DataFrame(rows).sort_values("rhythm_group").reset_index(drop=True)
    stable_rate = float(result.loc[result.rhythm_group.eq("stable"), "retention_90d"].iloc[0])
    nonstable = anchors[anchors.rhythm_group.ne("stable")]
    nonstable_rate = float(
        (nonstable["next_at"].notna() & nonstable["next_release_days"].le(90)).mean()
    )
    return result, (stable_rate - nonstable_rate) * 100


def calendar_timing(frame: pd.DataFrame) -> pd.DataFrame:
    pairs = frame[
        frame["historical_median_gap_before"].gt(0) & frame["next_at"].notna()
    ].copy()
    pairs["timing_deviation_days"] = (
        pairs["next_release_days"] - pairs["historical_median_gap_before"]
    )
    pairs["count_bucket"] = pd.cut(
        pairs["release_count"], [2, 5, 10, 20, np.inf],
        labels=["3-5", "6-10", "11-20", "21+"],
    )
    rows = []
    for label, group in [("all", pairs), *pairs.groupby("count_bucket", observed=True)]:
        deviation = group["timing_deviation_days"]
        baseline = group["historical_median_gap_before"]
        rows.append(
            {
                "release_count_bucket": str(label),
                "pair_n": int(len(group)),
                "before_expected_rate": float(deviation.lt(0).mean()),
                "within_7d_rate": float(deviation.abs().le(7).mean()),
                "within_14d_rate": float(deviation.abs().le(14).mean()),
                "within_30d_rate": float(deviation.abs().le(30).mean()),
                "over_30d_late_rate": float(deviation.gt(30).mean()),
                "over_1_5x_rate": float(group["next_release_days"].gt(1.5 * baseline).mean()),
                "over_2x_rate": float(group["next_release_days"].gt(2.0 * baseline).mean()),
                "deviation_median_days": float(deviation.median()),
                "deviation_p25_days": float(deviation.quantile(0.25)),
                "deviation_p75_days": float(deviation.quantile(0.75)),
            }
        )
    return pd.DataFrame(rows)


def reminder_timing(frame: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    rows = []
    baseline = frame["historical_median_gap_before"]
    for threshold in (0.8, 1.0, 1.2, 1.5, 2.0):
        event_date = frame["created_at"] + pd.to_timedelta(baseline * threshold, unit="D")
        reached = baseline.gt(0) & event_date.le(as_of) & (
            frame["next_at"].isna() | frame["next_at"].ge(event_date)
        )
        for days in (30, 60, 90):
            eligible = frame[
                reached & event_date.le(as_of - pd.Timedelta(days=days))
            ]
            eligible_event_date = event_date.loc[eligible.index]
            redispatched = eligible["next_at"].notna() & eligible["next_at"].le(
                eligible_event_date + pd.Timedelta(days=days)
            )
            rows.append(
                {
                    "threshold": threshold,
                    "window_days": days,
                    "eligible_event_n": int(len(eligible)),
                    "eligible_company_n": int(eligible["company_id"].nunique()),
                    "redispatched_n": int(redispatched.sum()),
                    "natural_redispatch_rate": float(redispatched.mean()),
                }
            )
    return pd.DataFrame(rows)


def restart_habituation(frame: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    restart = frame[
        frame["release_count"].ge(4)
        & (frame["previous_gap_days"].ge(90) | frame["gap_ratio"].ge(2.0))
    ].sort_values(["company_id", "created_at", "release_id"], kind="stable")
    restart = restart.drop_duplicates("company_id", keep="first").copy()
    observed = restart[restart["created_at"].le(as_of - pd.Timedelta(days=365))]
    reached = {}
    for total_releases, column in (
        (2, "next_at"), (3, "next_2_at"), (4, "next_3_at"), (5, "next_4_at")
    ):
        reached[total_releases] = observed[column].notna() & observed[column].le(
            observed["created_at"] + pd.Timedelta(days=365)
        )
    normal_2 = (
        reached[3]
        & observed["gap_ratio_after_1"].le(1.5)
        & observed["gap_ratio_after_2"].le(1.5)
    )
    normal_3 = (
        reached[4]
        & observed["gap_ratio_after_1"].le(1.5)
        & observed["gap_ratio_after_2"].le(1.5)
        & observed["gap_ratio_after_3"].le(1.5)
    )
    normal_3_rows = observed[normal_3].copy()
    end_date = normal_3_rows["next_3_at"]
    follow_eligible = normal_3_rows[end_date.le(as_of - pd.Timedelta(days=180))]
    follow_end = follow_eligible["next_3_at"]
    follow = follow_eligible["next_4_at"].notna() & follow_eligible["next_4_at"].le(
        follow_end + pd.Timedelta(days=180)
    )
    return {
        "restart_company_n": int(len(restart)),
        "fully_observed_365d_n": int(len(observed)),
        "restart_first_only_rate": float((~reached[2]).mean()),
        "reached_second_rate": float(reached[2].mean()),
        "reached_third_rate": float(reached[3].mean()),
        "reached_fourth_rate": float(reached[4].mean()),
        "reached_fifth_rate": float(reached[5].mean()),
        "two_consecutive_normal_gap_rate": float(normal_2.mean()),
        "three_consecutive_normal_gap_rate": float(normal_3.mean()),
        "normal_3_followup_180d_n": int(len(follow_eligible)),
        "normal_3_subsequent_180d_retention": float(follow.mean()),
    }


def incentive_metrics(
    frame: pd.DataFrame, as_of: pd.Timestamp
) -> tuple[pd.DataFrame, pd.DataFrame]:
    pairs = frame[
        frame["historical_median_gap_before"].gt(0) & frame["next_at"].notna()
    ].copy()
    pairs["count_bucket"] = pd.cut(
        pairs["release_count"], [2, 10, 20, np.inf], labels=["3-10", "11-20", "21+"]
    )
    rules = {
        "within_1_0x": pairs["next_release_days"].le(pairs["historical_median_gap_before"]),
        "within_1_2x": pairs["next_release_days"].le(1.2 * pairs["historical_median_gap_before"]),
        "within_1_5x": pairs["next_release_days"].le(1.5 * pairs["historical_median_gap_before"]),
        "within_90d": pairs["next_release_days"].le(90),
    }
    rows = []
    yearly = []
    for rule, mask in rules.items():
        matched = pairs[mask]
        baseline = matched[matched["next_at"].le(as_of - pd.Timedelta(days=90))]
        further = baseline["next_2_at"].notna() & baseline["next_2_at"].le(
            baseline["next_at"] + pd.Timedelta(days=90)
        )
        row = {
            "rule": rule,
            "eligible_company_n": int(matched["company_id"].nunique()),
            "eligible_pair_n": int(len(matched)),
            "eligible_pair_share": float(len(matched) / len(pairs)),
            "baseline_90d_n": int(len(baseline)),
            "subsequent_90d_natural_rate": float(further.mean()),
        }
        for bucket in ("3-10", "11-20", "21+"):
            row[f"pair_n_{bucket}"] = int(matched["count_bucket"].eq(bucket).sum())
        rows.append(row)
        for year in range(2019, 2026):
            # A reward event occurs when the qualifying next release is sent,
            # so calendar-year volume belongs to next_at rather than the anchor.
            sample = matched[matched["next_at"].dt.year.eq(year)]
            yearly.append(
                {"rule": rule, "calendar_year": year, "eligible_event_n": int(len(sample))}
            )
    return pd.DataFrame(rows), pd.DataFrame(yearly)


def product_scale(frame: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    grouped = frame.groupby("company_id", sort=False)
    company_gap = grouped["previous_gap_days"].median().rename("company_median_gap")
    latest = grouped.tail(1).join(company_gap, on="company_id")
    latest = latest[latest["release_count"].ge(3) & latest["company_median_gap"].gt(0)].copy()
    latest["current_gap_days"] = (
        as_of - latest["created_at"]
    ).dt.total_seconds() / 86400.0
    latest["current_gap_ratio"] = safe_ratio(
        latest["current_gap_days"], latest["company_median_gap"]
    )
    labels = ["0.8-1.0x", "1.0-1.2x", "1.2-1.5x", "1.5-2.0x", ">=2.0x"]
    bucket = pd.cut(
        latest["current_gap_ratio"], [0.8, 1.0, 1.2, 1.5, 2.0, np.inf],
        labels=labels, right=False,
    )
    rows = []
    for label in labels:
        sample = latest[bucket.eq(label)]
        rows.append(
            {
                "bucket": label,
                "company_n": int(len(sample)),
                "all_evaluable_share": (
                    float(len(sample) / len(latest)) if len(latest) else np.nan
                ),
                "company_n_release_count_3_10": int(sample["release_count"].between(3, 10).sum()),
            }
        )
    return pd.DataFrame(rows)
