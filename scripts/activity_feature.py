"""Validate the reviewed presentation/time metadata; never fetch during a build."""
from datetime import date, datetime
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


def load_feature(root: Path, radar: dict) -> dict:
    data = json.loads((root / 'data/activity-feature.json').read_text(encoding='utf-8'))
    if data.get('version') != 1 or not isinstance(data.get('events'), dict):
        raise ValueError('Unsupported activity feature schema')
    if date.fromisoformat(data['checked']) > date.today():
        raise ValueError('Future event review date')
    def official_url(value):
        u = urlparse(value)
        return u.scheme == 'https' and u.hostname in {'www.nvidia.com','www.apple.com'} and not u.username and not u.password
    for event_id, item in data['events'].items():
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', event_id):
            raise ValueError('Unsafe event identifier')
        date.fromisoformat(item['date'])
        if item.get('start_at'):
            dt = datetime.fromisoformat(item['start_at'].replace('Z', '+00:00'))
            if dt.tzinfo is None or dt.astimezone(ZoneInfo(item['time_zone'])).date().isoformat() != item['date']:
                raise ValueError('Event start must have an offset and match the source-local date')
            if not official_url(item.get('time_source_url','')):
                raise ValueError('Event time needs an official source')
            if date.fromisoformat(item['checked']) > date.today():
                raise ValueError('Future time review date')
        art = item.get('artwork', {})
        if not re.fullmatch(r'assets/activity/[a-z0-9-]+\.webp', art.get('local','')):
            raise ValueError('Unsafe event artwork path')
        if not official_url(art.get('url','')) or not official_url(art.get('source_url','')) or not art.get('credit'):
            raise ValueError('Event artwork requires official provenance and credit')
        if not (root / art['local']).is_file():
            raise ValueError('Missing locally cached event artwork: '+art['local'])
    return data
