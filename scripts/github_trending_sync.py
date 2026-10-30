"""Refresh GitHub Trending from its public Today page + GitHub Repository API.

Official Trending rank and "stars today" are NEVER inferred from API star counts.
Curated watchlist repositories have verified API totals but NO Trending rank.
A failed fetch preserves checked_at and the previously verified ranking.
"""
from __future__ import annotations

import argparse
import copy
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/github-hot.json"
TRENDING_URL = "https://github.com/trending?since=daily"
REPO_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
ARTICLE_RE = re.compile(
    r"<article\b[^>]*\bclass\s*=\s*['\"][^'\"]*\bBox-row\b[^'\"]*['\"][^>]*>(.*?)</article\s*>",
    re.I | re.S,
)
STARS_TODAY_RE = re.compile(r"\b([\d,]+)\s+stars?\s+today\b", re.I)
AI_TERMS = re.compile(
    r"\b(ai|llm|agents?|agentic|mcp|language models?|neural|machine learning|"
    r"deep learning|inference|diffusion|rag|transformers?|coding assistant|"
    r"prompt engineering|generative|claude|tts|text[- ]to[- ]speech|"
    r"speech generation|voice cloning)\b", re.I
)
CATEGORIES = {
    "reverse-engineering": "AI 逆向工程",
    "agent-memory": "Agent Memory",
    "agent-harness": "Agent Harness",
    "agent-runtime": "Agent Runtime",
    "agent-interface": "Agent Interface",
    "agent-skills": "Agent Skills",
    "model-optimization": "模型优化",
    "ai-learning": "AI 学习 / 工程",
    "ai-tools": "AI 工具 / 开源",
    "other": "其他开源",
}


