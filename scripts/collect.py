"""Collect release metadata from official GitHub repositories. Never generate capability claims.

Only an explicitly configured GITHUB_TOKEN is used (optional). No browser cookies,
credential files, or authenticated user profile are read. Requests are read-only.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT=Path(__file__).resolve().parents[1]
REPO_RE=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$')
MAX_BYTES=2_000_000

class FetchError(Exception): pass

def fetch_releases(repo: str, *, token: str='', opener=urlopen, sleeper=time.sleep) -> list:
    if not REPO_RE.fullmatch(repo):raise FetchError('Invalid repository identifier')
    headers={'User-Agent':'ai-progress-release-index/0.2','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
    if token:headers['Authorization']='Bearer '+token
    url=f'https://api.github.com/repos/{repo}/releases?per_page=10'
    for attempt in range(3):
        try:
            with opener(Request(url,headers=headers),timeout=20) as response:
                raw=response.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:raise FetchError('Response exceeds size limit')
            data=json.loads(raw)
            if not isinstance(data,list):raise FetchError('Unexpected API response')
            return data
        except HTTPError as e:
            if e.code==429 or 500<=e.code<=599:
                if attempt<2:sleeper(2**attempt);continue
            raise FetchError(f'GitHub HTTP {e.code}') from None
        except (URLError,TimeoutError) as e:
            if attempt<2:sleeper(2**attempt);continue
            raise FetchError('Network unavailable or timed out') from None
        except (ValueError,UnicodeError):raise FetchError('Invalid JSON response') from None
    raise FetchError('Fetch failed')

def normalize(rows: list, task:dict, now:str) -> list:
    """Retain exact release metadata; discard drafts, prereleases, malformed/future items."""
    out=[]
    upper=datetime.fromisoformat(now.replace('Z','+00:00'))
    if upper.tzinfo is None:upper=upper.replace(tzinfo=timezone.utc)
    for r in rows:
        if not isinstance(r,dict) or r.get('draft') or r.get('prerelease'):continue
        stamp=r.get('published_at')
        try:
            dt=datetime.fromisoformat(stamp.replace('Z','+00:00'))
            if dt.tzinfo is None or dt>upper:continue
        except (ValueError,AttributeError,TypeError):continue
        url=r.get('html_url','')
        if not isinstance(url,str) or not url.startswith('https://github.com/'+task['repo']+'/releases/'):continue
        rid=r.get('id');tag=r.get('tag_name')
        if not isinstance(rid,int) or not isinstance(tag,str):continue
        title=r.get('name') or tag
        if not isinstance(title,str):title=tag
        out.append({'id':f'upstream-{rid}','task':task['id'],'repo':task['repo'],'tag':tag[:200],
            'title':title[:300],'published_at':stamp,'observed_at':now,'url':url,
            'review_status':'unreviewed'})
    return out

def collect(catalog:dict,previous:dict,fetcher=fetch_releases,now:str|None=None,token:str='') -> dict:
    now=now or datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
    tasks=[t for t in catalog['items'] if t.get('repo')]
    valid={t['id'] for t in tasks}
    records={r['id']:dict(r) for r in previous.get('releases',[]) if r.get('task') in valid}
    errors=[];succeeded=0
    for t in tasks:
        try:
            rows=fetcher(t['repo'],token=token)
            normalized=normalize(rows,t,now)
            for row in normalized:
                # Preserve original first observation to avoid changing old items on every run.
                if row['id'] in records:row['observed_at']=records[row['id']]['observed_at']
                records[row['id']]=row
            succeeded+=1
        except (FetchError,ValueError) as e:
            errors.append({'task':t['id'],'repo':t['repo'],'at':now,'message':str(e)[:160]})
    return {'last_attempt':now,'last_success':now if succeeded==len(tasks) and tasks else previous.get('last_success'),
        'repositories_succeeded':succeeded,'repositories_total':len(tasks),
        'releases':sorted(records.values(),key=lambda r:r['published_at'],reverse=True)[:500],
        'errors':errors,'note':'Official release metadata only. Capability assessments require editorial review.'}

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog',type=Path,default=ROOT/'data/catalog.json')
    p.add_argument('--out',type=Path,default=ROOT/'data/upstream.json')
    args=p.parse_args()
    catalog=json.loads(args.catalog.read_text(encoding='utf-8'))
    previous=json.loads(args.out.read_text(encoding='utf-8')) if args.out.exists() else {}
    data=collect(catalog,previous,token=os.environ.get('GITHUB_TOKEN',''))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    temp=args.out.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(args.out)
    print(f'Repositories: {data["repositories_succeeded"]}/{data["repositories_total"]}; release records: {len(data["releases"])}; errors: {len(data["errors"])}')
    return 0 if not data['errors'] else 2
if __name__=='__main__':sys.exit(main())
