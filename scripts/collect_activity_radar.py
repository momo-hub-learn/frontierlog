from __future__ import annotations
import argparse, hashlib, html, json, re, urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/activity-radar.json'
API=ROOT/'api/v1/activity-radar.json'

def text(el, names):
    for name in names:
        node=el.find(name)
        if node is not None and node.text:
            return node.text.strip()
    return ''

def clean(s):
    s=re.sub(r'<[^>]+>',' ',html.unescape(s or ''))
    return re.sub(r'\s+',' ',s).strip()

def date_only(raw):
    if not raw:return ''
    try:return parsedate_to_datetime(raw).date().isoformat()
    except Exception:
        try:return datetime.fromisoformat(raw.replace('Z','+00:00')).date().isoformat()
        except Exception:return ''

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'frontierlog-activity-radar/1.0'})
    with urllib.request.urlopen(req,timeout=20) as r:return r.read()

def entries(xml):
    root=ET.fromstring(xml)
    out=[]
    for item in root.findall('.//item'):
        out.append({
            'title':text(item,['title']),
            'url':text(item,['link']),
            'date':date_only(text(item,['pubDate','{http://purl.org/dc/elements/1.1/}date'])),
            'summary':clean(text(item,['description','{http://purl.org/rss/1.0/modules/content/}encoded']))
        })
    if out:return out
    ns='{http://www.w3.org/2005/Atom}'
    for item in root.findall('.//'+ns+'entry'):
        link=''
        for a in item.findall(ns+'link'):
            if a.get('rel','alternate')=='alternate' and a.get('href'):link=a.get('href');break
        out.append({
            'title':text(item,[ns+'title']),
            'url':link,
            'date':date_only(text(item,[ns+'published',ns+'updated'])),
            'summary':clean(text(item,[ns+'summary',ns+'content']))
        })
    return out

def tags(s):
    q=s.lower(); out=[]
    rules=[('agent','Agents'),('alignment','Alignment'),('recursive','RSI'),('diffusion','Diffusion'),('inference','Inference'),('robot','Robotics'),('bio','BioAI'),('coding','Coding'),('programming','Coding'),('gpu','AI Infra'),('nvidia','AI Infra'),('safety','Safety'),('model','Models')]
    for k,v in rules:
        if k in q and v not in out:out.append(v)
    return out[:4]

def main():
    d=json.loads(DATA.read_text())
    sources={x['id']:x for x in d['sources']}
    manual=[x for x in d.get('media_items',[]) if x.get('origin')!='rss']
    auto=[]; ok=0
    for sid,s in sources.items():
        url=s.get('feed_url')
        if not url:continue
        try:
            rows=entries(fetch(url)); ok+=1
        except Exception as e:
            print('feed failed',sid,e);continue
        kws=[x.lower() for x in s.get('include_keywords',[])]
        kept=0
        for x in rows:
            hay=(x['title']+' '+x['summary']).lower()
            if kws and not any(k in hay for k in kws):continue
            if not x['title'] or not x['url'] or not x['date']:continue
            key=hashlib.sha1((sid+'|'+x['url']).encode()).hexdigest()[:12]
            auto.append({'id':sid+'-'+key,'source_id':sid,'published':x['date'],'title':x['title'][:220],'summary':x['summary'][:320],'url':x['url'],'tags':tags(hay),'origin':'rss'})
            kept+=1
            if kept>=3:break
    if not ok:raise SystemExit('no public feeds fetched successfully')
    existing={(x['source_id'],x['title'].strip().lower()) for x in manual}
    unique=[];seen_ids=set();seen_titles=set()
    for x in auto:
        title_key=(x['source_id'],x['title'].strip().lower())
        if title_key in existing or title_key in seen_titles or x['id'] in seen_ids:continue
        seen_titles.add(title_key);seen_ids.add(x['id']);unique.append(x)
    auto=unique
    merged=manual+auto
    merged.sort(key=lambda x:(x.get('published',''),x.get('id','')),reverse=True)
    d['media_items']=merged[:18]
    now=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
    d['checked_at']=now;d['sync']['last_success']=now
    text_out=json.dumps(d,ensure_ascii=False,indent=2)+'\n'
    DATA.write_text(text_out)
    API.write_text(text_out)
    print('activity radar:',len(d['media_items']),'items from',ok,'feeds')

if __name__=='__main__':main()
