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
    editorial_today = datetime.now(ZoneInfo('Asia/Shanghai')).date()
    if date.fromisoformat(data['checked']) > editorial_today:
        raise ValueError('Future event review date')
    radar_events = {event.get('id'): event for event in radar.get('events', [])}
    radar_sources = {source.get('id'): source for source in radar.get('sources', [])}
    def secure_url(value):
        u = urlparse(value)
        return u.scheme == 'https' and bool(u.hostname) and not u.username and not u.password
    def official_event_url(value, event_id):
        event = radar_events.get(event_id, {})
        source = radar_sources.get(event.get('source_id'), {})
        if source.get('authority') != 'official' or not secure_url(value):
            return False
        trusted_hosts = {
            urlparse(url).hostname
            for url in (event.get('url'), source.get('url'))
            if secure_url(url)
        }
        return urlparse(value).hostname in trusted_hosts
    def known_official_url(value):
        u = urlparse(value)
        return secure_url(value) and u.hostname in {'www.nvidia.com','www.apple.com','forum.openai.com'}
    for event_id, item in data['events'].items():
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', event_id):
            raise ValueError('Unsafe event identifier')
        start_date = date.fromisoformat(item['date'])
        if item.get('end_date') and date.fromisoformat(item['end_date']) < start_date:
            raise ValueError('Event end date precedes its start date')
        if item.get('start_at'):
            dt = datetime.fromisoformat(item['start_at'].replace('Z', '+00:00'))
            if dt.tzinfo is None or dt.astimezone(ZoneInfo(item['time_zone'])).date().isoformat() != item['date']:
                raise ValueError('Event start must have an offset and match the source-local date')
            if not official_event_url(item.get('time_source_url',''), event_id):
                raise ValueError('Event time needs an official source')
            if date.fromisoformat(item['checked']) > editorial_today:
                raise ValueError('Future time review date')
        art = item.get('artwork', {})
        # Artwork is optional: the UI has a labelled text fallback. Do not delay
        # a verified event just because no reusable official art is available.
        if art:
            if not re.fullmatch(r'assets/activity/[a-z0-9-]+\.webp', art.get('local','')):
                raise ValueError('Unsafe event artwork path')
            if not known_official_url(art.get('url','')) or not known_official_url(art.get('source_url','')) or not art.get('credit'):
                raise ValueError('Event artwork requires official provenance and credit')
            if not (root / art['local']).is_file():
                raise ValueError('Missing locally cached event artwork: '+art['local'])
    return data
