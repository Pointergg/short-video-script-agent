import copy
import json
from pathlib import Path
import unittest

from script_agent.agent import run_agent
from script_agent.providers import MockProvider
from script_agent.tools import Toolset, validate_request

ROOT = Path(__file__).resolve().parents[1]


class SequenceProvider:
    mode, model = "mock", "adversarial-replay"

    def __init__(self, actions):
        self.actions = iter(actions)

    def decide(self, context, trace):
        return next(self.actions)


def decision(action, **arguments):
    return {"action": action, "arguments": arguments, "reason": "test stimulus"}


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads((ROOT / "data/materials.json").read_text(encoding="utf-8"))
        self.request = json.loads((ROOT / "examples/inputs/over_duration.json").read_text(encoding="utf-8"))
        self.script = {"title": "字幕助手", "scenes": [{"visual": "字幕功能文字卡片", "visual_seconds": 0,
            "segments": [{"kind": "fact", "text": "支持字幕", "source_id": "P01"}]}]}

    def run_mock(self, **kwargs):
        return run_agent(self.request, self.corpus, MockProvider(), **kwargs)

    def tools(self):
        tools = Toolset(self.corpus, self.request)
        tools.search_materials("字幕")
        return tools

    def test_over_duration_is_revised_then_rechecked(self):
        result = self.run_mock()
        self.assertEqual(result["status"], "completed")
        estimates = [t["observation"] for t in result["trace"] if t["action"] == "estimate_duration"]
        self.assertFalse(estimates[0]["within_limit"])
        self.assertTrue(estimates[1]["within_limit"])
        self.assertEqual(result["source_ids"], ["P01"])
        self.assertEqual(result["checks"]["rules"]["scenes"][-1]["source_ids"], ["P01"])
        for timing, check in zip(result["checks"]["duration"]["scenes"], result["checks"]["rules"]["scenes"]):
            self.assertEqual(timing["source_ids"], check["source_ids"])

    def test_changing_duration_changes_next_action(self):
        short = self.run_mock()
        self.request["target_seconds"] = 60
        long = self.run_mock()
        def after_estimate(result):
            idx = next(i for i, t in enumerate(result["trace"]) if t["action"] == "estimate_duration")
            return result["trace"][idx + 1]["action"]
        self.assertEqual(after_estimate(short), "write_script")
        self.assertEqual(after_estimate(long), "check_rules")

    def test_no_materials_rewrites_then_requests_input(self):
        self.corpus["materials"] = []
        result = self.run_mock()
        self.assertEqual(result["status"], "needs_input")
        self.assertEqual([t["action"] for t in result["trace"]], ["search_materials", "search_materials", "request_info"])
        self.assertIsNone(result["script"])

    def test_query_rewrite_can_recover(self):
        self.request["topic"] = "介绍这个工具"
        result = self.run_mock()
        self.assertEqual(result["trace"][0]["observation"]["count"], 0)
        self.assertEqual(result["trace"][1]["observation"]["count"], 1)
        self.assertEqual(result["status"], "completed")

    def test_missing_info_never_calls_business_tools(self):
        del self.request["audience"]
        result = self.run_mock()
        self.assertEqual(result["status"], "needs_input")
        self.assertIn("audience", result["questions"])
        self.assertEqual(result["steps_used"], 1)

    def test_tool_failure_is_not_success(self):
        result = self.run_mock(fail_search=True)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["trace"][0]["observation"]["error"], "SEARCH_UNAVAILABLE")
        self.assertIsNone(result["script"])

    def test_step_limit_explicitly_incomplete(self):
        result = self.run_mock(max_steps=2)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["steps_used"], 2)
        self.assertIsNone(result["script"])

    def test_impossible_duration_fails(self):
        self.request["target_seconds"] = 1
        self.assertEqual(self.run_mock()["status"], "failed")

    def test_fabricated_eighty_percent_is_rejected(self):
        tools = self.tools()
        self.script["scenes"][0]["segments"][0]["text"] = "效率提升80%"
        tools.write_script(self.script)
        self.assertFalse(tools.check_rules()["passed"])
        self.assertIn("scene_1:UNSUPPORTED_FACT", tools.check["issues"])
        self.assertFalse(tools.ready())

    def test_forged_source_and_neutral_claim_and_visual_are_rejected(self):
        for mutation in ("source", "neutral", "visual", "title"):
            with self.subTest(mutation=mutation):
                tools = self.tools()
                script = copy.deepcopy(self.script)
                if mutation == "source": script["scenes"][0]["segments"][0]["source_id"] = "P99"
                if mutation == "neutral": script["scenes"][0]["segments"] = [{"kind": "neutral", "text": "自动识别，效率提升80%"}]
                if mutation == "visual": script["scenes"][0]["visual"] = "展示不存在的自动识别界面"
                if mutation == "title": script["title"] = "效率提升80%"
                tools.write_script(script)
                self.assertFalse(tools.check_rules()["passed"])

    def test_unretrieved_fact_not_accepted(self):
        tools = Toolset(self.corpus, self.request)
        tools.write_script(self.script)
        self.assertFalse(tools.check_rules()["passed"])

    def test_edit_invalidates_checks(self):
        tools = self.tools()
        tools.write_script(self.script)
        tools.estimate_duration()
        tools.check_rules()
        self.assertTrue(tools.ready())
        revised = copy.deepcopy(self.script)
        revised["scenes"][0]["visual_seconds"] = 45
        tools.write_script(revised)
        self.assertIsNone(tools.check)
        self.assertIsNone(tools.estimate)
        self.assertFalse(tools.ready())

    def test_premature_finish_is_rejected(self):
        provider = SequenceProvider([decision("finish"), decision("fail", message="stop")])
        result = run_agent(self.request, self.corpus, provider)
        self.assertEqual(result["trace"][0]["observation"]["error"], "FINAL_CHECKS_REQUIRED")
        self.assertEqual(result["status"], "failed")

    def test_invalid_tool_arguments_can_be_corrected(self):
        provider = SequenceProvider([decision("search_materials", bad="x"), decision("search_materials", query="字幕"), decision("fail", message="test end")])
        result = run_agent(self.request, self.corpus, provider)
        self.assertEqual(result["trace"][0]["observation"]["error"], "INVALID_TOOL_ARGUMENTS")
        self.assertEqual(result["trace"][1]["observation"]["count"], 1)

    def test_malformed_model_response_is_recorded(self):
        result = run_agent(self.request, self.corpus, SequenceProvider([{"action": "finish"}]))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["trace"][0]["action"], "model_error")

    def test_duration_matches_scene_timeline(self):
        result = self.run_mock()
        timing = result["checks"]["duration"]
        self.assertEqual(round(sum(s["seconds"] for s in timing["scenes"]), 1), timing["total_seconds"])
        self.assertEqual(timing["scenes"][-1]["end_seconds"], timing["total_seconds"])

    def test_nonfinite_and_boolean_duration_rejected(self):
        for value in (float("nan"), float("inf"), True, -1, 0):
            self.request["target_seconds"] = value
            self.assertTrue(validate_request(self.request))

    def test_failed_rules_can_be_repaired_and_rechecked(self):
        bad = copy.deepcopy(self.script)
        bad["scenes"][0]["segments"][0]["text"] = "效率提升80%"
        provider = SequenceProvider([
            decision("search_materials", query="字幕"), decision("write_script", script=bad),
            decision("estimate_duration"), decision("check_rules"),
            decision("write_script", script=self.script), decision("estimate_duration"),
            decision("check_rules"), decision("finish")])
        result = run_agent(self.request, self.corpus, provider)
        self.assertFalse(result["trace"][3]["observation"]["passed"])
        self.assertTrue(result["trace"][6]["observation"]["passed"])
        self.assertEqual(result["status"], "completed")

    def test_invalid_material_file_is_rejected(self):
        self.corpus["materials"].append(self.corpus["materials"][0])
        with self.assertRaisesRegex(ValueError, "unique"):
            self.run_mock()

    def test_oversized_or_negative_draft_is_rejected(self):
        tools = self.tools()
        self.script["scenes"][0]["visual_seconds"] = -1
        with self.assertRaises(ValueError):
            tools.write_script(self.script)

    def test_draft_is_owned_by_tool_not_provider(self):
        tools = self.tools()
        tools.write_script(self.script)
        self.script["title"] = "被外部对象修改"
        self.assertEqual(tools.draft["title"], "字幕助手")

    def test_hidden_unchecked_copy_fields_are_rejected(self):
        tools = self.tools()
        self.script["scenes"][0]["extra_caption"] = "效率提升80%"
        with self.assertRaisesRegex(ValueError, "permits only"):
            tools.write_script(self.script)


if __name__ == "__main__":
    unittest.main()
