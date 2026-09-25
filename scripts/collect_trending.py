from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GH_TRENDING_URL = "https://github.com/trending?since=daily"
HF_TRENDING_URL = "https://huggingface.co/models?sort=trending"
HF_API_URL = "https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=100"
USER_AGENT = "frontierlog-trending-sync/1.0 (+https://github.com/momo-hub-learn/frontierlog)"


def fetch_text(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> str:
    req_headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    return body.decode("utf-8")


def strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html_lib.unescape(value)).strip()


def parse_github_trending(page: str) -> list[dict[str, Any]]:
    articles = re.findall(
        r'<article\b[^>]*class=["\'][^"\']*\bBox-row\b[^"\']*["\'][^>]*>(.*?)</article>',
        page,
        flags=re.I | re.S,
    )
    if not articles:
        raise ValueError("GitHub Trending parser found no repository rows")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for article in articles:
        repo_match = re.search(
            r'<h2\b[^>]*>.*?<a\b[^>]*href=["\']/([^/"\'?#\s]+/[^/"\'?#\s]+)["\']',
            article,
            flags=re.I | re.S,
        )
        if not repo_match:
            continue
        repo = html_lib.unescape(repo_match.group(1)).strip()
        if repo in seen:
            continue
        stars_match = re.search(r'([\d,]+)\s+stars?\s+today', strip_tags(article), flags=re.I)
        if not stars_match:
            raise ValueError(f"GitHub Trending row missing stars today: {repo}")
        rows.append({"repo": repo, "stars_today": int(stars_match.group(1).replace(",", ""))})
        seen.add(repo)
    if len(rows) < 5:
        raise ValueError(f"GitHub Trending parser returned only {len(rows)} rows")
    return rows


def parse_hf_page_order(page: str, api_ids: set[str], limit: int = 20) -> list[str]:
    order: list[str] = []
    seen: set[str] = set()
    for raw in re.findall(r'href=["\']/([^"\'?#]+)', page, flags=re.I):
        model_id = html_lib.unescape(raw).strip("/")
        if model_id in api_ids and model_id not in seen:
            seen.add(model_id)
            order.append(model_id)
            if len(order) >= limit:
                break
    if len(order) < limit:
        raise ValueError(f"Hugging Face page order parser returned {len(order)} of {limit} models")
    return order


def github_api(repo: str) -> dict[str, Any]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    return json.loads(fetch_text(f"https://api.github.com/repos/{repo}", headers=headers))


def compact_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    noisy_prefixes = ("license:", "region:", "base_model:", "dataset:", "arxiv:")
    noisy = {"transformers", "safetensors", "endpoints_compatible", "conversational", "custom_code", "eval-results"}
    out: list[str] = []
    for tag in tags:
        if tag in noisy or tag.startswith(noisy_prefixes):
            continue
        if tag not in out:
            out.append(tag)
        if len(out) == 4:
            break
    return out


def classify_new_repo(meta: dict[str, Any]) -> tuple[bool, str, list[str]]:
    description = str(meta.get("description") or "")
    topics = [str(x) for x in (meta.get("topics") or [])]
    text = " ".join([str(meta.get("full_name") or ""), description, *topics]).lower()
    ai_related = bool(re.search(r"\b(ai|agent|agents|agentic|llm|claude|mcp|model)\b", text))
    if "memory" in text and ai_related:
        category = "agent-memory"
    elif any(k in text for k in ("skill", "skills", "plugin", "plugins")) and ai_related:
        category = "agent-skills"
    elif any(k in text for k in ("orchestration", "runtime")) and ai_related:
        category = "agent-runtime"
    elif any(k in text for k in ("optimizer", "optimization", "quantization", "distillation")) and ai_related:
        category = "model-optimization"
    elif any(k in text for k in ("stock", "finance", "financial")) and ai_related:
        category = "vertical-agent"
    elif any(k in text for k in ("course", "tutorial", "ai-engineering", "ai engineering")) and ai_related:
        category = "ai-learning"
    elif ai_related:
        category = "agent-harness"
    else:
        category = "developer-infra"
    return ai_related, category, topics[:4]


def append_history(old: dict[str, Any] | None, at: str, stars: int) -> list[dict[str, Any]]:
    hist = [x for x in ((old or {}).get("star_history") or []) if isinstance(x, dict) and x.get("at")]
    if not hist or int(hist[-1].get("stars", -1)) != stars:
        hist.append({"at": at, "stars": stars})
    return hist[-48:]


