import copy,json,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from xml.etree import ElementTree as ET
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
from model_data import validate_models,validate_resets,model_rss,reset_rss
from collect_models import collect_aa,collect_x,normalize_aa,classify_post,FetchFailure,atomic_json
M=json.loads((R/'data/models.json').read_text());E=json.loads((R/'data/resets.json').read_text());SITE=json.loads((R/'data/site.json').read_text())
NOW=datetime(2026,9,21,8,tzinfo=timezone.utc)
AA={'data':[{'id':'stable-123','name':'Fixture 2 (high)','model_creator':{'name':'Test lab'},'evaluations':{'artificial_analysis_intelligence_index':45,'artificial_analysis_coding_index':41},'pricing':{'price_1m_input_tokens':0.08,'price_1m_output_tokens':0.20},'median_output_tokens_per_second':150}]}
def row(postid='123',text='Codex reset cards next week?',created='2026-09-21T02:30:00Z'):
 return {'id':postid,'text':text,'author_id':'777','created_at':created,'conversation_id':'101'}
def transport_for(posts,next_token=None):
 def transport(url,headers):
  if '/users/by/username/' in url:return {'data':{'id':'777','username':'thsottiaux'}}
  return {'data':posts,'meta':{'next_token':next_token} if next_token else {'result_count':len(posts)}}
 return transport
