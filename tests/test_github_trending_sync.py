"""Official Trending snapshots must be evidenced and independently tracked from REA."""
from __future__ import annotations
import json
import sys
import unittest
from urllib.error import HTTPError
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from github_trending_sync import parse_trending, update_state, history_for

def page(n=8):
    out=[]
    for i in range(n):
        owner,repo=("morluto","rea") if i==0 else ("example",f"repo-{i}")
        out.append(f'''<article class="Box-row"><h2 class="h3 lh-condensed">
          <a href="/{owner}/{repo}">{owner} / <span>{repo}</span></a>
          </h2><p class="col-9 color-fg-muted my-1 pr-4">AI Agent harness {i}</p>
          <span itemprop="programmingLanguage">Python</span>
          <span>1,2{i}5 stars today</span></article>''')
    return "<html><body>" + "".join(out) + "</body></html>"

def api(repo):
    return {
        "full_name":repo, "stargazers_count":144000 if repo=="morluto/rea" else 2500,
        "forks_count":32000 if repo=="morluto/rea" else 33,
        "description":"Agent-assisted reverse engineering using MCP" if repo=="morluto/rea" else "AI agent coding harness",
        "language":"TypeScript","created_at":"2026-04-14T00:51:32Z",
        "pushed_at":"2026-10-12T16:00:00Z","html_url":"https://github.com/"+repo
    }

class GitHubSyncTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'data/github-hot.json').read_text(encoding='utf-8'))
        self.now=datetime(2026,10,13,8,15,tzinfo=timezone.utc)

    def test_official_rank_and_stars_today_are_parsed(self):
        rows=parse_trending(page())
        self.assertEqual(rows[0]['repo'],'morluto/rea')
        self.assertEqual(rows[0]['rank'],1)
        self.assertEqual(rows[0]['stars_today'],1205)
        self.assertEqual(rows[1]['stars_today'],1215)
        self.assertEqual(rows[0]['language'],'Python')

    def test_invalid_page_fails_closed(self):
        with self.assertRaises(ValueError):parse_trending("<p>robot check</p>")
        with self.assertRaises(ValueError):parse_trending(page(2))
        with self.assertRaises(ValueError):parse_trending(page().replace("1,205 stars today","unknown stars today"))
        with self.assertRaises(ValueError):parse_trending(page().replace('href="/example/repo-1"','href="/morluto/rea"'))

    def test_success_replaces_old_ranks_and_updates_watchlist_separately(self):
        out=update_state(self.data,self.now,fetch_page=page,fetch_metadata=api)
        self.assertEqual(out['sync']['status'],'success')
        self.assertEqual(out['checked_at'],'2026-10-13T08:15:00Z')
        self.assertEqual([x['rank'] for x in out['items']],list(range(1,9)))
        self.assertEqual(out['items'][0]['stars_today'],1205)
        tracked=out['watchlist'][0]
        self.assertEqual(tracked['repo'],'morluto/rea')
        self.assertEqual(tracked['stars'],144000)
        self.assertNotIn('stars_today',tracked)
        self.assertNotIn('rank',tracked)
        self.assertEqual(tracked['verified_at'],'2026-10-13T08:15:00Z')
        self.assertGreaterEqual(len(out['items'][0]['star_history']),1)
        self.assertEqual(out['items'][0]['star_history'][-1]['at'],'2026-10-13T08:15:00Z')
        self.assertEqual(out['items'][0]['metadata_verified_at'],'2026-10-13T08:15:00Z')
        self.assertEqual(out['sync']['metadata_status'],'success')

    def test_api_limit_preserves_complete_official_ranking_and_old_metadata(self):
        previous=self.data['items'][0]
        target=previous['repo']
        def limited(repo):
            if repo==target:
                raise HTTPError('https://api.github.com/repos/'+repo,403,'Forbidden',{},None)
            return api(repo)
        html=page().replace('/morluto/rea','/'+target,1)
        out=update_state(self.data,self.now,fetch_page=lambda:html,fetch_metadata=limited)
        self.assertEqual(out['sync']['status'],'success')
        self.assertEqual(out['sync']['metadata_status'],'partial')
        self.assertEqual(len(out['items']),8)
        self.assertEqual([x['rank'] for x in out['items']],list(range(1,9)))
        row=out['items'][0]
        self.assertEqual(row['repo'],target)
        self.assertEqual(row['stars'],previous['stars'])
        self.assertEqual(row['rank'],1)
        self.assertEqual(row['stars_today'],1205)
        self.assertEqual(row['metadata_verified_at'],self.data['checked_at'])
        self.assertEqual(row['metadata_status'],'stale')

    def test_failed_trending_does_not_advance_verified_date_or_old_rank(self):
        original=json.dumps(self.data['items'],sort_keys=True)
        out=update_state(self.data,self.now,fetch_page=lambda:"<html>blocked</html>",fetch_metadata=api)
        self.assertEqual(out['sync']['status'],'error')
        self.assertEqual(out['checked_at'],self.data['checked_at'])
        self.assertEqual(json.dumps(out['items'],sort_keys=True),original)
        self.assertEqual(out['watchlist'][0]['stars'],144000)
        self.assertEqual(out['sync']['last_checked_at'],'2026-10-13T08:15:00Z')

    def test_history_drops_weeks_old_points_and_never_forges_intervals(self):
        old={'star_history':[{'at':'2026-09-25T23:16:36Z','stars':100}]}
        self.assertEqual(history_for(old,200,'2026-10-13T08:15:00Z'),
                         [{'at':'2026-10-13T08:15:00Z','stars':200}])
        old={'star_history':[{'at':'2026-10-12T08:15:00Z','stars':100}]}
        self.assertEqual(len(history_for(old,200,'2026-10-13T08:15:00Z')),2)

    def test_no_utc_naive_clock(self):
        with self.assertRaises(ValueError):
            update_state(self.data,datetime(2026,10,13,8,15),fetch_page=page,fetch_metadata=api)

if __name__=="__main__":unittest.main()
