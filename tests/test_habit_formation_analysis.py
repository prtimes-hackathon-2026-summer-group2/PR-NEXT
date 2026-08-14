from __future__ import annotations

import unittest

import pandas as pd

from prtimes_analysis.habit_formation_analysis import (
    build_timeline,
    calendar_timing,
    reminder_timing,
    retention_curve,
)


class HabitFormationAnalysisTests(unittest.TestCase):
    def test_timeline_and_calendar_metrics_use_only_prior_gaps(self) -> None:
        release = pd.DataFrame(
            {
                "company_id": [1, 1, 1, 1],
                "release_id": [4, 1, 3, 2],
                "created_at": pd.to_datetime(
                    ["2025-03-12", "2025-01-01", "2025-02-10", "2025-01-11"]
                ),
            }
        )

        timeline = build_timeline(release).set_index("release_id")

        self.assertEqual(timeline.at[3, "historical_median_gap_before"], 10.0)
        self.assertEqual(timeline.at[3, "gap_ratio"], 3.0)
        calendar = calendar_timing(timeline.reset_index())
        self.assertEqual(calendar.iloc[0]["pair_n"], 1)
        self.assertEqual(calendar.iloc[0]["deviation_median_days"], 20.0)

    def test_retention_curve_right_censors_each_window(self) -> None:
        as_of = pd.Timestamp("2026-01-31")
        frame = pd.DataFrame(
            {
                "release_count": [3, 3],
                "created_at": pd.to_datetime(["2026-01-01", "2026-01-15"]),
                "next_at": pd.to_datetime(["2026-01-20", None]),
                "next_release_days": [19.0, float("nan")],
            }
        )

        result = retention_curve(frame, as_of).set_index("release_count")

        self.assertEqual(result.at[3, "eligible_30d_n"], 1)
        self.assertEqual(result.at[3, "retention_30d"], 1.0)
        self.assertEqual(result.at[3, "eligible_90d_n"], 0)

    def test_reminder_event_requires_release_after_threshold(self) -> None:
        as_of = pd.Timestamp("2026-03-31")
        frame = pd.DataFrame(
            {
                "company_id": [1, 2, 3, 4],
                "created_at": pd.to_datetime(
                    ["2026-01-01", "2026-01-01", "2026-01-01", "2026-03-20"]
                ),
                "historical_median_gap_before": [10.0, 10.0, 10.0, 10.0],
                # Company 3 released before the 1.0x event and must not enter it.
                "next_at": pd.to_datetime(
                    ["2026-01-20", None, "2026-01-05", None]
                ),
            }
        )

        result = reminder_timing(frame, as_of)
        event = result[result["threshold"].eq(1.0) & result["window_days"].eq(30)].iloc[0]

        self.assertEqual(event["eligible_event_n"], 2)
        self.assertEqual(event["redispatched_n"], 1)
        self.assertEqual(event["natural_redispatch_rate"], 0.5)


if __name__ == "__main__":
    unittest.main()
