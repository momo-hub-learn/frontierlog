"""Token-free AI People candidate watch from existing, separately-provenanced queues.

No web scraping, LLM calls, private following data, or automatic people/events edits.
Named-person matches are distinct from team-level releases without individual credit.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data/people-watch-config.json"
OUT = ROOT / "data/people-watch-candidates.json"
INPUTS = {
    "cn": ROOT / "data/cn-official-inbox.json",
    "media": ROOT / "data/media-inbox.json",
}

def stamp(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Timezone required")
    return now.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")

def find_leads(config: dict, inboxes: dict[str, dict], previous: dict, now: datetime | None = None) -> tuple[dict, dict]:
    t = stamp(now)
    people = config.get("people", [])
    if config.get("version") != 1 or not people or len({p["person_id"] for p in people}) != len(people):
        raise ValueError("Invalid people watch configuration")
    data = copy.deepcopy(previous or {})
    prior = {x["id"]: x for x in data.get("items", [])}
    added = 0
    stats = {}
    for channel, inbox in inboxes.items():
        seen = 0
        if not isinstance(inbox.get("items"), list):
            raise ValueError("Invalid candidate queue " + channel)
        for item in inbox["items"]:
            title = item.get("title", "")
            url = item.get("source_url") or item.get("url")
            if not isinstance(title, str) or not isinstance(url, str) or not url.startswith("https://"):
                continue
            for person in people:
                direct = any(name.casefold() in title.casefold() for name in person["names"])
                team = (channel == "cn" and item.get("publisher_id") in person.get("team_publishers", [])
                        and any(term.casefold() in title.casefold() for term in person.get("team_terms", [])))
                if not (direct or team):
                    continue
                relation = "named_mention" if direct else "organization_context_only"
                rid = hashlib.sha256((person["person_id"] + "|" + url).encode()).hexdigest()[:24]
                if rid not in prior:
                    prior[rid] = {
                        "id": rid, "person_id": person["person_id"],
                        "title": title[:260], "url": url, "source_channel": channel,
                        "source_item_id": item.get("id"), "published_at": item.get("published_at"),
                        "first_seen_at": t, "relation": relation,
                        "review_status": "unreviewed",
                        "evidence_level": "lead_only_not_people_event",
                        "boundary": ("报道或页面提及姓名，需查原文确认真实参与及时间"
                                     if direct else "仅属其公开负责团队的相关项目，不代表本人独立贡献"),
                    }
                    added += 1
                seen += 1
        stats[channel] = {"leads_detected": seen}
    out = {
        "version": 1,
        "note": "Machine triage only; verified people profiles/events require separate human editorial review.",
        "last_scan_at": t if added else data.get("last_scan_at"), "last_ingested_at": t if added else data.get("last_ingested_at"),
        "items": sorted(prior.values(), key=lambda x:(x.get("published_at") or x["first_seen_at"],x["id"]), reverse=True)[:300],
    }
    return out, {"new_candidates": added, "sources": stats, "total": len(out["items"])}

def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, default=CONFIG)
    p.add_argument("--out", type=Path, default=OUT)
    args=p.parse_args(argv)
    cfg=json.loads(args.config.read_text(encoding="utf-8"))
    inputs={}
    failures={}
    for name,path in INPUTS.items():
        try:
            inputs[name]=json.loads(path.read_text(encoding="utf-8"))
        except (OSError,ValueError) as exc:
            failures[name]=(type(exc).__name__+": "+str(exc))[:180]
    previous=json.loads(args.out.read_text(encoding="utf-8")) if args.out.exists() else {}
    if not inputs:
        print(json.dumps({"status":"failed","errors":failures},ensure_ascii=False))
        return 2
    result, summary=find_leads(cfg,inputs,previous)
    result["source_errors"] = failures
    dest=args.out
    tmp=dest.with_suffix(".tmp")
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tmp.replace(dest)
    status="success" if not failures else "partial"
    print(json.dumps({"status":status,"errors":failures,"scanned_at":stamp(),**summary},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