class ValidationTests(unittest.TestCase):
 def test_valid_catalogs(self):validate_models(M);validate_resets(E)
 def test_intelligence_index_methodology_is_complete_and_source_backed(self):
  index=M['intelligence_index']
  self.assertEqual((index['version'],index['checked'],index['source']),('4.3.2','2026-10-27','aa-method'))
  self.assertEqual(sum(x['weight'] for x in index['categories']),100)
  evaluations=[e for category in index['categories'] for e in category['evaluations']]
  self.assertEqual(len(evaluations),10)
  self.assertEqual({e['name'] for e in evaluations},{'AA-Briefcase v1.1','GDPval-AA v2.1','AutomationBench-AA','AA-Omniscience','GDP.pdf','AA-LCR v1.1','Terminal-Bench 4.0','SciCode',"Humanity's Last Exam",'CritPt'})
  source=next(x for x in M['sources'] if x['id']==index['source'])
  self.assertEqual(source['url'],'https://artificialanalysis.ai/methodology/intelligence-benchmarking')
  validate_models(M)
 def test_intelligence_index_bad_weights_rejected(self):
  d=copy.deepcopy(M);d['intelligence_index']['categories'][0]['evaluations'][0]['weight']+=1
  with self.assertRaises(ValueError):validate_models(d)
 def test_nan_rejected(self):
  d=copy.deepcopy(M);d['boards'][0]['rows'][0]['intelligence']=float('nan')
  with self.assertRaises(ValueError):validate_models(d)
 def test_negative_prices_rejected(self):
  d=copy.deepcopy(M);d['boards'][0]['rows'][0]['input_price']=-1
  with self.assertRaises(ValueError):validate_models(d)
 def test_duplicate_models_rejected(self):
  d=copy.deepcopy(M);d['boards'][0]['rows'].append(d['boards'][0]['rows'][0])
  with self.assertRaises(ValueError):validate_models(d)
 def test_source_javascript_rejected(self):
  d=copy.deepcopy(M);d['sources'][0]['url']='javascript:alert(1)'
  with self.assertRaises(ValueError):validate_models(d)
 def test_missing_model_citation(self):
  d=copy.deepcopy(M);d['boards'][0]['rows'][0]['source']='missing'
  with self.assertRaises(ValueError):validate_models(d)
 def test_cross_score_system_rejected(self):
  d=copy.deepcopy(M);d['boards'][0]['rows'][0]['preference']=1500
  with self.assertRaises(ValueError):validate_models(d)
 def test_invalid_interval(self):
  d=copy.deepcopy(M);d['boards'][1]['rows'][0]['rank_spread']=[9,1]
  with self.assertRaises(ValueError):validate_models(d)
 def test_date_only_no_midnight(self):
  d=copy.deepcopy(E);d['events'][0]['published_at']='2026-09-03T00:00:00Z'
  with self.assertRaises(ValueError):validate_resets(d)
 def test_timezone_required(self):
  d=copy.deepcopy(E);d['events'][0].update(precision='instant',published_at='2026-09-03T01:00:00')
  with self.assertRaises(ValueError):validate_resets(d)
 def test_deadline_requires_timezone_and_is_not_execution(self):
  row=next(x for x in E['events'] if x['id']=='tibo-reset-announced-2026-10-22-day17')
  self.assertEqual(row['status'],'announced');self.assertNotIn('effective_at',row)
  self.assertEqual(datetime.fromisoformat(row['deadline_at'].replace('Z','+00:00')).astimezone(timezone(timedelta(hours=8))).isoformat(),'2026-10-24T01:00:00+08:00')
  d=copy.deepcopy(E);next(x for x in d['events'] if x['id']==row['id'])['deadline_at']='2026-10-23T17:00:00'
  with self.assertRaises(ValueError):validate_resets(d)
 def test_oct23_reset_confirmation_keeps_announcement_separate(self):
  rows={x['id']:x for x in E['events']}
  announcement=rows['tibo-reset-announced-2026-10-22-day17']
  confirmed=rows['tibo-global-confirmed-2026-10-23-day18']
  self.assertEqual(announcement['status'],'announced')
  self.assertEqual(confirmed['status'],'confirmed')
  self.assertEqual(confirmed['review_basis'],'primary_source')
  self.assertIn(announcement['id'],confirmed['related_ids'])
  self.assertEqual(confirmed['published_at'],'2026-10-23T04:46:19.007Z')
  self.assertIn("that's a reset",confirmed['original_text'])
  validate_resets(E)
 def test_oct25_day20_propagation_is_primary_completion_evidence(self):
  row=next(x for x in E['events'] if x['id']=='tibo-global-confirmed-2026-10-25-day20')
  self.assertEqual((row['kind'],row['status'],row['review_basis']),('global','confirmed','primary_source'))
  self.assertEqual(row['published_at'],'2026-10-25T06:06:16.025Z')
  self.assertTrue(row['verified_at'].endswith('+08:00'))
  self.assertIn('all propagated',row['original_text'])
  self.assertIn('不能证明每个账户',row['boundary'])
  self.assertEqual(len(row['sources']),3)
  validate_resets(E)
 def test_pending_not_confirmed(self):
  d=copy.deepcopy(E);next(x for x in d['events'] if x['review_basis']=='secondary_lead')['status']='confirmed'
  with self.assertRaises(ValueError):validate_resets(d)
 def test_announcement_never_completed(self):
  d=copy.deepcopy(E);e=d['events'][0];e['kind']='announcement'
  with self.assertRaises(ValueError):validate_resets(d)
 def test_primary_required_for_confirmed(self):
  d=copy.deepcopy(E);d['events'][0]['sources']=['aihot-reset']
  with self.assertRaises(ValueError):validate_resets(d)
 def test_false_success_rejected(self):
  d=copy.deepcopy(M);d['sync'].update(status='success',last_success=None)
  with self.assertRaises(ValueError):validate_models(d)
 def test_feed_keeps_sources_no_fake_pubdate(self):
  xml=ET.fromstring(reset_rss(E,SITE));items=xml.findall('./channel/item')
  self.assertEqual(len(items),len(E['events']))
  precise=sum(1 for e in E['events'] if e['precision']=='instant')
  self.assertEqual(sum(i.find('pubDate') is not None for i in items),precise)
  self.assertTrue(any('待核验' in i.findtext('title') for i in items));self.assertIn('help.openai.com',ET.tostring(xml,encoding='unicode'))
 def test_oct7_reset_processed_is_confirmed_only_after_direct_primary_review(self):
  rows={x['id']:x for x in E['events']}
  self.assertIn('tibo-global-processed-2026-10-07',rows)
  self.assertIn('tibo-banked-loading-2026-10-07',rows)
  self.assertEqual(rows['tibo-global-processed-2026-10-07']['status'],'confirmed')
  self.assertEqual(rows['tibo-banked-loading-2026-10-07']['status'],'pending')
  self.assertEqual(rows['tibo-global-processed-2026-10-07']['review_basis'],'primary_source')
  self.assertEqual(rows['tibo-global-processed-2026-10-07']['evidence_strength'],'high')
  self.assertTrue(rows['tibo-global-processed-2026-10-07']['verified_at'].endswith('+08:00'))
  self.assertIn('processed',rows['tibo-global-processed-2026-10-07']['original_text'])
  validate_resets(E)
 def test_model_feed_boards_separate_stable_guids(self):
  a=ET.fromstring(model_rss(M,SITE));b=ET.fromstring(model_rss(M,SITE))
  self.assertEqual(len(a.findall('./channel/item')),2)
  self.assertEqual([x.text for x in a.findall('.//guid')],[x.text for x in b.findall('.//guid')])
 def test_aa_oct24_leaders_are_source_backed_and_missing_metrics_stay_null(self):
  board=next(x for x in M['boards'] if x['id']=='aa')
  rows=sorted(board['rows'],key=lambda x:(-(x['intelligence'] or -1),x['source_order']))[:5]
  self.assertEqual([(x['name'],x['intelligence']) for x in rows],[
   ('Claude Opus 5.5 (max with fallback)',58),
   ('Claude Sonnet 5.5 (Max, Default Fallback)',56),
   ('Claude Opus 5.5 (Xhigh, Default Fallback)',56),
   ('Muse Wonder Full (Max)',56),
   ('Kimi K3.1 Pro',55),
  ])
  self.assertTrue(all(x['source']=='aa-live' for x in rows))
  self.assertIsNone(rows[1]['speed'])
 def test_gpt61_terra_has_current_independent_snapshot_without_cross_board_score(self):
  board=next(x for x in M['boards'] if x['id']=='aa')
  row=next(x for x in board['rows'] if x['id']=='aa-gpt61-terra-max')
  self.assertEqual((row['intelligence'],row['speed'],row['cost_task']),(48,None,0.4))
  self.assertEqual((row['input_price'],row['output_price'],row['context']),(1,5,'1M'))
  self.assertIsNone(row['coding'])
  source=next(x for x in M['sources'] if x['id']==row['source'])
  self.assertEqual((source['published'],source['checked']),('2026-10-26','2026-10-27'))
  self.assertIn('/releases/gpt-6-1-terra',source['url'])
  validate_models(M)
 def test_arena_oct22_excerpt_preserves_official_rank_uncertainty_and_preliminary(self):
  board=next(x for x in M['boards'] if x['id']=='arena')
  self.assertEqual(board['as_of'],'2026-10-22')
  self.assertGreaterEqual(board['checked'],board['as_of'])
  source=next(x for x in M['sources'] if x['id']==board['source'])
  self.assertEqual(source['published'],board['as_of'])
  self.assertEqual(source['checked'],board['checked'])
  self.assertEqual([x['source_rank'] for x in board['rows']],[1,2,3,4,5,18,21,26])
  leader=board['rows'][0]
  self.assertEqual((leader['name'],leader['preference'],leader['score_error'],leader['votes']),
                   ('Gemini 4 Argon (High)',1517,7,10083))
  self.assertEqual(leader['rank_spread'],[1,3])
  self.assertTrue(leader['preliminary'])
  self.assertTrue(all(x['source']=='arena-text' for x in board['rows']))
