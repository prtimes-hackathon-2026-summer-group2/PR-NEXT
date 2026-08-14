"""Time-safe historical, previous-release, and peer comparisons."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from .statistics import safe_ratio, strict_historical_median


MIN_PEER_N = 20
PEER_WINDOW_DAYS = 180


class Fenwick:
    def __init__(self, size: int) -> None:
        self.values = np.zeros(size + 1, dtype=np.int64)

    def add(self, index: int, delta: int) -> None:
        index += 1
        while index < len(self.values):
            self.values[index] += delta
            index += index & -index

    def prefix(self, index: int) -> int:
        result = 0
        index += 1
        while index > 0:
            result += int(self.values[index])
            index -= index & -index
        return result

    def total(self) -> int:
        return self.prefix(len(self.values) - 2)

    def kth(self, rank: int) -> int:
        """Zero-based index of the value at ordered ``rank``."""
        index = 0
        bit = 1 << (len(self.values).bit_length() - 1)
        target = rank + 1
        while bit:
            next_index = index + bit
            if next_index < len(self.values) and self.values[next_index] < target:
                index = next_index
                target -= int(self.values[next_index])
            bit >>= 1
        return index


def state_from_ratio(values: pd.Series) -> pd.Series:
    return pd.Series(np.select([values.ge(1.2), values.lt(0.8)], ["HIGH", "LOW"], default="NORMAL"), index=values.index).where(values.notna(), "UNKNOWN")


def state_from_percentile(values: pd.Series) -> pd.Series:
    return pd.Series(np.select([values.ge(0.7), values.lt(0.3)], ["HIGH", "LOW"], default="NORMAL"), index=values.index).where(values.notna(), "UNKNOWN")


def _strict_historical_percentile(frame: pd.DataFrame, group_col: str, value_col: str) -> pd.Series:
    """Percentile among strictly earlier releases (ties are not counted as lower)."""
    output = pd.Series(np.nan, index=frame.index, dtype="float64")
    for _, group in frame.groupby(group_col, sort=False, dropna=False):
        values = group[value_col].dropna().astype(float).to_numpy()
        coordinates = np.unique(values)
        if not len(coordinates):
            continue
        tree = Fenwick(len(coordinates))
        for _, same_time in group.groupby("created_at", sort=False, dropna=False):
            count = tree.total()
            if count:
                for index, value in same_time[value_col].items():
                    if pd.notna(value):
                        output.loc[index] = tree.prefix(int(np.searchsorted(coordinates, float(value))) - 1) / count
            for value in same_time[value_col].dropna().astype(float):
                tree.add(int(np.searchsorted(coordinates, value)), 1)
    return output


def _recent_prior_statistics(frame: pd.DataFrame, metric: str, window: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Prior 3/5-release statistics with a same-timestamp embargo."""
    means = pd.Series(np.nan, index=frame.index, dtype="float64")
    medians = pd.Series(np.nan, index=frame.index, dtype="float64")
    counts = pd.Series(0, index=frame.index, dtype="int64")
    for _, group in frame.groupby("company_id", sort=False, dropna=False):
        history: deque[float] = deque(maxlen=window)
        for _, same_time in group.groupby("created_at", sort=False, dropna=False):
            prior = np.asarray(history, dtype=float)
            valid_count = len(prior)
            counts.loc[same_time.index] = valid_count
            if valid_count:
                means.loc[same_time.index] = float(prior.mean())
                medians.loc[same_time.index] = float(np.median(prior))
            for value in same_time[metric].dropna().astype(float):
                history.append(float(value))
    return means, medians, counts


def add_company_comparisons(frame: pd.DataFrame, metrics: Iterable[str]) -> pd.DataFrame:
    frame = frame.copy()
    frame = frame.sort_values(["company_id", "created_at", "release_id"], kind="stable").reset_index(drop=True)
    grouped = frame.groupby("company_id", sort=False, dropna=False)
    frame["release_seq"] = grouped.cumcount() + 1
    frame["prev_release_id"] = grouped["release_id"].shift(1)
    frame["prev_release_at"] = grouped["created_at"].shift(1)
    frame["days_from_prev_release"] = (frame["created_at"] - frame["prev_release_at"]).dt.total_seconds() / 86400.0
    for metric in metrics:
        grouped = frame.groupby("company_id", sort=False, dropna=False)
        history_median, history_count = strict_historical_median(frame, metric)
        frame[f"historical_{metric}_count"] = history_count
        frame[f"historical_{metric}_median"] = history_median
        frame[f"{metric}_self_ratio"] = safe_ratio(frame[metric], history_median)
        frame[f"log2_{metric}_self_ratio"] = np.log2(frame[f"{metric}_self_ratio"].where(frame[f"{metric}_self_ratio"].gt(0)))
        frame[f"historical_{metric}_percentile"] = _strict_historical_percentile(frame, "company_id", metric)
        frame[f"prev_{metric}"] = grouped[metric].shift(1)
        frame[f"{metric}_prev_ratio"] = safe_ratio(frame[metric], frame[f"prev_{metric}"])
        frame[f"{metric}_prev_change_pct"] = safe_ratio(frame[metric] - frame[f"prev_{metric}"], frame[f"prev_{metric}"])
        frame[f"{metric}_self_state"] = state_from_ratio(frame[f"{metric}_self_ratio"])
        for window in (3, 5):
            mean, median, count = _recent_prior_statistics(frame, metric, window)
            frame[f"recent_{window}_{metric}_mean"] = mean
            frame[f"recent_{window}_{metric}_median"] = median
            frame[f"recent_{window}_{metric}_count"] = count
        # Many optional metrics can otherwise produce a fragmented dataframe
        # (and noisy warnings) without changing any values.
        frame = frame.copy()
    gap_median, gap_count = strict_historical_median(frame, "days_from_prev_release")
    frame["historical_gap_count"] = gap_count
    frame["historical_gap_median"] = gap_median
    frame["gap_ratio"] = safe_ratio(frame["days_from_prev_release"], gap_median)
    return frame


