import argparse
import json
from pathlib import Path
from .agent import run_agent
from .providers import MockProvider, OpenAICompatibleProvider


def render_markdown(result):
    lines = ["# 短视频脚本运行报告", "", f"- 状态：{result['status']}", f"- 运行模式：{result['provider']} / {result['model']}",
             f"- 说明：{result['message']}", f"- 预计总时长：{result['estimated_total_seconds']} 秒", "", "## 可编辑脚本", ""]
    script = result["script"]
    if script:
        lines += [f"标题：{script['title']}", "", "| 镜头 | 画面 | 旁白 / 字幕 | 起止秒 | 来源 | 规则 |", "|---|---|---|---|---|---|"]
        for scene, timing, check in zip(script["scenes"], result["checks"]["duration"]["scenes"], result["checks"]["rules"]["scenes"]):
            text = "".join(s["text"] for s in scene["segments"])
            lines.append(f"| {timing['scene']} | {scene['visual']} | {text} | {timing['start_seconds']}–{timing['end_seconds']} | {', '.join(timing['source_ids']) or '创意白名单'} | {'通过' if check['passed'] else '失败'} |")
    else:
        lines.append("无可交付脚本。未通过草稿可在 JSON 的 draft 字段查看。")
    lines += ["", "## 补充信息", "", *["- " + q for q in result["questions"]], "", "## 风险", "", *["- " + risk for risk in result["risks"]],
              "", "## 动作记录", "", "| 步骤 | 动作 | 简要依据 | 结果 |", "|---|---|---|---|"]
    for event in result["trace"]:
        obs = event["observation"]
        summary = {k: v for k, v in obs.items() if k in ("ok", "error", "count", "total_seconds", "within_limit", "passed", "issues", "status")}
        lines.append(f"| {event['step']} | {event['action']} | {event['reason']} | {json.dumps(summary, ensure_ascii=False)} |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="事实可追溯短视频脚本 Agent")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--materials", type=Path, default=Path("data/materials.json"))
    parser.add_argument("--provider", choices=("mock", "live"), default="mock")
    parser.add_argument("--max-steps", type=int, default=14)
    parser.add_argument("--simulate-search-failure", action="store_true", help="仅用于故障注入验证")
    parser.add_argument("--output", type=Path, default=Path("runs/latest"))
    args = parser.parse_args()
    try:
        request = json.loads(args.input.read_text(encoding="utf-8-sig"))
        corpus = json.loads(args.materials.read_text(encoding="utf-8-sig"))
        if not isinstance(request, dict) or not isinstance(corpus, dict):
            raise ValueError("input and materials must be JSON objects")
        provider = MockProvider() if args.provider == "mock" else OpenAICompatibleProvider()
        result = run_agent(request, corpus, provider, args.max_steps, args.simulate_search_failure)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (args.output / "report.md").write_text(render_markdown(result), encoding="utf-8")
        print(json.dumps({"status": result["status"], "provider": result["provider"], "seconds": result["estimated_total_seconds"], "output": str(args.output)}, ensure_ascii=False))
        return {"completed": 0, "needs_input": 2, "failed": 3, "incomplete": 4}[result["status"]]
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Configuration/input error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
