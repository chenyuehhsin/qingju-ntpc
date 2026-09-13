import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))

from aws_integration.bedrock_policy_answer import answer_policy_question


class Registry:
    def execute(self, name, args):
        if name == "search_policy_knowledge":
            return {"evidence": [{"text": "official evidence"}], "sources": [{"source": "official"}], "limitations": ["scope limited"]}
        return {"data_period": {"year": "113"}, "limitations": ["period limitation"]}


class Client:
    def __init__(self):
        self.request = None

    def converse(self, **kwargs):
        self.request = kwargs
        return {"output": {"message": {"content": [{"text": "依現有資料回答。"}]}}}


class BedrockPolicyAnswerTests(unittest.TestCase):
    def test_answer_is_grounded_and_keeps_deterministic_provenance(self):
        client = Client()
        result = answer_policy_question("青年就業資料有哪些限制？", registry=Registry(), client=client, model_id="amazon.nova-lite-v1:0")
        self.assertEqual(result["answer"], "依現有資料回答。")
        self.assertEqual(result["sources"], [{"source": "official"}])
        self.assertIn("EVIDENCE JSON", client.request["messages"][0]["content"][0]["text"])

    def test_empty_question_is_rejected_before_model_call(self):
        with self.assertRaises(Exception):
            answer_policy_question("", registry=Registry(), client=Client())


if __name__ == "__main__":
    unittest.main()
