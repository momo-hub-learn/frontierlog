from datetime import date
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from deep_dive_watch import report
from build import build

class DeepDiveFreshnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.deep=json.loads((ROOT/'data/deep-dives.json').read_text(encoding='utf-8'))
        cls.hot=json.loads((ROOT/'data/hot.json').read_text(encoding='utf-8'))

    def test_newest_and_stale_boundary(self):
        x=report(self.deep,self.hot,date(2026,10,13))
        self.assertEqual(x['latest_id'],'rea-agent-reverse-engineering')
        self.assertEqual(x['latest_published'],'2026-10-13')
        self.assertFalse(x['stale'])
        self.assertFalse(report(self.deep,self.hot,date(2026,10,19))['stale'])
        self.assertTrue(report(self.deep,self.hot,date(2026,10,20))['stale'])

    def test_prior_article_alone_exposes_staleness(self):
        old=dict(self.deep,articles=[x for x in self.deep['articles'] if x['id']!='rea-agent-reverse-engineering'])
        x=report(old,self.hot,date(2026,10,13))
        self.assertTrue(x['stale'])
        self.assertEqual(x['latest_published'],'2026-09-24')

    def test_candidate_queue_is_not_a_publication(self):
        x=report(self.deep,self.hot,date(2026,10,13))
        self.assertTrue(all(item['id'] not in {id for a in self.deep['articles'] for id in a.get('hot_ids',[])}
            for item in x['uncovered_hot_candidates']))
        self.assertIn('不会自动发布',x['note'])

    def test_bad_threshold(self):
        with self.assertRaises(ValueError):report(self.deep,self.hot,date(2026,10,13),0)

if __name__=='__main__': unittest.main()
