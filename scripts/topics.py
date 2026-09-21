"""Validate editorial topic data and render topic-specific RSS; standard library only."""
from datetime import date, datetime, timezone
from email.utils import format_datetime
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
import re

ID = re.compile(r'^[a-z0-9][a-z0-9-]*$')

def safe_url(value):
    u=urlsplit(value)
    return u.scheme=='https' and bool(u.hostname) and not u.username and not u.password

def validate_topics(data, intake):
    if data.get('version')!=1: raise ValueError('Unknown topic schema')
    checked=date.fromisoformat(data['checked'])
    groups={}
    for name in ('sectors','topics','sources','articles'):
        seq=data[name];ids=[x['id'] for x in seq]
        if len(ids)!=len(set(ids)) or any(not ID.fullmatch(x) for x in ids):
            raise ValueError('Invalid or duplicate '+name+' ID')
        groups[name]={x['id']:x for x in seq}
    for t in data['topics']:
        if t['sector'] not in groups['sectors']:raise ValueError('Unknown sector')
        if t['group'] not in groups['sectors'][t['sector']]['groups']:raise ValueError('Unknown subgroup')
    for s in data['sources']:
        if not safe_url(s['url']):raise ValueError('Unsafe source URL')
        if date.fromisoformat(s['checked'])>checked:raise ValueError('Source check after snapshot')
        if s['published'] and date.fromisoformat(s['published'])>checked:raise ValueError('Future publication')
    for a in data['articles']:
        if a['kind'] not in {'update','tool','reference'}:raise ValueError('Unknown article type')
        if not a['topics'] or not a['sources']:raise ValueError('Missing topic or evidence')
        if not set(a['sources'])<=groups['sources'].keys():raise ValueError('Unknown source')
        for t in a['topics']:
            if t not in groups['topics'] or groups['topics'][t]['sector']!=a['sector']:raise ValueError('Wrong article topic')
        if date.fromisoformat(a['checked'])>checked:raise ValueError('Check after snapshot')
        if a['published'] and date.fromisoformat(a['published'])>checked:raise ValueError('Future article')
        if not isinstance(a['tested'],bool) or not a['metrics']:raise ValueError('Missing evidence state')
    for item in intake.get('items',[]):
        if item.get('review_status')!='unreviewed':raise ValueError('Machine may not approve an item')
        if not safe_url(item['url']):raise ValueError('Unsafe candidate URL')
        if not set(item['topics'])<=groups['topics'].keys():raise ValueError('Unknown candidate topic')
    for k in ('last_attempt','last_success','last_full_success'):
        if intake.get(k):datetime.fromisoformat(intake[k].replace('Z','+00:00'))

def topic_rss(data,site,scope='all'):
    base=site['base_url'].rstrip('/')+'/'
    sources={s['id']:s for s in data['sources']}
    sectors={s['id']:s for s in data['sectors']}
    topics={t['id']:t for t in data['topics']}
    if scope not in {'all',*sectors,*topics}:raise ValueError('Unknown feed scope')
    title='全部专题' if scope=='all' else (sectors.get(scope) or topics[scope])['title']
    rss=ET.Element('rss',version='2.0');c=ET.SubElement(rss,'channel')
    for k,v in {'title':'AI坐标 · '+title,'link':base+'#/'+(scope if scope in sectors else 'topics'),
                'description':'已编选资料与原始来源。历史日期保留，不代表本站已实测。','language':'zh-CN'}.items():ET.SubElement(c,k).text=v
    ET.register_namespace('atom','http://www.w3.org/2005/Atom')
    ET.SubElement(c,'{http://www.w3.org/2005/Atom}link',href=base+'feeds/'+scope+'.xml',rel='self',type='application/rss+xml')
    ET.SubElement(c,'lastBuildDate').text=format_datetime(datetime.fromisoformat(data['checked']).replace(tzinfo=timezone.utc))
    for a in data['articles']:
        if scope!='all' and a['sector']!=scope and scope not in a['topics']:continue
        i=ET.SubElement(c,'item')
        ET.SubElement(i,'title').text=a['title']
        ET.SubElement(i,'link').text=base+'#/'+a['sector']+'?article='+a['id']
        ET.SubElement(i,'guid',isPermaLink='false').text='frontierlog:topic:'+a['id']
        if a['published']:
            ET.SubElement(i,'pubDate').text=format_datetime(datetime.fromisoformat(a['published']).replace(tzinfo=timezone.utc))
        # No pubDate for evergreen materials. Review date must not become news date.
        ET.SubElement(i,'description').text=a['summary']+'\n\n编辑解读：'+a['why']+'\n\n边界：'+a['boundary']+'\n资料核对：'+a['checked']+'；本站未实测。\n原始来源：\n'+'\n'.join(sources[s]['url'] for s in a['sources'])
        for t in a['topics']:ET.SubElement(i,'category').text=topics[t]['title']
    return ET.tostring(rss,encoding='utf-8',xml_declaration=True)
