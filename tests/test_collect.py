import copy
import io
import json
import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from collect import normalize,collect,fetch_releases,FetchError
T={'id':'project','repo':'owner/project'}
NOW='2026-09-20T00:00:00Z'
R={'id':1,'tag_name':'v1.0.0','name':'Release <v1>','published_at':'2026-09-18T12:00:00Z','html_url':'https://github.com/owner/project/releases/tag/v1.0.0','draft':False,'prerelease':False}

class CollectorTests(unittest.TestCase):
    def test_release_is_unreviewed(self):
        r=normalize([R],T,NOW)[0]
        self.assertEqual(r['review_status'],'unreviewed');self.assertNotIn('capability',r)
        self.assertNotIn('body',r)
    def test_skip_draft_and_prerelease(self):
        self.assertEqual(normalize([{**R,'draft':True},{**R,'prerelease':True}],T,NOW),[])
    def test_skip_future_and_malformed(self):
        self.assertEqual(normalize([{**R,'published_at':'2099-01-01T00:00:00Z'},{**R,'published_at':None},None],T,NOW),[])
    def test_block_url_on_other_host(self):
        self.assertEqual(normalize([{**R,'html_url':'https://evil.invalid/release'}],T,NOW),[])
    def test_collect_idempotent_content(self):
        c={'items':[T]};fetch=lambda *a,**k:[R]
        a=collect(c,{},fetch,NOW);b=collect(c,a,fetch,'2026-09-21T00:00:00Z')
        self.assertEqual(a['releases'],b['releases']);self.assertEqual(len(b['releases']),1)
    def test_retains_old_records_when_api_fails(self):
        old=collect({'items':[T]}, {},lambda *a,**k:[R],NOW)
        def fail(*a,**kw):raise FetchError('Network unavailable')
        new=collect({'items':[T]},old,fail,'2026-09-21T00:00:00Z')
        self.assertEqual(old['releases'],new['releases']);self.assertEqual(old['last_success'],new['last_success'])
        self.assertEqual(new['repositories_succeeded'],0);self.assertEqual(len(new['errors']),1)
    def test_no_claim_of_full_success_on_partial_failure(self):
        def partial(repo,**kwargs):
            if repo=='owner/project':return [R]
            raise FetchError('HTTP 404')
        a=collect({'items':[T,{'id':'other','repo':'owner/other'}]}, {},partial,NOW)
        self.assertIsNone(a['last_success']);self.assertEqual(a['repositories_succeeded'],1)
    def test_unsafe_repo_does_not_fetch(self):
        with self.assertRaises(FetchError):fetch_releases('../../example.com')
    def test_retries_transient_errors(self):
        calls=[]
        def opener(req,**kwargs):
            calls.append(req)
            if len(calls)<3:raise HTTPError(req.full_url,503,'Unavailable',{},None)
            return io.BytesIO(json.dumps([R]).encode())
        data=fetch_releases(T['repo'],opener=opener,sleeper=lambda _:None)
        self.assertEqual(len(calls),3);self.assertEqual(data[0]['id'],1)
    def test_reject_non_array(self):
        with self.assertRaises(FetchError):fetch_releases(T['repo'],opener=lambda *a,**kw:io.BytesIO(b'{}'))
    def test_auth_error_does_not_retry_or_expose_token(self):
        calls=[]
        def opener(req,**kwargs):
            calls.append(req);raise HTTPError(req.full_url,401,'private-secret-value',{},None)
        with self.assertRaises(FetchError) as e:fetch_releases(T['repo'],token='private-secret-value',opener=opener)
        self.assertEqual(str(e.exception),'GitHub HTTP 401');self.assertEqual(len(calls),1)

if __name__=='__main__':unittest.main()
