import copy,json,sys,tempfile,unittest
from pathlib import Path
from xml.etree import ElementTree as ET
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
import topics,collect_topics as c,build
RSS=b'''<rss version="2.0"><channel><item><title>AI for wafer process control</title><link>https://example.org/a?utm_source=feed&amp;version=2</link><description><![CDATA[<p>Semiconductor fab FDC and APC software.</p>]]></description><pubDate>Fri, 18 Sep 2026 09:00:00 GMT</pubDate></item></channel></rss>'''
ATOM=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Clinical study report automation</title><link href="https://example.org/csr"/><summary>Medical writing with source checks</summary><updated>2026-09-18T12:00:00Z</updated></entry></feed>'''
class TopicDataTests(unittest.TestCase):
 def setUp(self):
  self.d=json.loads((R/'data/industry.json').read_text());self.i=json.loads((R/'data/topic-intake.json').read_text());self.s=json.loads((R/'data/site.json').read_text())
 def test_valid_topics(self):topics.validate_topics(self.d,self.i)
 def test_counts(self):self.assertEqual((len(self.d['sectors']),len(self.d['topics']),len(self.d['articles']),len(self.d['sources'])),(2,10,15,20))
 def test_reject_cross_sector(self):
  self.d['articles'][0]['topics']=['fab-yield']
  with self.assertRaises(ValueError):topics.validate_topics(self.d,self.i)
 def test_missing_source(self):
  self.d['articles'][0]['sources']=['not-real']
  with self.assertRaises(ValueError):topics.validate_topics(self.d,self.i)
 def test_no_unsafe_links(self):
  self.d['sources'][0]['url']='javascript:alert(1)'
  with self.assertRaises(ValueError):topics.validate_topics(self.d,self.i)
 def test_unknown_date_not_fabricated(self):
  rss=ET.fromstring(topics.topic_rss(self.d,self.s,'csr'))
  self.assertEqual(len(rss.findall('./channel/item')),3)
  self.assertEqual(len(rss.findall('./channel/item/pubDate')),0)
 def test_rss_scope_membership(self):
  for scope in [s['id'] for s in self.d['sectors']]+[t['id'] for t in self.d['topics']]:
   feed=ET.fromstring(topics.topic_rss(self.d,self.s,scope))
   count=sum(a['sector']==scope or scope in a['topics'] for a in self.d['articles'])
   self.assertEqual(len(feed.findall('./channel/item')),count)
 def test_invalid_feed_scope(self):
  with self.assertRaises(ValueError):topics.topic_rss(self.d,self.s,'../leak')
 def test_machine_cannot_upgrade_evidence(self):
  self.i['items']=[{'review_status':'verified','url':'https://example.org','topics':['csr']}]
  with self.assertRaises(ValueError):topics.validate_topics(self.d,self.i)
 def test_build_embeds_new_module_and_safe_payload(self):
  with tempfile.TemporaryDirectory() as d:
   a=build.build(Path(d));h=(Path(d)/'index.html').read_text()
   self.assertIn('const VERT=',h);self.assertIn('industry',a);self.assertEqual(len(list((Path(d)/'feeds').glob('*.xml'))),17) # 13 topic feeds + models, resets, benchmark and hot feeds
   self.assertNotIn('momo-hub-learn.github.io/ai-progress',h)
 def test_entire_build_offline(self):
  with tempfile.TemporaryDirectory() as d:
   build.build(Path(d));h=(Path(d)/'index.html').read_text()
   self.assertNotIn('<script src=',h);self.assertNotIn('@@CSS@@',h);self.assertNotIn('@@JS@@',h)
class CollectorTests(unittest.TestCase):
 def config(self):return {'max_items':50,'topic_ids':['csr','targets','molecules','clinical','fab-process','fab-yield','fab-maintenance','equipment-maintenance','equipment-design','digital-twin'],'sources':[{'id':'fixture','type':'rss','url':'https://example.org/feed','name':'TEST FIXTURE','enabled':True,'default_topics':[]}]}
 def test_rss_dates_and_url(self):
  r=c.parse_feed(RSS,'https://example.org/')[0]
  self.assertEqual(r['published_at'],'2026-09-18T09:00:00Z');self.assertEqual(r['url'],'https://example.org/a?version=2')
 def test_atom_updated_not_publish(self):
  r=c.parse_feed(ATOM,'https://example.org/')[0];self.assertIsNone(r['published_at']);self.assertEqual(r['updated_at'],'2026-09-18T12:00:00Z')
 def test_parser_rejects_html(self):
  with self.assertRaises(ValueError):c.parse_feed(b'<html>not feed</html>','https://example.org')
 def test_parser_rejects_entities(self):
  with self.assertRaises(ValueError):c.parse_feed(b'<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///etc/passwd">]><rss/>','https://example.org')
 def test_target_not_ad_target(self):
  self.assertNotIn('targets',c.classify('AI improves advertising target audience'))
  self.assertIn('targets',c.classify('Genetic evidence improves drug target prioritization'))
 def test_csr_context(self):
  self.assertIn('csr',c.classify('CSR drafting for clinical trial reports'))
  self.assertNotIn('csr',c.classify('CSR corporate social responsibility sustainability report'))
 def test_gpu_not_fab(self):self.assertEqual(c.classify('NVIDIA GPU benchmark speed and chip financing'),[])
 def test_semiconductor_routes(self):
  self.assertIn('fab-process',c.classify('Semiconductor wafer FDC and process control'))
  self.assertIn('fab-yield',c.classify('Wafer defect inspection with AI'))
  self.assertIn('fab-maintenance',c.classify('Semiconductor fab Equipment Intelligence maintenance'))
 def test_equipment_routes(self):
  self.assertIn('equipment-design',c.classify('Industrial engineering PLC copilot'))
  self.assertIn('digital-twin',c.classify('Factory digital twin simulation'))
 def test_tracking_removal_does_not_remove_meaning(self):self.assertEqual(c.canonical_url('https://example.org/x?a=2&utm_source=bad#piece'),'https://example.org/x?a=2')
 def test_reject_local_and_credentials(self):
  for x in ['http://example.org/','https://localhost/','https://127.0.0.1','https://user:secret@example.org/','https://example.org:3000/']:
   self.assertFalse(c.valid_url(x))
 def test_excerpt_not_full_markup(self):
  x=c.plain('<script>alert(1)</script><b>Hello</b> &amp; world');self.assertEqual(x,'Hello & world')
 def test_release_metadata_no_html(self):
  p=json.dumps([{'html_url':'https://github.com/x/y/releases/tag/1','name':'v1','published_at':'2026-09-18T00:00:00Z','body':'<b>testing</b>','draft':False}]).encode()
  self.assertEqual(c.parse_releases(p)[0]['excerpt'],'testing')
 def test_collect_success_unreviewed(self):
  r=c.collect(self.config(),{},lambda s:RSS,now='2026-09-21T01:17:00Z')
  self.assertEqual(len(r['items']),1);self.assertEqual(r['items'][0]['review_status'],'unreviewed');self.assertEqual(r['last_full_success'],r['last_attempt'])
 def test_dedup_and_first_seen(self):
  r=c.collect(self.config(),{},lambda s:RSS,now='2026-09-20T01:17:00Z')
  r2=c.collect(self.config(),r,lambda s:RSS,now='2026-09-21T01:17:00Z')
  self.assertEqual(len(r2['items']),1);self.assertEqual(r2['items'][0]['first_seen'],r['items'][0]['first_seen'])
 def test_total_failure_retains_records_and_success_time(self):
  r=c.collect(self.config(),{},lambda s:RSS,now='2026-09-20T01:17:00Z')
  def fail(s):raise TimeoutError('secret must not show')
  r2=c.collect(self.config(),r,fail,now='2026-09-21T01:17:00Z')
  self.assertEqual(r2['items'],r['items']);self.assertEqual(r2['last_success'],r['last_success']);self.assertNotIn('secret',json.dumps(r2))
 def test_partial_failure_does_not_update_full_success(self):
  conf=self.config();conf['sources'].append({**conf['sources'][0],'id':'failed'})
  def fetch(s):
   if s['id']=='failed':raise TimeoutError()
   return RSS
  r=c.collect(conf,{'last_full_success':'2026-09-19T00:00:00Z'},fetch,now='2026-09-21T01:17:00Z')
  self.assertEqual(r['last_full_success'],'2026-09-19T00:00:00Z');self.assertEqual(len(r['errors']),1);self.assertEqual(len(r['items']),1)
 def test_future_signal_not_included(self):
  r=c.collect(self.config(),{},lambda s:RSS,now='2020-01-01T00:00:00Z');self.assertEqual(r['items'],[])
if __name__=='__main__':unittest.main()
