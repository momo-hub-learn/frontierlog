from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "huggingface-hot.json"
API_URL = "https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=20"
SOURCE_URL = "https://huggingface.co/models?sort=trending"

DROP_TAG_PREFIXES = (
    "license:", "base_model:", "region:", "deploy:", "arxiv:", "diffusers:"
)
DROP_TAGS = {
    "transformers", "safetensors", "gguf", "mlx", "conversational",
    "endpoints_compatible", "custom_code", "8-bit", "fp8"
}


def fetch_json(url: str) -> list[dict]:
    req = Request(url, headers={"User-Agent": "frontierlog-hf-sync/1.0"})
    with urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Hugging Face API returned HTTP {resp.status}")
        return json.load(resp)


def display_tags(raw: list[str], previous: list[str] | None = None) -> list[str]:
    if previous:
        return previous[:4]
    out: list[str] = []
    for tag in raw:
        if tag in DROP_TAGS or any(tag.startswith(p) for p in DROP_TAG_PREFIXES):
            continue
        if tag not in out:
            out.append(tag)
        if len(out) == 4:
            break
    return out


def normalize(items: list[dict], old: dict) -> dict:
    if len(items) < 20:
        raise RuntimeError(f"Expected at least 20 models, got {len(items)}")
    previous = {x["id"]: x for x in old.get("items", [])}
    rows = []
    for rank, item in enumerate(items[:20], start=1):
        model_id = item["id"]
        prior = previous.get(model_id, {})
        rows.append(
            {
                "rank": rank,
                "id": model_id,
                "url": f"https://huggingface.co/{model_id}",
                "trending_score": int(item.get("trendingScore") or 0),
                "likes": int(item.get("likes") or 0),
                "downloads": int(item.get("downloads") or 0),
                "task": item.get("pipeline_tag") or "other",
                "library": item.get("library_name") or "",
                "created_at": str(item.get("createdAt") or "").replace(".000Z", "Z"),
                "tags": display_tags(item.get("tags") or [], prior.get("tags")),
            }
        )
    scores = [x["trending_score"] for x in rows]
    if scores != sorted(scores, reverse=True):
        raise RuntimeError("Official API result is not descending by trendingScore")
    if len({x["id"] for x in rows}) != 20:
        raise RuntimeError("Duplicate model IDs in official top 20")
    return {
        "version": 1,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_url": SOURCE_URL,
        "api_url": API_URL,
        "source_scope": "Hugging Face Models · Trending · Top 20",
        "note": (
            "完整顺序来自 Hugging Face 官方 Models Trending / API 的 trendingScore 降序。"
            "trendingScore、likes、downloads 都是 Hugging Face 官方字段；"
            "它们代表平台热度与使用信号，不代表模型能力、质量或本站实测。"
        ),
        "items": rows,
    }


def main() -> None:
    old = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    fresh = normalize(fetch_json(API_URL), old)
    DATA_PATH.write_text(
        json.dumps(fresh, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
