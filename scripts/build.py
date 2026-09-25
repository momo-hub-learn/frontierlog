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
        p=e.get('publication')
        if p is not None:
            if not isinstance(p,dict) or p.get('status') not in {'preprint','accepted','published'}: raise ValueError('Invalid publication status')
            if not isinstance(p.get('venue'),str) or not p['venue'].strip(): raise ValueError('Missing publication venue')
            if not https_url(p.get('url','')): raise ValueError('Invalid publication URL')
            if p.get('ccf') not in {None,'A','B','C'}: raise ValueError('Invalid CCF rank')
            if p.get('tier') not in {'preprint','top-journal','top-conference','journal','conference'}: raise ValueError('Invalid publication tier')
            date.fromisoformat(p['verified'])
            if p['status']=='preprint' and (p.get('ccf') or p.get('tier')!='preprint'): raise ValueError('Preprint cannot claim venue tier')
    for e in upstream.get('releases',[]):
        if e['task'] not in ids or not https_url(e['url']): raise ValueError('Invalid upstream release')
        if e['review_status']!='unreviewed': raise ValueError('Collector may not approve evidence')
        datetime.fromisoformat(e['published_at'].replace('Z','+00:00'))
    if site.get('repository') and not REPO_RE.fullmatch(site['repository']): raise ValueError('Invalid site repository')
    if site.get('base_url') and not https_url(site['base_url']): raise ValueError('Base URL must use HTTPS')

