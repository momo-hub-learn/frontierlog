from __future__ import annotations
import copy,json,sys,tempfile,unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from email.utils import parsedate_to_datetime
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
from hot_data import validate_hot, hot_rss
from build import build

class HotDataTests(unittest.TestCase):
 def setUp(self):
  self.data=json.loads((R/'data/hot.json').read_text())
  self.site=json.loads((R/'data/site.json').read_text())
 def reject(self,fn):
  d=copy.deepcopy(self.data);fn(d)
  with self.assertRaises((ValueError,KeyError,TypeError)):validate_hot(d)
 def test_valid_and_counts(self):
  validate_hot(self.data);self.assertEqual(len(self.data['items']),10);self.assertEqual(len(self.data['categories']),6)
 def test_not_fake_live(self):self.reject(lambda d:d['method'].update(automatic=True))
 def test_no_claimed_success(self):self.reject(lambda d:d['method'].update(last_success='2026-09-21T00:00:00Z'))
 def test_heat_range(self):self.reject(lambda d:d['items'][0].update(heat=145))
 def test_bad_trend(self):self.reject(lambda d:d['items'][0].update(trend='viral'))
 def test_unsafe_url(self):self.reject(lambda d:d['items'][0].update(url='javascript:alert(1)'))
 def test_bad_internal_link(self):self.reject(lambda d:d['items'][0].update(link='https://evil.example'))
 def test_rss_dates_sources_and_stable_guid(self):
  root=ET.fromstring(hot_rss(self.data,self.site));items=root.findall('channel/item')
  self.assertEqual(len(items),10);self.assertEqual(len({i.findtext('guid') for i in items}),10)
  self.assertTrue(all(i.findtext('link').startswith('https://') for i in items))
  self.assertTrue(all('不是全网流量' in i.findtext('description') for i in items))
  self.assertEqual({parsedate_to_datetime(i.findtext('pubDate')).date().isoformat() for i in items},{x['published'] for x in self.data['items']})
 def test_build_embeds_hot_and_model_benchmark_tab(self):
  with tempfile.TemporaryDirectory() as td:
   out=Path(td);app=build(out);html=(out/'index.html').read_text()
   self.assertIn('const HOT=APP.hot',html);self.assertEqual(len(app['hot']['items']),10)
   self.assertTrue((out/'api/v1/hot.json').exists());self.assertTrue((out/'feeds/hot.xml').exists())
   self.assertIn("modelHubTabs('benchmarks')",html);self.assertIn('热点榜',html)
