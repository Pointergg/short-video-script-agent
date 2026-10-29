"""Local tools. Every publishable product statement must be an exact source quote.

This deliberately conservative contract rejects unsupported paraphrases rather than
pretending a heuristic can establish arbitrary semantic entailment.
"""
import hashlib
import copy
import json
import math
import re


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def validate_request(request):
    missing = [k for k in ("topic", "audience", "platform", "style")
               if not isinstance(request.get(k), str) or not request[k].strip()]
    duration = request.get("target_seconds")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or not 1 <= duration <= 600:
        missing.append("target_seconds (1..600)")
    return missing


def validate_corpus(corpus):
    if not isinstance(corpus, dict) or not isinstance(corpus.get("materials"), list) or not isinstance(corpus.get("brand"), dict):
        raise ValueError("materials file needs materials array and brand object")
    seen = set()
    for material in corpus["materials"]:
        if not isinstance(material, dict) or any(not isinstance(material.get(key), str) or not material[key].strip() for key in ("id", "product", "provenance")):
            raise ValueError("each material needs nonempty id/product/provenance")
        if material["id"] in seen:
            raise ValueError("material IDs must be unique")
        seen.add(material["id"])
        for key in ("tags", "facts"):
            if not isinstance(material.get(key), list) or not material[key] or any(not isinstance(s, str) or not s.strip() for s in material[key]):
                raise ValueError("material tags/facts must be nonempty string arrays")
    for key in ("forbidden_terms", "neutral_copy", "visual_cues"):
        values = corpus["brand"].get(key)
        if not isinstance(values, list) or any(not isinstance(s, str) or not s.strip() for s in values):
            raise ValueError("brand rules must contain string arrays")
        if key != "forbidden_terms" and not values:
            raise ValueError("brand neutral_copy/visual_cues cannot be empty")