class AATests(unittest.TestCase):
 def test_no_opt_in_no_network(self):
  self.assertEqual(collect_aa(M,{'enabled':False},'secret',NOW,lambda *_:self.fail('network')),M)
 def test_missing_key_no_network(self):
  d=collect_aa(M,{'enabled':True},'',NOW,lambda *_:self.fail('network'))
  self.assertEqual(d['sync']['status'],'not_configured')
 def test_official_mapping_prices_distinct(self):
  d=normalize_aa(AA,'2026-09-21');r=d['rows'][0]
  self.assertEqual(r['input_price'],.08);self.assertIsNone(r['cost_task']);self.assertIsNone(r['context']);self.assertEqual(r['coding'],41)
 def test_stable_id_survives_name_change(self):
  b=copy.deepcopy(AA);b['data'][0]['name']='new display name'
  self.assertEqual(normalize_aa(AA,'2026-09-21')['rows'][0]['id'],normalize_aa(b,'2026-09-21')['rows'][0]['id'])
 def test_success_preserves_arena(self):
  d=collect_aa(M,{'enabled':True},'fixture-key',NOW,lambda *_:AA,True)
  self.assertEqual(d['sync']['status'],'success');self.assertEqual(d['boards'][1],M['boards'][1]);validate_models(d)
 def test_ttl_no_network(self):
  d=copy.deepcopy(M);d['sync']['last_success']=NOW.isoformat()
  self.assertEqual(collect_aa(d,{'enabled':True,'ttl_hours':24},'fixture-key',NOW,lambda *_:self.fail('network')),d)
 def test_empty_response_preserves_rows(self):
  d=collect_aa(M,{'enabled':True},'fixture-key',NOW,lambda *_:{'data':[]},True)
  self.assertEqual(d['boards'],M['boards']);self.assertEqual(d['sync']['status'],'error')
 def test_error_does_not_leak_secret(self):
  def bad(*_):raise ValueError('request header PRIVATE-SECRET')
  d=collect_aa(M,{'enabled':True},'PRIVATE-SECRET',NOW,bad,True)
  self.assertNotIn('PRIVATE-SECRET',json.dumps(d))
 def test_duplicate_api_identity_rejected(self):
  d=copy.deepcopy(AA);d['data'].append(d['data'][0])
  with self.assertRaises(ValueError):normalize_aa(d,'2026-09-21')
