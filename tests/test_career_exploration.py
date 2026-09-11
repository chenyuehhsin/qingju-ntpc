from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from components.career_evidence_viewer import (  # noqa: E402
    _beauty_representative_paths,
    _build_path_view_models,
    _technology_representative_paths,
)
from components.career_exploration import _metric_dots  # noqa: E402


class CareerExplorationDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidates = pd.read_csv(ROOT / "outputs/career/nursing_to_technology_candidates_v35.csv")
        cls.training = pd.read_csv(ROOT / "outputs/career/nursing_to_technology_training_v4.csv")
        cls.beauty = pd.read_csv(ROOT / "outputs/career/nursing_to_beauty_candidates_phase5.csv")

    def test_each_domain_produces_three_unique_paths(self) -> None:
        for frame in [
            _technology_representative_paths(self.candidates, self.training),
            _beauty_representative_paths(self.beauty),
        ]:
            models = _build_path_view_models(frame)
            self.assertEqual(len(models), 3)
            self.assertEqual(len({model.occupation_id for model in models}), 3)

    def test_view_models_only_use_qualitative_metrics(self) -> None:
        frame = _technology_representative_paths(self.candidates, self.training)
        for model in _build_path_view_models(frame):
            self.assertIn(model.transition_distance, {"近", "中", "遠", "資料不足"})
            self.assertIn(model.skill_reuse, {"低", "中低", "中", "中高", "高", "資料不足"})
            self.assertNotIn("%", model.transition_distance + model.skill_reuse + model.learning_burden)

    def test_technology_aggregate_market_signal_stays_unverified(self) -> None:
        frame = _technology_representative_paths(self.candidates, self.training)
        signals = {model.market_signal for model in _build_path_view_models(frame)}
        self.assertEqual(signals, {"市場訊號待驗證"})

    def test_card_metrics_render_icons_and_favourable_dot_levels(self) -> None:
        self.assertEqual(_metric_dots("近", "transition_distance").count("is-active"), 3)
        self.assertEqual(_metric_dots("高", "skill_reuse").count("is-active"), 3)
        self.assertEqual(_metric_dots("低", "learning_burden").count("is-active"), 3)
        self.assertEqual(_metric_dots("市場訊號待驗證", "market_signal").count("is-active"), 1)


if __name__ == "__main__":
    unittest.main()
