from __future__ import annotations
import sys
import unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
from collect_trending import parse_github_trending, parse_hf_page_order, classify_new_repo, build_hf_data

class TrendingSyncTests(unittest.TestCase):
    def test_github_parser_preserves_official_order_and_daily_stars(self):
        page='''
        <article class="Box-row"><h2><a href="/alpha/agent-one">alpha</a></h2><span>1,234 stars today</span></article>
        <article class="Box-row"><h2><a href="/beta/tool-two">beta</a></h2><span>56 stars today</span></article>
        <article class="Box-row"><h2><a href="/gamma/tool-three">gamma</a></h2><span>7 stars today</span></article>
        <article class="Box-row"><h2><a href="/delta/tool-four">delta</a></h2><span>8 stars today</span></article>
        <article class="Box-row"><h2><a href="/epsilon/tool-five">epsilon</a></h2><span>9 stars today</span></article>
        '''
        rows=parse_github_trending(page)
        self.assertEqual([x['repo'] for x in rows],['alpha/agent-one','beta/tool-two','gamma/tool-three','delta/tool-four','epsilon/tool-five'])
        self.assertEqual(rows[0]['stars_today'],1234)

    def test_hf_page_order_wins_over_api_score_order(self):
        page='<a href="/org/model-b">B</a><a href="/org/model-a">A</a>'
        api=[
            {'id':'org/model-a','trendingScore':999,'likes':1,'downloads':2,'pipeline_tag':'text-generation','library_name':'transformers','createdAt':'2026-01-01T00:00:00Z','tags':[]},
            {'id':'org/model-b','trendingScore':10,'likes':3,'downloads':4,'pipeline_tag':'text-classification','library_name':'transformers','createdAt':'2026-01-02T00:00:00Z','tags':[]},
        ]
        old={'version':1,'items':[]}
        out=build_hf_data(old,page,api,'2026-09-25T00:00:00+00:00',limit=2)
        self.assertEqual([x['id'] for x in out['items']],['org/model-b','org/model-a'])
        self.assertEqual(out['items'][0]['trending_score'],10)

    def test_hf_missing_api_score_fails_closed(self):
        page='<a href="/org/model-a">A</a>'
        api=[{'id':'org/model-a','likes':1,'downloads':2,'pipeline_tag':'text-generation','library_name':'transformers','createdAt':'2026-01-01T00:00:00Z','tags':[]}]
        with self.assertRaises(ValueError): build_hf_data({'items':[]},page,api,'2026-09-25T00:00:00+00:00',limit=1)

    def test_conservative_ai_classification(self):
        ai={'full_name':'paperclipai/paperclip','description':'Manage agents at work','topics':[]}
        infra={'full_name':'openbao/openbao','description':'Manage secrets, certificates, and keys','topics':['security']}
        self.assertTrue(classify_new_repo(ai)[0])
        self.assertFalse(classify_new_repo(infra)[0])

if __name__=='__main__': unittest.main()