class XTests(unittest.TestCase):
 def test_missing_key_no_network(self):
  d=collect_x(E,{'enabled':True},'',NOW,lambda *_:self.fail('network'))
  self.assertEqual(d['sync']['status'],'not_configured')
 def test_candidate_classification(self):
  e=classify_post(row(),'thsottiaux',NOW.isoformat())
  self.assertEqual(e['candidate_kind'],'banked');self.assertEqual(e['review_status'],'pending')
  self.assertIn(e['semantic_type'],{'banked_announcement','banked_delivery'})
 def test_reply_timing_hint_uses_context(self):
  e=classify_post(row(text='3am on a Tuesday'),'thsottiaux',NOW.isoformat(),'When will the next Codex reset happen?')
  self.assertEqual(e['candidate_kind'],'announcement');self.assertEqual(e['semantic_type'],'timing_hint');self.assertEqual(e['evidence_strength'],'low')
  self.assertIn('时区',e['not_proves'])
 def test_propagation_is_semantically_distinct(self):
  e=classify_post(row(text='Reset all propagated. Enjoy the week.'),'thsottiaux',NOW.isoformat())
  self.assertEqual(e['semantic_type'],'propagation_complete');self.assertEqual(e['evidence_strength'],'high')
 def test_unrelated_post_ignored(self):self.assertIsNone(classify_post(row(text='Happy Monday!'),'thsottiaux',NOW.isoformat()))
 def test_negation_is_never_confirmed(self):
  e=classify_post(row(text='We did not reset Codex limits today.'),'thsottiaux',NOW.isoformat())
  self.assertEqual(e['review_status'],'pending');self.assertIn('否定',e['reason'])
 def test_x_success_does_not_modify_curated_events(self):
  d=collect_x(E,{'enabled':True},'test',NOW,transport_for([row()]),True)
  self.assertEqual(d['sync']['status'],'success');self.assertEqual(d['events'],E['events']);self.assertEqual(d['checked'],E['checked']);validate_resets(d)
 def test_reply_not_excluded(self):
  def f(url,headers):
   if '/tweets?' in url:self.assertNotIn('replies',url)
   return transport_for([row()])(url,headers)
  d=collect_x(E,{'enabled':True},'test',NOW,f,True);self.assertEqual(d['sync']['status'],'success')
 def test_deduplicate_candidates(self):
  d=collect_x(E,{'enabled':True},'test',NOW,transport_for([row(),row()]),True)
  self.assertEqual(len(d['inbox']),1)
 def test_bad_page_preserves_all_old_data(self):
  def f(*_):raise FetchFailure('http_403')
  d=collect_x(E,{'enabled':True},'test',NOW,f,True)
  self.assertEqual(d['inbox'],E['inbox']);self.assertEqual(d['events'],E['events']);self.assertEqual(d['sync']['error'],'http_403')
 def test_partial_page_does_not_advance_cursor(self):
  d=copy.deepcopy(E);d['sync']['cursor']='100'
  out=collect_x(d,{'enabled':True,'max_pages':1},'test',NOW,transport_for([row()],next_token='next'),True)
  self.assertEqual(out['sync']['cursor'],'100');self.assertEqual(out['sync']['status'],'partial')
 def test_wrong_author_rejected(self):
  p=row();p['author_id']='333'
  d=collect_x(E,{'enabled':True},'test',NOW,transport_for([p]),True)
  self.assertEqual(d['sync']['status'],'error');self.assertEqual(d['inbox'],E['inbox'])
 def test_feed_excerpt_is_limited(self):
  e=classify_post(row(text='reset '+('hello '*100)),'thsottiaux',NOW.isoformat());self.assertLessEqual(len(e['excerpt']),240)
 def test_atomic_write_idempotent(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'data.json';p.write_text('{}')
   self.assertTrue(atomic_json(p,{'foo':'bar'}));self.assertFalse(atomic_json(p,{'foo':'bar'}))
if __name__=='__main__':unittest.main()