def build_github_data(old: dict[str, Any], page: str, checked_at: str) -> dict[str, Any]:
    ranking = parse_github_trending(page)
    old_by_repo = {x.get("repo"): x for x in old.get("items", [])}
    categories = list(old.get("categories") or [])
    if not any(x.get("id") == "developer-infra" for x in categories):
        categories.append({"id": "developer-infra", "title": "开发基础设施"})
    items: list[dict[str, Any]] = []
    history_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    for rank, row in enumerate(ranking, 1):
        repo = row["repo"]
        meta = github_api(repo)
        old_item = old_by_repo.get(repo)
        if old_item:
            ai_related = bool(old_item.get("ai_related"))
            category = old_item.get("category") or "developer-infra"
            tags = list(old_item.get("tags") or [])
            description = old_item.get("description") or meta.get("description") or ""
        else:
            ai_related, category, tags = classify_new_repo(meta)
            description = meta.get("description") or ""
        items.append({
            "rank": rank,
            "repo": repo,
            "description": description,
            "language": meta.get("language"),
            "stars": int(meta.get("stargazers_count") or 0),
            "forks": int(meta.get("forks_count") or 0),
            "stars_today": int(row["stars_today"]),
            "url": meta.get("html_url") or f"https://github.com/{repo}",
            "ai_related": ai_related,
            "category": category,
            "tags": tags,
            "repo_created_at": meta.get("created_at"),
            "repo_pushed_at": meta.get("pushed_at"),
            "star_history": append_history(old_item, history_at, int(meta.get("stargazers_count") or 0)),
        })
    out = dict(old)
    out.update({
        "version": old.get("version", 1),
        "checked_at": checked_at,
        "source_url": "https://github.com/trending",
        "source_scope": "GitHub Trending · Today · Any spoken language · Any language",
        "note": "完整榜位与“今日 Star”来自 GitHub Trending 官方 Today 页面；总 Star / Fork、仓库创建时间与最近推送时间来自 GitHub Repository API。首页仅从完整榜中筛 AI / Agent 相关项目，并按 GitHub 页面给出的 stars today 排序。趋势线只来自本站连续保存的官方快照；Star 反映开发者关注与采用信号，不代表模型能力、技术突破或本站实测。",
        "categories": categories,
        "items": items,
    })
    return out


def build_hf_data(old: dict[str, Any], page: str, api_payload: list[dict[str, Any]], checked_at: str, limit: int = 20) -> dict[str, Any]:
    api_map = {str(x.get("id")): x for x in api_payload if x.get("id")}
    order = parse_hf_page_order(page, set(api_map), limit=limit)
    items: list[dict[str, Any]] = []
    for rank, model_id in enumerate(order, 1):
        row = api_map[model_id]
        score = row.get("trendingScore")
        if not isinstance(score, (int, float)):
            raise ValueError(f"Hugging Face API missing trendingScore for {model_id}")
        items.append({
            "rank": rank,
            "id": model_id,
            "task": row.get("pipeline_tag") or "other",
            "library": row.get("library_name"),
            "trending_score": score,
            "likes": int(row.get("likes") or 0),
            "downloads": int(row.get("downloads") or 0),
            "created_at": row.get("createdAt"),
            "tags": compact_tags(row.get("tags")),
            "url": f"https://huggingface.co/{model_id}",
        })
    out = dict(old)
    out.update({
        "version": old.get("version", 1),
        "checked_at": checked_at,
        "source_url": HF_TRENDING_URL,
        "api_url": "https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=100",
        "source_scope": "Hugging Face Models · Trending 页面前 20",
        "note": "完整榜位保留 Hugging Face 官方 Models Trending 页面顺序；trendingScore、Likes、Downloads、task、library、createdAt 来自 Hugging Face 官方 API。Trending 与这些互动/使用字段只反映 Hugging Face 平台关注和使用信号，不代表模型能力、Benchmark 成绩、技术突破或本站实测。",
        "items": items,
    })
    return out


def atomic_write(path: Path, obj: dict[str, Any]) -> None:
    payload = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as f:
        f.write(payload)
        tmp = Path(f.name)
    tmp.replace(path)


def collect(root: Path, dry_run: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    gh_old = json.loads((root / "data/github-hot.json").read_text(encoding="utf-8"))
    hf_old = json.loads((root / "data/huggingface-hot.json").read_text(encoding="utf-8"))

    gh_page = fetch_text(GH_TRENDING_URL)
    hf_page = fetch_text(HF_TRENDING_URL)
    hf_api = json.loads(fetch_text(HF_API_URL))
    if not isinstance(hf_api, list) or len(hf_api) < 20:
        raise ValueError("Hugging Face API returned an incomplete trending list")

    gh_new = build_github_data(gh_old, gh_page, checked_at)
    hf_new = build_hf_data(hf_old, hf_page, hf_api, checked_at, limit=20)

    if not dry_run:
        atomic_write(root / "data/github-hot.json", gh_new)
        atomic_write(root / "data/huggingface-hot.json", hf_new)
    return gh_new, hf_new


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh official GitHub and Hugging Face trending snapshots")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    gh, hf = collect(Path(args.root), dry_run=args.dry_run)
    print(json.dumps({
        "github_checked_at": gh["checked_at"],
        "github_rows": len(gh["items"]),
        "github_top": gh["items"][0]["repo"],
        "hf_checked_at": hf["checked_at"],
        "hf_rows": len(hf["items"]),
        "hf_top": hf["items"][0]["id"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
