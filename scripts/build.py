"""Build a portable static site. Python 3.10+, no third-party dependencies."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from datetime import date, datetime, timezone
from email.utils import format_datetime
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from topics import validate_topics, topic_rss
from model_data import validate_models, validate_resets, model_rss, reset_rss
from benchmark_data import validate_benchmarks, benchmark_rss
from hot_data import validate_hot, hot_rss
ROOT = Path(__file__).resolve().parents[1]
REPO_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$')

def https_url(value: str) -> bool:
    try:
        u=urlparse(value)
        return u.scheme=='https' and bool(u.hostname) and not u.username and not u.password
    except ValueError:
        return False

def validate(catalog: dict, upstream: dict, site: dict) -> None:
    if catalog.get('version') != 2:
        raise ValueError('Unsupported catalog schema version')
    snapshot = date.fromisoformat(catalog['snapshot'])
    ids=[x['id'] for x in catalog['items']]
    sids=[s['id'] for s in catalog['sources']]
    event_ids=[e['id'] for e in catalog['events']]
    for seq in (ids,sids,event_ids):
        if len(seq)!=len(set(seq)):
            raise ValueError('Duplicate identifiers')
    for i in ids+sids+event_ids:
        if not re.fullmatch('[a-z0-9][a-z0-9-]*',i):
            raise ValueError('Unsafe identifier: '+i)
    for s in catalog['sources']:
        if not https_url(s['url']): raise ValueError('Invalid source URL')
        if date.fromisoformat(s['checked'])>snapshot: raise ValueError('Check date after snapshot')
        if s['published'] and date.fromisoformat(s['published'])>snapshot: raise ValueError('Future source date')
    for t in catalog['items']:
        if t['status'] not in {'code','research'}: raise ValueError('Invalid availability')
        if t['accent'] not in {'lime','cyan','orange','blue','pink','violet'}: raise ValueError('Invalid accent')
        if not t['sources'] or not set(t['sources']).issubset(sids): raise ValueError('Missing sources')
        if not isinstance(t['tested'],bool): raise ValueError('Invalid tested state')
        if t['repo'] and not REPO_RE.fullmatch(t['repo']): raise ValueError('Invalid upstream repository')
        if not isinstance(t['checks'],list) or not t['checks']: raise ValueError('Missing checklist')
        date.fromisoformat(t['reviewed'])
    for e in catalog['events']:
        if e['task'] not in ids or e['kind'] not in {'release','research'}: raise ValueError('Invalid event')
        if not e['sources'] or not set(e['sources']).issubset(sids): raise ValueError('Event has no provenance')
        if date.fromisoformat(e['date'])>snapshot: raise ValueError('Future curated event')
    for e in upstream.get('releases',[]):
        if e['task'] not in ids or not https_url(e['url']): raise ValueError('Invalid upstream release')
        if e['review_status']!='unreviewed': raise ValueError('Collector may not approve evidence')
        datetime.fromisoformat(e['published_at'].replace('Z','+00:00'))
    if site.get('repository') and not REPO_RE.fullmatch(site['repository']): raise ValueError('Invalid site repository')
    if site.get('base_url') and not https_url(site['base_url']): raise ValueError('Base URL must use HTTPS')

def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def make_rss(catalog:dict,site:dict) -> bytes:
    base=site['base_url'].rstrip('/')+'/'
    rss=ET.Element('rss',version='2.0')
    channel=ET.SubElement(rss,'channel')
    for k,v in {'title':site['title'],'link':base,'description':site['description'],'language':'zh-CN'}.items():
        ET.SubElement(channel,k).text=v
    ts=datetime.fromisoformat(catalog['snapshot']).replace(tzinfo=timezone.utc)
    ET.SubElement(channel,'lastBuildDate').text=format_datetime(ts)
    ET.register_namespace('atom','http://www.w3.org/2005/Atom')
    ET.SubElement(channel,'{http://www.w3.org/2005/Atom}link',href=base+'feed.xml',rel='self',type='application/rss+xml')
    sources={s['id']:s for s in catalog['sources']}
    for e in sorted(catalog['events'],key=lambda e:e['date'],reverse=True):
        item=ET.SubElement(channel,'item')
        ET.SubElement(item,'title').text=e['title']
        ET.SubElement(item,'link').text=base+'#/activity?task='+e['task']+'&tab=timeline'
        ET.SubElement(item,'guid',isPermaLink='false').text='ai-progress:'+e['id']
        ET.SubElement(item,'pubDate').text=format_datetime(datetime.fromisoformat(e['date']).replace(tzinfo=timezone.utc))
        ET.SubElement(item,'description').text=e['summary']+'\n\n编辑解读：'+e['delta']+'\n\n公开资料，本站未复测。\n来源：'+'\n'.join(sources[s]['url'] for s in e['sources'])
    return ET.tostring(rss,encoding='utf-8',xml_declaration=True)

def build(output: Path, repository: str|None=None,base_url: str|None=None) -> dict:
    catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
    upstream=json.loads((ROOT/'data/upstream.json').read_text(encoding='utf-8'))
    site=json.loads((ROOT/'data/site.json').read_text(encoding='utf-8'))
    if repository is not None:site['repository']=repository
    if base_url is not None:site['base_url']=base_url.rstrip('/')+'/' if base_url else ''
    validate(catalog,upstream,site)
    industry=json.loads((ROOT/'data/industry.json').read_text(encoding='utf-8'))
    intake=json.loads((ROOT/'data/topic-intake.json').read_text(encoding='utf-8'))
    validate_topics(industry,intake)
    models=json.loads((ROOT/'data/models.json').read_text(encoding='utf-8'))
    resets=json.loads((ROOT/'data/resets.json').read_text(encoding='utf-8'))
    validate_models(models); validate_resets(resets)
    benchmarks=json.loads((ROOT/'data/benchmarks.json').read_text(encoding='utf-8'))
    validate_benchmarks(benchmarks)
    hot=json.loads((ROOT/'data/hot.json').read_text(encoding='utf-8'))
    validate_hot(hot)
    hot_policy=json.loads((ROOT/'data/hot-policy.json').read_text(encoding='utf-8'))
    app={'hot':hot,'hot_policy':hot_policy,'benchmarks':benchmarks,'models':models,'resets':resets,'catalog':catalog,'upstream':upstream,'site':site,'industry':industry,'intake':intake}
    template=(ROOT/'src/index.html').read_text(encoding='utf-8')
    css=(ROOT/'src/styles.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/vertical.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/models.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/benchmarks.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/hot.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/polish.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/type-icons.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/v9.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/v10.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/capabilities.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/intraday.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/v2.css').read_text(encoding='utf-8')
    js=(ROOT/'src/app.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/vertical.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/models.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/hot.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/benchmarks.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/v9.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/v10.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/capabilities.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/intraday.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/v2.js').read_text(encoding='utf-8')
    for marker in ('@@CSS@@','@@JS@@','@@DATA@@','@@FEED@@'):
        if template.count(marker)!=1:raise ValueError('Template marker missing or duplicated: '+marker)
    payload=json.dumps(app,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    from html import escape
    feed=''
    if site['base_url']:
        feed='<link rel="alternate" type="application/rss+xml" title="AI坐标" href="'+escape(site['base_url']+'feed.xml',quote=True)+'">\n<link rel="canonical" href="'+escape(site['base_url'],quote=True)+'">'
    html=template.replace('@@CSS@@',css).replace('@@JS@@',js).replace('@@DATA@@',payload).replace('@@FEED@@',feed)
    output.mkdir(parents=True,exist_ok=True)
    (output/'index.html').write_text(html,encoding='utf-8')
    (output/'404.html').write_text(html,encoding='utf-8')
    (output/'.nojekyll').write_text('')
    (output/'assets').mkdir(exist_ok=True)
    (output/'assets/brand.svg').write_bytes((ROOT/'src/brand.svg').read_bytes())
    write_json(output/'api/v1/index.json',app)
    write_json(output/'api/v1/events.json',{'snapshot':catalog['snapshot'],'events':catalog['events'],'sources':catalog['sources']})
    write_json(output/'api/v1/upstream.json',upstream)
    write_json(output/'api/v1/topics.json',industry)
    write_json(output/'api/v1/models.json',models)
    write_json(output/'api/v1/resets.json',resets)
    write_json(output/'api/v1/benchmarks.json',benchmarks)
    write_json(output/'api/v1/hot.json',hot)
    write_json(output/'api/v1/hot-policy.json',hot_policy)
    write_json(output/'api/v1/topic-intake.json',intake)
    if site['base_url']:
        # Unified RSS preserves original event dates and stable identifiers.
        rss=ET.fromstring(make_rss(catalog,site))
        rootfeed=ET.fromstring(topic_rss(industry,site,'all'))
        for item in rootfeed.findall('./channel/item'):rss.find('channel').append(item)
        rss.find('./channel/lastBuildDate').text=rootfeed.find('./channel/lastBuildDate').text
        (output/'feed.xml').write_bytes(ET.tostring(rss,encoding='utf-8',xml_declaration=True))
        (output/'feeds').mkdir(exist_ok=True)
        for scope in ['all']+[s['id'] for s in industry['sectors']]+[t['id'] for t in industry['topics']]:
            (output/'feeds'/f'{scope}.xml').write_bytes(topic_rss(industry,site,scope))
        (output/'feeds/models.xml').write_bytes(model_rss(models,site))
        (output/'feeds/resets.xml').write_bytes(reset_rss(resets,site))
        (output/'feeds/benchmarks.xml').write_bytes(benchmark_rss(benchmarks,site))
        (output/'feeds/hot.xml').write_bytes(hot_rss(hot,site))
        base=site['base_url']
        sitemap=ET.Element('urlset',xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
        u=ET.SubElement(sitemap,'url');ET.SubElement(u,'loc').text=base;ET.SubElement(u,'lastmod').text=industry['checked']
        (output/'sitemap.xml').write_bytes(ET.tostring(sitemap,encoding='utf-8',xml_declaration=True))
        (output/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+base+'sitemap.xml\n')
    else:
        for name in ('feed.xml','sitemap.xml','robots.txt'):(output/name).unlink(missing_ok=True)
        import shutil
        shutil.rmtree(output/'feeds',ignore_errors=True)
    return app

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,default=ROOT/'dist')
    p.add_argument('--repo',default=None)
    p.add_argument('--base-url',default=None)
    args=p.parse_args()
    app=build(args.out,args.repo,args.base_url)
    print(f'Built {args.out}: {len(app["catalog"]["items"])} tasks, {len(app["catalog"]["events"])} curated events. RSS: {bool(app["site"]["base_url"])}')
