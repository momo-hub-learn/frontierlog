"""Collect public RSS/Atom and GitHub Release metadata into a REVIEW queue.

Python 3.10+. No model, private data, browser cookies, or paid API required.
Only declared HTTPS endpoints are fetched, bounded to 4 MiB per response.
Never modifies industry.json, never promotes evidence, retains last good data.
"""
from __future__ import annotations
import argparse, copy, hashlib, html, ipaddress, json, os, re, sys, time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, urljoin
from urllib.request import Request, build_opener, HTTPRedirectHandler
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
MAX_BYTES=4*1024*1024
TRACKING={'fbclid','gclid','mc_cid','mc_eid'}
REPO_RE=re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')

def valid_url(value):
    try:
        u=urlsplit(value)
        if u.scheme!='https' or not u.hostname or u.username or u.password or u.port not in (None,443):return False
        if u.hostname in {'localhost','localhost.localdomain'} or u.hostname.endswith(('.local','.internal')):return False
        try:
            if not ipaddress.ip_address(u.hostname).is_global:return False
        except ValueError:pass
        return True
    except (TypeError,ValueError):return False

def canonical_url(value):
    if not valid_url(value):raise ValueError('Invalid public HTTPS URL')
    u=urlsplit(value)
    query=urlencode(sorted((k,v) for k,v in parse_qsl(u.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in TRACKING))
    return urlunsplit(('https',u.netloc.lower(),u.path or '/',query,''))

def plain(value,limit=180):
    # Remove markup and unneeded entire executable blocks before creating a short excerpt.
    s=re.sub(r'<(script|style)\b[^>]*>.*?</\1\s*>',' ',str(value or ''),flags=re.I|re.S)
    s=html.unescape(re.sub(r'<[^>]+>',' ',s))
    s=re.sub(r'\s+',' ',s).strip()
    return s[:limit]+('…' if len(s)>limit else '')

def parse_date(value):
    if not value:return None
    try:
        d=datetime.fromisoformat(value.strip().replace('Z','+00:00'))
    except (ValueError,TypeError):
        try:d=parsedate_to_datetime(value)
        except (TypeError,ValueError,OverflowError):return None
    if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).isoformat().replace('+00:00','Z')

def local(tag):return tag.split('}')[-1].lower()

def child_text(node,*names):
    for x in node:
        if local(x.tag) in names:return ''.join(x.itertext()).strip()
    return ''

def parse_feed(payload,base):
    if len(payload)>MAX_BYTES:raise ValueError('Feed too large')
    if re.search(br'<!\s*(DOCTYPE|ENTITY)',payload,re.I):raise ValueError('DTD / entity declarations prohibited')
    root=ET.fromstring(payload)
    if local(root.tag) not in {'rss','feed','rdf'}:raise ValueError('Expected RSS or Atom, not HTML')
    out=[]
    for node in root.iter():
        if local(node.tag) not in {'item','entry'}:continue
        link=child_text(node,'link')
        if local(node.tag)=='entry':
            for x in node:
                if local(x.tag)=='link' and x.attrib.get('rel','alternate')=='alternate':
                    link=x.attrib.get('href','');break
        url=urljoin(base,link)
        title=plain(child_text(node,'title'),240)
        if not title or not valid_url(url):continue
        raw=child_text(node,'published','pubdate','date')
        # Atom updated is metadata only; not silently relabelled publication date.
        out.append({'title':title,'url':canonical_url(url),'published_at':parse_date(raw),
                    'updated_at':parse_date(child_text(node,'updated')),
                    'excerpt':plain(child_text(node,'description','summary','encoded','content'))})
        if len(out)>=100:break
    return out

def parse_releases(payload):
    if len(payload)>MAX_BYTES:raise ValueError('Release response too large')
    value=json.loads(payload)
    if not isinstance(value,list):raise ValueError('Expected GitHub releases array')
    rows=[]
    for r in value[:30]:
        if r.get('draft') or not valid_url(r.get('html_url')):continue
        rows.append({'title':plain(r.get('name') or r.get('tag_name'),240),
                     'url':canonical_url(r['html_url']),'published_at':parse_date(r.get('published_at')),
                     'updated_at':None,'excerpt':plain(r.get('body')),
                     'prerelease':bool(r.get('prerelease'))})
    return rows

def has(text,terms):return any(x in text for x in terms)

def classify(title,excerpt='',defaults=()):
    """Conservative lexical routing, NOT a claim of capability. Multi-label allowed."""
    text=(title+' '+excerpt).lower();out=set(defaults)
    bio=has(text,['drug','clinical','biolog','protein','genetic','genomic','pharma','disease','靶点','临床','药物','医学','蛋白','基因','疾病'])
    fab=has(text,['wafer','semiconductor fab','semiconductor tool','semiconductor equipment','晶圆','晶圓','半导体设备','半導體設備'])
    industrial=has(text,['industrial','manufactur','factory','plc','machine tool','设备','装备','工业','工厂','产线','晶圆','fab'])
    if has(text,['clinical study report','clinical study reports','medical writing','regulatory authoring','临床研究报告','医学写作']):out.add('csr')
    elif re.search(r'\bcsr\b',text) and bio and not has(text,['corporate social responsibility','sustainability report','企业社会责任']):out.add('csr')
    if bio and has(text,['target','靶点','靶點','gene-disease','crispr']):out.add('targets')
    if bio and has(text,['molecule','molecular','protein design','docking','分子','虚拟筛选']):out.add('molecules')
    if has(text,['clinical trial','clinicaltrials.gov','临床试验','试验注册','trial registry']):out.add('clinical')
    if fab and has(text,['defect','yield','inspection','metrology','良率','缺陷','检测','量测']):out.add('fab-yield')
    if fab and has(text,['process control','fault detection','fdc','apc','工艺控制','过程控制','制程']):out.add('fab-process')
    if fab and has(text,['maintenance','equipment intelligence','dextro','chamber','维护','机台','腔体']):out.add('fab-maintenance')
    if industrial and has(text,['engineering','plc','cad','design','工程','研发','设计']):out.add('equipment-design')
    if industrial and has(text,['maintenance','anomaly','quality inspection','维护','运维','质检']):out.add('equipment-maintenance')
    if industrial and has(text,['digital twin','simulation','数字孪生','仿真']):out.add('digital-twin')
    return sorted(out)