class ArticleText(HTMLParser):
    """Only read repository links inside the article h2; never invent positions."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.repo = ""
        self.description = ""
        self.language = ""
        self.text = []
        self.in_heading = False
        self.in_description = False
        self.in_language = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "h2":
            self.in_heading = True
        if tag == "a" and self.in_heading:
            href = a.get("href", "").strip("/").split("?", 1)[0]
            if not self.repo and REPO_RE.fullmatch(href):
                self.repo = href
        if tag == "p" and "col-9" in (a.get("class") or "").split():
            self.in_description = True
        if a.get("itemprop") == "programmingLanguage":
            self.in_language = True

    def handle_data(self, data):
        self.text.append(data)
        if self.in_description:
            self.description += data
        if self.in_language:
            self.language += data

    def handle_endtag(self, tag):
        if tag == "h2":
            self.in_heading = False
        if tag == "p":
            self.in_description = False
        if tag == "span":
            self.in_language = False


def parse_trending(page: str, min_count: int = 6) -> list[dict]:
    if not isinstance(page, str):
        raise ValueError("Trending response is not HTML text")
    articles = ARTICLE_RE.findall(page)
    if len(articles) < min_count:
        raise ValueError("GitHub Trending structure missing: too few Box-row articles")
    out = []
    seen = set()
    for rank, content in enumerate(articles, 1):
        parser = ArticleText()
        parser.feed(content)
        if not parser.repo:
            continue
        if parser.repo.lower() in seen:
            raise ValueError("Duplicate repository on official Trending page")
        seen.add(parser.repo.lower())
        plain = " ".join(html.unescape(" ".join(parser.text)).split())
        match = STARS_TODAY_RE.search(plain)
        if not match:
            raise ValueError("Missing official stars-today value for " + parser.repo)
        out.append({
            "repo": parser.repo, "rank": rank,
            "stars_today": int(match.group(1).replace(",", "")),
            "description": " ".join(parser.description.split()),
            "language": " ".join(parser.language.split())
        })
    if len(out) < min_count or len(out) < len(articles) * 0.75:
        raise ValueError("Failed to parse enough official Trending rows")
    return out


def request_json(url: str, token: str = "") -> dict:
    if not url.startswith("https://api.github.com/repos/"):
        raise ValueError("Only GitHub Repository API URLs are allowed")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "FrontierLog-GithubTrending/1.0",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    with urlopen(Request(url, headers=headers), timeout=16) as response:
        obj = json.load(response)
    if not isinstance(obj, dict) or type(obj.get("stargazers_count")) is not int:
        raise ValueError("Malformed GitHub Repository API response")
    return obj


def request_trending() -> str:
    headers = {
        "Accept": "text/html", "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": "Mozilla/5.0 (compatible; FrontierLog/1.0; +https://github.com/momo-hub-learn/frontierlog)"
    }
    with urlopen(Request(TRENDING_URL, headers=headers), timeout=25) as response:
        raw = response.read(5_000_001)
    if len(raw) > 5_000_000:
        raise ValueError("Trending HTML exceeds expected size")
    return raw.decode("utf-8", "replace")


def metadata(repo: str, token: str = "") -> dict:
    if not REPO_RE.fullmatch(repo):
        raise ValueError("Unsafe GitHub repository name")
    return request_json("https://api.github.com/repos/" + quote(repo, safe="/"), token)


def classify(repo: str, description: str, old: dict | None = None,
             topics: list[str] | None = None) -> tuple[str, bool, list[str]]:
    # Repository topics are official repository metadata and often carry the
    # only explicit AI signal for terse Trending descriptions (for example,
    # an IDE may say only "vibe code" on the public list).  Treat them as
    # classification evidence, while keeping the displayed description intact.
    topic_text = " ".join(x for x in (topics or []) if isinstance(x, str))
    q = (repo + " " + description + " " + topic_text).lower()
    detected_ai = bool(AI_TERMS.search(q))
    # Preserve reviewed labels unless fresh official text provides a strong AI
    # signal that corrects a previous false negative. This keeps editorial
    # categories stable without leaving newly explicit Claude/TTS repos out of
    # the site's AI-only subset.
    if (old and old.get("category") and isinstance(old.get("ai_related"), bool)
            and old.get("tags") and (old["ai_related"] or not detected_ai)):
        return old["category"], old["ai_related"], old["tags"]
    if any(key in q for key in ("reverse engineer", "decompil", "ghidra", "binary analysis")):
        return "reverse-engineering", bool(AI_TERMS.search(q) or "morluto/rea" in repo.lower()), ["Reverse Engineering", "Agent", "MCP"]
    if "agent" in q and ("memory" in q or "memories" in q):
        return "agent-memory", True, ["Agent", "Memory", "AI"]
    if "harness" in q:
        return "agent-harness", True, ["Agent", "Harness", "Tools"]
    if "agent" in q and ("runtime" in q or "orchestrat" in q):
        return "agent-runtime", True, ["Agent", "Runtime", "AI"]
    if "agent" in q and any(k in q for k in ("tool", "cli", "mcp", "interface")):
        return "agent-interface", True, ["Agent", "Tools", "MCP"]
    if ("agent" in q or "claude" in q) and "skill" in q:
        return "agent-skills", True, ["Agent", "Skills", "Workflow"]
    if AI_TERMS.search(q):
        return "ai-tools", True, ["AI", "Open Source", "GitHub"]
    return "other", False, ["Open Source", "GitHub"]


def utc_stamp(now: datetime) -> str:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("A timezone-aware clock is required")
    return now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def history_for(old: dict, stars: int, stamp: str) -> list[dict]:
    now = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    recent = []
    for p in old.get("star_history", []):
        try:
            then = datetime.fromisoformat(p["at"].replace("Z", "+00:00"))
            if 0 < (now - then).total_seconds() < 48 * 3600 and type(p["stars"]) is int:
                recent.append({"at": p["at"], "stars": p["stars"]})
        except (KeyError, ValueError, TypeError):
            continue
    return (recent[-11:] + [{"at": stamp, "stars": stars}])[-12:]


def api_fields(repo: dict) -> dict:
    if any(type(repo.get(key)) is not int or repo[key] < 0 for key in ("stargazers_count","forks_count")):
        raise ValueError("Repository API counts missing or invalid")
    for key in ("created_at", "pushed_at"):
        stamp = repo.get(key)
        if not isinstance(stamp,str) or not stamp or datetime.fromisoformat(stamp.replace("Z","+00:00")).tzinfo is None:
            raise ValueError("Missing or naive repository timestamp")
    return {
        "stars": repo["stargazers_count"], "forks": repo["forks_count"],
        "repo_created_at": repo["created_at"], "repo_pushed_at": repo["pushed_at"],
        "language": repo.get("language") or "",
    }


def update_state(data: dict, now: datetime, fetch_page=request_trending,
                 fetch_metadata=None) -> dict:
    """Fetch independently: a broken Trending source must not freeze watchlist API totals."""
    stamp = utc_stamp(now)
    token = os.environ.get("GITHUB_TOKEN", "")
    fetch_metadata = fetch_metadata or (lambda name: metadata(name, token))
    out = copy.deepcopy(data)
    previous = {x["repo"].lower(): x for x in data.get("items", [])}
    status = {"mode": "official_trending_plus_repository_api", "status": "error",
              "last_checked_at": stamp, "last_success_at": data.get("sync", {}).get("last_success_at") or data.get("checked_at"),
              "note": "仅官方 Trending 确认可更新榜位与今日 Star；失败时保留上次成功快照。"}
    tracked_errors = []
    for row in out.get("watchlist", []):
        try:
            info = fetch_metadata(row["repo"])
            row.update(api_fields(info))
            row["description"] = info.get("description") or row.get("description") or ""
            row["verified_at"] = stamp
            row["url"] = info.get("html_url") or "https://github.com/" + row["repo"]
            # Watchlist has no rank or daily Trending stars; remove accidental leakage.
            row.pop("rank", None)
            row.pop("stars_today", None)
            row.pop("star_history", None)
        except (HTTPError, URLError, OSError, ValueError, KeyError) as exc:
            tracked_errors.append(row["repo"] + ": " + str(exc)[:130])
    status["watchlist_checked_at"] = stamp
    status["watchlist_errors"] = tracked_errors[:5]
    status["watchlist_failed_count"] = len(tracked_errors)
    try:
        source = parse_trending(fetch_page())
        rows = []
        misses = []
        for x in source:
            old = previous.get(x["repo"].lower(), {})
            try:
                info = fetch_metadata(x["repo"])
                repo_name = info.get("full_name") or x["repo"]
                if repo_name.lower() != x["repo"].lower():
                    # Renamed/moved repos are not silently attributed to another Trending rank.
                    raise ValueError("Repository path changed since Trending snapshot")
                desc = info.get("description") or x["description"]
                category, related, tags = classify(
                    x["repo"], desc, old, info.get("topics")
                )
                merged = {**x, **api_fields(info), "repo": x["repo"],
                          "description": desc, "category": category,
                          "ai_related": related, "tags": tags,
                          "url": "https://github.com/" + x["repo"],
                          "metadata_verified_at": stamp,
                          "star_history": history_for(old, info["stargazers_count"], stamp)}
                rows.append(merged)
            except (HTTPError, URLError, OSError, ValueError, KeyError) as exc:
                misses.append(x["repo"] + ": " + str(exc)[:100])
                # Trending rank and stars-today come from the official page and
                # remain usable when the independent Repository API is limited.
                # Preserve the last verified metadata instead of silently
                # deleting a row from the official ranking.
                if old:
                    fallback = copy.deepcopy(old)
                    fallback.update(x)
                    fallback["repo"] = x["repo"]
                    fallback["url"] = "https://github.com/" + x["repo"]
                    fallback["description"] = x.get("description") or old.get("description", "")
                    fallback["language"] = x.get("language") or old.get("language", "")
                    category, related, tags = classify(
                        x["repo"], fallback["description"], old
                    )
                    fallback["category"] = category
                    fallback["ai_related"] = related
                    fallback["tags"] = tags
                    has_verified_metadata = (
                        old.get("metadata_status") != "unavailable"
                        and all(isinstance(old.get(k), int) for k in ("stars", "forks"))
                        and all(old.get(k) for k in ("repo_created_at", "repo_pushed_at"))
                    )
                    if has_verified_metadata:
                        fallback["metadata_verified_at"] = old.get("metadata_verified_at") or data.get("checked_at")
                        fallback["metadata_status"] = "stale"
                    else:
                        # Repeated API limits must not promote a never-verified
                        # placeholder into an apparent historical snapshot.
                        for key in ("stars", "forks", "repo_created_at", "repo_pushed_at", "metadata_verified_at"):
                            fallback[key] = None
                        fallback["metadata_status"] = "unavailable"
                        fallback["star_history"] = []
                    rows.append(fallback)
                else:
                    # A new official Trending row is still valid evidence for
                    # rank and stars-today when the independent Repository API
                    # is unavailable. Keep API-only fields explicitly unknown
                    # instead of dropping the row (or the whole official list).
                    category, related, tags = classify(x["repo"], x.get("description", ""))
                    rows.append({
                        **x,
                        "stars": None,
                        "forks": None,
                        "repo_created_at": None,
                        "repo_pushed_at": None,
                        "category": category,
                        "ai_related": related,
                        "tags": tags,
                        "url": "https://github.com/" + x["repo"],
                        "metadata_verified_at": None,
                        "metadata_status": "unavailable",
                        "star_history": [],
                    })
        if len(rows) != len(source):
            raise ValueError("Official Trending rows lack reusable repository metadata")
        out["items"] = rows
        out["checked_at"] = stamp
        categories = {x["id"]: x for x in out.get("categories", [])}
        for category in sorted({x["category"] for x in rows} | {x["category"] for x in out.get("watchlist", [])}):
            if category not in categories:
                categories[category] = {"id": category, "title": CATEGORIES.get(category, category)}
        out["categories"] = list(categories.values())
        status["status"] = "success"
        status["last_success_at"] = stamp
        status["trending_count"] = len(source)
        status["verified_count"] = len(source) - len(misses)
        status["metadata_failed_count"] = len(misses)
        status["metadata_status"] = "partial" if misses else "success"
        if not misses:
            status["metadata_checked_at"] = stamp
        status["skipped"] = misses[:6]
    except (HTTPError, URLError, OSError, ValueError, KeyError) as exc:
        status["status"] = "error"
        status["error"] = str(exc)[:240]
    out["sync"] = status
    out["note"] = (
        "榜位与今日新增 Star 仅来自 GitHub Trending Today；仓库总 Star / Fork、"
        "创建与推送来自 GitHub Repository API。独立关注的仓库不自动获得榜位或今日 Star。"
        "快照过期将显式标注，Star 不等于真实使用量、任务成功率或本站实测。"
    )
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", type=Path, default=DATA)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--strict", action="store_true", help="Fail if a live Trending refresh is unavailable")
    args = p.parse_args()
    original = json.loads(args.data.read_text(encoding="utf-8"))
    result = update_state(original, datetime.now(timezone.utc))
    output = args.out or args.data
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"trending_status": result["sync"]["status"],
                      "checked_at": result["checked_at"], "last_attempt": result["sync"]["last_checked_at"],
                      "trending_items": len(result["items"]),
                      "watchlist": [(x["repo"], x.get("stars")) for x in result.get("watchlist", [])],
                      "error": result["sync"].get("error", "")}, ensure_ascii=False))
    if args.strict and result["sync"]["status"] != "success":
        sys.exit(2)


if __name__ == "__main__":
    main()
