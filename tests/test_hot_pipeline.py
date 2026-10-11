"""Regressions for content growth, editorial time, and non-publishing shadow sync."""
from __future__ import annotations
import copy
from datetime import datetime
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from hot_data import validate_hot, hot_rss
import hot_sync


def fixture(count=1):
    # Fixed, minimal fixtures decouple contract tests from today's headlines.
    item = {
        'id': 'fixture-0', 'category': 'product', 'heat': 80, 'trend': 'up',
        'published': '2026-10-09', 'checked': '2026-10-11',
        'title': 'Fixture', 'summary': 'Contract only', 'why': 'Test',
        'boundary': 'Not a real publication', 'source': 'Fixture',
        'source_kind': 'test', 'url': 'https://example.com/source',
        'access': [{'label': 'Source', 'note': 'Test', 'url': 'https://example.com/source'}],
        'related': [{'source': 'Fixture', 'title': 'Test', 'url': 'https://example.com/related'}],
    }
    return {
        'version': 1, 'checked': '2026-10-11',
        'method': {'automatic': False, 'last_success': None},
        'categories': [{'id': 'all'}, {'id': 'product'}],
        'items': [dict(copy.deepcopy(item), id=f'fixture-{n}') for n in range(count)],
    }


class HotTimeRegressions(unittest.TestCase):
    def setUp(self):
        # The exact UTC date that failed in run 38087089743 is still October 10.
        self.now = datetime.fromisoformat('2026-10-10T21:18:14+00:00')

    def test_beijing_next_day_is_not_a_future_review(self):
        validate_hot(fixture(), now=self.now)

    def test_same_instant_in_different_zones_gives_same_verdict(self):
        for raw in ('2026-10-10T21:18:14+00:00', '2026-10-11T05:18:14+08:00',
                    '2026-10-10T14:18:14-07:00'):
            with self.subTest(raw=raw):
                validate_hot(fixture(), now=datetime.fromisoformat(raw))

    def test_true_future_review_still_rejected(self):
        d = fixture(); d['checked'] = '2026-10-12'
        with self.assertRaisesRegex(ValueError, 'Future hot check date'):
            validate_hot(d, now=self.now)

    def test_beijing_midnight_boundary(self):
        with self.assertRaisesRegex(ValueError, 'Future hot check date'):
            validate_hot(fixture(), now=datetime.fromisoformat('2026-10-10T15:59:59+00:00'))
        validate_hot(fixture(), now=datetime.fromisoformat('2026-10-10T16:00:00+00:00'))

    def test_naive_clock_rejected(self):
        with self.assertRaisesRegex(ValueError, 'clock must include timezone'):
            validate_hot(fixture(), now=datetime(2026, 10, 11))

    def test_precise_future_instant_is_rejected_even_on_same_day(self):
        for key in ('published_at', 'first_seen_at', 'captured_at', 'verified_at'):
            with self.subTest(key=key):
                d = fixture(); d['items'][0][key] = '2026-10-11T05:19:00+08:00'
                with self.assertRaisesRegex(ValueError, 'Future hot timestamp'):
                    validate_hot(d, now=self.now)

    def test_timestamp_day_is_normalized_to_review_timezone(self):
        d = fixture()
        # Kiritimati calendar date is October 12; the same instant is October 11 in Beijing.
        d['items'][0]['captured_at'] = '2026-10-12T01:00:00+14:00'
        validate_hot(d, now=datetime.fromisoformat('2026-10-11T12:00:00+00:00'))

    def test_missing_timestamp_zone_is_rejected(self):
        d = fixture(); d['items'][0]['verified_at'] = '2026-10-11T04:00:00'
        with self.assertRaisesRegex(ValueError, 'timestamp must include timezone'):
            validate_hot(d, now=self.now)

    def test_future_event_and_duplicate_id_still_rejected(self):
        for change in ('event', 'duplicate'):
            d = fixture(2)
            if change == 'event': d['items'][0]['published'] = '2026-10-12'
            else: d['items'][1]['id'] = d['items'][0]['id']
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_hot(d, now=self.now)


class HotGrowthRegressions(unittest.TestCase):
    def test_rss_handles_shrinking_and_growing_lists_without_losing_items(self):
        for count in (1, 10, 12, 17):
            with self.subTest(count=count):
                d = fixture(count)
                root = ET.fromstring(hot_rss(d, {'base_url': 'https://example.com/frontierlog/'}))
                rows = root.findall('channel/item')
                self.assertEqual(len(rows), count)
                self.assertEqual({x.findtext('guid') for x in rows},
                                 {'frontierlog:hot:' + x['id'] for x in d['items']})


class HotShadowRegressions(unittest.TestCase):
    def test_shadow_evaluation_never_changes_editorial_review_or_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'data').mkdir()
            d = fixture(); d['checked'] = '2026-10-10'
            d['items'][0]['checked'] = '2026-10-10'
            for name, value in {'hot.json': d, 'hot-policy.json': {},
                                'hot-inbox.json': {'version': 1, 'candidates': []}}.items():
                (root / 'data' / name).write_text(json.dumps(value), encoding='utf-8')
            for _ in range(2):
                with patch.object(hot_sync, 'ROOT', root), patch.object(hot_sync, 'collect_candidates', return_value=[]), \
                     patch.object(sys, 'argv', ['hot_sync.py', '--now', '2026-10-11T02:00:00Z']):
                    hot_sync.main()
                result = json.loads((root / 'data/hot.json').read_text())
                self.assertEqual(result['checked'], d['checked'])
                self.assertEqual(result['items'], d['items'])
                self.assertEqual(result['method'], d['method'])
                self.assertEqual(result['sync']['mode'], 'shadow')
                self.assertEqual(result['sync']['last_checked_at'], '2026-10-11T02:00:00Z')

    def test_workflow_evaluates_latest_checkout_without_copying_stale_hot_data(self):
        text = (ROOT / '.github/workflows/hot-sync.yml').read_text()
        self.assertLess(text.index('git reset --hard origin/main'), text.index('python scripts/hot_sync.py'))
        self.assertNotIn('cp /tmp/hot.json data/hot.json', text)
        self.assertNotIn('git push --force', text)


if __name__ == '__main__':
    unittest.main()
