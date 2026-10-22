from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
import json
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from deep_revision_guard import validate_revision

BASE=json.loads((ROOT/'data/deep-dives.json').read_text(encoding='utf-8'))
NEXT_DATE=(date.fromisoformat(BASE['checked'])+timedelta(days=1)).isoformat()

class DeepRevisionQualityTests(unittest.TestCase):
    def test_cosmetic_date_update_rejected(self):
        changed=deepcopy(BASE)
        changed['checked']=NEXT_DATE
        changed['articles'][0]['updated']=NEXT_DATE
        with self.assertRaisesRegex(ValueError,'Cosmetic-only date change'):
            validate_revision(BASE,changed)

    def test_authorized_substantive_revision_passes(self):
        changed=deepcopy(BASE)
        changed['checked']=NEXT_DATE
        changed['articles'][0]['updated']=NEXT_DATE
        changed['articles'][0]['sections'][0]['blocks'][0]['text'] += '（经原始证据复核后的实质追加。）'
        validate_revision(BASE,changed)

    def test_source_timestamp_only_is_not_material(self):
        changed=deepcopy(BASE)
        changed['checked']=NEXT_DATE
        changed['articles'][0]['updated']=NEXT_DATE
        changed['articles'][0]['sources'][0]['verified_at']=NEXT_DATE
        with self.assertRaisesRegex(ValueError,'Cosmetic-only date change'):
            validate_revision(BASE,changed)

    def test_checked_only_update_rejected(self):
        changed=deepcopy(BASE)
        changed['checked']=NEXT_DATE
        with self.assertRaisesRegex(ValueError,'Cannot refresh'):
            validate_revision(BASE,changed)

    def test_non_editorial_update_no_false_positive(self):
        validate_revision(BASE,deepcopy(BASE))

if __name__=='__main__':unittest.main()
