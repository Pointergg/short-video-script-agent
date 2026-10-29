import json
import time
from .tools import Toolset, fingerprint, validate_request, validate_corpus


def run_agent(request, corpus, provider, max_steps=14, fail_search=False):
    if not isinstance(request, dict):
        raise ValueError("request must be an object")
    validate_corpus(corpus)
    if isinstance(max_steps, bool) or not isinstance(max_steps, int) or not 1 <= max_steps <= 50:
        raise ValueError("max_steps must be 1..50")
    missing = validate_request(request)
    tools = Toolset(corpus, request, fail_search)
    context = {"request": request, "missing": missing, "brand": corpus["brand"], "max_steps": max_steps}
    trace, questions = [], []
    status, message = "incomplete", "已达到执行步数上限，任务未完成。"
    started = time.monotonic()
    for step in range(1, max_steps + 1):
        try:
            decision = provider.decide(context, trace)
            if not isinstance(decision, dict) or not isinstance(decision.get("arguments"), dict) or not isinstance(decision.get("reason"), str):
                raise ValueError("Invalid action envelope")
            action, arguments = decision.get("action"), decision["arguments"]
            if not isinstance(action, str) or len(json.dumps(decision, ensure_ascii=False)) > 30000:
                raise ValueError("Invalid or oversized decision")
        except Exception as error:
            status, message = "failed", "模型调用或动作解析失败。"
            trace.append({"step": step, "action": "model_error", "arguments": {}, "reason": message,
                          "observation": {"ok": False, "error": str(error) if isinstance(error, RuntimeError) else type(error).__name__}})
            break
        if missing and action != "request_info":
            observation = {"ok": False, "error": "MISSING_REQUIRED_INPUT", "fields": missing}
        elif action == "finish":
            if tools.ready():
                status, message = "completed", "脚本通过当前素材、品牌规则与估算时长检查。"
                observation = {"ok": True, "status": status}
            else:
                observation = {"ok": False, "error": "FINAL_CHECKS_REQUIRED", "message": "须对最新草稿完成且通过时长与规则检查"}
        elif action == "request_info":
            questions = arguments.get("questions")
            if not isinstance(questions, list) or not questions or any(not isinstance(q, str) or not q.strip() for q in questions):
                questions = []
                observation = {"ok": False, "error": "QUESTIONS_REQUIRED"}
            else:
                status, message = "needs_input", "需要补充信息或素材。"
                observation = {"ok": True, "questions": questions}
        elif action == "fail":
            status, message = "failed", str(arguments.get("message", "模型报告无法满足要求。"))[:500]
            observation = {"ok": True, "status": status}
        else:
            try:
                observation = tools.execute(action, arguments)
            except (TypeError, ValueError, KeyError) as error:
                observation = {"ok": False, "error": "INVALID_TOOL_ARGUMENTS", "detail": str(error)[:300]}
        trace.append({"step": step, "action": action, "arguments": arguments,
                      "reason": decision["reason"][:500], "observation": observation})
        if status != "incomplete":
            break
    source_ids = sorted({s["source_id"] for scene in (tools.draft or {}).get("scenes", [])
                         for s in scene["segments"] if isinstance(s.get("source_id"), str)})
    risks = ["时长为文本启发式估算，未使用真实配音测量。", "创意范围受已批准文案和画面白名单限制；任意语义改写需另行人工审核。",
             "尚未进行真实平台政策、法律合规或最终视频审核。"]
    if provider.mode == "mock":
        risks.insert(0, "本次为离线 Mock：仅证明工程流程，不证明真实模型决策或创作质量。")
    if status != "completed":
        risks.append("任务未完成；draft 仅供排查，不能当作已验收脚本发布。")
    return {"schema_version": "1.0", "status": status, "message": message, "provider": provider.mode,
            "model": provider.model, "input": request, "corpus_sha256": fingerprint(corpus),
            "script": tools.draft if status == "completed" else None,
            "draft": tools.draft if status != "completed" else None,
            "estimated_total_seconds": (tools.estimate or {}).get("total_seconds"),
            "source_ids": source_ids, "sources": [tools.retrieved[s] for s in source_ids if s in tools.retrieved],
            "checks": {"duration": tools.estimate, "rules": tools.check}, "questions": questions,
            "risks": risks, "steps_used": len(trace), "max_steps": max_steps,
            "elapsed_seconds": round(time.monotonic() - started, 3), "trace": trace}
