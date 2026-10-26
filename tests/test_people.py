"""Public professional provenance and site-integration contracts."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from people_data import validate_people, load_people
from build import build

class PeopleTests(unittest.TestCase):
 def setUp(self):
  self.data=json.loads((ROOT/'data/people.json').read_text())
 def reject(self,fn):
  d=copy.deepcopy(self.data);fn(d)
  with self.assertRaises((ValueError,TypeError,KeyError)):validate_people(d)
 def test_sources_and_contributions(self):
  validate_people(self.data)
  self.assertGreaterEqual(len(self.data['people']),30)
  self.assertTrue({'kaiming-he','qiushi-han','shreya-shankar','shyam-sankar'}<=set(p['id'] for p in self.data['people']))
  self.assertGreaterEqual(sum(p['discovery']=='work' for p in self.data['people']),5)
 def test_duplicate_person(self):self.reject(lambda d:d['people'].append(copy.deepcopy(d['people'][0])))
 def test_missing_source(self):self.reject(lambda d:d['people'][0].update(sources=[]))
 def test_unsafe_source(self):self.reject(lambda d:d['people'][0]['sources'][0].update(url='javascript:alert(1)'))
 def test_credential_url(self):self.reject(lambda d:d['people'][0]['works'][0].update(url='https://name:secret@example.org/'))
 def test_whitespace_url(self):self.reject(lambda d:d['people'][0]['sources'][0].update(url='https://example.org/\n'))
 def test_missing_attribution(self):self.reject(lambda d:d['people'][0]['works'][0].pop('relation'))
 def test_unknown_author(self):self.reject(lambda d:d['events'][0].update(people=['missing']))
 def test_reference_type(self):self.reject(lambda d:d['events'][0].update(people='kaiming-he'))
 def test_future_event(self):self.reject(lambda d:d['events'][0].update(date='2099-01-01'))
 def test_event_review_order(self):self.reject(lambda d:d['events'][0].update(checked='2000-01-01'))
 def test_calendar_invalid(self):self.reject(lambda d:d['events'][0].update(date='2026-02-30'))
 def test_people_not_ranked(self):self.reject(lambda d:d['people'][0].update(score=99))
 def test_every_person_has_source_backed_impact_facets(self):
  self.assertEqual(len(self.data['people']),33)
  self.assertTrue(all(p['impact']['dimensions'] and p['impact']['basis'] for p in self.data['people']))
  self.reject(lambda d:d['people'][0].pop('impact'))
  self.reject(lambda d:d['people'][0]['impact'].update(dimensions=['global-ranking']))
  self.reject(lambda d:d['people'][0]['impact'].update(score=99))
 def test_verified_recent_activity_has_original_dates_and_no_fake_events(self):
  ids={x['id'] for x in self.data['events']}
  self.assertIn('harrison-company-harness-20261024',ids)
  self.assertIn('hamel-decision-evals-20261020',ids)
  self.assertIn('danqi-queen-chess-20261002',ids)
  self.assertEqual(len(ids),len(self.data['events']))
  self.assertTrue(all(x['date']<=x['checked'] for x in self.data['events']))
 def test_private_fields_excluded(self):self.reject(lambda d:d['people'][0].update(email='private@example.org'))
 def test_no_arbitrary_related_href(self):self.reject(lambda d:d['people'][0]['related'].append({'id':'sierra','kind':'product','label':'Test','href':'javascript:bad'}))
 def test_no_automatic_claim(self):self.reject(lambda d:d.update(mode='live'))
 def test_unknown_domain(self):self.reject(lambda d:d['people'][0].update(areas=['missing']))
 def test_real_build_and_api(self):
  with tempfile.TemporaryDirectory() as tmp:
   app=build(Path(tmp), 'momo-hub-learn/frontierlog','https://momo-hub-learn.github.io/frontierlog/')
   compiled=json.loads((Path(tmp)/'api/v1/people.json').read_text())
   self.assertEqual(len(compiled['people']),len(self.data['people']))
   self.assertEqual(compiled,app['people'])
   self.assertEqual(self.data['people'][0]['checked'],compiled['people'][0]['checked'])
   palantir=next(p for p in compiled['people'] if p['id']=='shyam-sankar')
   self.assertIn('product=palantir-aip',palantir['related'][0]['href'])
   html=(Path(tmp)/'index.html').read_text()
   self.assertIn('const PeopleUI',html);self.assertIn('AI 人物',html)
   self.assertEqual((Path(tmp)/'404.html').read_text(),html)
   self.assertIn('palantir-aip',[x['id'] for x in app['product_radar']['items']])
   self.assertEqual(self.data,json.loads((ROOT/'data/people.json').read_text()))