class Toolset:
    def __init__(self, corpus, request, fail_search=False):
        self.corpus, self.request = corpus, request
        self.fail_search = fail_search
        self.retrieved = {}
        self.draft = None
        self.estimate = None
        self.check = None
        self.calls = {"search_materials": 0, "write_script": 0, "estimate_duration": 0, "check_rules": 0}

    def execute(self, name, arguments):
        if name not in self.calls:
            raise ValueError("Unknown tool")
        self.calls[name] += 1
        return getattr(self, name)(**arguments)

    def search_materials(self, query):
        if not isinstance(query, str) or not 1 <= len(query) <= 200:
            raise ValueError("query must be 1..200 characters")
        if self.fail_search:
            return {"ok": False, "error": "SEARCH_UNAVAILABLE", "retryable": False}
        tokens = re.findall(r"[\w]+", query.lower())
        found = [m for m in self.corpus["materials"] if any(
            token in " ".join([m["product"], *m["tags"], *m["facts"]]).lower()
            or any(tag.lower() in token for tag in m["tags"]) for token in tokens)]
        self.retrieved.update({m["id"]: m for m in found})
        return {"ok": True, "materials": found, "count": len(found)}

    def write_script(self, script):
        if not isinstance(script, dict) or len(json.dumps(script, ensure_ascii=False)) > 24000:
            raise ValueError("script must be an object under 24000 characters")
        if set(script) != {"title", "scenes"} or not isinstance(script["title"], str):
            raise ValueError("script permits only title and scenes")
        scenes = script.get("scenes")
        if not isinstance(scenes, list) or not 1 <= len(scenes) <= 12:
            raise ValueError("script needs 1..12 scenes")
        for scene in scenes:
            if not isinstance(scene, dict) or not isinstance(scene.get("segments"), list) or not 1 <= len(scene["segments"]) <= 30:
                raise ValueError("each scene needs 1..30 segments")
            if not {"visual", "segments"} <= set(scene) or set(scene) - {"visual", "visual_seconds", "segments"} or not isinstance(scene["visual"], str):
                raise ValueError("scene permits only visual, visual_seconds and segments")
            hold = scene.get("visual_seconds", 0)
            if isinstance(hold, bool) or not isinstance(hold, (int, float)) or not math.isfinite(hold) or not 0 <= hold <= 600:
                raise ValueError("visual_seconds must be 0..600")
            for segment in scene["segments"]:
                if not isinstance(segment, dict) or not isinstance(segment.get("text"), str) or not 1 <= len(segment["text"]) <= 500:
                    raise ValueError("segment text must be 1..500 characters")
                if set(segment) - {"kind", "text", "source_id"} or not isinstance(segment.get("kind"), str):
                    raise ValueError("segment permits only kind, text and source_id")
                if "source_id" in segment and not isinstance(segment["source_id"], str):
                    raise ValueError("source_id must be a string")
        self.draft = copy.deepcopy(script)
        self.estimate = self.check = None
        return {"ok": True, "draft_id": fingerprint(script), "scene_count": len(scenes)}

    def estimate_duration(self):
        if self.draft is None:
            return {"ok": False, "error": "NO_DRAFT"}
        results, cursor = [], 0
        for index, scene in enumerate(self.draft["scenes"], 1):
            text = "".join(s["text"] for s in scene["segments"])
            units = len(re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9]+", text))
            punctuation = len(re.findall(r"[，。！？,.!?；;：:]", text))
            seconds = math.ceil(max(units / 4 + punctuation * 0.25 + 0.5, scene.get("visual_seconds", 0)) * 10) / 10
            sources = sorted({s.get("source_id") for s in scene["segments"] if s.get("source_id")})
            results.append({"scene": index, "start_seconds": round(cursor, 1), "seconds": seconds,
                            "end_seconds": round(cursor + seconds, 1), "source_ids": sources, "speech_units": units})
            cursor += seconds
        total = round(cursor, 1)
        self.estimate = {"ok": True, "draft_id": fingerprint(self.draft), "scenes": results,
                         "total_seconds": total, "limit_seconds": self.request["target_seconds"],
                         "within_limit": total <= self.request["target_seconds"],
                         "method": "4 Chinese characters or English words/sec + 0.25 sec/punctuation + 0.5 sec/scene; max with visual hold"}
        return self.estimate

    def check_rules(self):
        if self.draft is None:
            return {"ok": False, "error": "NO_DRAFT"}
        brand = self.corpus["brand"]
        issues, details = [], []
        products = {m["product"] for m in self.retrieved.values()}
        if self.draft.get("title") not in products:
            issues.append("TITLE_NOT_RETRIEVED_PRODUCT_NAME")
        fact_count = 0
        for index, scene in enumerate(self.draft["scenes"], 1):
            scene_issues, sources = [], []
            if scene.get("visual") not in brand["visual_cues"]:
                scene_issues.append("UNAPPROVED_VISUAL")
            for segment in scene["segments"]:
                text = segment["text"]
                if segment.get("kind") == "fact":
                    material = self.retrieved.get(segment.get("source_id"))
                    if material is None or text not in material["facts"]:
                        scene_issues.append("UNSUPPORTED_FACT")
                    else:
                        fact_count += 1
                        sources.append(material["id"])
                elif segment.get("kind") != "neutral" or text not in brand["neutral_copy"] or segment.get("source_id"):
                    scene_issues.append("UNAPPROVED_COPY")
            joined = "".join(s["text"] for s in scene["segments"])
            if any(term in joined for term in brand["forbidden_terms"]):
                scene_issues.append("FORBIDDEN_BRAND_TERM")
            issues.extend(f"scene_{index}:{issue}" for issue in sorted(set(scene_issues)))
            details.append({"scene": index, "passed": not scene_issues, "source_ids": sorted(set(sources)), "issues": sorted(set(scene_issues))})
        if not fact_count:
            issues.append("NO_SUPPORTED_FACT")
        self.check = {"ok": True, "draft_id": fingerprint(self.draft), "passed": not issues, "issues": issues, "scenes": details}
        return self.check

    def ready(self):
        return bool(self.draft and self.estimate and self.check and self.estimate["within_limit"] and self.check["passed"]
                    and self.estimate["draft_id"] == self.check["draft_id"] == fingerprint(self.draft))
