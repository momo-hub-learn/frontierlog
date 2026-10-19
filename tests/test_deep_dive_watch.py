from datetime import date
import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from deep_dive_watch import report, content_date, DEFAULT_CADENCE_DAYS

class DeepDiveFreshnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.deep=json.loads((ROOT/'data/deep-dives.json').read_text(encoding='utf-8'))
        cls.hot=json.loads((ROOT/'data/hot.json').read_text(encoding='utf-8'))

    def test_three_day_cycle_in_beijing_calendar_days(self):
        self.assertEqual(DEFAULT_CADENCE_DAYS,3)
        x=report(self.deep,self.hot,date(2026,10,17))
        self.assertEqual(x['latest_id'],'rea-agent-reverse-engineering')
        self.assertEqual(x['latest_published'],'2026-10-13')
        self.assertEqual(x['latest_updated'],'2026-10-15')
        self.assertEqual(x['latest_content_date'],'2026-10-15')
        self.assertEqual(x['next_due'],'2026-10-18')
        self.assertEqual(x['age_days'],2)
        self.assertFalse(x['stale'])
        due=report(self.deep,self.hot,date(2026,10,18))
        self.assertEqual(due['age_days'],3)
        self.assertTrue(due['stale'])
        overdue=report(self.deep,self.hot,date(2026,10,19))
        self.assertTrue(overdue['stale'])
        self.assertEqual(overdue['overdue_days'],1)

    def test_revision_is_not_a_new_publication(self):
        d=deepcopy(self.deep)
        old=next(a for a in d['articles'] if a['id']=='jev-agent-decision-layer')
        old['updated']='2026-10-19'
        x=report(d,self.hot,date(2026,10,19))
        self.assertEqual(x['latest_id'],'jev-agent-decision-layer')
        self.assertEqual(x['latest_published'],'2026-09-24')
        self.assertEqual(x['latest_content_date'],'2026-10-19')
        self.assertEqual(x['latest_new_id'],'rea-agent-reverse-engineering')
        self.assertFalse(x['stale'])
        self.assertTrue(report(d,self.hot,date(2026,10,22))['stale'])

    def test_prior_article_alone_exposes_revision_date(self):
        old=dict(self.deep,articles=[x for x in self.deep['articles'] if x['id']!='rea-agent-reverse-engineering'])
        x=report(old,self.hot,date(2026,10,19))
        self.assertTrue(x['stale'])
        self.assertEqual(x['latest_published'],'2026-09-24')
        self.assertEqual(x['latest_content_date'],'2026-10-15')

    def test_candidate_queue_is_not_a_publication(self):
        x=report(self.deep,self.hot,date(2026,10,19))
        self.assertTrue(all(item['id'] not in {i for a in self.deep['articles'] for i in a.get('hot_ids',[])}
            for item in x['uncovered_hot_candidates']))
        self.assertIn('不会自动发布',x['note'])
        self.assertIn('只改 updated',x['note'])

    def test_empty_archive_remains_overdue(self):
        x=report({'articles':[]},self.hot,date(2026,10,19))
        self.assertTrue(x['stale'])
        self.assertIsNone(x['next_due'])

    def test_bad_threshold(self):
        for value in (0,-1,True):
            with self.assertRaises(ValueError):
                report(self.deep,self.hot,date(2026,10,19),value)

    def test_revision_cannot_predate_publication(self):
        with self.assertRaises(ValueError):
            content_date({'published':'2026-10-20','updated':'2026-10-19'})

if __name__=='__main__': unittest.main()
