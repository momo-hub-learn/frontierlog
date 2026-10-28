import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.activity_feature import load_feature


ROOT = Path(__file__).resolve().parents[1]


class ActivityFeatureTests(unittest.TestCase):
    def setUp(self):
        self.radar = json.loads((ROOT / 'data/activity-radar.json').read_text())
        self.feature = json.loads((ROOT / 'data/activity-feature.json').read_text())

    def load(self, feature=None, radar=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'data').mkdir()
            for item in (feature or self.feature)['events'].values():
                local = item.get('artwork', {}).get('local')
                if local:
                    target = root / local
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / local, target)
            (root / 'data/activity-feature.json').write_text(
                json.dumps(feature or self.feature), encoding='utf-8'
            )
            return load_feature(root, radar or self.radar)

    def test_official_event_host_can_prove_its_own_time(self):
        data = self.load()
        self.assertIn('nvidia-medtech-days-2026', data['events'])

    def test_third_party_or_cross_host_time_source_is_rejected(self):
        feature = copy.deepcopy(self.feature)
        feature['events']['nvidia-medtech-days-2026']['time_source_url'] = 'https://example.com/schedule'
        with self.assertRaisesRegex(ValueError, 'official source'):
            self.load(feature=feature)

    def test_end_date_cannot_precede_start_date(self):
        feature = copy.deepcopy(self.feature)
        feature['events']['nvidia-medtech-days-2026']['end_date'] = '2026-10-26'
        with self.assertRaisesRegex(ValueError, 'end date'):
            self.load(feature=feature)

    def test_next_session_must_be_offset_aware_and_within_source_local_range(self):
        feature = copy.deepcopy(self.feature)
        medtech = feature['events']['nvidia-medtech-days-2026']
        medtech['next_session_at'] = '2026-10-29T08:00:00-07:00'
        with self.assertRaisesRegex(ValueError, 'Next session'):
            self.load(feature=feature)
        medtech['next_session_at'] = '2026-10-28T08:00:00'
        with self.assertRaisesRegex(ValueError, 'Next session'):
            self.load(feature=feature)


if __name__ == '__main__':
    unittest.main()
