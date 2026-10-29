"""Run the acceptance fixtures and persist actual results, never synthetic traces."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from script_agent.agent import run_agent
from script_agent.cli import render_markdown
from script_agent.providers import MockProvider, OpenAICompatibleProvider


def behavior_checks(name, result):
    trace = result["trace"]
    checks = {}
    if result["status"] == "completed":
        checks["latest_checks_pass"] = bool(result["checks"]["rules"]["passed"] and result["checks"]["duration"]["within_limit"])
    if name == "missing_info":
        checks["no_business_tools"] = all(t["action"] in ("request_info", "model_error") for t in trace)
    if name in ("impossible_duration", "tool_failure"):
        checks["explicit_model_failure"] = trace[-1]["action"] == "fail"
    if name == "query_rewrite":
        searches = [t["observation"] for t in trace if t["action"] == "search_materials"]
        checks["search_recovered"] = len(searches) >= 2 and searches[0].get("count") == 0 and any(s.get("count", 0) > 0 for s in searches[1:])
    if name == "controlled_over_duration":
        estimates = [t["observation"] for t in trace if t["action"] == "estimate_duration"]
        checks["observed_over_then_under"] = len(estimates) >= 2 and not estimates[0]["within_limit"] and estimates[-1]["within_limit"]
        checks["model_rewrote"] = any(t["action"] == "write_script" and t.get("origin") == "model" for t in trace)
    if name == "controlled_rule_repair":
        rules = [t["observation"] for t in trace if t["action"] == "check_rules"]
        checks["observed_rule_repair"] = len(rules) >= 2 and not rules[0]["passed"] and rules[-1]["passed"]
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["mock", "live"], default="mock")
    args = parser.parse_args()
    provider = MockProvider() if args.provider == "mock" else OpenAICompatibleProvider()
    load = lambda path: json.loads((ROOT / path).read_text(encoding="utf-8"))
    corpus = load("data/materials.json")
    base = load("examples/inputs/over_duration.json")
    cases = [
        ("normal", load("examples/inputs/normal.json"), corpus, {}, "completed"),
        ("over_duration", base, corpus, {}, "completed"),
        ("missing_info", load("examples/inputs/missing_info.json"), corpus, {}, "needs_input"),
        ("no_materials", base, load("data/no_materials.json"), {}, "needs_input"),
        ("tool_failure", base, corpus, {"fail_search": True}, "failed"),
        ("impossible_duration", load("examples/inputs/impossible_duration.json"), corpus, {}, "failed"),
        ("query_rewrite", load("examples/inputs/query_rewrite.json"), corpus,
         {"seed_query": "介绍这个新工具"} if args.provider == "live" else {}, "completed"),
        ("step_limit", base, corpus, {"max_steps": 2}, "incomplete"),
    ]
    if args.provider == "live":
        seed = load("examples/mock/normal/result.json")["script"]
        cases.append(("controlled_over_duration", base, corpus, {"seed_script": seed}, "completed"))
        bad_seed = json.loads(json.dumps(seed))
        bad_seed["scenes"][-1]["segments"][0]["text"] = "效率提升80%"
        cases.append(("controlled_rule_repair", base, corpus, {"seed_script": bad_seed, "seed_rule_check": True}, "completed"))
    root = ROOT / "examples" / args.provider
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, request, materials, options, expected in cases:
        result = run_agent(request, materials, provider, **options)
        folder = root / name
        folder.mkdir(exist_ok=True)
        for file, value in [("input.json", request), ("materials.json", materials), ("options.json", options), ("result.json", result)]:
            (folder / file).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (folder / "report.md").write_text(render_markdown(result), encoding="utf-8")
        behaviors = behavior_checks(name, result)
        row = {"case": name, "expected": expected, "actual": result["status"], "passed": result["status"] == expected and all(behaviors.values()), "behavior_checks": behaviors,
               "seconds": result["estimated_total_seconds"], "actions": [t["action"] for t in result["trace"]],
               "evidence": f"{name}/result.json"}
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False))
    summary = {"provider": args.provider, "model": provider.model,
               "scope": "Mock only validates engineering flow" if args.provider == "mock" else "Live model observations; inspect traces for acceptance",
               "cases": rows, "passed": sum(r["passed"] for r in rows), "total": len(rows)}
    (root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if all(r["passed"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
