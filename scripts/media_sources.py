"""No-LLM media/creator discovery with source-level provenance.

Media reporting is a discovery lead, never an official-model claim. A creator's
own changelog only documents that creator's project; it is not their WeChat feed.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data/media-sources.json"
LINKS = ROOT / "data/media-original-links.json"
INBOX = ROOT / "data/media-inbox.json"
ATOM = "{http://www.w3.org/2005/Atom}"
RULES = {
    "agent": ("agent", "智能体", "自主智能"),
    "coding": ("编程", "coding", "code agent", "codex"),
    "multimodal": ("多模态", "视频生成", "视觉", "语音", "图像生成"),
    "model": ("模型", "大模型", "model", "推理", "benchmark", "评测"),
    "biomedical": ("医药", "生物", "制药", "临床", "药物", "medical", "clinical", "pharma", "drug"),
    "manufacturing": ("制造", "半导体", "工业", "良率", "质检"),
}
MAX_BODY = 2_000_000


def utc_stamp(when: datetime) -> str:
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError("A timezone is required for an instant")
    return when.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def safe_https(url: str, hosts: list[str]) -> bool:
    try:
        p = urlsplit(url)
        return (
            p.scheme == "https" and p.hostname in hosts and
            not p.username and not p.password and p.port in (None, 443)
        )
    except (TypeError, ValueError):
        return False


def canonical_article(url: str, hosts: list[str]) -> str | None:
    if not isinstance(url, str) or not safe_https(url, hosts):
        return None
    p = urlsplit(url)
    # For publisher URLs only: strip tracking, anchors and trailing slash.
    # WeChat original share links preserve their full query separately.
    return urlunsplit(("https", p.netloc.lower(), p.path.rstrip("/") or "/", "", ""))


class SameHostRedirect(HTTPRedirectHandler):
    def __init__(self, hosts: list[str]):
        super().__init__()
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not safe_https(newurl, self.hosts):
            raise ValueError("Refusing redirect away from a declared source")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(source: dict) -> bytes:
    if not safe_https(source["url"], source["hosts"]):
        raise ValueError("Untrusted media source URL")
    opener = build_opener(SameHostRedirect(source["hosts"]))
    req = Request(source["url"], headers={
        "User-Agent": "AI-Coordinate-Publisher-Feed/1.0",
        "Accept": "application/rss+xml, application/atom+xml, text/xml, text/html",
    })
    with opener.open(req, timeout=25) as response:
        raw = response.read(MAX_BODY + 1)
    if len(raw) > MAX_BODY:
        raise ValueError("Source response exceeds 2 MB")
    return raw


def source_instant(raw: str | None, now: datetime) -> tuple[str | None, bool]:
    """(published_at, future) -- no local midnight inferred from a date-only input."""
    if not raw or not raw.strip():
        return None, False
    raw = raw.strip()
    try:
        dt = (datetime.fromisoformat(raw.replace("Z", "+00:00"))
              if re.match(r"^\d{4}-\d{2}-\d{2}[T ]", raw)
              else parsedate_to_datetime(raw))
    except (ValueError, TypeError, IndexError):
        return None, False
    if dt.tzinfo is None or dt.utcoffset() is None:
        return None, False
    if dt.astimezone(timezone.utc) > now.astimezone(timezone.utc) + timedelta(minutes=5):
        return None, True
    return utc_stamp(dt), False


def clean_title(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text)).strip()[:200]


def label_rules(title: str) -> list[str]:
    low = title.casefold()
    return [label for label, triggers in RULES.items() if any(t in low for t in triggers)]


def parse_feed(raw: bytes, source: dict, now: datetime) -> list[dict]:
    if len(raw) > MAX_BODY:
        raise ValueError("Feed too large")
    root = ET.fromstring(raw)
    if root.tag == "rss":
        posts = root.findall("./channel/item")
        atom = False
    elif root.tag == ATOM + "feed":
        posts = root.findall(ATOM + "entry")
        atom = True
    else:
        raise ValueError("Expected RSS or Atom, not HTML/other XML")
    if not posts:
        raise ValueError("Publisher feed has no entries; parser/source needs review")
    records, seen = [], set()
    for post in posts[:max(1, min(source.get("max_items", 40) * 2, 100))]:
        if atom:
            title_node = post.find(ATOM + "title")
            title = clean_title("".join(title_node.itertext()) if title_node is not None else "")
            link = next((a.get("href", "") for a in post.findall(ATOM + "link")
                         if a.get("rel") in (None, "alternate")), "")
            date_node = post.find(ATOM + "published")
            if date_node is None:
                date_node = post.find(ATOM + "updated")
        else:
            title_node = post.find("title")
            title = clean_title("".join(title_node.itertext()) if title_node is not None else "")
            link = (post.findtext("link") or "").strip()
            date_node = post.find("pubDate")
        url = canonical_article(link, source["article_hosts"])
        if not url or not title or url in seen:
            continue
        raw_date = "".join(date_node.itertext()) if date_node is not None else ""
        published_at, future = source_instant(raw_date, now)
        if future:
            continue
        seen.add(url)
        records.append({
            "source_url": url,
            "title": title,
            "published_at": published_at,
            "labels": label_rules(title),
        })
        if len(records) >= source.get("max_items", 40):
            break
    if not records:
        raise ValueError("No valid same-publisher feed entries")
    return records


class Headings(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_main = False
        self.main_depth = 0
        self.capture = None
        self.words = []
        self.titles = []

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self.in_main = True
            self.main_depth += 1
        elif self.in_main and tag in ("h1", "h2", "h3"):
            self.capture = tag
            self.words = []

    def handle_data(self, data):
        if self.capture:
            self.words.append(data)

    def handle_endtag(self, tag):
        if tag == self.capture:
            title = clean_title(" ".join(self.words))
            if title and len(title) >= 3:
                self.titles.append(title)
            self.capture = None
            self.words = []
        if tag == "main" and self.main_depth:
            self.main_depth -= 1
            self.in_main = bool(self.main_depth)


def changelog_digest(raw: bytes) -> tuple[str, int]:
    page = raw.decode("utf-8", "replace")
    parser = Headings()
    parser.feed(page)
    # Hash recent visible changelog headings, never dynamic counters/nav or HTML bytes.
    topics = parser.titles[:30]
    if not any(("模型榜" in s or "AIHOT" in s or "更新日志" in s) for s in topics) or len(topics) < 2:
        raise ValueError("Creator changelog headings unavailable; cannot claim success")
    digest = hashlib.sha256("\n".join(topics).encode("utf-8")).hexdigest()
    return digest, len(topics)


def validate_sources(config: dict) -> None:
    if config.get("version") != 1 or not isinstance(config.get("sources"), list):
        raise ValueError("Invalid media registry")
    seen = set()
    for source in config["sources"]:
        sid = source.get("id")
        if not sid or sid in seen or source.get("mode") not in ("rss", "page_watch"):
            raise ValueError("Duplicate or unsupported media source")
        seen.add(sid)
        if not safe_https(source.get("url", ""), source.get("hosts", [])):
            raise ValueError("Media feed origin not pinned")
        if source["mode"] == "rss" and (not source.get("article_hosts") or source.get("max_items", 0) < 1):
            raise ValueError("Missing media article host restrictions")
        if source.get("publisher_kind") not in ("media", "creator"):
            raise ValueError("Unreviewed publisher tier required")
    for source in config.get("manual_sources", []):
        if source.get("mode") != "wechat_share_link" or source.get("publisher_kind") != "creator":
            raise ValueError("Manual source must be a creator's share-link intake")


def candidate_id(sid: str, url: str) -> str:
    return hashlib.sha256((sid + "|" + url).encode("utf-8")).hexdigest()[:24]


def update(config: dict, manual: dict, previous: dict,
           fetcher=fetch, now: datetime | None = None) -> tuple[dict, dict]:
    validate_sources(config)
    now = now or datetime.now(timezone.utc)
    stamp = utc_stamp(now)
    out = copy.deepcopy(previous or {})
    rows = {r["id"]: r for r in out.get("items", []) if isinstance(r, dict) and r.get("id")}
    old_ids = set(rows)
    states = copy.deepcopy(out.get("sources", {}))
    results = {}
    sources = {s["id"]: s for s in config["sources"]}
    for sid, source in sources.items():
        state = copy.deepcopy(states.get(sid, {}))
        if not source.get("enabled", True):
            results[sid] = {"status": "disabled"}
            continue
        state["last_attempt_at"] = stamp
        try:
            raw = fetcher(source)
            if not isinstance(raw, bytes):
                raise ValueError("Source body must be bytes")
            if source["mode"] == "page_watch":
                digest, headings = changelog_digest(raw)
                if state.get("last_digest") and state["last_digest"] != digest:
                    state["changed_unreviewed_at"] = stamp
                state["last_digest"] = digest
                found = []
                results[sid] = {"status": "success", "mode": "creator_project_changelog",
                                "headings": headings, "new_articles": 0}
            else:
                found = parse_feed(raw, source, now)
                for row in found:
                    item_id = candidate_id(sid, row["source_url"])
                    if item_id not in rows:
                        rows[item_id] = {
                            "id": item_id, "source_id": sid,
                            "publisher_id": source["publisher_id"], "publisher": source["publisher"],
                            "publisher_kind": source["publisher_kind"],
                            "source_role": source["source_role"],
                            "discovery_feed": source["url"],
                            "source_url": row["source_url"], "title": row["title"],
                            "published_at": row["published_at"], "first_seen_at": stamp,
                            "labels": row["labels"], "review_status": "unreviewed",
                            "evidence_level": "secondary_media_lead",
                        }
                results[sid] = {"status": "success", "mode": "publisher_rss", "entries": len(found)}
            state["last_success_at"] = stamp
            state["status"] = "success"
            state["last_error"] = None
        except (OSError, UnicodeError, ValueError, ET.ParseError) as exc:
            state["status"] = "failed"
            state["last_error"] = (type(exc).__name__ + ": " + str(exc))[:180]
            results[sid] = {"status": "failed", "error": state["last_error"]}
        states[sid] = state

    allowed_manual = {s["id"]: s for s in config.get("manual_sources", []) if s.get("enabled")}
    manual_accepted = 0
    if not isinstance(manual.get("items", []), list):
        raise ValueError("Manual link data must have an items array")
    for supplied in manual.get("items", []):
        if not isinstance(supplied, dict):
            continue
        sid = supplied.get("source_id")
        source = allowed_manual.get(sid)
        link = supplied.get("url")
        if source is None or not isinstance(link, str):
            continue
        if not safe_https(link, ["mp.weixin.qq.com"]):
            continue
        p = urlsplit(link)
        if not (p.path == "/s" or p.path.startswith("/s/")):
            continue
        link = urlunsplit(("https", "mp.weixin.qq.com", p.path, p.query, ""))
        rid = candidate_id(sid, link)
        if rid not in rows:
            title = clean_title(str(supplied.get("title") or "微信公众号原文链接，待核验"))
            rows[rid] = {
                "id": rid, "source_id": sid, "publisher_id": source["publisher_id"],
                "publisher": source["publisher"], "publisher_kind": "creator",
                "source_role": "wechat_unverified_share_link",
                "discovery_feed": None, "source_url": link,
                "title": title, "published_at": None, "first_seen_at": stamp,
                "labels": label_rules(title),
                "review_status": "unreviewed",
                "evidence_level": "link_only_publisher_unverified",
                "note": "Do not infer WeChat original author, content or publication date from a shared URL.",
            }
            manual_accepted += 1

    added = len(set(rows) - old_ids)
    out.update({
        "version": 1,
        "note": "Publisher-operated RSS leads, creator-owned project changes and manual unverified WeChat links. Never automatically publish as official facts.",
        "last_attempt_at": stamp,
        "last_ingested_at": stamp if added else out.get("last_ingested_at"),
        "sources": states,
        "items": sorted(rows.values(), key=lambda r: (r.get("published_at") or r.get("first_seen_at") or "", r["id"]), reverse=True),
    })
    successful = sum(r["status"] == "success" for r in results.values())
    return out, {"sources": results, "sources_succeeded": successful,
                 "sources_failed": sum(r["status"] == "failed" for r in results.values()),
                 "new_candidates": added, "manual_links_added": manual_accepted}


def validate_inbox(obj: dict, config: dict | None = None) -> None:
    if obj.get("version") != 1 or not isinstance(obj.get("sources"), dict) or not isinstance(obj.get("items"), list):
        raise ValueError("Invalid media evidence queue")
    config = config or json.loads(CONFIG.read_text(encoding="utf-8"))
    approved_hosts = {"mp.weixin.qq.com"}
    for source in config.get("sources", []):
        approved_hosts.update(source.get("article_hosts", []))
    seen = set()
    for row in obj["items"]:
        rid = row.get("id")
        if not isinstance(rid, str) or rid in seen:
            raise ValueError("Duplicate or invalid media ID")
        seen.add(rid)
        if row.get("review_status") not in ("unreviewed", "approved", "rejected"):
            raise ValueError("Unsupported review status")
        if row.get("evidence_level") not in ("secondary_media_lead", "link_only_publisher_unverified"):
            raise ValueError("Media cannot be promoted to official evidence")
        if not safe_https(row.get("source_url", ""), sorted(approved_hosts)):
            raise ValueError("Unexpected media article URL")


def atomic_write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=CONFIG)
    ap.add_argument("--links", type=Path, default=LINKS)
    ap.add_argument("--out", type=Path, default=INBOX)
    ap.add_argument("--offline-check", action="store_true")
    args = ap.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    validate_sources(config)
    if args.offline_check:
        if args.out.exists():
            validate_inbox(json.loads(args.out.read_text(encoding="utf-8")))
        print(json.dumps({"status": "validated", "sources": len(config["sources"])}))
        return 0
    manual = json.loads(args.links.read_text(encoding="utf-8"))
    previous = json.loads(args.out.read_text(encoding="utf-8")) if args.out.exists() else {}
    state, report = update(config, manual, previous)
    validate_inbox(state)
    atomic_write(args.out, state)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["sources_succeeded"] > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