def _peer_stats(frame: pd.DataFrame, metric: str, group_columns: list[str], label: str) -> tuple[pd.Series, pd.Series]:
    percentile = pd.Series(np.nan, index=frame.index, dtype="float64")
    peer_n = pd.Series(0, index=frame.index, dtype="int64")
    eligible = frame.dropna(subset=[*group_columns, "created_at"]) if group_columns else frame.dropna(subset=["created_at"])
    valid_groups = eligible.groupby(group_columns, sort=False, dropna=False) if group_columns else [("all", eligible)]
    for _, group in valid_groups:
        group = group.sort_values(["created_at", "release_id"], kind="stable")
        values = group[metric].dropna().astype(float).to_numpy()
        coordinates = np.unique(values)
        if not len(coordinates):
            continue
        tree = Fenwick(len(coordinates))
        history: deque[tuple[pd.Timestamp, float]] = deque()
        for timestamp, same_time in group.groupby("created_at", sort=False):
            cutoff = timestamp - pd.Timedelta(days=PEER_WINDOW_DAYS)
            while history and history[0][0] < cutoff:
                _, expired = history.popleft()
                tree.add(int(np.searchsorted(coordinates, expired)), -1)
            n = tree.total()
            peer_n.loc[same_time.index] = n
            if n >= MIN_PEER_N:
                for index, value in same_time[metric].items():
                    if pd.notna(value):
                        lower = tree.prefix(int(np.searchsorted(coordinates, float(value))) - 1)
                        percentile.loc[index] = lower / n
            for value in same_time[metric].dropna().astype(float):
                number = float(value)
                tree.add(int(np.searchsorted(coordinates, number)), 1)
                history.append((timestamp, number))
    return peer_n, percentile


def _add_peer_metric(frame: pd.DataFrame, metric: str) -> None:
    """Use industry+type, then a documented less-specific peer fallback."""
    candidates = [
        ("industry_release_type", ["industry", "release_type"]),
        ("industry", ["industry"]),
        ("release_type", ["release_type"]),
        ("all_releases", []),
    ]
    selected_n = pd.Series(0, index=frame.index, dtype="int64")
    selected_percentile = pd.Series(np.nan, index=frame.index, dtype="float64")
    selected_level = pd.Series("UNAVAILABLE", index=frame.index, dtype="object")
    for label, columns in candidates:
        counts, percentiles = _peer_stats(frame, metric, columns, label)
        use = selected_percentile.isna() & counts.ge(MIN_PEER_N) & percentiles.notna()
        selected_n.loc[use] = counts.loc[use]
        selected_percentile.loc[use] = percentiles.loc[use]
        selected_level.loc[use] = label
        # Preserve the most-specific population size for transparency even if
        # no eligible fallback exists.
        if label == "industry_release_type":
            selected_n = selected_n.where(selected_n.ne(0), counts)
    frame[f"{metric}_peer_n"] = selected_n
    frame[f"{metric}_peer_percentile"] = selected_percentile
    frame[f"{metric}_peer_top_pct"] = (1.0 - selected_percentile).where(selected_percentile.notna())
    frame[f"{metric}_peer_group_level"] = selected_level
    frame[f"{metric}_peer_state"] = state_from_percentile(selected_percentile)


def add_peer_comparisons(frame: pd.DataFrame, metrics: Iterable[str]) -> pd.DataFrame:
    frame = frame.copy()
    for metric in metrics:
        _add_peer_metric(frame, metric)
    # The core PV cohort size is the reportable peer_n; metric-specific counts remain available.
    if "pv_peer_n" in frame:
        frame["peer_n"] = frame["pv_peer_n"]
        frame["peer_group_level"] = frame["pv_peer_group_level"]
    return frame
