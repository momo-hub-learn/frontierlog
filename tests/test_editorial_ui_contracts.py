"""Contract regressions for editorial growth and visible heat hierarchy."""
import copy, json, subprocess, sys, unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from topics import topic_rss, validate_topics

class EditorialContracts(unittest.TestCase):
 def test_hot_internal_deep_links_resolve_to_real_records(self):
  hot=json.loads((ROOT/'data/hot.json').read_text())
  catalog=json.loads((ROOT/'data/catalog.json').read_text())
  industry=json.loads((ROOT/'data/industry.json').read_text())
  task_ids={x['id'] for x in catalog['items']}
  article_ids={x['id'] for x in industry['articles']}
  checked=0
  for item in hot['items']:
   link=item.get('link','')
   if not link.startswith('#/') or '?' not in link: continue
   query=parse_qs(urlsplit(link[1:]).query)
   if 'task' in query:
    self.assertIn(query['task'][0],task_ids,item['id'])
    checked+=1
   if 'article' in query:
    self.assertIn(query['article'][0],article_ids,item['id'])
    checked+=1
  self.assertGreaterEqual(checked,2)

 def test_hot_industry_records_open_the_matching_evidence_drawer(self):
  hot=json.loads((ROOT/'data/hot.json').read_text())
  industry=json.loads((ROOT/'data/industry.json').read_text())
  article_ids={x['id'] for x in industry['articles']}
  matched=0
  for item in hot['items']:
   if item['category']!='industry' or item['id'] not in article_ids: continue
   internal=[x for x in item.get('access',[]) if x.get('kind')=='internal']
   if not internal: continue
   query=parse_qs(urlsplit(item['link'][1:]).query)
   self.assertEqual(query.get('article'),[item['id']],item['id'])
   self.assertEqual(internal[0]['url'],item['link'],item['id'])
   matched+=1
  self.assertGreaterEqual(matched,2)

 def test_sidebar_date_names_the_dataset_it_actually_describes(self):
  html=(ROOT/'src/index.html').read_text()
  app=(ROOT/'src/app.js').read_text()
  self.assertIn('<span>垂类资料核对</span><code id="snapshot-date">',html)
  self.assertNotIn('<span>资料快照</span><code id="snapshot-date">',html)
  self.assertIn("$('#snapshot-date').textContent=VERT.checked",app)
 def test_top_level_navigation_resets_scroll_and_focuses_main(self):
  html=(ROOT/'src/index.html').read_text()
  app=(ROOT/'src/app.js').read_text()
  self.assertIn('<main id="main" tabindex="-1">',html)
  self.assertIn('const previousView=state.view;',app)
  self.assertIn("if(previousView!==state.view)requestAnimationFrame(()=>{window.scrollTo(0,0);$('#main').focus({preventScroll:true})})",app)
 def test_mobile_quick_jump_keeps_its_search_icon_visible(self):
  html=(ROOT/'src/index.html').read_text()
  css=(ROOT/'src/styles.css').read_text()
  self.assertIn('<button class="command-trigger" data-action="command" aria-label="快速跳转"><span data-icon="search"></span><span>快速跳转</span>',html)
  self.assertIn('.top-actions .command-trigger>span:not([data-icon]),.top-actions .command-trigger kbd{display:none}',css)
  self.assertNotIn('.top-actions .command-trigger>span,.top-actions .command-trigger kbd{display:none}',css)
 def test_hot_heading_has_no_decorative_punctuation_in_its_accessible_name(self):
  for name in ('v10.js','hot.js','github-hot.js','huggingface-hot.js','models.js','toolkit.js'):
   text=(ROOT/'src'/name).read_text()
   self.assertNotIn('<span class="accent">.</span></h1>',text,name)
  self.assertIn('<h1>热点时间线</h1>',(ROOT/'src/v10.js').read_text())
 def test_tibo_first_screen_states_the_account_propagation_boundary(self):
  base=(ROOT/'src/models.js').read_text()
  enhanced=(ROOT/'src/tibo-intel.js').read_text()
  self.assertIn('公开记录不能证明每个账户已经到账',base)
  self.assertIn('公开原帖不能证明每个账户已经到账',enhanced)
 def test_industry_cards_expose_source_strength_before_opening_detail(self):
  text=(ROOT/'src/vertical.js').read_text()
  self.assertIn("function articleEvidenceLabel(a)",text)
  self.assertIn("官方一手 · 本站未实测",text)
  self.assertIn("articleEvidenceChip(a)",text)
 def test_limited_industry_access_is_visible_before_opening_detail(self):
  industry=json.loads((ROOT/'data/industry.json').read_text())
  row=next(x for x in industry['articles'] if x['id']=='openai-gpt6-rosalind-research-20261030')
  self.assertEqual((row['access_status'],row['access_label']),('limited','访问：限量审批'))
  self.assertIn('Chat 页不可用',row['access'])
  js=(ROOT/'src/vertical.js').read_text()
  css=(ROOT/'src/vertical.css').read_text()
  self.assertIn('function articleAccessChip(a)',js)
  self.assertIn('${articleAccessChip(a)}',js)
  self.assertIn('.v-access-chip.status-limited',css)
 def test_microsoft_synthetic_enterprise_evaluation_keeps_internal_boundary(self):
  hot=json.loads((ROOT/'data/hot.json').read_text())
  research=json.loads((ROOT/'data/research-radar.json').read_text())
  industry=json.loads((ROOT/'data/industry.json').read_text())
  record_id='microsoft-industry-evaluation-data-20261030'
  signal=next(x for x in hot['items'] if x['id']==record_id)
  radar=next(x for x in research['items'] if x['id']==record_id)
  article=next(x for x in industry['articles'] if x['id']==record_id)
  self.assertEqual(signal['published'],'2026-10-30')
  self.assertNotIn('published_at',signal)
  self.assertEqual(signal['link'],'#/pharma?article='+record_id)
  self.assertIn('内部平台',signal['verification_status'])
  self.assertIn('未见公开数据集',radar['boundary'])
  self.assertIn('不能跨系统比较',article['boundary'])
  self.assertEqual((article['access_status'],article['access_label']),('unavailable','访问：内部平台'))
  self.assertFalse(article['tested'])
 def test_foxconn_healthcare_event_keeps_clinical_and_robotics_claims_bounded(self):
  hot=json.loads((ROOT/'data/hot.json').read_text())
  industry=json.loads((ROOT/'data/industry.json').read_text())
  signal=next(x for x in hot['items'] if x['id']=='foxconn-smart-healthcare-agents-robotics-20261030')
  clinical=next(x for x in industry['articles'] if x['id']=='foxconn-smart-healthcare-agents-20261030')
  robotics=next(x for x in industry['articles'] if x['id']=='foxconn-hospital-robotics-digital-twin-20261030')
  self.assertEqual(signal['published'],'2026-10-30')
  self.assertEqual(signal['evidence_level'],'primary-source')
  self.assertIn('未做临床或现场复验',signal['verification_status'])
  self.assertEqual((clinical['sector'],robotics['sector']),('pharma','manufacturing'))
  self.assertIn('未披露前瞻性临床试验',clinical['boundary'])
  self.assertIn('仿真与流程集成不能替代真实医院验收',robotics['boundary'])
  self.assertFalse(clinical['tested']);self.assertFalse(robotics['tested'])
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
  self.assertIn('新鲜度排序分 ',text)
  self.assertIn("hHeatBand(x.heat).label+' · 排序 '+esc(String(v10Top5Score(x)))",text)
  css=(ROOT/'src/feed-cockpit.css').read_text()
  for band in ('extreme','high','rising','watch'):self.assertIn('.fc-heat-'+band,css)
 def test_model_rows_show_access_boundary_separately_from_score(self):
  js=(ROOT/'src/models.js').read_text()
  css=(ROOT/'src/models.css').read_text()
  self.assertIn('function mAccessBadge(r)',js)
  self.assertIn('${mAccessBadge(r)}',js)
  self.assertIn('.m-access-limited',css)
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

 def test_tibo_explicit_confirmation_has_a_distinct_visible_state(self):
  text=(ROOT/'src/tibo-intel.js').read_text()
  self.assertIn("explicit_reset_confirmation:'明确确认'",text)
  self.assertIn("if(x.semantic_type==='explicit_reset_confirmation')return 'Tibo：reset 已确认'",text)
  self.assertIn("'explicit_reset_confirmation'",text)

 def test_tibo_loads_history_embeds_only_near_the_viewport(self):
  text=(ROOT/'src/tibo-intel.js').read_text()
  self.assertIn('data-x-priority="eager"',text)
  self.assertIn('data-x-priority="deferred"',text)
  self.assertIn("new IntersectionObserver",text)
  self.assertIn("{rootMargin:'500px 0px'}",text)
  self.assertIn("m.dataset.xState='deferred'",text)

 def test_tibo_featured_embed_stays_bounded_when_a_quote_has_large_media(self):
  css=(ROOT/'src/tibo-intel.css').read_text()
  js=(ROOT/'src/tibo-intel.js').read_text()
  self.assertIn('.tibo-featured-x[data-x-state="loaded"]{max-height:520px;overflow-y:auto',css)
  self.assertIn('原帖嵌入可滚动；失败时退回原文摘录，不模拟截图。',js)

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
  self.assertIn('function v2UpstreamHealth(count)',current)
  self.assertIn('最近完整成功 ${success} 北京时间',current)
  self.assertIn('${succeeded}/${total||\'—\'} 源成功',current)
  self.assertIn('${failed} 源失败',current)
  self.assertIn('role="status"',current)
  self.assertIn('#/activity?kind=upstream',current)
  self.assertIn('const upstreamIntro=',current)
  self.assertIn("$('#content').innerHTML=upstreamMode",current)
  self.assertIn("classList.toggle('is-upstream-queue',upstreamMode)",current)
  self.assertIn('?`${upstreamIntro}${lifecycleSection}`',current)
  enhanced=(ROOT/'src/activity-hero.js').read_text()
  self.assertIn("const queueMode=state.view==='activity'&&state.kind==='upstream'",enhanced)
  self.assertIn("state.view!=='activity'||queueMode",enhanced)
  for url in (
   'https://github.com/OpenHands/OpenHands/releases/tag/v1.34.0',
   'https://github.com/OpenHands/OpenHands/releases/tag/v1.33.0',
