"""Monitor Chinese AI companies via first-party public pages, not WeChat scraping.

Publisher official-page links become unreviewed candidates. Original WeChat articles
can be queued from explicitly supplied share URLs but are never claimed as
verified publisher posts merely because their URL is on mp.weixin.qq.com.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "data/cn-official-sources.json"
DEFAULT_INPUTS = ROOT / "data/wechat-original-links.json"
DEFAULT_OUTPUT = ROOT / "data/cn-official-inbox.json"


def stamp(instant: datetime) -> str:
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("Timezone required")
    return instant.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def allowed(url: str, hosts: list[str] | tuple[str, ...]) -> bool:
    try:
        p = urlsplit(url)
        return p.scheme == "https" and p.hostname in hosts and not p.username and not p.password and p.port in (None, 443)
    except (TypeError, ValueError):
        return False


class PinnedRedirect(HTTPRedirectHandler):
    def __init__(self, hosts):
        super().__init__()
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed(newurl, self.hosts):
            raise ValueError("Redirect outside verified publisher host")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_page(feed: dict) -> str:
    hosts = feed["allowed_hosts"]
    if not allowed(feed["url"], hosts):
        raise ValueError("Unapproved official site URL")
    opener = build_opener(PinnedRedirect(hosts))
    request = Request(feed["url"], headers={"User-Agent": "AI-Coordinate-Official-Sources/1.0"})
    with opener.open(request, timeout=25) as response:
        content = response.read(2_000_001)
    if len(content) > 2_000_000:
        raise ValueError("Official page exceeds 2 MB")
    return content.decode("utf-8", "replace")


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            values = dict(attrs)
            self.active = (values.get("href", ""), [])

    def handle_data(self, data):
        if self.active is not None:
            self.active[1].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.active is not None:
            url, words = self.active
            self.links.append((url, " ".join(words)))
            self.active = None


def canonical(url: str, base: str, hosts: list[str]) -> str | None:
    try:
        absolute = urljoin(base, url.strip())
        if not allowed(absolute, hosts):
            return None
        p = urlsplit(absolute)
        # Query parameters and fragments are not used as independent article identities.
        return urlunsplit((p.scheme, p.netloc, p.path.rstrip("/") or "/", "", ""))
    except (TypeError, ValueError):
        return None


def parse_links(text: str, feed: dict) -> list[dict]:
    kind = feed["type"]
    if kind == "page_watch":
        return []
    if kind == "markdown_links":
        matches = re.findall(r"\[([^\]\n]{2,160})\]\((https://[^\s)]+)\)", text)
        candidates = [(href, title) for title, href in matches]
    elif kind == "html_links":
        parser = Anchors()
        parser.feed(text)
        candidates = parser.links
    else:
        raise ValueError("Unsupported official page strategy")
    seen, result = set(), []
    origin = canonical(feed["url"], feed["url"], feed["allowed_hosts"])
    for href, title in candidates:
        link = canonical(href, feed["url"], feed["allowed_hosts"])
        if not link or link == origin:
            continue
        p = urlsplit(link)
        if not any(p.path.startswith(prefix) for prefix in feed["allowed_paths"]):
            continue
        title = re.sub(r"\s+", " ", title).strip()[:220]
        if not title or len(title) < 3 or link in seen:
            continue
        seen.add(link)
        result.append({"url": link, "title": title})
        if len(result) >= min(feed.get("limit", 30), 100):
            break
    if not result:
        raise ValueError("No readable same-publisher article links; cannot claim fresh check")
    return result


def article_id(publisher: str, url: str) -> str:
    return hashlib.sha256((publisher + "|" + url).encode("utf-8")).hexdigest()[:24]


def validate_config(config: dict) -> None:
    if config.get("version") != 1 or not isinstance(config.get("publishers"), list):
        raise ValueError("Invalid publisher registry")
    ids = set()
    for publisher in config["publishers"]:
        pid = publisher.get("id")
        if not pid or pid in ids or not publisher.get("name") or not isinstance(publisher.get("feeds"), list):
            raise ValueError("Duplicate/invalid publisher")
        ids.add(pid)
        for feed in publisher["feeds"]:
            if not allowed(feed["url"], feed["allowed_hosts"]) or feed["type"] not in ("html_links", "markdown_links", "page_watch"):
                raise ValueError("Unsafe official source")
            if feed["type"] != "page_watch" and not feed.get("allowed_paths"):
                raise ValueError("Article index must restrict link paths")


def update(config: dict, supplied: dict, previous: dict, fetcher=fetch_page,
           now: datetime | None = None) -> tuple[dict, dict]:
    validate_config(config)
    now = now or datetime.now(timezone.utc)
    t = stamp(now)
    result = copy.deepcopy(previous or {})
    rows = {x["id"]: x for x in result.get("items", []) if isinstance(x, dict) and x.get("id")}
    original_ids = set(rows)
    states = copy.deepcopy(result.get("sources", {}))
    summary = {"successful": 0, "failed": 0, "unreviewed_wechat_links": 0, "source_results": {}}
    known_publishers = {x["id"]: x for x in config["publishers"]}
    for publisher in config["publishers"]:
        for feed in publisher["feeds"]:
            sid = publisher["id"] + "/" + feed["id"]
            state = copy.deepcopy(states.get(sid, {}))
            state["last_attempt_at"] = t
            try:
                body = fetcher(feed)
                if not isinstance(body, str) or not body.strip() or len(body) > 2_000_000:
                    raise ValueError("Unreadable/oversized publisher response")
                if feed["type"] == "page_watch":
                    # Page digest is only a change lead, not evidence of an announcement.
                    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
                    if state.get("last_hash") and state["last_hash"] != digest:
                        state["changed_unreviewed_at"] = t
                    state["last_hash"] = digest
                    found = []
                else:
                    found = parse_links(body, feed)
                for candidate in found:
                    rid = article_id(publisher["id"], candidate["url"])
                    if rid not in rows:
                        rows[rid] = {
                            "id": rid, "publisher_id": publisher["id"], "publisher": publisher["name"],
                            "title": candidate["title"], "source_url": candidate["url"],
                            "source_type": "official_company_site", "published_at": None,
                            "first_seen_at": t, "review_status": "unreviewed",
                            "evidence_level": "first_party_site_link",
                        }
                state["last_success_at"] = t
                state["last_error"] = None
                state["status"] = "success"
                summary["successful"] += 1
                summary["source_results"][sid] = {"status": "success", "links": len(found)}
            except (OSError, ValueError, UnicodeError) as exc:
                state["status"] = "failed"
                state["last_error"] = (type(exc).__name__ + ": " + str(exc))[:180]
                summary["failed"] += 1
                summary["source_results"][sid] = {"status": "failed", "error": state["last_error"]}
            states[sid] = state

    for item in supplied.get("items", []):
        if not isinstance(item, dict):
            continue
        pid, link = item.get("publisher_id"), item.get("url")
        if pid not in known_publishers or not isinstance(link, str):
            continue
        # Import only explicit first-party shared links, not search pages or mirrors.
        p = urlsplit(link)
        if not allowed(link, ["mp.weixin.qq.com"]) or not (p.path == "/s" or p.path.startswith("/s/")):
            continue
        # Shared URLs with query tokens remain intact to preserve accessibility.
        url = urlunsplit((p.scheme, p.netloc, p.path, p.query, ""))
        rid = article_id(pid, url)
        if rid not in rows:
            rows[rid] = {
                "id": rid, "publisher_id": pid, "publisher": known_publishers[pid]["name"],
                "title": (item.get("title") or "微信公众号原文，待核验")[:220],
                "source_url": url, "source_type": "wechat_shared_url",
                "published_at": None, "first_seen_at": t,
                "review_status": "unreviewed", "evidence_level": "publisher_unverified_share_link",
                "note": "公众号身份、正文和发布时间未经直接核验；不得用作已确认的新闻证据。",
            }
        summary["unreviewed_wechat_links"] += 1

    summary["new_candidates"] = len(set(rows) - original_ids)
    result.update({
        "version": 1,
        "note": "No-WeChat-scraping evidence queue. Only official-site links and explicitly shared WeChat URLs; never publish as approved facts.",
        "sources": states,
        "last_attempt_at": t,
        "last_ingested_at": t if summary["new_candidates"] else result.get("last_ingested_at"),
        "items": sorted(rows.values(), key=lambda x: (x.get("published_at") or x.get("first_seen_at") or "", x["id"]), reverse=True),
    })
    return result, summary


def atomic_write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--links", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    links = json.loads(args.links.read_text(encoding="utf-8"))
    previous = json.loads(args.out.read_text(encoding="utf-8")) if args.out.exists() else {}
    out, summary = update(cfg, links, previous)
    atomic_write(args.out, out)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["successful"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