def validate_product_radar(data:dict)->None:
    if not isinstance(data,dict) or data.get('version')!=1: raise ValueError('Unsupported product radar schema')
    checked=date.fromisoformat(data['checked'])
    if checked>date.today(): raise ValueError('Future product radar check date')
    groups=data.get('groups'); items=data.get('items')
    if not isinstance(groups,list) or len(groups)<2 or not isinstance(items,list) or not 5<=len(items)<=12: raise ValueError('Invalid product radar lists')
    gids=[g.get('id') for g in groups]
    if len(gids)!=len(set(gids)) or any(not isinstance(x,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*',x) for x in gids): raise ValueError('Invalid product radar groups')
    for g in groups:
        if not isinstance(g.get('title'),str) or not g['title'].strip() or not isinstance(g.get('description'),str) or not g['description'].strip(): raise ValueError('Incomplete product radar group')
    ids=[x.get('id') for x in items]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate product radar ID')
    required=('name','company','summary','source_label','evidence','boundary')
    for item in items:
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*',item.get('id','')): raise ValueError('Unsafe product radar ID')
        if item.get('group') not in set(gids): raise ValueError('Unknown product radar group')
        tags=item.get('tags')
        if not isinstance(tags,list) or not 2<=len(tags)<=4 or len(tags)!=len(set(tags)) or any(not isinstance(t,str) or not t.strip() for t in tags): raise ValueError('Invalid product radar tags')
        filter_ids=item.get('filter_ids')
        if not isinstance(filter_ids,list) or not filter_ids or len(filter_ids)!=len(set(filter_ids)): raise ValueError('Invalid product radar filters')
        for key in required:
            if not isinstance(item.get(key),str) or not item[key].strip(): raise ValueError('Missing product radar '+key)
        for key in ('product_url','source_url'):
            if not https_url(item.get(key,'')): raise ValueError('Invalid product radar URL: '+key)
        timeline=item.get('timeline')
        if not isinstance(timeline,list): raise ValueError('Invalid product radar timeline')
        last=None
        for event in timeline:
            if not isinstance(event,dict): raise ValueError('Invalid product radar timeline event')
            ed=date.fromisoformat(event.get('date',''))
            if ed>checked: raise ValueError('Future product radar event')
            if last and ed>last: raise ValueError('Product radar timeline must be newest first')
            last=ed
            for key in ('kind','title'):
                if not isinstance(event.get(key),str) or not event[key].strip(): raise ValueError('Incomplete product radar timeline event')
            if not https_url(event.get('url','')): raise ValueError('Invalid product radar timeline URL')
    filters=data.get('filters')
    if not isinstance(filters,list) or not filters: raise ValueError('Missing product radar filters')
    fids=[f.get('id') for f in filters]
    if len(fids)!=len(set(fids)) or any(not isinstance(x,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*',x) for x in fids): raise ValueError('Invalid product radar filter IDs')
    if any(not isinstance(f.get('title'),str) or not f['title'].strip() for f in filters): raise ValueError('Invalid product radar filter title')
    known=set(fids)
    for item in items:
        if not set(item['filter_ids']).issubset(known): raise ValueError('Unknown product radar filter')

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
    product_radar=json.loads((ROOT/'data/product-radar.json').read_text(encoding='utf-8'))
    validate_product_radar(product_radar)
    hot_policy=json.loads((ROOT/'data/hot-policy.json').read_text(encoding='utf-8'))
    activity_radar=json.loads((ROOT/'data/activity-radar.json').read_text(encoding='utf-8'))
    if activity_radar.get('version') != 1: raise ValueError('Unsupported activity radar schema')
    datetime.fromisoformat(activity_radar['checked_at'].replace('Z','+00:00'))
    ar_sources={s['id']:s for s in activity_radar.get('sources',[])}
    if len(ar_sources)!=len(activity_radar.get('sources',[])): raise ValueError('Duplicate activity radar source')
    for s in ar_sources.values():
        if not https_url(s.get('url','')): raise ValueError('Invalid activity radar source URL')
        if s.get('feed_url') and not https_url(s['feed_url']): raise ValueError('Invalid activity radar feed URL')
    for e in activity_radar.get('events',[]):
        date.fromisoformat(e['date'])
        if e.get('source_id') not in ar_sources or not https_url(e.get('url','')): raise ValueError('Invalid activity radar event')
    ar_ids=set()
    for m in activity_radar.get('media_items',[]):
        if m.get('id') in ar_ids: raise ValueError('Duplicate activity radar item')
        ar_ids.add(m.get('id'))
        date.fromisoformat(m['published'])
        if m.get('source_id') not in ar_sources or not https_url(m.get('url','')): raise ValueError('Invalid activity radar media')
    capabilities=json.loads((ROOT/'data/capabilities.json').read_text(encoding='utf-8'))
    deep_dives=json.loads((ROOT/'data/deep-dives.json').read_text(encoding='utf-8'))
    if deep_dives.get('version') != 1 or not isinstance(deep_dives.get('articles'),list):
        raise ValueError('Unsupported deep-dives schema')
    deep_ids=[a.get('id') for a in deep_dives['articles']]
    if len(deep_ids)!=len(set(deep_ids)): raise ValueError('Duplicate deep-dive ID')
    for a in deep_dives['articles']:
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*',a.get('id','')): raise ValueError('Unsafe deep-dive ID')
        date.fromisoformat(a['published'])
        if not isinstance(a.get('sections'),list) or len(a['sections'])<4: raise ValueError('Incomplete deep-dive sections')
        if not isinstance(a.get('sources'),list) or not a['sources']: raise ValueError('Missing deep-dive sources')
        source_ids=[s.get('id') for s in a['sources']]
        if len(source_ids)!=len(set(source_ids)): raise ValueError('Duplicate deep-dive source ID')
        for s in a['sources']:
            if not https_url(s.get('url','')): raise ValueError('Invalid deep-dive source URL')
        known=set(source_ids)
        for section in a['sections']:
            if not set(section.get('source_refs',[])).issubset(known): raise ValueError('Unknown deep-dive source ref')
    github_hot=json.loads((ROOT/'data/github-hot.json').read_text(encoding='utf-8'))
    if github_hot.get('version') != 1: raise ValueError('Unsupported GitHub hot schema version')
    datetime.fromisoformat(github_hot['checked_at'])
    if not https_url(github_hot.get('source_url','')): raise ValueError('Invalid GitHub hot source URL')
    gh_categories=github_hot.get('categories')
    if not isinstance(gh_categories,list) or not gh_categories: raise ValueError('Missing GitHub hot categories')
    gh_category_ids=set()
    for c in gh_categories:
        cid=c.get('id')
        if not isinstance(cid,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*',cid) or cid in gh_category_ids: raise ValueError('Invalid GitHub hot category')
        if not isinstance(c.get('title'),str) or not c['title'].strip(): raise ValueError('Missing GitHub hot category title')
        gh_category_ids.add(cid)
    gh_seen=set()
    for row in github_hot.get('items',[]):
        if not REPO_RE.fullmatch(row.get('repo','')): raise ValueError('Invalid GitHub hot repository')
        if row['repo'] in gh_seen: raise ValueError('Duplicate GitHub hot repository')
        gh_seen.add(row['repo'])
        if not https_url(row.get('url','')): raise ValueError('Invalid GitHub hot repository URL')
        if any((not isinstance(row.get(k),int) or row[k] < 0) for k in ('rank','stars','forks','stars_today')): raise ValueError('Invalid GitHub hot metric')
        if row.get('category') not in gh_category_ids: raise ValueError('Unknown GitHub hot category')
        if not isinstance(row.get('ai_related'),bool): raise ValueError('Invalid GitHub AI relation flag')
        tags=row.get('tags')
        if not isinstance(tags,list) or not 0 <= len(tags) <= 4 or len(tags)!=len(set(tags)) or any(not isinstance(t,str) or not t.strip() or len(t)>40 for t in tags): raise ValueError('Invalid GitHub hot tags')
        if row.get('category') in {'agent-app','agent-framework','agent-infra','mcp-knowledge'}: raise ValueError('GitHub hot category is too coarse')
        datetime.fromisoformat(row['repo_created_at'].replace('Z','+00:00'))
        datetime.fromisoformat(row['repo_pushed_at'].replace('Z','+00:00'))
        history=row.get('star_history')
        if not isinstance(history,list) or len(history)<1 or len(history)>12: raise ValueError('Invalid GitHub hot star history')
        hist_times=[]
        for point in history:
            if not isinstance(point,dict) or not isinstance(point.get('stars'),int) or point['stars']<0: raise ValueError('Invalid GitHub hot star history point')
            hist_times.append(datetime.fromisoformat(point['at'].replace('Z','+00:00')))
        if hist_times!=sorted(hist_times) or len(set(hist_times))!=len(hist_times): raise ValueError('Unordered GitHub hot star history')
    huggingface_hot=json.loads((ROOT/'data/huggingface-hot.json').read_text(encoding='utf-8'))
    if huggingface_hot.get('version') != 1: raise ValueError('Unsupported Hugging Face hot schema version')
    datetime.fromisoformat(huggingface_hot['checked_at'])
    for key in ('source_url','api_url'):
        if not https_url(huggingface_hot.get(key,'')): raise ValueError('Invalid Hugging Face hot source URL')
    hf_items=huggingface_hot.get('items')
    if not isinstance(hf_items,list) or not 5<=len(hf_items)<=50: raise ValueError('Invalid Hugging Face hot items')
    hf_seen=set()
    for row in hf_items:
        mid=row.get('id','')
        if not REPO_RE.fullmatch(mid): raise ValueError('Invalid Hugging Face model ID')
        if mid in hf_seen: raise ValueError('Duplicate Hugging Face model')
        hf_seen.add(mid)
        if not https_url(row.get('url','')): raise ValueError('Invalid Hugging Face model URL')
        if any((not isinstance(row.get(k),int) or row[k] < 0) for k in ('rank','likes','downloads')): raise ValueError('Invalid Hugging Face metric')
        score=row.get('trending_score')
        if isinstance(score,bool) or not isinstance(score,(int,float)) or score < 0: raise ValueError('Invalid Hugging Face trending score')
        datetime.fromisoformat(row['created_at'].replace('Z','+00:00'))
        if not isinstance(row.get('task'),str) or not row['task'].strip(): raise ValueError('Missing Hugging Face task')
        library=row.get('library')
        if library is not None and (not isinstance(library,str) or not library.strip()): raise ValueError('Invalid Hugging Face library')
        tags=row.get('tags')
        if not isinstance(tags,list) or not 0<=len(tags)<=4 or len(tags)!=len(set(tags)) or any(not isinstance(t,str) or not t.strip() or len(t)>48 for t in tags): raise ValueError('Invalid Hugging Face tags')
    if [x['rank'] for x in hf_items] != list(range(1,len(hf_items)+1)): raise ValueError('Hugging Face ranks must be sequential')
    app={'hot':hot,'product_radar':product_radar,'activity_radar':activity_radar,'hot_policy':hot_policy,'github_hot':github_hot,'huggingface_hot':huggingface_hot,'deep_dives':deep_dives,'capabilities':capabilities,'benchmarks':benchmarks,'models':models,'resets':resets,'catalog':catalog,'upstream':upstream,'site':site,'industry':industry,'intake':intake}
    from activity_feature import load_feature
    app['activity_feature']=load_feature(ROOT, activity_radar)
    template=(ROOT/'src/index.html').read_text(encoding='utf-8')
    css=(ROOT/'src/styles.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/vertical.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/models.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/benchmarks.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/hot.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/polish.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/type-icons.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/v9.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/v10.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/intraday.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/v2.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/product-v3.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/top5-editorial.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/github-hot.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/huggingface-hot.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/tibo-intel.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/deep-dives.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/feed-cockpit.css').read_text(encoding='utf-8')+'\n'+(ROOT/'src/progress-v4.css').read_text(encoding='utf-8')
    js=(ROOT/'src/app.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/vertical.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/models.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/hot.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/benchmarks.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/v9.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/v10.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/intraday.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/v2.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/product-v3.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/top5-editorial.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/tibo-intel.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/github-hot.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/huggingface-hot.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/deep-dives.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/feed-cockpit.js').read_text(encoding='utf-8')+'\n'+(ROOT/'src/progress-v4.js').read_text(encoding='utf-8')
    css+='\n'+(ROOT/'src/activity-hero.css').read_text(encoding='utf-8')
    js+='\n'+(ROOT/'src/activity-hero.js').read_text(encoding='utf-8')
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
    from shutil import copytree
    copytree(ROOT/'assets/activity', output/'assets/activity', dirs_exist_ok=True)
    write_json(output/'api/v1/activity-feature.json',app['activity_feature'])
    write_json(output/'api/v1/index.json',app)
    write_json(output/'api/v1/events.json',{'snapshot':catalog['snapshot'],'events':catalog['events'],'sources':catalog['sources']})
    write_json(output/'api/v1/upstream.json',upstream)
    write_json(output/'api/v1/topics.json',industry)
    write_json(output/'api/v1/models.json',models)
    write_json(output/'api/v1/resets.json',resets)
    write_json(output/'api/v1/benchmarks.json',benchmarks)
    write_json(output/'api/v1/hot.json',hot)
    write_json(output/'api/v1/product-radar.json',product_radar)
    write_json(output/'api/v1/activity-radar.json',activity_radar)
    write_json(output/'api/v1/hot-policy.json',hot_policy)
    write_json(output/'api/v1/github-hot.json',github_hot)
    write_json(output/'api/v1/huggingface-hot.json',huggingface_hot)
    write_json(output/'api/v1/capabilities.json',capabilities)
    write_json(output/'api/v1/deep-dives.json',deep_dives)
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
