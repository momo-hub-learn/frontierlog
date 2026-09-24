import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build

class BuildTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads((ROOT/'data/catalog.json').read_text())
        self.u=json.loads((ROOT/'data/upstream.json').read_text())
        self.s=json.loads((ROOT/'data/site.json').read_text())
    def test_catalog_valid(self): build.validate(self.c,self.u,self.s)
    def test_missing_source_rejected(self):
        self.c['items'][0]['sources']=['missing']
        with self.assertRaises(ValueError):build.validate(self.c,self.u,self.s)
    def test_duplicate_id_rejected(self):
        self.c['items'].append(copy.deepcopy(self.c['items'][0]))
        with self.assertRaises(ValueError):build.validate(self.c,self.u,self.s)
    def test_unsafe_source_url_rejected(self):
        self.c['sources'][0]['url']='javascript:alert(1)'
        with self.assertRaises(ValueError):build.validate(self.c,self.u,self.s)
    def test_future_event_rejected(self):
        self.c['events'][0]['date']='2099-01-01'
        with self.assertRaises(ValueError):build.validate(self.c,self.u,self.s)
    def test_invalid_repo_rejected(self):
        self.s['repository']='owner/repo/../../other'
        with self.assertRaises(ValueError):build.validate(self.c,self.u,self.s)
    def test_https_base_required(self):
        self.s['base_url']='javascript:alert(1)'
        with self.assertRaises(ValueError):build.validate(self.c,self.u,self.s)
    def test_local_build_no_fake_feed(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);app=build.build(d,'','')
            self.assertEqual(app['site']['repository'],'')
            self.assertFalse((d/'feed.xml').exists())
            self.assertTrue((d/'api/v1/index.json').exists())
            html=(d/'index.html').read_text()
            self.assertNotIn('@@DATA@@',html)
            self.assertNotIn('<link rel="alternate"',html)
            self.assertNotIn('<script src=',html)
    def test_deployed_build_supports_project_subpath(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);app=build.build(d,'test-owner/ai-progress','https://test-owner.github.io/ai-progress')
            self.assertEqual(app['site']['base_url'],'https://test-owner.github.io/ai-progress/')
            rss=ET.parse(d/'feed.xml')
            self.assertEqual(len(rss.findall('./channel/item')),len(self.c['events'])+15)
            self.assertTrue(all(i.text.startswith(app['site']['base_url']) for i in rss.findall('./channel/item/link')))
            self.assertEqual(len({i.text for i in rss.findall('./channel/item/guid')}),len(self.c['events'])+15)
            self.assertIn('sitemap.xml',(d/'robots.txt').read_text())
    def test_model_table_shows_company_logo_column(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);build.build(d,'','')
            html=(d/'index.html').read_text()
            self.assertIn('<th class="m-company-col">公司</th>',html)
            self.assertIn('m-company-logo',html)
            self.assertIn('https://openai.com/favicon.ico',html)
            self.assertIn('https://www.anthropic.com/favicon.ico',html)
            self.assertIn('https://robotics.xiaomi.com/favicon.ico',html)
            self.assertIn('mLogoForMaker',html)

    def test_frontier_model_tracks_render(self):
        models=json.loads((ROOT/'data/models.json').read_text())
        build.validate_models(models)
        self.assertEqual([x['id'] for x in models['frontier_tracks']],['vla','world-models','neo-labs'])
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);build.build(d,'','')
            html=(d/'index.html').read_text()
            self.assertIn('前沿模型雷达',html)
            self.assertIn('VLA / 具身智能',html)
            self.assertIn('World Model / JEPA',html)
            self.assertIn('Neo Labs / 新实验室',html)
            self.assertIn('Helix 2.5',html)
            self.assertIn('V-JEPA 2.1',html)
            self.assertIn('Jev / System One Models',html)

    def test_sidebar_uses_floating_tool_dock(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);build.build(d,'','')
            html=(d/'index.html').read_text()
            self.assertIn('id="v2-tool-dock"',html)
            self.assertIn('V2_TOOL_DOCK_KEY',html)
            self.assertIn('pointermove',html)
            self.assertIn("['内容',['feed','hot','models','progress','activity','toolkit']]",html)
            self.assertNotIn("['模型',['models']]",html)
            self.assertNotIn("['我的',['saved']]",html)
            self.assertNotIn("['工具',['tibo']]",html)
            self.assertIn("{view:'tibo',href:'#/tibo',title:'Tibo 重置'",html)
            self.assertNotIn("{view:'toolkit',href:'#/toolkit'",html)
            self.assertNotIn("{view:'benchmarks',href:'#/benchmarks'",html)
            self.assertIn('href="#/saved"',html)

    def test_github_hot_uses_granular_topics(self):
        data=json.loads((ROOT/'data/github-hot.json').read_text())
        cats={c['id'] for c in data['categories']}
        self.assertGreaterEqual(len(cats),10)
        self.assertFalse({'agent-app','agent-framework','agent-infra','mcp-knowledge'} & cats)
        self.assertTrue({'agent-runtime','agent-harness','agent-memory','agent-skills','agent-router'} <= cats)
        self.assertTrue(all(x['category'] in cats for x in data['items']))
        self.assertTrue(all(3 <= len(x['tags']) <= 4 for x in data['items'] if x['ai_related']))
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);build.build(d,'','')
            html=(d/'index.html').read_text()
            self.assertIn('gh-topic-chip',html)
            self.assertIn('Agent Runtime',html)
            self.assertIn('Agent Harness',html)
            self.assertIn('Agent Memory',html)
            self.assertIn('Persistent Memory',html)
            self.assertNotIn('<em>AI 相关</em>',html)

    def test_github_hot_shows_time_and_star_trend(self):
        data=json.loads((ROOT/'data/github-hot.json').read_text())
        self.assertTrue(all(x.get('repo_created_at') and x.get('repo_pushed_at') for x in data['items']))
        self.assertTrue(all(len(x.get('star_history',[])) >= 3 for x in data['items']))
        self.assertTrue(all(x['star_history'][-1]['stars'] >= x['star_history'][0]['stars'] for x in data['items']))
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);build.build(d,'','')
            html=(d/'index.html').read_text()
            self.assertIn('gh-spark',html)
            self.assertIn('ghTrendLabel(x)',html)
            self.assertIn('repo_created_at',html)
            self.assertIn('repo_pushed_at',html)

    def test_hot_panel_title_is_inline_bilingual(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);build.build(d,'','')
            html=(d/'index.html').read_text()
            self.assertIn('class="fc-panel-titleline"><h2>热点</h2><span class="eyebrow">HOT / NOW</span>',html)
            self.assertNotIn('<p class="eyebrow">HOT / NOW</p><h2>热点</h2>',html)

    def test_feed_header_has_no_redundant_big_title(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);build.build(d,'','')
            html=(d/'index.html').read_text()
            self.assertNotIn('<h1>今天，AI 走到哪了？</h1>',html)
            self.assertIn('每日精选 /',html)
            self.assertIn('全部热点',html)

    def test_feed_escapes_text(self):
        c=copy.deepcopy(self.c);c['events'][0]['title']='A < B & C'
        s={**self.s,'base_url':'https://example.org/sub/'}
        xml=build.make_rss(c,s)
        self.assertIn(b'&lt;',xml);self.assertIn(b'&amp;',xml)
        ET.fromstring(xml)
    def test_no_rss_left_from_previous_build(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);build.build(d,'test/site','https://test.github.io/site/')
            self.assertTrue((d/'feed.xml').exists())
            build.build(d,'','')
            self.assertFalse((d/'feed.xml').exists())
            self.assertFalse((d/'robots.txt').exists())

if __name__=='__main__':unittest.main()
