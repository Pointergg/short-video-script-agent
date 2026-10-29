"""Controlled feedback probes. Seed history is fixture-driven, not model-authored.

Every seeded observation is computed by the real local tools. Only the NEXT
decision is elicited from a live model; these probes supplement full live runs.
"""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from script_agent.providers import OpenAICompatibleProvider
from script_agent.tools import Toolset


def main():
    provider = OpenAICompatibleProvider()
    corpus = json.loads((ROOT / "data/materials.json").read_text(encoding="utf-8"))
    request = json.loads((ROOT / "examples/inputs/normal.json").read_text(encoding="utf-8"))
    fixture = json.loads((ROOT / "examples/mock/normal/result.json").read_text(encoding="utf-8"))["script"]
    rows = []
    for name, seconds, kind, expected in [
        ("duration_60", 60, "duration", ["check_rules"]),
        ("duration_30", 30, "duration", ["write_script", "fail"]),
        ("empty_search", 30, "empty", ["search_materials", "request_info"]),
        ("search_failure", 30, "failure", ["fail", "request_info"]),
        ("unsupported_fact", 30, "rules", ["write_script", "fail"]),
    ]:
        req, materials = dict(request, target_seconds=seconds), copy.deepcopy(corpus)
        if kind == "empty":
            materials["materials"] = []
        tools = Toolset(materials, req, fail_search=(kind == "failure"))
        trace = []
        def execute(action, arguments):
            observation = tools.execute(action, arguments)
            trace.append({"step": len(trace) + 1, "action": action, "arguments": arguments,
                          "reason": "受控测试夹具执行，非模型选择", "observation": observation})
        execute("search_materials", {"query": "字幕"})
        if kind in ("duration", "rules"):
            script = copy.deepcopy(fixture)
            if kind == "rules":
                script["scenes"][-1]["segments"][0]["text"] = "效率提升80%"
            execute("write_script", {"script": script})
            execute("estimate_duration", {})
            if kind == "rules":
                execute("check_rules", {})
        context = {"request": req, "missing": [], "brand": materials["brand"], "max_steps": 14}
        try:
            decision = provider.decide(context, trace)
            passed = isinstance(decision, dict) and decision.get("action") in expected
            row = {"probe": name, "provider": "live", "model": provider.model,
                   "history_origin": "test_fixture_with_actual_local_tool_results", "input": req,
                   "seeded_trace": trace, "actual_model_decision": decision,
                   "expected_actions": expected, "passed": passed}
        except Exception as error:
            row = {"probe": name, "provider": "live", "error_type": type(error).__name__, "passed": False}
        rows.append(row)
        print(json.dumps({"probe": name, "passed": row["passed"]}, ensure_ascii=False))
    folder = ROOT / "examples/live"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "feedback-probes.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if all(row["passed"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
