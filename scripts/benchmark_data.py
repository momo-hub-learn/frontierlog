"""Validate protocol catalog and emit a dated, source-linked RSS. No eval execution."""
from __future__ import annotations
from datetime import date, datetime, timezone
from email.utils import format_datetime
import re
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

def validate_benchmarks(data:dict)->None:
    if not isinstance(data,dict) or data.get('version')!=1: raise ValueError('Unsupported benchmark schema')
    today=date.fromisoformat(data['checked'])
    if today>date.today():raise ValueError('Future catalog check date')
    if data.get('sync',{}).get('status')!='manual':raise ValueError('This schema stores manual protocol snapshots only')
    if data['sync'].get('last_success') is not None:raise ValueError('No verified automated collection')
    def records(key):
        a=data.get(key)
        if not isinstance(a,list):raise ValueError('Missing list: '+key)
        ids=[x.get('id') for x in a]
        if len(ids)!=len(set(ids)):raise ValueError('Duplicate '+key+' ID')
        if not all(isinstance(x,str) and re.fullmatch(r'[a-z0-9][a-z0-9-]*',x) for x in ids):raise ValueError('Unsafe ID')
        return set(ids)
    groups=records('groups');sources=records('sources');ids=records('items');records('changes');records('suites')
    def url(x):
        u=urlparse(x)
        if u.scheme!='https' or not u.hostname or u.username or u.password:raise ValueError('Unsafe source URL')
    def refs(a):
        if not isinstance(a,list) or not a or not set(a)<=sources:raise ValueError('Missing source reference')
    def strings(a):
        if not isinstance(a,list) or not a or not all(isinstance(x,str) and x.strip() for x in a):raise ValueError('Empty checklist')
    for s in data['sources']:
        url(s['url'])
        if date.fromisoformat(s['checked'])>today:raise ValueError('Check date beyond snapshot')
        if s.get('published') and date.fromisoformat(s['published'])>today:raise ValueError('Future source event')
    for b in data['items']:
        if b['group'] not in groups-{'all'}:raise ValueError('Invalid category')
        if b.get('kind') not in {'benchmark','dataset'}:raise ValueError('Invalid item kind')
        if b.get('tested') is not False:raise ValueError('No test results in this catalog schema')
        if any(k in b for k in ['score','rank','sota','best_model']):raise ValueError('Scores belong to separately verified results, not protocol catalog')
        for key in ['name','edition','subtitle','summary','metric','metric_note','protocol','boundary','business','setup']:
            if not isinstance(b.get(key),str) or not b[key].strip():raise ValueError('Missing '+key)
        refs(b['sources']);strings(b['checks'])
        if b.get('result_url'):url(b['result_url'])
        if date.fromisoformat(b['checked'])>today:raise ValueError('Future checked date')
    for e in data['changes']:
        if date.fromisoformat(e['date'])>today:raise ValueError('Future change')
        if not e['benchmarks'] or not set(e['benchmarks'])<=ids:raise ValueError('Invalid change reference')
        refs(e['sources'])
    for s in data['suites']:
        if not 1<=len(s['benchmarks'])<=6 or not set(s['benchmarks'])<=ids:raise ValueError('Invalid suite')
        if not s.get('gap'):raise ValueError('Business proposals require explicit scope gap')
        strings(s['checks']);strings(s['questions'])
        if s.get('sources'):refs(s['sources'])

def benchmark_rss(data:dict,site:dict)->bytes:
    base=site['base_url'].rstrip('/')+'/'
    root=ET.Element('rss',version='2.0');c=ET.SubElement(root,'channel')
    ET.SubElement(c,'title').text='AI坐标 · Benchmark 口径事件'
    ET.SubElement(c,'link').text=base+'#/benchmarks?mode=changes'
    ET.SubElement(c,'description').text='有原始来源的历史事件；编辑解读分列，不是实时跑分或自动核验。'
    ET.SubElement(c,'language').text='zh-CN'
    ET.SubElement(c,'lastBuildDate').text=format_datetime(datetime.fromisoformat(data['checked']).replace(tzinfo=timezone.utc))
    ET.register_namespace('atom','http://www.w3.org/2005/Atom')
    ET.SubElement(c,'{http://www.w3.org/2005/Atom}link',href=base+'feeds/benchmarks.xml',rel='self',type='application/rss+xml')
    sources={s['id']:s for s in data['sources']}
    for e in sorted(data['changes'],key=lambda e:e['date'],reverse=True):
        i=ET.SubElement(c,'item');ET.SubElement(i,'title').text=e['title']
        ET.SubElement(i,'guid',isPermaLink='false').text='frontierlog:benchmark:'+e['id']
        ET.SubElement(i,'link').text=base+'#/benchmarks?mode=changes&bench='+e['benchmarks'][0]
        ET.SubElement(i,'pubDate').text=format_datetime(datetime.fromisoformat(e['date']).replace(tzinfo=timezone.utc))
        ET.SubElement(i,'description').text=e['summary']+'\n\n编辑解读：'+e['implication']+'\n\n来源：\n'+'\n'.join(sources[id]['url'] for id in e['sources'])
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)
