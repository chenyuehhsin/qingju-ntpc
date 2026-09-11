from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from career_recommender import (  # noqa: E402
    DOMAIN_TARGETS,
    SOURCE_OCCUPATIONS,
    build_dynamic_career_recommendations,
)


class DynamicCareerRecommenderTest(unittest.TestCase):
    def test_every_configured_scenario_returns_three_ranked_paths(self) -> None:
        for source in SOURCE_OCCUPATIONS:
            for domain in DOMAIN_TARGETS:
                with self.subTest(source=source, domain=domain):
                    result = build_dynamic_career_recommendations(source, domain)
                    self.assertEqual(len(result), 3)
                    self.assertTrue(result["dynamic_match_score"].is_monotonic_decreasing)
                    self.assertTrue(result["shared_top_skills"].astype(str).str.len().gt(0).all())

    def test_background_changes_the_ranking(self) -> None:
        admin = build_dynamic_career_recommendations("Administrative / Office Work", "科技 / AI")
        marketing = build_dynamic_career_recommendations("Marketing / Planning", "科技 / AI")
        self.assertNotEqual(
            admin["target_occupation_name"].tolist(),
            marketing["target_occupation_name"].tolist(),
        )

    def test_unknown_scenario_returns_no_fake_result(self) -> None:
        self.assertTrue(build_dynamic_career_recommendations("unknown", "科技 / AI").empty)
        self.assertTrue(build_dynamic_career_recommendations("Registered Nurses", "unknown").empty)


if __name__ == "__main__":
    unittest.main()
