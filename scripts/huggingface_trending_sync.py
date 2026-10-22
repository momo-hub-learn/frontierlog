"""Refresh Hugging Face's web Trending order and API metrics independently.

The webpage owns the displayed rank.  The API owns trendingScore, likes,
downloads, task and library fields.  A failed source never advances the other
source's successful timestamp and never erases its last verified snapshot.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/huggingface-hot.json"
WEB_URL = "https://huggingface.co/models?sort=trending"
API_URL = "https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=20"
MODEL_ID = re.compile(r"^[^/?#\s]+/[^/?#\s]+$")


class TrendingPageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_card = 0
        self.ids: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article" and "overview-card-wrapper" in (attrs.get("class") or "").split():
            self.in_card += 1
        elif tag == "a" and self.in_card:
            model_id = (attrs.get("href") or "").strip("/").split("?", 1)[0]
            if MODEL_ID.fullmatch(model_id) and model_id not in self.ids:
                self.ids.append(model_id)

    def handle_endtag(self, tag):
        if tag == "article" and self.in_card:
            self.in_card -= 1


def parse_web_order(page: str, limit: int = 20) -> list[str]:
    parser = TrendingPageParser()
    parser.feed(page)
    if len(parser.ids) < limit:
        raise ValueError(f"Hugging Face Trending returned only {len(parser.ids)} model cards")
    return parser.ids[:limit]


def parse_api(payload: object, limit: int = 20) -> list[dict]:
    if not isinstance(payload, list) or len(payload) < limit:
        raise ValueError("Hugging Face API response has too few models")
    rows = []
    for rank, item in enumerate(payload[:limit], 1):
        if not isinstance(item, dict) or not MODEL_ID.fullmatch(str(item.get("id", ""))):
            raise ValueError("Hugging Face API response contains an invalid model ID")
        score = item.get("trendingScore")
        if type(score) not in (int, float):
            raise ValueError("Hugging Face API response is missing trendingScore")
        tags = []
        for tag in item.get("tags") or []:
            tag = str(tag).strip()
            if tag and len(tag) <= 48 and tag not in tags:
                tags.append(tag)
            if len(tags) == 4:
                break
        if not tags:
            tags = [item.get("pipeline_tag") or "未标注"]
        rows.append({
            "rank": rank,
            "id": item["id"],
            "url": "https://huggingface.co/" + item["id"],
            "trending_score": score,
            "likes": item.get("likes") if type(item.get("likes")) is int else None,
            "downloads": item.get("downloads") if type(item.get("downloads")) is int else None,
            "task": item.get("pipeline_tag") or "未标注",
            "library": item.get("library_name") or "未标注",
            "created_at": item.get("createdAt"),
            "tags": tags,
        })
    return rows


def stamp(now: datetime) -> str:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("A timezone-aware clock is required")
    return now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def update_state(data: dict, now: datetime, web_page: str | None, api_payload: object | None) -> dict:
    out = copy.deepcopy(data)
    now_text = stamp(now)
    web_ok = api_ok = False
    if web_page is not None:
        out["web_order"] = parse_web_order(web_page)
        out["web_fetched_at"] = now_text
        web_ok = True
    if api_payload is not None:
        out["items"] = parse_api(api_payload)
        out["api_fetched_at"] = now_text
        api_ok = True
    out["checked_at"] = now_text
    api_ids = [row["id"] for row in out.get("items", [])]
    out["web_order_matches_api"] = out.get("web_order", []) == api_ids[:len(out.get("web_order", []))]
    out["sync"] = {
        "status": "success" if web_ok and api_ok else "partial",
        "last_checked_at": now_text,
        "web_status": "success" if web_ok else "preserved",
        "api_status": "success" if api_ok else "preserved",
    }
    out["note"] = (
        "页面 # 严格使用官方 Models Trending 网页顺序；trendingScore、Likes、Downloads、"
        "task 与 library 来自官方 API。两个来源分别记录抓取时间，不拼成伪精确榜；"
        "平台指标只是热度/使用信号，不是能力成绩或本站实测。"
    )
    return out


def fetch_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; FrontierLog/1.0)"})
    with urlopen(req, timeout=30) as response:
        return response.read(5_000_001).decode("utf-8", "replace")


def fetch_json(url: str) -> object:
    return json.loads(fetch_text(url))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    data = json.loads(args.data.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    errors = []
    try:
        page = fetch_text(WEB_URL)
        parse_web_order(page)
    except Exception as exc:  # independent source preservation is intentional
        page = None
        errors.append("web: " + str(exc)[:180])
    try:
        payload = fetch_json(API_URL)
        parse_api(payload)
    except Exception as exc:  # independent source preservation is intentional
        payload = None
        errors.append("api: " + str(exc)[:180])
    if page is None and payload is None:
        print(json.dumps({"status": "error", "errors": errors}, ensure_ascii=False))
        return 1
    out = update_state(data, now, page, payload)
    target = args.out or args.data
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": out["sync"]["status"], "web": out["sync"]["web_status"],
                      "api": out["sync"]["api_status"], "errors": errors}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
