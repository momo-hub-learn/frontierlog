"""Schemas and source-faithful feeds for model scores and public reset records.

No dependencies. A benchmark score is never a clinical/industrial validation;
source-date events are never silently converted to an exact reset timestamp.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from email.utils import format_datetime
from hashlib import sha256
from urllib.parse import urlparse, quote
from xml.etree import ElementTree as ET
import json, math, re

ID = re.compile(r'^[a-z0-9][a-z0-9-]{0,160}$')
NUMBERS = ('intelligence','preference','speed','cost_task','input_price','output_price','coding','math','score_error','source_rank','source_order','votes')

def fail(message: str) -> None: raise ValueError(message)
def text(x, name):
    if not isinstance(x,str) or not x.strip(): fail('Missing text: '+name)
    return x

def day(x):
    if not isinstance(x,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',x): fail('Invalid source date')
    return date.fromisoformat(x)

def instant(x):
    if not isinstance(x,str): fail('Invalid timestamp')
    t=datetime.fromisoformat(x.replace('Z','+00:00'))
    if not t.tzinfo: fail('Timestamp requires timezone')
    return t

def https(x):
    if not isinstance(x,str): return False
    try:
        u=urlparse(x)
        return u.scheme=='https' and bool(u.hostname) and not u.username and not u.password
    except ValueError:return False

def identifiers(seq):
    ids=[x.get('id') for x in seq]
    if any(not isinstance(x,str) or not ID.fullmatch(x) for x in ids) or len(set(ids))!=len(ids): fail('Unsafe or duplicate identifiers')
    return set(ids)

def sources(data):
    if not isinstance(data.get('sources'),list) or not data['sources']: fail('Missing sources')
    ids=identifiers(data['sources'])
    for s in data['sources']:
        if not https(s.get('url')):fail('Unsafe source URL')
        text(s.get('title'),'source title');text(s.get('publisher'),'publisher');day(s['checked'])
        if s.get('published') is not None:day(s['published'])
    return ids

def sync(data):
    s=data.get('sync')
    if not isinstance(s,dict) or s.get('status') not in {'not_configured','success','error','partial','disabled'}:fail('Invalid sync state')
    for f in ('last_attempt','last_success'):
        if s.get(f) is not None:instant(s[f])
    if s.get('status')=='success' and not s.get('last_success'): fail('Success requires timestamp')

def validate_models(data):
    if data.get('version')!=1:fail('Unsupported model schema')
    day(data['checked']);sids=sources(data);sync(data)
    if not isinstance(data.get('boards'),list) or not data['boards']:fail('Missing boards')
    identifiers(data['boards']);all_ids=set()
    for b in data['boards']:
        if b['id'] not in {'aa','arena'}:fail('Unknown board')
        day(b['checked'])
        if b.get('as_of') is not None:day(b['as_of'])
        if b['source'] not in sids:fail('Board source missing')
        if b['mode'] not in {'manual_excerpt','authorized_api'}:fail('Invalid ingestion mode')
        text(b.get('methodology'),'methodology');text(b.get('scope'),'scope')
        rows=b.get('rows')
        if not isinstance(rows,list) or not rows or len(rows)>3000:fail('Invalid model rows')
        ids=identifiers(rows)
        if ids & all_ids:fail('Duplicate cross-board model ID')
        all_ids|=ids
        for r in rows:
            text(r.get('name'),'name');text(r.get('maker'),'maker')
            if r.get('source') not in sids:fail('Model source missing')
            for k in NUMBERS:
                v=r.get(k)
                if v is not None and (type(v) not in (int,float) or not math.isfinite(v) or v<0):fail('Invalid model value: '+k)
            for k in ('source_rank','source_order','votes'):
                if r.get(k) is not None and int(r[k])!=r[k]:fail('Count or rank must be an integer')
            if b['id']=='aa' and r.get('preference') is not None:fail('Arena scores cannot be AA scores')
            if b['id']=='arena' and r.get('intelligence') is not None:fail('AA scores cannot be Arena scores')
            spread=r.get('rank_spread')
            if spread is not None and (not isinstance(spread,list) or len(spread)!=2 or any(type(v)!=int or v<1 for v in spread) or spread[0]>spread[1]):fail('Invalid rank interval')
            if r.get('preliminary') is not None and not isinstance(r['preliminary'],bool):fail('Invalid provisional flag')

def validate_resets(data):
    if data.get('version')!=1:fail('Unsupported reset schema')
    day(data['checked']);sids=sources(data);sync(data)
    if not re.fullmatch(r'[A-Za-z0-9_]{1,15}',data.get('account','')):fail('Invalid public handle')
    for key in ('profile_url','usage_url'):
        if not https(data.get(key)):fail('Invalid public URL')
    events=data.get('events')
    if not isinstance(events,list):fail('Missing reset list')
    ids=identifiers(events)
    primary={s['id'] for s in data['sources'] if s.get('kind') in {'官方说明','官方原帖'}}
    for e in events:
        if e.get('kind') not in {'global','banked','announcement'}:fail('Invalid reset kind')
        if e.get('status') not in {'confirmed','pending','announced','withdrawn'}:fail('Invalid reset state')
        if not e.get('sources') or not set(e['sources'])<=sids:fail('Reset source missing')
        day(e['date']);day(e['reviewed']);text(e.get('title'),'event title')
        for field in ('summary','scope','boundary'):text(e.get(field),field)
        if e.get('precision') not in {'source_date','instant'}:fail('Invalid date precision')
        if e['precision']=='source_date' and (e.get('published_at') or e.get('effective_at')):fail('Do not synthesize source-date timestamps')
        if e['precision']=='instant':instant(e.get('published_at'))
        if e.get('effective_at'):instant(e['effective_at'])
        if e['status'] in {'confirmed','announced'} and (e.get('review_basis')!='primary_source' or not primary.intersection(e['sources'])):fail('Confirmation needs primary-source review')
        if e['kind']=='announcement' and e['status']=='confirmed':fail('An announcement is not a completed reset')
        if not set(e.get('related_ids',[]))<=ids:fail('Unknown related record')
    inbox=data.get('inbox',[])
    if not isinstance(inbox,list) or len(inbox)>3000:fail('Invalid intake')
    identifiers(inbox)
    for e in inbox:
        if e.get('review_status')!='pending' or not https(e.get('url')):fail('Collector cannot approve reset claims')
        instant(e['published_at']);text(e.get('excerpt'),'excerpt')
        if len(e['excerpt'])>280:fail('Excerpt too long')

def feed_base(site,title,description,checked,path):
    base=site.get('base_url','').rstrip('/')+'/'
    if not https(base):fail('RSS requires a public HTTPS base URL')
    rss=ET.Element('rss',version='2.0');ch=ET.SubElement(rss,'channel')
    for k,v in {'title':title,'link':base+path,'description':description,'language':'zh-CN'}.items():ET.SubElement(ch,k).text=v
    # Snapshot build date is not an assertion about original event times.
    ET.SubElement(ch,'lastBuildDate').text=format_datetime(datetime.combine(day(checked),datetime.min.time(),timezone.utc))
    return rss,ch,base

def model_rss(data,site):
    validate_models(data)
    rss,ch,base=feed_base(site,'AI坐标 · 模型榜','榜单快照与原始来源；不同评分体系不混算。',data['checked'],'#/models')
    smap={s['id']:s for s in data['sources']}
    for b in data['boards']:
        e=ET.SubElement(ch,'item');ET.SubElement(e,'title').text=b['provider']+' · '+b['checked']+' 核对快照'
        ET.SubElement(e,'link').text=base+'#/models?board='+b['id']
        signature=sha256(json.dumps(b,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
        ET.SubElement(e,'guid',isPermaLink='false').text='frontierlog:models:'+b['id']+':'+signature
        ET.SubElement(e,'description').text=f"{b['scope']}\n方法：{b['methodology']}\n来源日期：{b.get('as_of') or '未标单一日期'}\n核对日期：{b['checked']}\n来源：{smap[b['source']]['url']}"
    return ET.tostring(rss,encoding='utf-8',xml_declaration=True)

def reset_rss(data,site):
    validate_resets(data)
    rss,ch,base=feed_base(site,'AI坐标 · Tibo 重置监控','公开公告记录，不是个人额度。日期不完整的记录不编造发生时刻。',data['checked'],'#/tibo')
    status={'confirmed':'来源已确认','pending':'待核验','announced':'预告','withdrawn':'已撤回'}
    smap={s['id']:s for s in data['sources']}
    for r in sorted(data['events'],key=lambda r:r['date'],reverse=True):
        e=ET.SubElement(ch,'item');ET.SubElement(e,'title').text='['+status[r['status']]+'] '+r['title']
        ET.SubElement(e,'link').text=base+'#/tibo?event='+quote(r['id'])
        ET.SubElement(e,'guid',isPermaLink='false').text='frontierlog:reset:'+r['id']+':'+r['status']
        if r['precision']=='instant':ET.SubElement(e,'pubDate').text=format_datetime(instant(r['published_at']))
        ET.SubElement(e,'description').text=f"来源记日：{r['date']}\n{r['summary']}\n范围：{r['scope']}\n限制：{r['boundary']}\n来源："+'\n'.join(smap[i]['url'] for i in r['sources'])
    return ET.tostring(rss,encoding='utf-8',xml_declaration=True)
