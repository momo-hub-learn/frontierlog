"""Contract regressions for editorial growth and visible heat hierarchy."""
import copy, json, subprocess, sys, unittest
from pathlib import Path
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from topics import topic_rss, validate_topics

class EditorialContracts(unittest.TestCase):
 def test_topic_rss_grows_and_shrinks_without_losing_identity(self):
  base=json.loads((ROOT/'data/industry.json').read_text())
  source=copy.deepcopy(base['articles'][0])
  for count in (1,10,18,25):
   with self.subTest(count=count):
    d=copy.deepcopy(base)
    d['articles']=[dict(copy.deepcopy(source),id='fixture-'+str(i)) for i in range(count)]
    validate_topics(d,{'items':[]})
    feed=ET.fromstring(topic_rss(d,{'base_url':'https://example.org/'}))
    rows=feed.findall('./channel/item')
    self.assertEqual(len(rows),count)
    self.assertEqual({r.findtext('guid') for r in rows},{'frontierlog:topic:fixture-'+str(i) for i in range(count)})
 def test_unknown_dates_remain_unknown_in_mixed_feed(self):
  d=json.loads((ROOT/'data/industry.json').read_text())
  a=copy.deepcopy(d['articles'][0]);a['id']='unknown-date';a['published']=None
  b=dict(copy.deepcopy(a),id='known-date',published='2026-10-15');d['articles']=[a,b]
  rows=ET.fromstring(topic_rss(d,{'base_url':'https://example.org/'})).findall('./channel/item')
  self.assertIsNone(rows[0].find('pubDate'));self.assertIsNotNone(rows[1].find('pubDate'))
 def test_homepage_heat_band_thresholds(self):
  text=(ROOT/'src/feed-cockpit.js').read_text()
  fn=text[text.index('function fcHeatBand('):text.index('function fcHotPanel(')]
  code=fn+"console.log(JSON.stringify([99,98,97,96,95,94,90,89].map(fcHeatBand)));"
  rows=json.loads(subprocess.check_output(['node','-e',code],text=True))
  self.assertEqual([r['key'] for r in rows],['extreme','extreme','high','high','high','rising','rising','watch'])
  self.assertEqual([r['label'] for r in rows],['爆热','爆热','高热','高热','高热','升温','升温','关注'])
 def test_homepage_heat_has_text_and_accessible_numeric_label(self):
  text=(ROOT/'src/feed-cockpit.js').read_text()
  self.assertIn('aria-label="编辑热度 ',text)
  self.assertIn("fcHeatBand(x.heat).label+'</small>'",text)
  css=(ROOT/'src/feed-cockpit.css').read_text()
  for band in ('extreme','high','rising','watch'):self.assertIn('.fc-heat-'+band,css)
 def test_intraday_heat_is_not_mislabelled_as_an_ai_score(self):
  text=(ROOT/'src/intraday.js').read_text()
  self.assertNotIn('AI 评分',text)
  self.assertIn('本站热度',text)
  self.assertIn('aria-label="本站编辑热度 ${x.heat} 分"',text)
 def test_hot_primary_cta_does_not_call_documents_an_experience(self):
  text=(ROOT/'src/hot.js').read_text()
  self.assertIn("const label=interactive?'立即体验':r.kind==='docs'?'查看资料':'阅读官方资料'",text)
  self.assertIn("icon(interactive?'zap':'book')",text)
