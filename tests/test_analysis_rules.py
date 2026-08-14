from __future__ import annotations

import unittest
import numpy as np
import pandas as pd

from prtimes_analysis.compare import add_company_comparisons, add_peer_comparisons
from prtimes_analysis.continuation import add_continuation_flags


def releases(rows: list[tuple]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["company_id", "release_id", "created_at", "industry", "release_type", "pv", "uu"]).assign(created_at=lambda x: pd.to_datetime(x["created_at"]), views_per_user=lambda x: x["pv"] / x["uu"].replace(0, np.nan))


class AnalysisRuleTests(unittest.TestCase):
    def test_self_median_excludes_future_and_first_is_null(self) -> None:
        data = releases([(1, 1, "2025-01-01", "a", "t", 10, 10), (1, 2, "2025-02-01", "a", "t", 20, 10), (1, 3, "2025-03-01", "a", "t", 1000, 10)])
        result = add_company_comparisons(data, ["pv", "uu", "views_per_user"])
        self.assertTrue(pd.isna(result.loc[0, "pv_self_ratio"]))
        self.assertEqual(result.loc[1, "historical_pv_median"], 10)
        self.assertEqual(result.loc[1, "pv_self_ratio"], 2)

    def test_previous_and_zero_denominator(self) -> None:
        data = releases([(1, 1, "2025-01-01", "a", "t", 0, 2), (1, 2, "2025-01-02", "a", "t", 10, 4)])
        result = add_company_comparisons(data, ["pv", "uu", "views_per_user"])
        self.assertEqual(result.loc[1, "prev_release_id"], 1)
        self.assertTrue(pd.isna(result.loc[1, "pv_prev_ratio"]))
        self.assertTrue(pd.isna(result.loc[1, "pv_prev_change_pct"]))

    def test_gap_ratio_uses_only_prior_gaps(self) -> None:
        data = releases([(1, 1, "2025-01-01", "a", "t", 1, 1), (1, 2, "2025-01-11", "a", "t", 1, 1), (1, 3, "2025-02-10", "a", "t", 1, 1)])
        result = add_company_comparisons(data, ["pv", "uu", "views_per_user"])
        self.assertEqual(result.loc[2, "historical_gap_median"], 10)
        self.assertEqual(result.loc[2, "gap_ratio"], 3)

    def test_peer_excludes_future_and_requires_twenty(self) -> None:
        rows = [(i, i, "2025-01-01", "a", "t", i, 1) for i in range(1, 21)]
        rows.append((99, 99, "2025-02-01", "a", "t", 10, 1))
        data = add_peer_comparisons(releases(rows), ["pv"])
        current = data[data["release_id"] == 99].iloc[0]
        self.assertEqual(current["pv_peer_n"], 20)
        self.assertEqual(current["pv_peer_percentile"], 9 / 20)
        self.assertAlmostEqual(current["pv_peer_top_pct"], 11 / 20)
        self.assertTrue(pd.isna(data.iloc[0]["pv_peer_percentile"]))

    def test_peer_below_minimum_is_unavailable(self) -> None:
        rows = [(i, i, "2025-01-01", "a", "t", i, 1) for i in range(1, 20)]
        rows.append((99, 99, "2025-02-01", "a", "t", 10, 1))
        current = add_peer_comparisons(releases(rows), ["pv"]).query("release_id == 99").iloc[0]
        self.assertEqual(current["pv_peer_n"], 19)
        self.assertTrue(pd.isna(current["pv_peer_percentile"]))

    def test_continuation_and_right_censoring(self) -> None:
        data = releases([(1, 1, "2025-01-01", "a", "t", 1, 1), (1, 2, "2025-01-30", "a", "t", 1, 1), (2, 3, "2025-05-01", "a", "t", 1, 1)])
        data["release_seq"] = [1, 2, 1]
        result = add_continuation_flags(data)
        first = result[result.release_id == 1].iloc[0]
        recent = result[result.release_id == 3].iloc[0]
        self.assertTrue(first["continued_within_90d"])
        self.assertFalse(recent["continuation_eligible_90d"])

if __name__ == "__main__":
    unittest.main()
