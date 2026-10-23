from __future__ import annotations
import copy,json,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime
from xml.etree import ElementTree as ET
from email.utils import parsedate_to_datetime
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
from hot_data import validate_hot, validate_hot_inbox, hot_rss
from hot_sync import collect_candidates, curated_urls, evaluate
from build import build

class HotDataTests(unittest.TestCase):
 def setUp(self):
  self.data=json.loads((R/'data/hot.json').read_text())
  self.site=json.loads((R/'data/site.json').read_text())
 def reject(self,fn):
  d=copy.deepcopy(self.data);fn(d)
  with self.assertRaises((ValueError,KeyError,TypeError)):validate_hot(d)
 def test_valid_and_counts(self):
  validate_hot(self.data);self.assertGreater(len(self.data['items']),0);self.assertEqual(len(self.data['categories']),6)
 def test_not_fake_live(self):self.reject(lambda d:d['method'].update(automatic=True))
 def test_no_claimed_success(self):self.reject(lambda d:d['method'].update(last_success='2026-09-21T00:00:00Z'))
 def test_shadow_runtime_state_cannot_enter_editorial_content(self):
  validate_hot(self.data);self.assertNotIn('sync',self.data)
  self.reject(lambda d:d.update(sync={'mode':'shadow','last_checked_at':'2026-10-21T00:00:00Z'}))
 def test_hot_inbox_and_shadow_collector(self):
  inbox=json.loads((R/'data/hot-inbox.json').read_text());validate_hot_inbox(inbox)
  rows=collect_candidates(datetime.fromisoformat('2026-09-28T09:55:00+00:00'))
  self.assertTrue(rows);self.assertTrue(all(x['action'] in {'publish','merge','hold'} for x in rows))
  self.assertTrue(all(x['url'].startswith('https://') for x in rows))
  self.assertTrue(all(0<=x['priority_score']<=1 for x in rows))
  result,decision=evaluate(datetime.fromisoformat('2026-09-28T09:55:00+00:00'),inbox)
  validate_hot_inbox(result);self.assertEqual(decision['candidate_count'],len(rows))
 def test_nested_evidence_url_is_not_a_novel_candidate(self):
  self.assertIn('https://antigravity.google/blog/gemini-4-argon-in-google-antigravity',curated_urls(self.data))

 def test_heat_range(self):self.reject(lambda d:d['items'][0].update(heat=145))
 def test_bad_trend(self):self.reject(lambda d:d['items'][0].update(trend='viral'))
 def test_unsafe_url(self):self.reject(lambda d:d['items'][0].update(url='javascript:alert(1)'))
 def test_bad_internal_link(self):self.reject(lambda d:d['items'][0].update(link='https://evil.example'))
 def test_toolkit_links_use_supported_task_contract(self):
  tasks={x['id'] for x in json.loads((R/'data/catalog.json').read_text())['items']}
  links=[x['link'] for x in self.data['items'] if x.get('link','').startswith('#/toolkit?')]
  self.assertTrue(links)
  for link in links:
   with self.subTest(link=link):
    self.assertNotIn('?id=',link)
    query=link.split('?',1)[1]
    params=dict(part.split('=',1) for part in query.split('&'))
    self.assertIn(params.get('task'),tasks)
    self.assertEqual(params.get('tab'),'run')
 def test_benchmark_links_use_supported_deep_link_contract(self):
  benchmarks={x['id'] for x in json.loads((R/'data/benchmarks.json').read_text())['items']}
  links=[x['link'] for x in self.data['items'] if x.get('link','').startswith('#/benchmarks?')]
  self.assertTrue(links)
  for link in links:
   with self.subTest(link=link):
    params=dict(part.split('=',1) for part in link.split('?',1)[1].split('&'))
    self.assertIn(params.get('bench'),benchmarks)
 def test_historical_trending_rank_is_not_presented_as_current(self):
  item=next(x for x in self.data['items'] if x['id']=='minimax-m31-flash-open-weights-20261023')
  self.assertIn('首次收录时',item['summary'])
  self.assertIn('当前榜位以热榜页最新官方快照为准',item['summary'])
  self.assertIn('会随平台快照变化',item['boundary'])
  self.assertEqual(item['link'],'#/hot?tab=hf')
 def test_precise_timestamp_optional(self):
  d=copy.deepcopy(self.data);d['items'][0]['published_at']='2026-09-10T16:10:00+08:00';validate_hot(d)
 def test_precise_timestamp_requires_timezone(self):self.reject(lambda d:d['items'][0].update(published_at='2026-09-10T16:10:00'))
 def test_rss_dates_sources_and_stable_guid(self):
  root=ET.fromstring(hot_rss(self.data,self.site));items=root.findall('channel/item')
  self.assertEqual(len(items),len(self.data['items']));self.assertEqual({i.findtext('guid') for i in items},{'frontierlog:hot:'+x['id'] for x in self.data['items']})
  self.assertTrue(all(i.findtext('link').startswith('https://') for i in items))
  self.assertTrue(all('不是全网流量' in i.findtext('description') for i in items))
  self.assertEqual({parsedate_to_datetime(i.findtext('pubDate')).date().isoformat() for i in items},{x['published'] for x in self.data['items']})
 def test_build_embeds_hot_and_model_benchmark_tab(self):
  with tempfile.TemporaryDirectory() as td:
   out=Path(td);app=build(out);html=(out/'index.html').read_text()
   self.assertIn('const HOT=APP.hot',html);self.assertEqual(app['hot']['items'],self.data['items'])
   self.assertTrue((out/'api/v1/hot.json').exists());self.assertTrue((out/'api/v1/hot-inbox.json').exists());self.assertTrue((out/'feeds/hot.xml').exists())
   self.assertIn("modelHubTabs('benchmarks')",html);self.assertIn('热点榜',html)
