"""Discover *unreviewed* recent world-model/JEPA papers from arXiv Atom.

This creates an editorial issue, NEVER an automatically ranked model or a claim
that the model is available. The arXiv ID, published date and author list form
the evidence; updates to an existing paper do not become new releases.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
ATOM="{http://www.w3.org/2005/Atom}"
MAX_BYTES=2_000_000
API="https://export.arxiv.org/api/query"
ARXIV_RE=re.compile(r"(?:arxiv\.org/(?:abs|pdf)/|arxiv:)(\d{4}\.\d{4,5})",re.I)
TOPIC=re.compile(r"\b(?:world[\s-]?models?|jepa|visual planning|inverse dynamics|"
                 r"latent dynamics|action[\s-]?conditioned|predictive architecture|"
                 r"visual control)\b",re.I)
AUTHOR_RE=re.compile(r"(?:^|[\s,])le[\s-]?cun(?:$|[\s,])",re.I)


def feed_url(query: str, maximum=50) -> str:
    return API+"?"+urlencode({"search_query":query,"start":0,
                              "max_results":maximum,
                              "sortBy":"submittedDate","sortOrder":"descending"})


def get_feed(url: str) -> bytes:
    req=Request(url,headers={"User-Agent":"FrontierLog-WorldModelResearchWatch/1.0 "
                                           "(https://github.com/momo-hub-learn/frontierlog)",
                             "Accept":"application/atom+xml"})
    with urlopen(req,timeout=25) as res:
        payload=res.read(MAX_BYTES+1)
    if len(payload)>MAX_BYTES:raise ValueError("arXiv response too large")
    return payload


def parse_feed(payload: bytes) -> list[dict]:
    if re.search(br"<!\s*(?:DOCTYPE|ENTITY)",payload,re.I):
        raise ValueError("DTD/entity not allowed")
    root=ET.fromstring(payload)
    if root.tag!=ATOM+"feed":raise ValueError("Expected arXiv Atom feed")
    out=[]
    for e in root.findall(ATOM+"entry")[:70]:
        url=(e.findtext(ATOM+"id") or "").strip()
        match=ARXIV_RE.search(url)
        if not match:continue
        published=(e.findtext(ATOM+"published") or "").strip()
        try:d=datetime.fromisoformat(published.replace("Z","+00:00"))
        except ValueError:continue
        if d.tzinfo is None:continue
        title=" ".join((e.findtext(ATOM+"title") or "").split())
        abstract=" ".join((e.findtext(ATOM+"summary") or "").split())
        authors=[" ".join((a.findtext(ATOM+"name") or "").split())
                 for a in e.findall(ATOM+"author")]
        if not title or not authors:continue
        out.append({"arxiv_id":match.group(1),"title":title,"date":str(d.date()),
                    "url":"https://arxiv.org/abs/"+match.group(1),
                    "authors":authors,"abstract":abstract[:700]})
    return out


def covered_ids(models: dict, research: dict) -> set[str]:
    urls=[x.get("url","") for x in models.get("sources",[])]
    urls += [s.get("url","") for x in research.get("items",[])
             for s in x.get("sources",[])]
    return {m.group(1) for url in urls if (m:=ARXIV_RE.search(url))}


def candidates(author_rows: list[dict],topic_rows: list[dict],
               known: set[str],today: date, horizon=30) -> list[dict]:
    if not 1<=horizon<=90:raise ValueError("Invalid research discovery horizon")
    merged={}
    for row in author_rows:
        if any(AUTHOR_RE.search(x) for x in row["authors"]) and TOPIC.search(row["title"]+" "+row["abstract"]):
            merged[row["arxiv_id"]]=row
    for row in topic_rows:
        if TOPIC.search(row["title"]):
            merged.setdefault(row["arxiv_id"],row)
    return sorted(({
        "arxiv_id":x["arxiv_id"],"title":x["title"],"url":x["url"],
        "date":x["date"],"authors":x["authors"][:8],
        "status":"editorial_review_required"
    } for x in merged.values()
        if x["arxiv_id"] not in known and 0<=(today-date.fromisoformat(x["date"])).days<=horizon),
        key=lambda x:(x["date"],x["arxiv_id"]),reverse=True)[:25]


def discover(today: date,fetch=get_feed) -> dict:
    models=json.loads((ROOT/"data/models.json").read_text(encoding="utf-8"))
    research=json.loads((ROOT/"data/research-radar.json").read_text(encoding="utf-8"))
    by_author=parse_feed(fetch(feed_url("au:LeCun",maximum=45)))
    by_topic=parse_feed(fetch(feed_url('ti:"world model" OR ti:JEPA',maximum=60)))
    if not by_author or not by_topic:
        raise ValueError("arXiv source empty: do not claim research monitoring succeeded")
    rows=candidates(by_author,by_topic,covered_ids(models,research),today)
    return {"checked":str(today),"source":"arXiv Atom API","status":"review_only",
            "auto_publish":False,"candidates":rows,
            "note":"论文题目/摘要只产生待核验线索，需人工核对贡献、代码、基准和日期；不会据此直接产生跨模型排名。"}


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--today",default="",help="YYYY-MM-DD UTC for reproducible checking")
    p.add_argument("--output",type=Path,default=None)
    args=p.parse_args()
    today=date.fromisoformat(args.today) if args.today else datetime.now(timezone.utc).date()
    result=discover(today)
    text=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if args.output:args.output.write_text(text,encoding="utf-8")
    else:print(text)


if __name__=="__main__":main()
