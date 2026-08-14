"""Convert computed columns into structured, non-causal analysis facts."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _number(value: Any) -> float | int | None:
    if value is None or pd.isna(value):
        return None
    return value.item() if hasattr(value, "item") else value


def _metric_fact(row: pd.Series, metric: str) -> dict[str, Any] | None:
    if metric not in row:
        return None
    return {
        "current": _number(row[metric]),
        "self_ratio": _number(row.get(f"{metric}_self_ratio")),
        "self_state": row.get(f"{metric}_self_state", "UNKNOWN"),
        "prev": _number(row.get(f"prev_{metric}")),
        "prev_ratio": _number(row.get(f"{metric}_prev_ratio")),
        "prev_change_pct": _number(row.get(f"{metric}_prev_change_pct")),
        "peer_n": _number(row.get(f"{metric}_peer_n")),
        "peer_percentile": _number(row.get(f"{metric}_peer_percentile")),
        "peer_top_pct": _number(row.get(f"{metric}_peer_top_pct")),
    }


def candidate_findings(row: pd.Series, company: pd.Series | None) -> list[str]:
    findings: list[str] = []
    if row.get("pv_self_state") == "HIGH" and row.get("uu_self_state") == "NORMAL" and row.get("views_per_user_self_state") == "HIGH":
        findings.append("PVの伸びは閲覧者数の増加だけではなく、1人あたりの閲覧回数の増加と関連している可能性がある。")
    if row.get("pv_self_state") == "LOW" and row.get("uu_self_state") == "LOW" and row.get("views_per_user_self_state") == "NORMAL":
        findings.append("閲覧後の回遊よりも、閲覧者への到達量が弱かった傾向を示唆している。")
    if row.get("pv_self_state") == "NORMAL" and row.get("media_count_self_state") == "HIGH":
        findings.append("PVには大きな変化がない一方、外部媒体への広がりが通常より大きい可能性がある。")
    if company is not None and company.get("current_blank_ratio", 0) >= 2:
        findings.append("自社の通常配信ペースから大きく離れ、広報活動が止まり始めている可能性がある。")
    return findings[:3]


def analyze_release(row: pd.Series, company: pd.Series | None) -> dict[str, Any]:
    return {
        "company_id": _number(row["company_id"]),
        "release_id": _number(row["release_id"]),
        "created_at": row["created_at"].isoformat() if pd.notna(row["created_at"]) else None,
        "title": row.get("title"),
        "reaction": _metric_fact(row, "pv"),
        "audience": _metric_fact(row, "uu"),
        "view_depth": _metric_fact(row, "views_per_user"),
        "continuity": None if company is None else {
            "usual_gap_days": _number(company.get("median_gap_days")),
            "current_inactive_days": _number(company.get("current_inactive_days")),
            "blank_ratio": _number(company.get("current_blank_ratio")),
            "state": company.get("continuity_state", "UNKNOWN"),
        },
        "findings": candidate_findings(row, company),
        "heuristic_rule": True,
    }
