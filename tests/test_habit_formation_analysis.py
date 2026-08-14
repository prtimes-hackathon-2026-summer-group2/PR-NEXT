from __future__ import annotations

import unittest

import pandas as pd

from prtimes_analysis.habit_formation_analysis import (
    build_timeline,
    calendar_timing,
    incentive_metrics,
    product_scale,
    reminder_timing,
    restart_habituation,
    retention_curve,
    rhythm_stability,
)


class HabitFormationAnalysisTests(unittest.TestCase):
    def test_rhythm_stability_compares_stable_and_nonstable_groups(self) -> None:
        as_of = pd.Timestamp("2026-12-31")
        frame = pd.DataFrame(
            {
                "company_id": [1, 2],
                "created_at": pd.to_datetime(["2025-01-01", "2025-01-01"]),
                "gap_ratio_m2": [1.0, 1.0],
                "gap_ratio_m1": [1.0, 3.0],
                "gap_ratio": [1.0, 1.0],
                "next_at": pd.to_datetime(["2025-03-01", "2025-05-01"]),
                "next_release_days": [59.0, 120.0],
            }
        )

        result, difference = rhythm_stability(frame, as_of)

        rates = result.set_index("rhythm_group")["retention_90d"]
        self.assertEqual(rates["stable"], 1.0)
        self.assertEqual(rates["highly_irregular"], 0.0)
        self.assertEqual(difference, 100.0)

    def test_rhythm_stability_without_stable_group_returns_nan_difference(self) -> None:
        frame = pd.DataFrame(
            {
                "company_id": [1],
                "created_at": pd.to_datetime(["2025-01-01"]),
                "gap_ratio_m2": [1.0],
                "gap_ratio_m1": [3.0],
                "gap_ratio": [1.0],
                "next_at": pd.to_datetime(["2025-01-31"]),
                "next_release_days": [30.0],
            }
        )

        result, difference = rhythm_stability(frame, pd.Timestamp("2026-12-31"))

        self.assertEqual(result["rhythm_group"].tolist(), ["highly_irregular"])
        self.assertTrue(pd.isna(difference))

    def test_rhythm_stability_accepts_small_legal_input(self) -> None:
        frame = pd.DataFrame(
            {
                "company_id": [1],
                "created_at": pd.to_datetime(["2025-12-31"]),
                "gap_ratio_m2": [float("nan")],
                "gap_ratio_m1": [float("nan")],
                "gap_ratio": [float("nan")],
                "next_at": pd.to_datetime([None]),
                "next_release_days": [float("nan")],
            }
        )

        result, difference = rhythm_stability(frame, pd.Timestamp("2026-01-01"))

        self.assertTrue(result.empty)
        self.assertTrue(pd.isna(difference))

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

    def test_restart_habituation_handles_no_restart_candidate(self) -> None:
        timeline = build_timeline(
            pd.DataFrame(
                {
                    "company_id": [1, 1, 1],
                    "release_id": [1, 2, 3],
                    "created_at": pd.to_datetime(
                        ["2025-01-01", "2025-01-11", "2025-01-21"]
                    ),
                }
            )
        )

        result = restart_habituation(timeline, pd.Timestamp("2026-12-31"))

        self.assertEqual(result["restart_company_n"], 0)
        self.assertTrue(pd.isna(result["reached_second_rate"]))

    def test_restart_habituation_single_company_restart(self) -> None:
        timeline = build_timeline(
            pd.DataFrame(
                {
                    "company_id": [1] * 8,
                    "release_id": list(range(1, 9)),
                    "created_at": pd.to_datetime(
                        [
                            "2020-01-01",
                            "2020-01-11",
                            "2020-01-21",
                            "2020-04-30",
                            "2020-05-10",
                            "2020-05-20",
                            "2020-05-30",
                            "2020-06-09",
                        ]
                    ),
                }
            )
        )

        result = restart_habituation(timeline, pd.Timestamp("2022-01-01"))

        self.assertEqual(result["restart_company_n"], 1)
        self.assertEqual(result["reached_fifth_rate"], 1.0)
        self.assertEqual(result["three_consecutive_normal_gap_rate"], 1.0)
        self.assertEqual(result["normal_3_subsequent_180d_retention"], 1.0)

    def test_incentive_metrics_preserves_normal_rates(self) -> None:
        frame = pd.DataFrame(
            {
                "company_id": [1],
                "release_count": [3],
                "historical_median_gap_before": [10.0],
                "next_release_days": [8.0],
                "next_at": pd.to_datetime(["2025-01-10"]),
                "next_2_at": pd.to_datetime(["2025-02-01"]),
            }
        )

        rules, yearly = incentive_metrics(frame, pd.Timestamp("2026-01-01"))

        self.assertTrue(rules["eligible_pair_share"].eq(1.0).all())
        self.assertTrue(rules["subsequent_90d_natural_rate"].eq(1.0).all())
        self.assertEqual(yearly["calendar_year"].unique().tolist(), [2025])

    def test_incentive_metrics_empty_pairs_return_nan_share(self) -> None:
        frame = pd.DataFrame(
            {
                "company_id": [1],
                "release_count": [1],
                "historical_median_gap_before": [float("nan")],
                "next_release_days": [float("nan")],
                "next_at": pd.to_datetime([None]),
                "next_2_at": pd.to_datetime([None]),
            }
        )

        rules, yearly = incentive_metrics(frame, pd.Timestamp("2026-01-01"))

        self.assertEqual(len(rules), 4)
        self.assertTrue(rules["eligible_pair_share"].isna().all())
        self.assertTrue(yearly.empty)
        self.assertEqual(
            yearly.columns.tolist(),
            ["rule", "calendar_year", "eligible_event_n"],
        )

    def test_incentive_metrics_uses_dynamic_year_range_after_2025(self) -> None:
        frame = pd.DataFrame(
            {
                "company_id": [1, 2],
                "release_count": [3, 3],
                "historical_median_gap_before": [10.0, 10.0],
                "next_release_days": [8.0, 8.0],
                "next_at": pd.to_datetime(["2026-01-10", "2028-01-10"]),
                "next_2_at": pd.to_datetime([None, None]),
            }
        )

        _, yearly = incentive_metrics(frame, pd.Timestamp("2029-01-01"))

        self.assertEqual(
            sorted(yearly["calendar_year"].unique().tolist()),
            [2026, 2027, 2028],
        )
        self.assertTrue(yearly.loc[yearly["calendar_year"].eq(2027), "eligible_event_n"].eq(0).all())

    def test_incentive_metrics_single_year_input_emits_only_that_year(self) -> None:
        frame = pd.DataFrame(
            {
                "company_id": [1, 2],
                "release_count": [3, 4],
                "historical_median_gap_before": [10.0, 20.0],
                "next_release_days": [8.0, 15.0],
                "next_at": pd.to_datetime(["2030-01-10", "2030-09-10"]),
                "next_2_at": pd.to_datetime([None, None]),
            }
        )

        _, yearly = incentive_metrics(frame, pd.Timestamp("2031-01-01"))

        self.assertEqual(yearly["calendar_year"].unique().tolist(), [2030])

    def test_incentive_metrics_accepts_empty_legal_input(self) -> None:
        frame = pd.DataFrame(
            {
                "company_id": pd.Series(dtype="int64"),
                "release_count": pd.Series(dtype="int64"),
                "historical_median_gap_before": pd.Series(dtype="float64"),
                "next_release_days": pd.Series(dtype="float64"),
                "next_at": pd.Series(dtype="datetime64[ns]"),
                "next_2_at": pd.Series(dtype="datetime64[ns]"),
            }
        )

        rules, yearly = incentive_metrics(frame, pd.Timestamp("2026-01-01"))

        self.assertEqual(len(rules), 4)
        self.assertTrue(rules["eligible_pair_share"].isna().all())
        self.assertTrue(yearly.empty)

    def test_product_scale_handles_single_company_and_zero_denominator(self) -> None:
        eligible = pd.DataFrame(
            {
                "company_id": [1, 1, 1],
                "release_count": [1, 2, 3],
                "previous_gap_days": [float("nan"), 10.0, 10.0],
                "created_at": pd.to_datetime(
                    ["2025-01-01", "2025-01-11", "2025-01-21"]
                ),
            }
        )
        scale = product_scale(eligible, pd.Timestamp("2025-02-05"))
        selected = scale.set_index("bucket").loc["1.5-2.0x"]
        self.assertEqual(selected["company_n"], 1)
        self.assertEqual(selected["all_evaluable_share"], 1.0)

        zero_denominator = eligible.assign(
            previous_gap_days=[float("nan"), 0.0, 0.0]
        )
        empty_scale = product_scale(
            zero_denominator, pd.Timestamp("2025-02-05")
        )
        self.assertEqual(empty_scale["company_n"].sum(), 0)
        self.assertTrue(empty_scale["all_evaluable_share"].isna().all())


if __name__ == "__main__":
    unittest.main()
