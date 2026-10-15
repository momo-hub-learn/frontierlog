"""Durable, review-only world-model discovery queue.

The arXiv watcher discovers candidate metadata; this module preserves each
candidate across rolling GitHub issues. No candidate becomes a ranked model.
"""
from __future__ import annotations
import argparse
import json
import re
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[1]
ARXIV_ID = re.compile(r"^\d{4}\.\d{4,5}$")
STATES = {"pending", "reviewed", "rejected"}


def valid_day(value: str) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Invalid candidate date")
    return date.fromisoformat(value)


def validate_queue(queue: dict) -> None:
    if not isinstance(queue, dict) or queue.get("version") != 1:
        raise ValueError("Unsupported discovery queue")
    checked = valid_day(queue.get("checked"))
    if not isinstance(queue.get("items"), list) or len(queue["items"]) > 1000:
        raise ValueError("Invalid candidate queue length")
    ids = set()
    for entry in queue["items"]:
        aid = entry.get("arxiv_id")
        if not isinstance(aid, str) or not ARXIV_ID.fullmatch(aid) or aid in ids:
            raise ValueError("Invalid or duplicate arXiv candidate")
        ids.add(aid)
        if entry.get("url") != f"https://arxiv.org/abs/{aid}":
            raise ValueError("Candidate must link to its immutable arXiv ID")
        published, first_seen = valid_day(entry.get("date")), valid_day(entry.get("first_seen_on"))
        if published > first_seen or first_seen > checked:
            raise ValueError("Inconsistent candidate dates")
        if not isinstance(entry.get("title"), str) or not 5 <= len(entry["title"]) <= 300:
            raise ValueError("Invalid candidate title")
        authors = entry.get("authors")
        if not isinstance(authors, list) or not 1 <= len(authors) <= 12 or any(
            not isinstance(a, str) or not a.strip() or len(a) > 180 for a in authors
        ):
            raise ValueError("Invalid candidate authors")
        if entry.get("status") not in STATES:
            raise ValueError("Invalid candidate review status")
        if entry.get("discovery_source") != "arXiv Atom API":
            raise ValueError("Unrecognized discovery provenance")


def merge_queue(queue: dict, report: dict, known_ids: set[str]) -> tuple[dict, int]:
    """Append previously unseen records; preserve prior statuses and evidence."""
    validate_queue(queue)
    if report.get("status") != "review_only" or report.get("auto_publish") is not False:
        raise ValueError("Refusing automatic publication from unreviewed material")
    if report.get("source") != "arXiv Atom API":
        raise ValueError("Untrusted discovery source")
    checked = valid_day(report.get("checked"))
    if checked < valid_day(queue["checked"]):
        raise ValueError("Out-of-order discovery report")
    old = {row["arxiv_id"] for row in queue["items"]}
    incoming = report.get("candidates")
    if not isinstance(incoming, list) or len(incoming) > 80:
        raise ValueError("Invalid candidate report")
    new = []
    for row in incoming:
        aid = row.get("arxiv_id")
        if not isinstance(aid, str) or not ARXIV_ID.fullmatch(aid):
            raise ValueError("Invalid candidate ID")
        if row.get("status") != "editorial_review_required":
            raise ValueError("Candidate unexpectedly marked as approved")
        if row.get("url") != f"https://arxiv.org/abs/{aid}":
            raise ValueError("Invalid candidate provenance URL")
        published = valid_day(row.get("date"))
        if published > checked:
            raise ValueError("Candidate published in the future")
        if aid in old or aid in known_ids:
            continue
        title, authors = row.get("title"), row.get("authors")
        if not isinstance(title, str) or not 5 <= len(title) <= 300:
            raise ValueError("Invalid candidate title")
        if not isinstance(authors, list) or not 1 <= len(authors) <= 12:
            raise ValueError("Invalid candidate authors")
        new.append({
            "arxiv_id": aid, "title": title, "date": row["date"],
            "authors": authors, "url": row["url"],
            "first_seen_on": report["checked"], "status": "pending",
            "discovery_source": "arXiv Atom API",
            "source_issue": "https://github.com/momo-hub-learn/frontierlog/issues/35",
        })
        old.add(aid)
    if not new:
        return queue, 0
    updated = dict(queue)
    updated["items"] = sorted(
        [*queue["items"], *new],
        key=lambda x: (x["date"], x["arxiv_id"]), reverse=True,
    )
    updated["checked"] = report["checked"]  # last change, not last poll
    validate_queue(updated)
    return updated, len(new)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--queue", type=Path, default=ROOT / "data/frontier-candidates.json")
    args = parser.parse_args()
    from frontier_paper_watch import covered_ids
    report = json.loads(args.report.read_text(encoding="utf-8"))
    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    models = json.loads((ROOT / "data/models.json").read_text(encoding="utf-8"))
    research = json.loads((ROOT / "data/research-radar.json").read_text(encoding="utf-8"))
    updated, added = merge_queue(queue, report, covered_ids(models, research))
    if added:
        with NamedTemporaryFile("w", encoding="utf-8", dir=args.queue.parent, delete=False) as f:
            f.write(json.dumps(updated, ensure_ascii=False, indent=2) + "\n")
            temp = Path(f.name)
        temp.replace(args.queue)
    print(f"World Model review queue: +{added} new, {len(updated['items'])} preserved; auto-published 0.")


if __name__ == "__main__":
    main()
