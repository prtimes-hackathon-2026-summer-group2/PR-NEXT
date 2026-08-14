"""Schema metadata used by the in-memory analysis contract."""

from __future__ import annotations

from dataclasses import dataclass

METRIC_CANDIDATES = {
    "PV": ("page_view", "pv"),
    "UU": ("unique_user", "uu"),
    "MEDIA_COUNT": ("media_count", "clipping_site_count"),
    "REFERRAL_SITE_COUNT": ("referral_site_count", "referrer_count"),
    "PC_SHARE": ("pc_share", "pc_percent"),
    "SMARTPHONE_SHARE": ("smartphone_share", "smartphone_percent"),
    "TABLET_SHARE": ("tablet_share", "tablet_percent"),
}


@dataclass(frozen=True)
class SchemaAudit:
    table_columns: dict[str, list[str]]
    available_metrics: list[dict[str, str]]
    unavailable_metrics: list[str]
    metric_columns: dict[str, str]

    def to_dict(self) -> dict:
        return {
            "table_columns": self.table_columns,
            "AVAILABLE_METRICS": self.available_metrics,
            "UNAVAILABLE_METRICS": self.unavailable_metrics,
            "metric_columns": self.metric_columns,
            "heuristic_rule": True,
        }
