from __future__ import annotations

import unittest

import pandas as pd

from prtimes_analysis.build_metrics import build_company_analysis, build_release_analysis_from_inputs
from prtimes_analysis.initial_metric_validation import build_release_metrics
from prtimes_analysis.providers.base import AnalysisInputs


def inputs(release_rows, statistic_rows, companies=None, media=None):
    return AnalysisInputs(
        company=companies if companies is not None else pd.DataFrame({"company_id": [1], "company_name": ["A"], "industry_id": [1]}),
        release=pd.DataFrame(release_rows, columns=["company_id", "release_id", "created_at", "release_type_id", "title"]),
        release_statistics=pd.DataFrame(statistic_rows, columns=["company_id", "release_id", "page_view", "unique_user"]),
        industry=pd.DataFrame({"industry_id": [1], "industry_name": ["I"]}),
        release_type=pd.DataFrame({"release_type_id": [1], "release_type_name": ["T"]}),
        repost_media=media,
    )


class AnalysisMetricTests(unittest.TestCase):
    def test_initial_metrics_accept_dataframe_and_embargo_future_values(self):
        raw = pd.DataFrame(
            {
                "company_id": [1, 1, 1, 1],
                "release_id": [1, 2, 3, 4],
                "created_at": pd.to_datetime(
                    ["2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01"]
                ),
                "page_view": [10, 20, 30, 1_000_000],
                "unique_user": [2, 4, 5, 10],
            }
        )

        result = build_release_metrics(raw).set_index("release_id")

        self.assertEqual(result.at[3, "historical_pv_median_before"], 15.0)
        self.assertEqual(result.at[3, "relative_pv"], 2.0)

    def test_historical_percentile_recent_stats_and_log2_are_strictly_prior(self):
        value = inputs(
            [(1, 1, "2025-01-01", 1, "one"), (1, 2, "2025-02-01", 1, "two"), (1, 3, "2025-03-01", 1, "three"), (1, 4, "2025-04-01", 1, "future")],
            [(1, 1, 10, 1), (1, 2, 20, 2), (1, 3, 30, 3), (1, 4, 1_000_000, 4)],
        )
        analysis, _ = build_release_analysis_from_inputs(value)
        third = analysis.query("release_id == 3").iloc[0]
        self.assertEqual(third["historical_pv_median"], 15)
        self.assertEqual(third["recent_3_pv_median"], 15)
        self.assertEqual(third["historical_pv_percentile"], 1.0)
        self.assertAlmostEqual(third["log2_pv_self_ratio"], 1.0)

    def test_media_new_repeat_is_point_in_time_safe(self):
        media = pd.DataFrame({"company_id": [1, 1, 1], "release_id": [1, 2, 3], "media_name": ["A", "A", "B"]})
        value = inputs(
            [(1, 1, "2025-01-01", 1, "one"), (1, 2, "2025-02-01", 1, "two"), (1, 3, "2025-03-01", 1, "three")],
            [(1, 1, 1, 1), (1, 2, 1, 1), (1, 3, 1, 1)], media=media,
        )
        analysis, _ = build_release_analysis_from_inputs(value)
        self.assertEqual(analysis.query("release_id == 1").iloc[0]["new_media_count"], 1)
        second = analysis.query("release_id == 2").iloc[0]
        self.assertEqual(second["new_media_count"], 0)
        self.assertEqual(second["repeat_media_count"], 1)
        self.assertEqual(analysis.query("release_id == 3").iloc[0]["new_media_count"], 1)

    def test_peer_falls_back_to_industry_when_type_group_is_small(self):
        companies = pd.DataFrame({"company_id": list(range(1, 22)), "company_name": [str(n) for n in range(1, 22)], "industry_id": [1] * 21})
        release_rows = [(number, number, "2025-01-01", 1, "old") for number in range(1, 21)] + [(21, 21, "2025-02-01", 2, "current")]
        stats = [(number, number, number, 1) for number in range(1, 21)] + [(21, 21, 10, 1)]
        value = inputs(release_rows, stats, companies=companies)
        value = AnalysisInputs(**{**value.__dict__, "release_type": pd.DataFrame({"release_type_id": [1, 2], "release_type_name": ["old", "new"]})})
        analysis, _ = build_release_analysis_from_inputs(value)
        current = analysis.query("release_id == 21").iloc[0]
        self.assertEqual(current["pv_peer_group_level"], "industry")
        self.assertEqual(current["pv_peer_n"], 20)

    def test_current_status_has_frequency_and_quality_fields(self):
        value = inputs(
            [(1, 1, "2025-01-01", 1, "one"), (1, 2, "2025-03-01", 1, "two"), (1, 3, "2025-06-01", 1, "three")],
            [(1, 1, 1, 1), (1, 2, 1, 1), (1, 3, 1, 1)],
        )
        release, _ = build_release_analysis_from_inputs(value)
        company = build_company_analysis(release).iloc[0]
        self.assertEqual(company["recent_90d_release_count"], 1)
        self.assertIn(company["continuity_data_quality"], {"OK", "NO_PRIOR_90D_BASELINE"})
        self.assertIn("current_days_since_last_release", company.index)


if __name__ == "__main__":
    unittest.main()
