"""Validate editorial getting-started guides; never equate docs checks with runtime tests."""
from __future__ import annotations
import json
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

# Explicit primary-source hosts, reviewed alongside each guide. No arbitrary redirects.
HOSTS = frozenset({'docling-project.github.io','microsoft.github.io','github.com',
    'www.microsoft.com','allenai.org','olmoearth.allenai.org',
    'blog.google','aistudio.google.com','gemini.google.com','help.openai.com',
    'chatgpt.com','openai.com','docs.openhands.dev','docs.browser-use.com',
    'leanprover-community.github.io','live.lean-lang.org','mistral.ai','docs.mistral.ai',
    'huggingface.co','arxiv.org','rfd4-proteina.org','claude.com','nvidianews.nvidia.com',
    'blogs.nvidia.com','developer.nvidia.com','docs.nvidia.com'})
ID = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
REVIEW_TIMEZONE = ZoneInfo('Asia/Shanghai')

def _text(value, limit=1200):
    if not isinstance(value, str) or not value.strip() or len(value)>limit:
        raise ValueError('Missing or oversized toolkit text')
    return value

def _url(value):
    _text(value, 2048)
    try:
        p=urlsplit(value)
        valid=p.scheme=='https' and p.hostname in HOSTS and not p.username and not p.password and p.port in (None,443)
    except ValueError:
        valid=False
    if not valid: raise ValueError('Toolkit requires an approved primary HTTPS source')

def _date(value, today):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
        raise ValueError('Invalid toolkit date precision')
    d=date.fromisoformat(value)
    if d>today: raise ValueError('Future toolkit verification/publication date')
    return d

def validate_toolkit(data, catalog, *, now=None):
    now = now if now is not None else datetime.now().astimezone()
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('Validation clock must include timezone')
    today = now.astimezone(REVIEW_TIMEZONE).date()
    if data.get('version')!=1: raise ValueError('Unsupported toolkit schema')
    enums={}
    for name in ('groups','access_modes'):
        rows=data.get(name)
        if not isinstance(rows,list) or not rows: raise ValueError('Missing toolkit facets')
        ids=[]
        for row in rows:
            if not isinstance(row,dict) or not ID.fullmatch(row.get('id','')): raise ValueError('Unsafe toolkit facet')
            ids.append(row['id']);_text(row.get('label'),40)
        if len(ids)!=len(set(ids)): raise ValueError('Duplicate toolkit facet')
        enums[name]=set(ids)
    rows=data.get('items')
    if not isinstance(rows,list): raise ValueError('Missing toolkit guides')
    expected={x['id'] for x in catalog['items'] if x['status']=='code'}
    ids=[]
    for row in rows:
        if not isinstance(row,dict) or row.get('id') not in expected: raise ValueError('Unknown toolkit task')
        ids.append(row['id'])
        if row.get('group') not in enums['groups'] or row.get('access') not in enums['access_modes']:
            raise ValueError('Unknown toolkit facet')
        for k in ('publisher','headline','input','output','requirements','limitation','cost','troubleshooting'):
            _text(row.get(k))
        if row.get('evidence_level')!='primary-docs' or row.get('runtime_tested') is not False:
            raise ValueError('Toolkit docs-only guides cannot claim runtime testing')
        if row.get('entry_url') is not None: _url(row['entry_url'])
        steps=row.get('steps')
        if not isinstance(steps,list) or not 2<=len(steps)<=4: raise ValueError('Invalid toolkit steps')
        for step in steps:
            _text(step.get('title'),80);_text(step.get('body'))
            if 'command' in step: _text(step['command'],4000)
        sources=row.get('sources')
        if not isinstance(sources,list) or not sources: raise ValueError('Missing toolkit evidence')
        urls=[]
        for s in sources:
            _text(s.get('title'),100);_url(s.get('url'));urls.append(s['url'])
            checked=_date(s.get('verified_at'),today)
            if s.get('published_at') is not None and _date(s['published_at'],today)>checked:
                raise ValueError('Toolkit publication after verification')
        if len(urls)!=len(set(urls)): raise ValueError('Duplicate toolkit source')
    if len(ids)!=len(set(ids)) or set(ids)!=expected: raise ValueError('Toolkit must cover eligible tasks exactly once')
    return data

def load_toolkit(root: Path, catalog):
    return validate_toolkit(json.loads((root/'data/toolkit.json').read_text(encoding='utf-8')),catalog)
