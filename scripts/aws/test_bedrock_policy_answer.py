import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))

from aws_integration.bedrock_policy_answer import answer_policy_question


SNAPSHOT = {
    "source_project": "official-youth-dashboard",
    "api_payloads": {
        "data_scope": {"survey_years": [109, 111, 113], "rounds": [{"survey_name": "official survey", "survey_year": 113}]},
        "policy_attention": {"topics": [], "disclaimer_zh": "not a performance score", "ranking_note_zh": "not causation"},
        "cards": {"cards": []}, "distributions": {"blocks": []}, "trend_charts": {"charts": []},
    },
}


class Client:
    def __init__(self):
        self.request = None

    def converse(self, **kwargs):
        self.request = kwargs
        return {"output": {"message": {"content": [{"text": "依現有資料回答。"}]}}}


class BedrockPolicyAnswerTests(unittest.TestCase):
    def test_answer_is_grounded_and_keeps_deterministic_provenance(self):
        client = Client()
        result = answer_policy_question("青年就業資料有哪些限制？", snapshot=SNAPSHOT, client=client, model_id="amazon.nova-lite-v1:0")
        self.assertEqual(result["answer"], "依現有資料回答。")
        self.assertEqual(result["sources"][0]["survey_name"], "official survey")
        self.assertIn("EVIDENCE JSON", client.request["messages"][0]["content"][0]["text"])

    def test_empty_question_is_rejected_before_model_call(self):
        with self.assertRaises(Exception):
            answer_policy_question("", snapshot=SNAPSHOT, client=Client())


if __name__ == "__main__":
    unittest.main()
