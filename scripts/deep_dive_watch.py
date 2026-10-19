"""Beijing-time editorial cadence monitor for the "拆一下" technical column.

Only a verified substantive new article or a substantive revision of an
existing article counts. This watcher creates an editor follow-up; it never
fabricates content, changes article dates, or auto-approves publication.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CADENCE_DAYS = 3


def content_date(article: dict) -> date:
    """Preserve original publication day; use latest editorial revision for cadence."""
    published = date.fromisoformat(article["published"])
    revised = date.fromisoformat(article.get("updated") or article["published"])
    if revised < published:
        raise ValueError("Article revision cannot predate publication")
    return revised


def report(deep: dict, hot: dict, today: date,
           threshold_days: int | None = None) -> dict:
    if threshold_days is None:
        threshold_days = deep.get("cadence_days", DEFAULT_CADENCE_DAYS)
    if type(threshold_days) is not int or threshold_days < 1:
        raise ValueError("threshold_days must be a positive integer")

    articles = deep.get("articles", [])
    if not isinstance(articles, list):
        raise ValueError("Missing deep-dive article list")
    rows = sorted(
        articles,
        key=lambda a: (content_date(a), a["published"], a["id"]),
        reverse=True,
    )
    latest = rows[0] if rows else None
    latest_date = content_date(latest) if latest else None
    age_days = max(0, (today - latest_date).days) if latest_date else None
    next_due = latest_date + timedelta(days=threshold_days) if latest_date else None
    stale = latest is None or (age_days is not None and age_days >= threshold_days)
    # latest published work is tracked separately; revising existing content
    # must not create a fake new-paper/publication date.
    latest_new = max(articles, key=lambda a: (a["published"], a["id"])) if articles else None

    seen = {hot_id for a in rows for hot_id in a.get("hot_ids", [])}
    options = []
    for x in hot.get("items", []):
        try:
            published = date.fromisoformat(x["published"])
        except (KeyError, ValueError, TypeError):
            continue
        if x.get("id") in seen or not 0 <= (today - published).days <= 30:
            continue
        if x.get("category") not in {"research", "model", "benchmark", "product"}:
            continue
        options.append({
            "id": x["id"], "title": x.get("title", ""),
            "published": str(published), "source": x.get("url", ""),
        })
    options = sorted(options, key=lambda x: (x["published"], x["id"]), reverse=True)[:6]
    return {
        "stale": stale,
        "today": str(today),
        "threshold_days": threshold_days,
        "latest_id": latest["id"] if latest else None,
        "latest_title": latest["title"] if latest else None,
        "latest_published": latest["published"] if latest else None,
        "latest_updated": latest.get("updated") if latest else None,
        "latest_content_date": str(latest_date) if latest_date else None,
        "latest_new_id": latest_new["id"] if latest_new else None,
        "latest_new_published": latest_new["published"] if latest_new else None,
        "next_due": str(next_due) if next_due else None,
        "age_days": age_days,
        "overdue_days": (max(0, (today - next_due).days) if next_due and stale else 0),
        "uncovered_hot_candidates": options,
        "note": (
            "只认原文、架构、实验或证据边界的实质新稿/修订；"
            "新论文与站内热点需编辑核验，不会自动发布深读，"
            "只改 updated 日期不能算完成更新。"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", default="", help="YYYY-MM-DD in Asia/Shanghai")
    parser.add_argument("--threshold-days", type=int, default=None)
    args = parser.parse_args()
    today = date.fromisoformat(args.today) if args.today else datetime.now(ZoneInfo("Asia/Shanghai")).date()
    deep = json.loads((ROOT / "data/deep-dives.json").read_text(encoding="utf-8"))
    hot = json.loads((ROOT / "data/hot.json").read_text(encoding="utf-8"))
    print(json.dumps(report(deep, hot, today, args.threshold_days), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