class GuardRedirect(HTTPRedirectHandler):
    def __init__(self,hosts):self.hosts=hosts
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not valid_url(newurl) or urlsplit(newurl).hostname not in self.hosts:raise ValueError('Unapproved redirect host')
        new=super().redirect_request(req,fp,code,msg,headers,newurl)
        if new and urlsplit(newurl).hostname!='api.github.com':
            new.remove_header('Authorization')
        return new

def fetch_source(source):
    if source['type']=='github':
        repo=source['repo']
        if not REPO_RE.fullmatch(repo):raise ValueError('Invalid repository name')
        url=f'https://api.github.com/repos/{repo}/releases?per_page=20'
    else:url=source['url']
    if not valid_url(url):raise ValueError('Endpoint must be public HTTPS')
    headers={'User-Agent':'FrontierLog/0.3 public-source-metadata','Accept':'application/json' if source['type']=='github' else 'application/rss+xml,application/atom+xml,application/xml,text/xml'}
    if source['type']=='github' and os.getenv('GITHUB_TOKEN'):
        headers['Authorization']='Bearer '+os.environ['GITHUB_TOKEN']
    hosts={urlsplit(url).hostname,*source.get('redirect_hosts',[])}
    opener=build_opener(GuardRedirect(hosts))
    for attempt in range(2):
        try:
            with opener.open(Request(url,headers=headers),timeout=20) as response:
                body=response.read(MAX_BYTES+1)
            if len(body)>MAX_BYTES:raise ValueError('Response exceeds limit')
            return body
        except HTTPError as e:
            if attempt==0 and e.code in (429,500,502,503,504):time.sleep(1);continue
            raise
        except URLError:
            if attempt==0:time.sleep(1);continue
            raise

def collect(config,previous,fetcher=fetch_source,now=None):
    now=now or datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    result=copy.deepcopy(previous)
    result.update(version=1,last_attempt=now,errors=[],sources=[])
    result.setdefault('last_success',None);result.setdefault('last_full_success',None)
    by_url={canonical_url(i['url']):copy.deepcopy(i) for i in previous.get('items',[]) if valid_url(i.get('url'))}
    enabled=[s for s in config['sources'] if s.get('enabled')];success=0
    known=set(config['topic_ids'])
    for s in enabled:
        try:
            if not set(s.get('default_topics',[]))<=known:raise ValueError('Unknown default topic')
            payload=fetcher(s)
            rows=parse_releases(payload) if s['type']=='github' else parse_feed(payload,s['url'])
            if not rows and not s.get('allow_empty',False):raise ValueError('No parseable records; verify feed endpoint')
            found=0
            for row in rows:
                topics=classify(row['title'],row.get('excerpt',''),s.get('default_topics',[]))
                topics=[t for t in topics if t in known]
                if not topics:continue
                if row.get('published_at') and row['published_at']>now:continue
                url=row['url'];old=by_url.get(url,{})
                item={**row,'id':old.get('id','signal-'+hashlib.sha256(url.encode()).hexdigest()[:16]),
                      'publisher':s['name'],'topics':sorted(set(old.get('topics',[]))|set(topics)),
                      'review_status':'unreviewed','first_seen':old.get('first_seen',now),'last_seen':now,
                      'source_ids':sorted(set(old.get('source_ids',[]))|{s['id']})}
                by_url[url]=item;found+=1
            success+=1;result['sources'].append({'id':s['id'],'name':s['name'],'status':'success','checked_at':now,'parsed':len(rows),'matched':found})
        except Exception as e:
            # Only log error type/status, never response bodies or credentials.
            error=f'HTTP {e.code}' if isinstance(e,HTTPError) else type(e).__name__
            result['errors'].append({'source_id':s['id'],'error':error})
            result['sources'].append({'id':s['id'],'name':s['name'],'status':'failed','checked_at':now,'error':error})
    if success:result['last_success']=now
    if enabled and success==len(enabled):result['last_full_success']=now
    # Bounded retention. On total failure retain every previous record unchanged.
    if success:
        result['items']=sorted(by_url.values(),key=lambda x:(x.get('published_at') or x.get('first_seen',''),x['id']),reverse=True)[:config.get('max_items',500)]
    else:result['items']=copy.deepcopy(previous.get('items',[]))
    result['note']='自动候选资料，未核验。机器分类不等于疗效、良率、可用性或监管结论。'
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,default=ROOT/'data/collect-sources.json')
    p.add_argument('--out',type=Path,default=ROOT/'data/topic-intake.json')
    args=p.parse_args()
    conf=json.loads(args.config.read_text());prev=json.loads(args.out.read_text()) if args.out.exists() else {}
    result=collect(conf,prev)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    tmp=args.out.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');tmp.replace(args.out)
    print(json.dumps({'sources':len(result['sources']),'failures':len(result['errors']),'queue_items':len(result['items'])}))
    # Partial failure recorded but allows valid sources to deploy. Total failure fails the job.
    return 2 if result['sources'] and all(s['status']=='failed' for s in result['sources']) else 0
if __name__=='__main__':sys.exit(main())
