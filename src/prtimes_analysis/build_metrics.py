"""Pure release- and company-grain analysis methods."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .compare import add_company_comparisons, add_peer_comparisons
from .load_data import SchemaAudit
from .input_adapter import audit_analysis_inputs, normalize_analysis_inputs
from .providers.base import AnalysisInputs
from .statistics import safe_ratio


def _validate_core(release: pd.DataFrame, statistic: pd.DataFrame) -> dict:
    duplicate = int(release.duplicated(["company_id", "release_id"]).sum())
    errors = {
        "company_id_null": int(release["company_id"].isna().sum()),
        "release_id_null": int(release["release_id"].isna().sum()),
        "duplicate_release_key": duplicate,
        "created_at_null": int(release["created_at"].isna().sum()),
    }
    if any(errors.values()):
        raise ValueError(f"Core release keys are invalid; fail fast: {errors}")
    stat_dupes = int(statistic.duplicated(["company_id", "release_id"]).sum())
    if stat_dupes:
        raise ValueError(f"release_statistic duplicate composite key: {stat_dupes}")
    return errors


def build_release_analysis_from_inputs(inputs: AnalysisInputs, audit: SchemaAudit | None = None) -> tuple[pd.DataFrame, dict]:
    """Build release-grain metrics from in-memory DataFrame inputs."""
    inputs = normalize_analysis_inputs(inputs)
    audit = audit or audit_analysis_inputs(inputs)
    release = inputs.release
    company = inputs.company
    statistic = inputs.release_statistics
    validation = _validate_core(release, statistic)

    if "PV" in audit.metric_columns:
        negative_pv = int((statistic[audit.metric_columns["PV"]] < 0).fillna(False).sum())
        validation["pv_negative"] = negative_pv
        if negative_pv:
            raise ValueError("PV contains negative values; fail fast")
    if "UU" in audit.metric_columns:
        negative_uu = int((statistic[audit.metric_columns["UU"]] < 0).fillna(False).sum())
        validation["uu_negative"] = negative_uu
        if negative_uu:
            raise ValueError("UU contains negative values; fail fast")

    for column in ("title", "release_type_id"):
        if column not in release:
            release[column] = pd.NA
    for column in ("company_name", "industry_id"):
        if column not in company:
            company[column] = pd.NA
    data = release.merge(company, on="company_id", how="left", validate="many_to_one")
    data = data.merge(statistic, on=["company_id", "release_id"], how="left", validate="one_to_one")
    statistic_value_columns = list(audit.metric_columns.values())
    validation["statistics_missing"] = int(data[statistic_value_columns].isna().all(axis=1).sum()) if statistic_value_columns else 0
    if validation["statistics_missing"]:
        raise ValueError(f"release without release_statistic: {validation['statistics_missing']}")

    if inputs.industry is not None:
        industry = inputs.industry
        if {"industry_id", "industry_name"}.issubset(industry.columns):
            data = data.merge(industry, on="industry_id", how="left", validate="many_to_one")
            data = data.rename(columns={"industry_name": "industry"})
    if "industry" not in data:
        data["industry"] = pd.NA
    if inputs.release_type is not None:
        release_type = inputs.release_type
        if {"release_type_id", "release_type_name"}.issubset(release_type.columns):
            data = data.merge(release_type, on="release_type_id", how="left", validate="many_to_one")
            data = data.rename(columns={"release_type_name": "release_type"})
    if "release_type" not in data:
        data["release_type"] = pd.NA
    metric_names = {
        "PV": "pv", "UU": "uu", "MEDIA_COUNT": "media_count",
        "REFERRAL_SITE_COUNT": "referral_site_count", "PC_SHARE": "pc_share",
        "SMARTPHONE_SHARE": "smartphone_share", "TABLET_SHARE": "tablet_share",
    }
    for metric, source in audit.metric_columns.items():
        data[metric_names[metric]] = data[source]
    if {"PV", "UU"}.issubset(audit.metric_columns):
        data["views_per_user"] = safe_ratio(data["pv"], data["uu"])

    data = _add_media_detail_metrics(data, inputs.repost_media)

    metrics = [column for column in ("pv", "uu", "views_per_user", "media_count", "referral_site_count", "new_media_count", "repeat_media_count", "pc_share", "smartphone_share", "tablet_share") if column in data]
    data = add_company_comparisons(data, metrics)
    data = add_peer_comparisons(data, metrics)
    for metric in ("pc_share", "smartphone_share", "tablet_share"):
        if metric in data:
            data[f"{metric}_self_delta"] = data[metric] - data[f"historical_{metric}_median"]
            data[f"{metric}_prev_delta"] = data[metric] - data[f"prev_{metric}"]
    return data, validation


def _add_media_detail_metrics(data: pd.DataFrame, media: pd.DataFrame | None) -> pd.DataFrame:
    """Classify media first-seen/repeat status using releases strictly before X.

    The source detail is optional, so absence yields explicit unavailable flags
    rather than fabricated zero media counts.
    """
    result = data.copy()
    result["media_detail_available"] = False
    result["new_media_count"] = np.nan
    result["repeat_media_count"] = np.nan
    if media is None or media.empty:
        return result
    identity = next((column for column in ("media_id", "site_id", "media_name", "site_name", "media") if column in media), None)
    if identity is None:
        return result
    detail = media[["company_id", "release_id", identity]].dropna(subset=[identity]).drop_duplicates()
    release_keys = result[["company_id", "release_id", "created_at"]]
    detail = detail.merge(release_keys, on=["company_id", "release_id"], how="inner", validate="many_to_one")
    detail = detail.sort_values(
        ["company_id", "created_at", "release_id"], kind="stable"
    )
    # Known releases with no rows are valid observations of zero detail.
    result["media_detail_available"] = True
    new_counts = pd.Series(0.0, index=result.index)
    repeat_counts = pd.Series(0.0, index=result.index)
    index_by_key = {(row.company_id, row.release_id): index for index, row in result[["company_id", "release_id"]].iterrows()}
    for _, company_rows in detail.groupby("company_id", sort=False, dropna=False):
        seen: set[object] = set()
        for _, same_time in company_rows.groupby("created_at", sort=False, dropna=False):
            # All same-time releases observe the identical strictly-prior set.
            for (company_id, release_id), release_rows in same_time.groupby(["company_id", "release_id"], sort=False):
                values = set(release_rows[identity])
                index = index_by_key[(company_id, release_id)]
                new_counts.loc[index] = len(values - seen)
                repeat_counts.loc[index] = len(values & seen)
            seen.update(same_time[identity].tolist())
    result["new_media_count"] = new_counts
    result["repeat_media_count"] = repeat_counts
    return result


def build_company_analysis(release: pd.DataFrame) -> pd.DataFrame:
    as_of_date = release["created_at"].max()
    grouped = release.groupby("company_id", dropna=False, sort=False)
    output = grouped.agg(
        company_name=("company_name", "first"),
        first_release_at=("created_at", "min"),
        last_release_at=("created_at", "max"),
        total_release_count=("release_id", "size"),
    ).reset_index()
    gap_median = grouped["days_from_prev_release"].median().rename("median_gap_days").reset_index()
    output = output.merge(gap_median, on="company_id", how="left")
    output["as_of_date"] = as_of_date
    output["current_inactive_days"] = (as_of_date - output["last_release_at"]).dt.total_seconds() / 86400.0
    output["current_blank_ratio"] = safe_ratio(output["current_inactive_days"], output["median_gap_days"])
    # Explicit names for the public current-status contract; retain the older
    # aliases above for compatibility with existing reports.
    output["current_days_since_last_release"] = output["current_inactive_days"]
    output["median_historical_release_interval_days"] = output["median_gap_days"]
    output["gap_ratio"] = output["current_blank_ratio"]
    for days in (30, 90, 180):
        recent = release[release["created_at"].gt(as_of_date - pd.Timedelta(days=days))].groupby("company_id")["release_id"].size()
        output[f"recent_{days}d_release_count"] = output["company_id"].map(recent).fillna(0).astype("int64")
        output[f"recent_{days}d_release_frequency"] = output[f"recent_{days}d_release_count"] / (days / 30.0)
    # Compare the recent 90d pace with the immediately preceding 90d pace.
    prior = release[release["created_at"].gt(as_of_date - pd.Timedelta(days=180)) & release["created_at"].le(as_of_date - pd.Timedelta(days=90))].groupby("company_id")["release_id"].size()
    output["prior_90d_release_count"] = output["company_id"].map(prior).fillna(0).astype("int64")
    output["recent_frequency_ratio"] = safe_ratio(output["recent_90d_release_count"].astype(float), output["prior_90d_release_count"].astype(float))
    output["continuity_data_quality"] = np.select(
        [output["total_release_count"].lt(2), output["median_gap_days"].isna(), output["prior_90d_release_count"].eq(0)],
        ["INSUFFICIENT_RELEASE_HISTORY", "MISSING_INTERVAL", "NO_PRIOR_90D_BASELINE"],
        default="OK",
    )
    output["continuity_data_quality_ok"] = output["continuity_data_quality"].eq("OK")
    output["continuity_state"] = pd.Series(
        np.select(
            [output["current_blank_ratio"].lt(1.2), output["current_blank_ratio"].lt(2.0)],
            ["NORMAL", "SLOWING"],
            default="AT_RISK",
        ), index=output.index,
    ).where(output["current_blank_ratio"].notna(), "UNKNOWN")
    output["heuristic_rule"] = True
    return output
