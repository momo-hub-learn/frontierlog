"""Reject cosmetic revision-date changes in the "拆一下" editorial archive.

This is a minimum machine-verifiable gate, not a substitute for source review.
Use --git-parent in CI; import validate_revision for deterministic tests.
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MATERIAL_FIELDS=("opening","sections","architecture","applications","demo","sources")


def material(article: dict) -> str:
    """Ignore date-only, cosmetic taxonomy, reading-time and verification time."""
    payload={k:article.get(k) for k in MATERIAL_FIELDS if k in article}
    if "sources" in payload:
        payload["sources"]=[
            {key:value for key,value in src.items() if key not in ("verified_at","checked")}
            for src in (payload["sources"] or [])
        ]
    return json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":"))


def validate_revision(previous: dict, current: dict) -> None:
    before={a["id"]:a for a in previous.get("articles",[])}
    after={a["id"]:a for a in current.get("articles",[])}
    changed=[]
    for key,now in after.items():
        old=before.get(key)
        if old is None:
            if not now.get("sections") or not now.get("sources"):
                raise ValueError("New deep dive needs substance and primary sources: "+key)
            changed.append(key)
            continue
        old_material=material(old)
        now_material=material(now)
        if now.get("updated")!=old.get("updated") and old_material==now_material:
            raise ValueError("Cosmetic-only date change is forbidden for deep dive: "+key)
        if old_material!=now_material:
            changed.append(key)
            if now.get("updated",now.get("published"))==old.get("updated",old.get("published")) and current.get("checked")!=previous.get("checked"):
                raise ValueError("Substantive revision must preserve a truthful updated date: "+key)
    if current.get("checked")!=previous.get("checked") and not changed:
        raise ValueError("Cannot refresh deep-dive archive checked date without actual content changes")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--git-parent",default="HEAD^")
    args=p.parse_args()
    proc=subprocess.run(
        ["git","show",args.git_parent+":data/deep-dives.json"],
        cwd=ROOT,capture_output=True,text=True,check=False
    )
    if proc.returncode:
        raise SystemExit("Cannot establish prior article data; require at least two fetched commits")
    old=json.loads(proc.stdout)
    current=json.loads((ROOT/"data/deep-dives.json").read_text(encoding="utf-8"))
    validate_revision(old,current)
    print("PASS deep-dive revision authenticity: no date-only updates")


if __name__=="__main__":
    main()
