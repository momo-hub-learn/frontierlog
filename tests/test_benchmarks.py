"""Catalog integrity, honest data boundaries and portable build contract."""
from __future__ import annotations
import copy, json, re, sys, tempfile, unittest
from pathlib import Path
from datetime import date, timedelta
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
from benchmark_data import validate_benchmarks, benchmark_rss
from build import build

class BenchmarkTests(unittest.TestCase):
 def setUp(self):
  self.data=json.loads((R/'data/benchmarks.json').read_text())
  self.site=json.loads((R/'data/site.json').read_text())
 def reject(self,change):
  change(self.data)
  with self.assertRaises((ValueError,KeyError,TypeError)):validate_benchmarks(self.data)
 def test_seed_counts_and_kinds(self):
  validate_benchmarks(self.data)
  self.assertEqual(len(self.data['items']),20)
  self.assertEqual(len(self.data['sources']),28)
  self.assertEqual(len(self.data['suites']),5)
  self.assertEqual(sum(b['kind']=='dataset' for b in self.data['items']),2)
 def test_duplicate_item(self):self.reject(lambda d:d['items'].append(copy.deepcopy(d['items'][0])))
 def test_duplicate_source(self):self.reject(lambda d:d['sources'].append(copy.deepcopy(d['sources'][0])))
 def test_id_unsafe(self):self.reject(lambda d:d['items'][0].update(id='<script>'))
 def test_source_unknown(self):self.reject(lambda d:d['items'][0].update(sources=['unknown']))
 def test_source_missing(self):self.reject(lambda d:d['items'][0].update(sources=[]))
 def test_no_unsafe_scheme(self):self.reject(lambda d:d['sources'][0].update(url='javascript:alert(1)'))
 def test_no_credentials(self):self.reject(lambda d:d['sources'][0].update(url='https://name:secret@example.org'))
 def test_no_unsafe_results(self):self.reject(lambda d:d['items'][0].update(result_url='data:text/html,unsafe'))
 def test_no_fabricated_evaluation(self):self.reject(lambda d:d['items'][0].update(tested=True))
 def test_scores_not_in_protocol_schema(self):
  for key in ['score','rank','sota','best_model']:
   d=copy.deepcopy(self.data);d['items'][0][key]=99
   with self.assertRaises(ValueError):validate_benchmarks(d)
 def test_no_claimed_collection(self):self.reject(lambda d:d['sync'].update(last_success='2026-09-21T10:00:00Z'))
 def test_no_pretended_live_status(self):self.reject(lambda d:d['sync'].update(status='live'))
 def test_future_date(self):self.reject(lambda d:d.update(checked=(date.today()+timedelta(days=1)).isoformat()))
 def test_source_after_check(self):self.reject(lambda d:d['sources'][0].update(checked='2099-01-01'))
 def test_change_after_check(self):self.reject(lambda d:d['changes'][0].update(date='2099-01-01'))
 def test_no_future_source_publication(self):self.reject(lambda d:d['sources'][0].update(published='2099-01-01'))
 def test_unknown_group(self):self.reject(lambda d:d['items'][0].update(group='made-up'))
 def test_no_empty_metric(self):self.reject(lambda d:d['items'][0].update(metric=''))
 def test_unknown_item_kind(self):self.reject(lambda d:d['items'][0].update(kind='clinical-standard'))
 def test_no_empty_checks(self):self.reject(lambda d:d['items'][0].update(checks=[]))
 def test_suite_requires_gap(self):self.reject(lambda d:d['suites'][0].update(gap=''))
 def test_suite_valid_ids_only(self):self.reject(lambda d:d['suites'][0].update(benchmarks=['unknown']))
 def test_suite_limit(self):self.reject(lambda d:d['suites'][0].update(benchmarks=[x['id'] for x in d['items'][:7]]))
 def test_change_refs(self):self.reject(lambda d:d['changes'][0].update(benchmarks=['unknown']))
 def test_dataset_business_scope_explicit(self):
  for id in ['secom','cmapss']:
   b=next(b for b in self.data['items'] if b['id']==id)
   self.assertEqual(b['kind'],'dataset');self.assertTrue(b['boundary'])
 def test_no_claim_ich_is_csr_benchmark(self):
  self.assertFalse(any('ich' in b['id'] for b in self.data['items']))
  s=next(s for s in self.data['suites'] if s['id']=='csr')
  self.assertTrue(s['gap']);self.assertTrue(s['sources'])
 def test_feed_keeps_event_dates_and_provenance(self):
  xml=ET.fromstring(benchmark_rss(self.data,self.site));items=xml.findall('channel/item')
  self.assertEqual(len(items),4)
  src_dates={x['date'] for x in self.data['changes']}
  self.assertEqual({parsedate_to_datetime(i.findtext('pubDate')).date().isoformat() for i in items},src_dates)
  self.assertEqual(len({i.findtext('guid') for i in items}),4)
  self.assertTrue(all('https://' in i.findtext('description') for i in items))
  self.assertTrue(all('/frontierlog/#/benchmarks' in i.findtext('link') for i in items))
 def test_feed_repeat_stable(self):self.assertEqual(benchmark_rss(self.data,self.site),benchmark_rss(self.data,self.site))
 def test_complete_portable_build(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp);build(p)
   html=(p/'index.html').read_text()
   self.assertIn('const BENCH=APP.benchmarks',html)
   self.assertIn('FrontierLog',html)
   self.assertIn('brand-copy',html)
   self.assertEqual((p/'index.html').read_bytes(),(p/'404.html').read_bytes())
   self.assertEqual(json.loads((p/'api/v1/benchmarks.json').read_text())['items'],self.data['items'])
   self.assertTrue((p/'assets/brand.svg').is_file())
   self.assertTrue((p/'feeds/benchmarks.xml').is_file())
   self.assertNotIn('https://momo-hub-learn.github.io/ai-progress/',html)
   self.assertNotRegex(html,r'<script[^>]+src=[\"\']https://')

if __name__=='__main__':unittest.main()
