import unittest
from scripts.evaluate import behavior_checks


class EvaluationTests(unittest.TestCase):
    def test_api_error_cannot_pass_impossible_duration_acceptance(self):
        result = {"status": "failed", "trace": [{"action": "model_error"}]}
        self.assertFalse(behavior_checks("impossible_duration", result)["explicit_model_failure"])

    def test_direct_search_hit_is_not_rewrite_evidence(self):
        result = {"status": "failed", "trace": [{"action": "search_materials", "observation": {"count": 1}}]}
        self.assertFalse(behavior_checks("query_rewrite", result)["search_recovered"])


if __name__ == "__main__":
    unittest.main()
