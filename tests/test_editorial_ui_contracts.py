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
  text=(ROOT/'src/hot.js').read_text()
  fn=text[text.index('function hHeatBand('):text.index('const H_ICON=')]
  code=fn+"console.log(JSON.stringify([99,98,97,96,95,94,90,89].map(hHeatBand)));"
  rows=json.loads(subprocess.check_output(['node','-e',code],text=True))
  self.assertEqual([r['key'] for r in rows],['extreme','extreme','high','high','high','rising','rising','watch'])
  self.assertEqual([r['label'] for r in rows],['爆热','爆热','高热','高热','高热','升温','升温','关注'])
 def test_homepage_heat_has_text_and_accessible_numeric_label(self):
  text=(ROOT/'src/feed-cockpit.js').read_text()
  self.assertIn('aria-label="编辑热度 ',text)
  self.assertIn("hHeatBand(x.heat).label+'</small>'",text)
  css=(ROOT/'src/feed-cockpit.css').read_text()
  for band in ('extreme','high','rising','watch'):self.assertIn('.fc-heat-'+band,css)
 def test_timeline_heat_has_text_tiers_and_non_color_shapes(self):
  timeline=(ROOT/'src/intraday.js').read_text()
  self.assertIn('class="intraday-score is-${band.key}"',timeline)
  self.assertIn('<span>${band.label}</span>',timeline)
  css=(ROOT/'src/v10.css').read_text()
  self.assertIn('.intraday-score.is-extreme',css)
  self.assertIn('border-left:3px solid',css)
  self.assertIn('border-style:dashed',css)
 def test_intraday_heat_is_not_mislabelled_as_an_ai_score(self):
  text=(ROOT/'src/intraday.js').read_text()
  self.assertNotIn('AI 评分',text)
  self.assertIn('aria-label="本站编辑热度 ${x.heat} 分，${band.label}"',text)

 def test_unreviewed_upstream_releases_require_an_explicit_queue_view(self):
  legacy=(ROOT/'src/app.js').read_text()
  current=(ROOT/'src/v2.js').read_text()
  catalog=json.loads((ROOT/'data/catalog.json').read_text())
  upstream=json.loads((ROOT/'data/upstream.json').read_text())
  sources={s['id']:s['url'].rstrip('/') for s in catalog['sources']}
  verified={sources[sid] for event in catalog['events'] for sid in event.get('sources',[]) if sid in sources}
  pending={r['url'].rstrip('/') for r in upstream['releases'] if r['url'].rstrip('/') not in verified}
  self.assertIn("activity:DATA.events.length,",legacy)
  self.assertNotIn("activity:DATA.events.length+UP.releases.length",legacy)
  self.assertIn("const pool=state.kind==='upstream'?raw:DATA.events",legacy)
  self.assertIn('function pendingUpstreamReleases()',legacy)
  self.assertIn('verifiedEventSourceUrls.has(normalizedSourceUrl(e.url))',legacy)
  self.assertIn("const upstreamMode=state.kind==='upstream'",current)
  self.assertIn('pendingUpstream=pendingUpstreamReleases()',current)
  self.assertIn('上游候选 ${pendingUpstream.length} 条',current)
  self.assertIn('机器收录，进入正文前仍需人工核验',current)
  self.assertIn('#/activity?kind=upstream',current)
  for url in (
   'https://github.com/OpenHands/OpenHands/releases/tag/v1.33.0',
   'https://github.com/docling-project/docling/releases/tag/v2.142.1',
   'https://github.com/NVIDIA-NeMo/Automodel/releases/tag/v0.7.0',
   'https://github.com/microsoft/flint-chart/releases/tag/1.0',
  ):self.assertNotIn(url,pending)
  automodel=[r for r in upstream['releases'] if r['url'].endswith('/v0.7.0') and r['repo']=='NVIDIA-NeMo/Automodel']
  self.assertEqual([r['task'] for r in automodel],['nvidia-nemo-automodel-0-7'])

 def test_each_intraday_source_link_has_a_unique_accessible_name(self):
  text=(ROOT/'src/intraday.js').read_text()
  self.assertIn('aria-label="查看「${esc(x.title)}」原始来源（新窗口打开）"',text)

 def test_toolkit_repeated_actions_include_tool_specific_accessible_names(self):
  text=(ROOT/'src/toolkit.js').read_text()
  self.assertIn('`${t.name} 官方上手文档（新窗口打开）`',text)
  self.assertIn('`${t.name} 打开入口（新窗口打开）`',text)
  self.assertIn('`${t.name}：${s.title}（新窗口打开）`',text)

 def test_platform_switch_exposes_current_page_to_assistive_technology(self):
  text=(ROOT/'src/hot.js').read_text()
  self.assertIn("const current=id=>active===id?' aria-current=\"page\"':'';",text)
  self.assertIn("current('github')",text)
  self.assertIn("current('hf')",text)
 def test_hot_primary_cta_does_not_call_documents_an_experience(self):
  text=(ROOT/'src/hot.js').read_text()
  self.assertIn("const label=interactive?'立即体验':r.kind==='docs'?'查看资料':'阅读官方资料'",text)
  self.assertIn("icon(interactive?'zap':'book')",text)
  self.assertIn("r.kind==='product'",text)
  self.assertIn('当前入口是候补或产品资料页，尚不能直接体验',text)
 def test_vertical_sector_has_one_topic_navigation(self):
  legacy=(ROOT/'src/vertical.js').read_text()
  current=(ROOT/'src/v2.js').read_text()
  self.assertNotIn('v-topic-strip',legacy)
  self.assertEqual(current.count('v2-business-chain'),1)
 def test_sector_default_exposes_latest_dated_record_without_rewriting_curated_order(self):
  text=(ROOT/'src/vertical.js').read_text()
  current=(ROOT/'src/v2.js').read_text()
  self.assertIn('function latestSectorArticle(sector)',text)
  self.assertIn('b.published.localeCompare(a.published)',text)
  self.assertIn('data-latest-id=',text)
  self.assertIn("if(state.topic!=='all'||state.format!=='all'||state.q||state.focus)return ''",text)
  self.assertIn('${latestSectorCard(sector)}${vToolbar()}',current)
 def test_saved_page_separates_global_index_from_project_watchlist(self):
  text=(ROOT/'src/app.js').read_text()
  self.assertIn("saved:['PROJECT WATCHLIST','已关注项目','bookmark']",text)
  self.assertNotIn("saved:['YOUR PERSONAL INDEX','我的关注','bookmark']",text)
