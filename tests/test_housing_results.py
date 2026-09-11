from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from components.map_view import build_housing_selection_map  # noqa: E402
from data_loader import MODE_ORDER, load_boundaries, load_dashboard_data  # noqa: E402
from recommendation_view import _housing_choices_by_mode, _livability_level  # noqa: E402


class HousingResultsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidates, cls.recommendations, _, cls.destination = load_dashboard_data("gangqian_neihu")

    def test_budget_filters_after_existing_mode_ranking(self) -> None:
        budget = 18_000
        choices = _housing_choices_by_mode(self.recommendations, self.candidates, budget)
        self.assertEqual(list(choices), MODE_ORDER)
        for mode, row in choices.items():
            self.assertIsNotNone(row, mode)
            self.assertLessEqual(float(row["rent"]), budget)
            eligible = self.recommendations[
                self.recommendations["preference_mode"].eq(mode)
                & pd.to_numeric(self.recommendations["rent"], errors="coerce").le(budget)
            ].sort_values("rank")
            self.assertEqual(str(row["candidate_name"]), str(eligible.iloc[0]["candidate_name"]))

    def test_no_result_is_explicit_when_budget_is_too_low(self) -> None:
        choices = _housing_choices_by_mode(self.recommendations, self.candidates, 5_000)
        self.assertTrue(all(row is None for row in choices.values()))

    def test_livability_level_does_not_invent_percentages(self) -> None:
        self.assertEqual(_livability_level(None, 0.3, 0.7), "資料不足")
        self.assertEqual(_livability_level(0.8, 0.3, 0.7), "高")
        self.assertEqual(_livability_level(0.5, 0.3, 0.7), "中")
        self.assertEqual(_livability_level(0.2, 0.3, 0.7), "基礎")

    def test_simplified_map_omits_technical_controls_and_labels(self) -> None:
        towns, cities = load_boundaries()
        row = _housing_choices_by_mode(self.recommendations, self.candidates, 18_000)[MODE_ORDER[0]]
        self.assertIsNotNone(row)
        rendered = build_housing_selection_map(
            MODE_ORDER[0], row, self.candidates, self.destination, towns, cities
        ).get_root().render()
        self.assertIn("大眾運輸通勤", rendered)
        self.assertIn("行政區租金中位數", rendered)
        self.assertNotIn("LayerControl", rendered)
        self.assertNotIn("Workplace anchor", rendered)
        self.assertNotIn("Top 3", rendered)
        self.assertNotIn("Top3", rendered)


if __name__ == "__main__":
    unittest.main()
