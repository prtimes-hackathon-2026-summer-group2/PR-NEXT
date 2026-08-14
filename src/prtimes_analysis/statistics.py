"""Reusable statistics that do not depend on storage or runtime services."""

from __future__ import annotations

import numpy as np
import pandas as pd


def safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Return a finite non-negative ratio with a positive denominator."""
    num = pd.to_numeric(numerator, errors="coerce").astype("float64")
    den = pd.to_numeric(denominator, errors="coerce").astype("float64")
    valid = (
        num.notna()
        & den.notna()
        & np.isfinite(num)
        & np.isfinite(den)
        & num.ge(0)
        & den.gt(0)
    )
    result = pd.Series(np.nan, index=num.index, dtype="float64")
    result.loc[valid] = num.loc[valid] / den.loc[valid]
    return result.where(np.isfinite(result))


def safe_signed_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Return a finite signed ratio with a strictly positive denominator."""
    num = pd.to_numeric(numerator, errors="coerce").astype("float64")
    den = pd.to_numeric(denominator, errors="coerce").astype("float64")
    valid = (
        num.notna()
        & den.notna()
        & np.isfinite(num)
        & np.isfinite(den)
        & den.gt(0)
    )
    result = pd.Series(np.nan, index=num.index, dtype="float64")
    result.loc[valid] = num.loc[valid] / den.loc[valid]
    return result.where(np.isfinite(result))


def strict_historical_median(
    frame: pd.DataFrame,
    value_col: str,
    group_col: str = "company_id",
    time_col: str = "created_at",
) -> tuple[pd.Series, pd.Series]:
    """Median/count from strictly earlier timestamps within each group.

    ``frame`` must be ordered by group, time, and its deterministic tie-breaker.
    Rows sharing a timestamp observe the same embargoed history.
    """
    values = pd.to_numeric(frame[value_col], errors="coerce").astype("float64")
    inclusive_median = (
        values.groupby(frame[group_col], sort=False, dropna=False)
        .expanding()
        .median()
        .reset_index(level=0, drop=True)
    )
    prior_median = inclusive_median.groupby(
        frame[group_col], sort=False, dropna=False
    ).shift(1)

    valid = values.notna().astype("int64")
    inclusive_count = valid.groupby(
        frame[group_col], sort=False, dropna=False
    ).cumsum()
    prior_count = (
        inclusive_count.groupby(frame[group_col], sort=False, dropna=False)
        .shift(1)
        .fillna(0)
        .astype("int64")
    )

    first_at_timestamp = ~frame.duplicated([group_col, time_col])
    time_keys = [frame[group_col], frame[time_col]]
    median = prior_median.where(first_at_timestamp).groupby(
        time_keys, sort=False, dropna=False
    ).transform("max")
    count = prior_count.where(first_at_timestamp).groupby(
        time_keys, sort=False, dropna=False
    ).transform("max")
    return median.astype("float64"), count.fillna(0).astype("int64")
