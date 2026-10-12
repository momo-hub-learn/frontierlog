"""A low-noise freshness signal for editorial deep dives.

This does not produce articles or claim independent verification. GitHub Actions
may turn a stale status into one editorial issue until the next deep dive.
"""
from __future__ import annotations
import argparse
import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]

def report(deep:dict, hot:dict, today:date, threshold_days:int=7)->dict:
    if threshold_days < 1: raise ValueError("threshold_days must be positive")
    articles=deep.get("articles",[])
    rows=sorted(articles,key=lambda a:(a["published"],a["id"]),reverse=True)
    latest=rows[0] if rows else None
    latest_date=date.fromisoformat(latest["published"]) if latest else None
    age_days=max(0,(today-latest_date).days) if latest_date else None
    seen={id for a in rows for id in a.get("hot_ids",[])}
    options=[]
    for x in hot.get("items",[]):
        try: published=date.fromisoformat(x["published"])
        except (KeyError,ValueError,TypeError): continue
        if x.get("id") in seen or not 0 <= (today-published).days <= 30: continue
        if x.get("category") not in {"research","model","benchmark","product"}: continue
        options.append({"id":x["id"],"title":x.get("title",""),"published":str(published),"source":x.get("url","")})
    options=sorted(options,key=lambda x:(x["published"],x["id"]),reverse=True)[:6]
    return {
      "stale":latest is None or (age_days is not None and age_days>=threshold_days),
      "today":str(today),"threshold_days":threshold_days,
      "latest_id":latest["id"] if latest else None,
      "latest_title":latest["title"] if latest else None,
      "latest_published":str(latest_date) if latest_date else None,
      "age_days":age_days,"uncovered_hot_candidates":options,
      "note":"待编辑审核：热点候选仅供选题，不保证研究价值或一手核验，不会自动发布深读。"
    }

def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today",default="",help="YYYY-MM-DD in Asia/Shanghai (for deterministic checks)")
    parser.add_argument("--threshold-days",type=int,default=7)
    args=parser.parse_args()
    today=date.fromisoformat(args.today) if args.today else datetime.now(ZoneInfo("Asia/Shanghai")).date()
    deep=json.loads((ROOT/"data/deep-dives.json").read_text(encoding="utf-8"))
    hot=json.loads((ROOT/"data/hot.json").read_text(encoding="utf-8"))
    print(json.dumps(report(deep,hot,today,args.threshold_days),ensure_ascii=False,indent=2))

if __name__=="__main__": main()
