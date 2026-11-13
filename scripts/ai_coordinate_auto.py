"""No-LLM source sync: official releases, HF Trending and an unreviewed official-news inbox.
Automated candidates never become editorial claims without independent review.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "data/official-news-inbox.json"
FEEDS = {
    "openai-news": {"url": "https://openai.com/news/rss.xml",
                    "publisher": "OpenAI", "hosts": ("openai.com", "www.openai.com")},
    "nvidia-developer": {"url": "https://developer.nvidia.com/blog/feed/",
                         "publisher": "NVIDIA Developer", "hosts": ("developer.nvidia.com",)},
}
COMMANDS = {
    "hf": ("huggingface_trending_sync.py", "data/huggingface-hot.json", 150),
    "upstream": ("collect.py", "data/upstream.json", 650),
    "cn": ("cn_official_sources.py", "data/cn-official-inbox.json", 260),
    "media": ("media_sources.py", "data/media-inbox.json", 180),
    "people_watch": ("people_watch.py", "data/people-watch-candidates.json", 30),
}
ATOM = "{http://www.w3.org/2005/Atom}"

def stamp(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Clock requires timezone")
    return now.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def safe_url(url: str, hosts: tuple[str, ...]) -> bool:
    try:
        p = urlsplit(url)
        return p.scheme == "https" and p.hostname in hosts and not p.username and not p.password and p.port in (None, 443)
    except (TypeError, ValueError):
        return False

class SameHostRedirect(HTTPRedirectHandler):
    def __init__(self, hosts: tuple[str, ...]):
        super().__init__()
        self.hosts = hosts
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not safe_url(newurl, self.hosts):
            raise ValueError("Refused off-domain or non-HTTPS redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def fetch_feed(source: dict) -> bytes:
    if not safe_url(source["url"], source["hosts"]):
        raise ValueError("Unexpected feed origin")
    opener = build_opener(SameHostRedirect(source["hosts"]))
    req = Request(source["url"], headers={"User-Agent": "FrontierLog-Official-Feed/1.0"})
    with opener.open(req, timeout=25) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("Feed exceeds 2 MB cap")
    return raw

def publication_time(text: str | None, now: datetime) -> tuple[str | None, bool]:
    """Never fabricate a source instant from a timezone-free or date-only string."""
    if not text or not text.strip():
        return None, False
    text = text.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00")) if re.match(r"^\d{4}-\d{2}-\d{2}[T ]", text) else parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return None, False
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None, False
    parsed = parsed.astimezone(timezone.utc)
    if parsed > now.astimezone(timezone.utc) + timedelta(minutes=5):
        return None, True
    return stamp(parsed), False

def _text(node: ET.Element | None) -> str:
    return re.sub(r"\s+", " ", "".join(node.itertext())).strip()[:240] if node is not None else ""

def parse_feed(raw: bytes, source: dict, now: datetime) -> list[dict]:
    if len(raw) > 2_000_000:
        raise ValueError("Feed too large")
    root = ET.fromstring(raw)
    rss = root.tag in ("rss", "RDF", "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF")
    atom = root.tag == ATOM + "feed"
    if not rss and not atom:
        raise ValueError("Unsupported RSS/Atom root")
    entries = root.findall("./channel/item") if rss and root.tag == "rss" else (root.findall(ATOM+"entry") if atom else root.findall("item"))
    if not entries:
        raise ValueError("No entries in official feed")
    records, seen = [], set()
    for item in entries[:80]:
        title = _text(item.find("title") if rss else item.find(ATOM+"title"))
        link = _text(item.find("link")) if rss else ""
        if atom:
            link = next((a.get("href", "") for a in item.findall(ATOM+"link") if a.get("rel") in (None, "alternate")), "")
        if not title or not safe_url(link, source["hosts"]) or link in seen:
            continue
        seen.add(link)
        pub = _text(item.find("pubDate")) if rss else _text(item.find(ATOM+"published")) or _text(item.find(ATOM+"updated"))
        published_at, future = publication_time(pub, now)
        if future:
            continue
        records.append({
            "id": hashlib.sha256(link.encode("utf-8")).hexdigest()[:20],
            "title": title, "url": link, "source_id": source["id"],
            "publisher": source["publisher"], "published_at": published_at,
            "status": "unreviewed", "evidence_level": "official_feed_candidate",
        })
    if not records:
        raise ValueError("Feed has no valid same-origin entries")
    return records

def update_inbox(previous: dict, fetcher=fetch_feed, now: datetime | None = None) -> tuple[dict, dict]:
    now = now or datetime.now(timezone.utc)
    t = stamp(now)
    old = copy.deepcopy(previous or {})
    rows = {r["id"]: r for r in old.get("items", []) if isinstance(r, dict) and r.get("id")}
    before = set(rows)
    results, states = {}, copy.deepcopy(old.get("sources", {}))
    for sid, cfg in FEEDS.items():
        source = {**cfg, "id": sid}
        state = copy.deepcopy(states.get(sid, {}))
        state["last_attempt_at"] = t
        try:
            found = parse_feed(fetcher(source), source, now)
            for candidate in found:
                rid = candidate["id"]
                if rid in rows:
                    # Existing editorial decisions and first-seen times are immutable here.
                    if rows[rid].get("status") == "unreviewed":
                        rows[rid]["title"] = candidate["title"]
                    continue
                rows[rid] = {**candidate, "first_seen_at": t}
            state["last_success_at"] = t
            state["status"], state["last_error"] = "success", None
            results[sid] = {"status": "success", "entries": len(found)}
        except (OSError, ValueError, ET.ParseError, UnicodeError, TimeoutError) as exc:
            state["status"] = "failed"
            state["last_error"] = (type(exc).__name__ + ": " + str(exc))[:180]
            results[sid] = {"status": "failed", "error": state["last_error"]}
        states[sid] = state
    new = len(set(rows)-before)
    items = sorted(rows.values(), key=lambda r: (r.get("published_at") or r.get("first_seen_at") or "", r["id"]), reverse=True)[:300]
    out = {
        "version": 1,
        "note": "Machine-discovered official feed candidates only. No facts or editorial claims are approved for automatic publication.",
        "last_attempt_at": t,
        "last_ingested_at": t if new else old.get("last_ingested_at"),
        "sources": states,
        "items": items,
    }
    return out, {"sources": results, "new_candidates": new, "success_count": sum(x["status"] == "success" for x in results.values())}

def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    tmp.replace(path)

def verify_data(path: Path, name: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(name+" must be a JSON object")
    if name == "official":
        if data.get("version") != 1 or not isinstance(data.get("sources"), dict):
            raise ValueError("Invalid official candidate queue")
        ids = [r["id"] for r in data.get("items", [])]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate official candidate IDs")
        if any(r.get("status") not in ("unreviewed", "approved", "rejected") or r.get("evidence_level") != "official_feed_candidate" for r in data.get("items", [])):
            raise ValueError("Untrusted candidate promoted to claim")
    if name == "hf" and ("web_order" not in data or "sync" not in data):
        raise ValueError("Missing HF source provenance")
    if name == "upstream" and ("releases" not in data or "errors" not in data):
        raise ValueError("Missing upstream source failure ledger")
    if name == "people_watch":
        if data.get("version") != 1 or not isinstance(data.get("items"), list):
            raise ValueError("Invalid AI People monitoring candidate queue")
        if any(x.get("review_status") not in ("unreviewed", "approved", "rejected") or x.get("evidence_level") != "lead_only_not_people_event" for x in data["items"]):
            raise ValueError("AI People watcher cannot automatically approve claims")
    if name == "media":
        from media_sources import validate_inbox
        validate_inbox(data)
    if name == "cn":
        if data.get("version") != 1 or not isinstance(data.get("sources"), dict) or not isinstance(data.get("items"), list):
            raise ValueError("Missing Chinese official-source evidence queue")
        ids = [r["id"] for r in data["items"]]
        if len(ids) != len(set(ids)) or any(r.get("review_status") not in ("unreviewed", "approved", "rejected") for r in data["items"]):
            raise ValueError("Unsafe or duplicate Chinese official candidates")

def run_commands(selected: list[str], executor=subprocess.run, now: datetime | None = None) -> tuple[dict, int]:
    result = {"started_at": stamp(now), "engine": "python-github-actions-no-llm", "sources": {}}
    successes = 0
    for name in selected:
        if name == "official":
            try:
                previous = json.loads(INBOX.read_text(encoding="utf-8")) if INBOX.exists() else {}
                data, summary = update_inbox(previous, now=now)
                atomic_json(INBOX, data)
                verify_data(INBOX, "official")
                success = summary["success_count"] > 0
                status = "success" if summary["success_count"] == len(FEEDS) else "partial" if success else "failed"
                result["sources"][name] = {"status": status, **summary}
            except (OSError, ValueError, ET.ParseError) as exc:
                success = False
                result["sources"][name] = {"status": "failed", "error": (type(exc).__name__+": "+str(exc))[:180]}
        else:
            script, relative, limit = COMMANDS[name]
            target = ROOT / relative
            t0 = time.monotonic()
            try:
                proc = executor([sys.executable, str(ROOT/"scripts"/script)], cwd=ROOT, capture_output=True, text=True, timeout=limit)
                verify_data(target, name)
                snapshot = json.loads(target.read_text(encoding="utf-8"))
                if name == "hf":
                    states = snapshot.get("sync", {})
                    status = "success" if states.get("web_status") == "success" and states.get("api_status") == "success" else "partial" if proc.returncode == 0 else "failed"
                    detail = {"web": states.get("web_status"), "api": states.get("api_status")}
                elif name == "people_watch":
                    errors = snapshot.get("source_errors", {})
                    status = "success" if proc.returncode == 0 and not errors else "partial" if proc.returncode == 0 else "failed"
                    detail = {"candidate_count": len(snapshot.get("items", [])), "source_errors": errors}
                elif name in ("cn", "media"):
                    states = snapshot.get("sources", {})
                    succeeded = sum(x.get("status") == "success" for x in states.values())
                    total = len(states)
                    status = "success" if proc.returncode == 0 and total > 0 and succeeded == total else "partial" if succeeded > 0 else "failed"
                    detail = {"sources_succeeded": succeeded, "sources_total": total, "failed": total - succeeded}
                else:
                    count = snapshot.get("repositories_succeeded", 0)
                    total = snapshot.get("repositories_total", 0)
                    status = "success" if proc.returncode == 0 and total > 0 and count == total else "partial" if count > 0 else "failed"
                    detail = {"repositories_succeeded": count, "repositories_total": total, "errors": len(snapshot.get("errors", []))}
                success = status != "failed"
                result["sources"][name] = {"status": status, "exit_code": proc.returncode, "seconds": round(time.monotonic()-t0, 1), **detail}
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                success = False
                result["sources"][name] = {"status": "failed", "error": (type(exc).__name__+": "+str(exc))[:180]}
        successes += int(success)
    result["completed_at"] = stamp()
    # An independently useful partial fetch does not make the whole cycle green.
    # Keep exit code 0 for publishing verified independent sources; the receipt
    # carries the distinct source/module-level status and complete failure count.
    states = [v["status"] for v in result["sources"].values()]
    result["status"] = ("success" if all(st == "success" for st in states)
                        else "partial" if any(st in ("success", "partial") for st in states)
                        else "failed")
    return result, 0 if successes else 2

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--modules", default="official,hf,upstream,cn,media,people_watch", help="Comma-separated: official,hf,upstream,cn,media,people_watch")
    ap.add_argument("--report", type=Path, default=Path("/tmp/ai-coordinate-sync-report.json"))
    ap.add_argument("--offline-check", action="store_true", help="Validate existing data without fetching or writing")
    args = ap.parse_args(argv)
    selected = [v.strip() for v in args.modules.split(",") if v.strip()]
    if len(selected) != len(set(selected)) or not selected or any(k not in (*COMMANDS, "official") for k in selected):
        ap.error("Unsupported or duplicate source name")
    if args.offline_check:
        for name in selected:
            verify_data(INBOX if name == "official" else ROOT/COMMANDS[name][1], name)
        print(json.dumps({"status": "validated", "sources": selected}))
        return 0
    report, code = run_commands(selected)
    atomic_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False))
    return code

if __name__ == "__main__":
    raise SystemExit(main())
