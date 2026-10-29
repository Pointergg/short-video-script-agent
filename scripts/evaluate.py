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
        ("query_rewrite", load("examples/inputs/query_rewrite.json"), corpus, {}, "completed"),
        ("step_limit", base, corpus, {"max_steps": 2}, "incomplete"),
    ]
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
        row = {"case": name, "expected": expected, "actual": result["status"], "passed": result["status"] == expected,
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
