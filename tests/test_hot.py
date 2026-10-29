from __future__ import annotations
import copy,json,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
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
 def test_internal_access_requires_an_explicit_safe_site_route(self):
  terra=next(x for x in self.data['items'] if x['id']=='openai-gpt-6-1-terra-20261026')
  route=next(x for x in terra['access'] if x.get('kind')=='internal')
  self.assertEqual(route['url'],'#/models')
  self.assertIn('v5',route['note']);validate_hot(self.data)
  self.reject(lambda d:next(x for x in d['items'] if x['id']==terra['id'])['access'][-1].update(url='javascript:alert(1)'))
  self.reject(lambda d:next(x for x in d['items'] if x['id']==terra['id'])['access'][-1].update(url='#//evil.example'))
 def test_openhands_1_34_links_release_to_runnable_guide_without_claiming_runtime_evidence(self):
  item=next(x for x in self.data['items'] if x['id']=='openhands-v1-34-runtime-security-20261027')
  self.assertEqual(item['published_at'],'2026-10-27T14:35:23Z')
  self.assertEqual(item['url'],'https://github.com/OpenHands/OpenHands/releases/tag/v1.34.0')
  self.assertEqual(item['link'],'#/toolkit?task=openhands&tab=run')
  self.assertIn('不是本站运行或安全审计',item['boundary'])
  route=next(x for x in item['access'] if x['kind']=='internal')
  self.assertEqual(route['url'],item['link'])
  validate_hot(self.data)
 def test_docling_and_unlimited_ocr_keep_runtime_and_vendor_claim_boundaries(self):
  docling=next(x for x in self.data['items'] if x['source']=='Docling Project')
  self.assertEqual(docling['link'],'#/toolkit?task=docling&tab=run')
  self.assertIn('不是本站运行或 OCR 质量评测',docling['boundary'])
  ocr=next(x for x in self.data['items'] if x['id']=='baidu-unlimited-ocr-2-20261027')
  self.assertEqual(ocr['url'],'https://huggingface.co/baidu/Unlimited-OCR-2')
  self.assertIn('厂商评测',ocr['verification_status'])
  self.assertIn('trust_remote_code',ocr['boundary'])
  self.assertIn('HF Trending 也不等于能力榜',ocr['boundary'])
  validate_hot(self.data)
 def test_novelty_judge_hot_item_preserves_author_result_and_weak_label_boundary(self):
  item=next(x for x in self.data['items'] if x['id']=='ai2-novelty-judge-instability-20261027')
  self.assertEqual(item['link'],'#/benchmarks?bench=novelty-judge-bench')
  self.assertIn('93.5%',item['summary'])
  self.assertIn('40.9%',item['summary'])
  self.assertIn('本站没有运行模型或复现实验',item['boundary'])
  self.assertIn('标签较弱',item['boundary'])
  self.assertEqual(item['evidence_level'],'primary-source')
  validate_hot(self.data)
 def test_anthropic_judgment_study_links_to_exact_research_record_with_limits(self):
  item=next(x for x in self.data['items'] if x['id']=='anthropic-agent-judgment-deferral-20261027')
  self.assertEqual(item['published'],'2026-10-27')
  self.assertEqual(item['url'],'https://www.anthropic.com/research/agents-judgment-calls')
  self.assertEqual(item['link'],'#/progress?view=research&research=anthropic-agent-judgment-calls')
  self.assertIn('86%',item['summary'])
  self.assertIn('一个分析任务',item['boundary'])
  self.assertIn('本站未复现实验',item['boundary'])
  internal=next(x for x in item['access'] if x['kind']=='internal')
  self.assertEqual(internal['url'],item['link'])
  validate_hot(self.data)
 def test_microsoft_copilot_harness_links_preview_to_exact_verification_guide(self):
  item=next(x for x in self.data['items'] if x['id']=='microsoft-copilot-harness-foundry-20261028')
  self.assertEqual(item['published'],'2026-10-28')
  self.assertEqual(item['link'],'#/toolkit?task=microsoft-copilot-harness&tab=run')
  self.assertIn('公开预览',item['summary'])
  self.assertIn('幂等',item['boundary'])
  self.assertIn('本站未部署或运行',item['boundary'])
  internal=next(x for x in item['access'] if x['kind']=='internal')
  self.assertEqual(internal['url'],item['link'])
  validate_hot(self.data)
 def test_nemotron_transcribe_separates_trending_vendor_results_and_runtime_evidence(self):
  item=next(x for x in self.data['items'] if x['id']=='nvidia-nemotron-3-5-transcribe-20261028')
  self.assertEqual(item['published'],'2026-10-28')
  self.assertEqual(item['link'],'#/toolkit?task=nvidia-nemotron-3-5-transcribe&tab=run')
  self.assertIn('第 19 位只代表当时平台趋势',item['boundary'])
  self.assertIn('不支持实时流式',item['boundary'])
  self.assertIn('本站未运行',item['verification_status'])
  self.assertEqual(next(x for x in item['access'] if x['kind']=='internal')['url'],item['link'])
  validate_hot(self.data)
 def test_icloud_release_keeps_read_write_scope_and_runtime_evidence_separate(self):
  item=next(x for x in self.data['items'] if x['id']=='openai-icloud-mail-calendar-20261027')
  self.assertEqual(item['published'],'2026-10-27')
  self.assertEqual(item['link'],'#/progress?view=map&q=iCloud')
  self.assertIn('更新日历事件',item['summary'])
  self.assertIn('没有宣布可直接发送 iCloud 邮件',item['boundary'])
  self.assertIn('本站未连接账户或执行写入',item['boundary'])
  validate_hot(self.data)
 def test_nvidia_meta_muse_collaboration_stays_a_plan_not_a_capability_claim(self):
  item=next(x for x in self.data['items'] if x['id']=='nvidia-meta-muse-collaboration-20261027')
  self.assertEqual(item['published'],'2026-10-27')
  self.assertEqual(item['link'],'#/toolkit?task=nvidia-openshell&tab=run')
  self.assertIn('合作与计划',item['boundary'])
  self.assertIn('没有给出优化后的 Benchmark',item['boundary'])
  self.assertIn('本站未复核',item['boundary'])
  validate_hot(self.data)
 def test_hot_source_edits_trigger_checked_in_pages_rebuild(self):
  workflow=(R/'.github/workflows/hot-sync.yml').read_text()
  self.assertIn("      - 'data/hot.json'",workflow)

 def test_tibo_resets_are_exclusive_to_the_reset_monitor(self):
  reset_ids={x['id'] for x in json.loads((R/'data/resets.json').read_text())['events']}
  self.assertIn('tibo-global-confirmed-2026-10-23-day18',reset_ids)
  self.assertIn('tibo-global-confirmed-2026-10-25-day20',reset_ids)
  self.assertFalse([x['id'] for x in self.data['items'] if x['id'].startswith('tibo-reset-') or x.get('link','').startswith('#/tibo')])
  self.reject(lambda d:d['items'][0].update(link='#/tibo?event=tibo-global-confirmed-2026-10-25-day20'))
  self.reject(lambda d:d['items'][0].update(id='tibo-reset-future'))
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
  beijing=ZoneInfo('Asia/Shanghai')
  self.assertEqual({parsedate_to_datetime(i.findtext('pubDate')).astimezone(beijing).date().isoformat() for i in items},{x['published'] for x in self.data['items']})
  by_guid={i.findtext('guid'):i for i in items}
  for row in self.data['items']:
   stamp=row.get('published_at')
   if stamp:
    self.assertEqual(parsedate_to_datetime(by_guid['frontierlog:hot:'+row['id']].findtext('pubDate')),datetime.fromisoformat(stamp.replace('Z','+00:00')))
 def test_build_embeds_hot_and_model_benchmark_tab(self):
  with tempfile.TemporaryDirectory() as td:
   out=Path(td);app=build(out);html=(out/'index.html').read_text()
   self.assertIn('const HOT=APP.hot',html);self.assertEqual(app['hot']['items'],self.data['items'])
   self.assertTrue((out/'api/v1/hot.json').exists());self.assertTrue((out/'api/v1/hot-inbox.json').exists());self.assertTrue((out/'feeds/hot.xml').exists())
   self.assertIn("modelHubTabs('benchmarks')",html);self.assertIn('热点榜',html)
