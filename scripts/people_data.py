"""Public professional profiles, attributed works and dated activity; no rankings."""
from __future__ import annotations
import copy
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse, quote

ID = re.compile(r'^[a-z0-9][a-z0-9-]*$')
KINDS = {'personal', 'institution', 'project', 'paper', 'article'}


def validate_people(data: dict) -> None:
    def text(value):
        if not isinstance(value, str) or not value.strip() or len(value) > 4000:
            raise ValueError('Invalid people text')
    def day(value):
        if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise ValueError('Invalid people date')
        parsed = date.fromisoformat(value)
        if parsed > date.today():
            raise ValueError('Future people date')
        return parsed
    def records(rows):
        if not isinstance(rows, list):
            raise ValueError('People registry must be a list')
        known = set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not ID.fullmatch(row['id']) or row['id'] in known:
                raise ValueError('Invalid or duplicate people ID')
            known.add(row['id'])
        return known
    def urls(raw):
        text(raw)
        if re.search(r'[\s\x00-\x1f\x7f]', raw):
            raise ValueError('Unsafe people URL')
        u = urlparse(raw)
        if u.scheme != 'https' or not u.hostname or u.username or u.password:
            raise ValueError('Unsafe people URL')
    def refs(values, known, allow_empty=False):
        if not isinstance(values, list) or (not values and not allow_empty) or any(not isinstance(v, str) for v in values):
            raise ValueError('Invalid people references')
        if len(values) != len(set(values)) or not set(values) <= known:
            raise ValueError('Unknown or duplicate people reference')
    if not isinstance(data, dict) or data.get('version') != 1 or data.get('mode') != 'manual':
        raise ValueError('Unsupported people schema')
    checked = day(data.get('checked'))
    text(data.get('note'))
    roles = records(data.get('roles'))
    areas = records(data.get('areas'))
    ids = records(data.get('people'))
    records(data.get('events'))
    for row in data['roles'] + data['areas']:
        text(row.get('title'))
    for p in data['people']:
        for key in ('name', 'intro', 'watch'):
            text(p.get(key))
        if set(p) & {'email', 'phone', 'address', 'salary', 'rank', 'score', 'age'}:
            raise ValueError('People profiles exclude private fields and rankings')
        refs(p.get('roles'), roles)
        refs(p.get('areas'), areas)
        impact=p.get('impact')
        if not isinstance(impact,dict) or set(impact)!={'dimensions','basis'}:
            raise ValueError('Every person needs documented impact dimensions')
        dims=impact['dimensions']
        if not isinstance(dims,list) or not dims or len(dims)!=len(set(dims)) or not set(dims)<={'research','ecosystem','industry'}:
            raise ValueError('Unsupported impact dimension or fake ranking')
        text(impact['basis'])
        if not isinstance(p.get('aliases'), list) or any(not isinstance(a, str) or not a.strip() for a in p['aliases']):
            raise ValueError('Invalid people aliases')
        if p.get('discovery') not in {'work', 'editorial'} or day(p.get('checked')) > checked:
            raise ValueError('Invalid people review metadata')
        for field in ('sources', 'works'):
            if not isinstance(p.get(field), list) or not p[field]:
                raise ValueError('People need attributed sources and works')
        for s in p['sources']:
            if not isinstance(s, dict) or s.get('kind') not in KINDS:
                raise ValueError('Invalid profile source kind')
            text(s.get('label')); urls(s.get('url'))
        for w in p['works']:
            if not isinstance(w, dict): raise ValueError('Invalid work')
            text(w.get('title')); text(w.get('relation')); urls(w.get('url'))
        if not isinstance(p.get('related'), list):
            raise ValueError('Invalid related records')
        for r in p['related']:
            if not isinstance(r, dict) or r.get('kind') not in {'research', 'product', 'benchmark'} or not isinstance(r.get('id'), str) or not ID.fullmatch(r['id']):
                raise ValueError('Invalid related entity')
            text(r.get('label'))
            if 'href' in r: raise ValueError('Related URLs are built from validated entity IDs')
    for e in data['events']:
        refs(e.get('people'), ids)
        if e.get('kind') not in {'paper', 'article', 'talk', 'release'}:
            raise ValueError('Invalid people event kind')
        if day(e.get('date')) > day(e.get('checked')) or day(e['checked']) > checked:
            raise ValueError('Invalid people event chronology')
        for field in ('title', 'summary', 'source', 'boundary'): text(e.get(field))
        urls(e.get('url'))
        if any(key in e for key in ('score', 'rank', 'tested')):
            raise ValueError('People activity is not an evaluation result')


def load_people(root: Path, app: dict) -> dict:
    data = json.loads((root / 'data/people.json').read_text(encoding='utf-8'))
    validate_people(data)
    result = copy.deepcopy(data)
    catalogs = {'product': app['product_radar']['items'],
                'research': app['research_radar']['items'],
                'benchmark': app['benchmarks']['items']}
    by_kind = {kind: {x['id']: x for x in rows} for kind, rows in catalogs.items()}
    for p in result['people']:
        for r in p['related']:
            entity = by_kind[r['kind']].get(r['id'])
            if entity is None:
                raise ValueError('Unknown people related entity: ' + r['id'])
            if r['kind'] == 'product':
                r['href'] = '#/hot?cat=product&pview=map&product=' + quote(r['id'])
            elif r['kind'] == 'benchmark':
                r['href'] = '#/benchmarks?bench=' + quote(r['id'])
            else:
                r['href'] = '#/progress?view=research&q=' + quote(entity['title'])
    return result
