"""Normalize in-memory inputs into the analysis DataFrame contract."""

from __future__ import annotations

import pandas as pd

from .load_data import METRIC_CANDIDATES, SchemaAudit
from .providers.base import AnalysisInputs


def normalize_release_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"company_id", "release_id", "created_at"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"standardized release input missing columns: {sorted(missing)}")
    result = frame.copy()
    result["created_at"] = pd.to_datetime(result["created_at"], errors="coerce")
    if result["created_at"].isna().any():
        raise ValueError("standardized release input has unparseable created_at values")
    return result


def normalize_analysis_inputs(inputs: AnalysisInputs) -> AnalysisInputs:
    for name, frame, required in (
        ("company", inputs.company, {"company_id"}),
        ("release_statistics", inputs.release_statistics, {"company_id", "release_id"}),
    ):
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"standardized {name} input missing columns: {sorted(missing)}")
    statistic = inputs.release_statistics.copy()
    # Keep identifiers stable but coerce candidate metric fields into a useful
    # numeric form.  Missing/invalid values become unavailable per release.
    for candidates in METRIC_CANDIDATES.values():
        for column in candidates:
            if column in statistic:
                statistic[column] = pd.to_numeric(statistic[column], errors="coerce")
    media = None if inputs.repost_media is None else inputs.repost_media.copy()
    if media is not None:
        missing_media = {"company_id", "release_id"} - set(media.columns)
        if missing_media:
            raise ValueError(f"standardized repost_media input missing columns: {sorted(missing_media)}")
    return AnalysisInputs(
        company=inputs.company.copy(), release=normalize_release_dataframe(inputs.release), release_statistics=statistic,
        industry=None if inputs.industry is None else inputs.industry.copy(), ipo_type=None if inputs.ipo_type is None else inputs.ipo_type.copy(), release_type=None if inputs.release_type is None else inputs.release_type.copy(),
        repost_media=media,
    )


def audit_analysis_inputs(inputs: AnalysisInputs) -> SchemaAudit:
    table_columns = {
        "company": list(inputs.company.columns), "release": list(inputs.release.columns),
        "release_statistic": list(inputs.release_statistics.columns),
    }
    for name in ("industry", "ipo_type", "release_type"):
        frame = getattr(inputs, name)
        if frame is not None:
            table_columns[name] = list(frame.columns)
    available, unavailable, metric_columns = [], [], {}
    for metric, candidates in METRIC_CANDIDATES.items():
        column = next((candidate for candidate in candidates if candidate in inputs.release_statistics.columns), None)
        if column is None:
            unavailable.append(metric)
        else:
            metric_columns[metric] = column
            available.append({"metric": metric, "source_table": "release_statistic", "column": column})
    if {"PV", "UU"}.issubset(metric_columns):
        available.append({"metric": "PV_PER_UU", "source_table": "derived", "column": "pv / uu"})
    else:
        unavailable.append("PV_PER_UU")
    return SchemaAudit(table_columns, available, unavailable, metric_columns)
