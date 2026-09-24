"""Validate FrontierLog's editorial hot list and generate RSS. Scores are internal signals, not web traffic."""
from __future__ import annotations
from datetime import date, datetime, timezone
from email.utils import format_datetime
import re
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

def validate_hot(data:dict)->None:
    if not isinstance(data,dict) or data.get('version')!=1: raise ValueError('Unsupported hot schema')
    checked=date.fromisoformat(data['checked'])
    if checked>date.today(): raise ValueError('Future hot check date')
    if data.get('method',{}).get('automatic') is not False: raise ValueError('Hot score must not pretend to be live')
    if data['method'].get('last_success') is not None: raise ValueError('No verified automated hot collection')
    cats=data.get('categories'); items=data.get('items')
    if not isinstance(cats,list) or not isinstance(items,list): raise ValueError('Missing lists')
    cids=[c.get('id') for c in cats]
    if cids[0]!='all' or len(cids)!=len(set(cids)): raise ValueError('Invalid categories')
    ids=[x.get('id') for x in items]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate hot ID')
    for item in items:
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*',item['id']): raise ValueError('Unsafe hot ID')
        if item['category'] not in set(cids)-{'all'}: raise ValueError('Unknown hot category')
        if not isinstance(item['heat'],int) or not 0<=item['heat']<=100: raise ValueError('Invalid hot score')
        if item['trend'] not in {'up','flat','down'}: raise ValueError('Invalid trend')
        published=date.fromisoformat(item['published'])
        if published>checked: raise ValueError('Future hot event')
        # Precise timeline timestamps are optional but, when present, must be timezone-aware ISO 8601.
        for time_key in ('published_at','first_seen_at','captured_at'):
            raw=item.get(time_key)
            if raw:
                precise=datetime.fromisoformat(str(raw).replace('Z','+00:00'))
                if precise.tzinfo is None: raise ValueError('Hot timestamp must include timezone: '+time_key)
                if precise.date()>checked: raise ValueError('Future hot timestamp: '+time_key)
        if date.fromisoformat(item['checked'])>checked: raise ValueError('Item checked after snapshot')
        u=urlparse(item['url'])
        if u.scheme!='https' or not u.hostname or u.username or u.password: raise ValueError('Unsafe hot source URL')
        if item.get('link') and not str(item['link']).startswith('#/'): raise ValueError('Unsafe internal link')
        for list_key, required in (('access',('label','note','url')),('related',('source','title','url'))):
            rows=item.get(list_key,[])
            if not isinstance(rows,list): raise ValueError('Invalid hot '+list_key)
            for row in rows:
                if not isinstance(row,dict): raise ValueError('Invalid hot '+list_key+' row')
                for key in required:
                    if not isinstance(row.get(key),str) or not row[key].strip(): raise ValueError('Missing hot '+list_key+' '+key)
                ru=urlparse(row['url'])
                if ru.scheme!='https' or not ru.hostname or ru.username or ru.password: raise ValueError('Unsafe hot '+list_key+' URL')
                if row.get('date') and date.fromisoformat(row['date'])>checked: raise ValueError('Future hot related date')
        for key in ['title','summary','why','boundary','source','source_kind']:
            if not isinstance(item.get(key),str) or not item[key].strip(): raise ValueError('Missing '+key)

def hot_rss(data:dict,site:dict)->bytes:
    base=site['base_url'].rstrip('/')+'/'
    root=ET.Element('rss',version='2.0');c=ET.SubElement(root,'channel')
    ET.SubElement(c,'title').text='AI坐标 · 热点榜'
    ET.SubElement(c,'link').text=base+'#/hot'
    ET.SubElement(c,'description').text='人工核对的高信号 AI 进展。站内热度不是全网浏览量。'
    ET.SubElement(c,'language').text='zh-CN'
    ET.SubElement(c,'lastBuildDate').text=format_datetime(datetime.fromisoformat(data['checked']).replace(tzinfo=timezone.utc))
    ET.register_namespace('atom','http://www.w3.org/2005/Atom')
    ET.SubElement(c,'{http://www.w3.org/2005/Atom}link',href=base+'feeds/hot.xml',rel='self',type='application/rss+xml')
    for x in sorted(data['items'],key=lambda x:(-x['heat'],x['id'])):
        i=ET.SubElement(c,'item');ET.SubElement(i,'title').text=x['title']
        ET.SubElement(i,'guid',isPermaLink='false').text='frontierlog:hot:'+x['id']
        ET.SubElement(i,'link').text=x['url']
        precise=x.get('published_at')
        if precise:
            pub_dt=datetime.fromisoformat(str(precise).replace('Z','+00:00'))
        else:
            pub_dt=datetime.fromisoformat(x['published']).replace(tzinfo=timezone.utc)
        ET.SubElement(i,'pubDate').text=format_datetime(pub_dt)
        ET.SubElement(i,'description').text=x['summary']+'\n\n为什么值得看：'+x['why']+'\n\n边界：'+x['boundary']+'\n\n站内热度 '+str(x['heat'])+'；不是全网流量。'
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)
