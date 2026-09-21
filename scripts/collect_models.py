"""Optional official API collectors. Disabled by default; no website scraping.

AA API key and X read access belong in GitHub Actions secrets, not this repo.
The X collector creates unreviewed candidates only; never changes curated events.
Transport is injected for offline tests. No third-party dependency required.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, math, os, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from model_data import validate_models, validate_resets, instant

ROOT=Path(__file__).resolve().parents[1]
AA_URL='https://artificialanalysis.ai/api/v2/data/llms/models'
X_ROOT='https://api.x.com/2'
MAX_BYTES=5_000_000

class FetchFailure(Exception):pass
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise FetchFailure('redirect_refused')

def fetch_json(url,headers):
    if not (url==AA_URL or url.startswith(X_ROOT+'/')):raise FetchFailure('endpoint_not_allowed')
    req=Request(url,headers={'Accept':'application/json','User-Agent':'FrontierLog/0.4 (official API reader)',**headers})
    try:
        with build_opener(NoRedirect).open(req,timeout=25) as r:
            if r.status!=200:raise FetchFailure('http_'+str(r.status))
            raw=r.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:raise FetchFailure('response_too_large')
            return json.loads(raw)
    except HTTPError as e:raise FetchFailure('http_'+str(e.code)) from None
    except (URLError,TimeoutError):raise FetchFailure('network_error') from None
    except (UnicodeDecodeError,json.JSONDecodeError):raise FetchFailure('invalid_json') from None

def timestamp(now):return now.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
def due(h,now,hours):
    if not h.get('last_success'):return True
    return now-instant(h['last_success'])>=timedelta(hours=max(1,float(hours)))
def safe_error(e):
    # Never log an arbitrary exception/request, which might embed an API key.
    if isinstance(e,FetchFailure) and re.fullmatch('[a-z_0-9]{1,48}',str(e)):return str(e)
    return 'invalid_response' if isinstance(e,(ValueError,KeyError,TypeError)) else 'collector_error'
def number(v):
    return v if type(v) in (float,int) and math.isfinite(v) and v>=0 else None

def normalize_aa(payload,checked):
    if not isinstance(payload,dict) or not isinstance(payload.get('data'),list):raise ValueError('Invalid API schema')
    rows=[];seen=set()
    for index,x in enumerate(payload['data']):
        if not isinstance(x,dict):raise ValueError('Invalid API row')
        stable=x.get('id');name=x.get('name');creator=x.get('model_creator')
        if not isinstance(stable,str) or not stable or not isinstance(name,str) or not name:raise ValueError('Missing API identity')
        if stable in seen:raise ValueError('Duplicate API identity')
        seen.add(stable)
        # Hash the stable ID, not the mutable display name. Avoid duplicate configurations.
        rid='aa-api-'+hashlib.sha256(stable.encode()).hexdigest()[:24]
        if not isinstance(creator,dict) or not isinstance(creator.get('name'),str):raise ValueError('Missing creator')
        ev=x.get('evaluations') or {};p=x.get('pricing') or {}
        if not isinstance(ev,dict) or not isinstance(p,dict):raise ValueError('Invalid evaluation')
        rows.append(dict(id=rid,upstream_id=stable,name=name,maker=creator['name'],
            intelligence=number(ev.get('artificial_analysis_intelligence_index')),
            coding=number(ev.get('artificial_analysis_coding_index')),
            math=number(ev.get('artificial_analysis_math_index')),
            speed=number(x.get('median_output_tokens_per_second')),
            input_price=number(p.get('price_1m_input_tokens')),
            output_price=number(p.get('price_1m_output_tokens')),
            cost_task=None,context=None,source_rank=None,source_order=index,
            score_error=None,rank_spread=None,votes=None,preliminary=False,source='aa-api'))
    if not rows or len(rows)>3000 or not any(r['intelligence'] is not None for r in rows):raise ValueError('Empty or unusable snapshot')
    return dict(id='aa',title='综合能力',provider='Artificial Analysis',metric='intelligence',
        as_of=None,checked=checked,methodology='Intelligence Index · 当前 API 口径（版本见原站）',
        mode='authorized_api',source='aa-api',scope=f'官方 API 返回 {len(rows)} 个配置；不与旧版指数拼接。缺失值留空，价格单位为 USD / 1M Token。',rows=rows)

def collect_aa(data,config,key,now,transport=fetch_json,force=False):
    out=copy.deepcopy(data);h=out['sync']
    if not config.get('enabled'):
        # Explicit opt-in protects API budget and existing valid snapshots.
        return out
    if not key:
        h.update(status='not_configured',note='AA 采集已配置，但未提供 ARTIFICIAL_ANALYSIS_API_KEY。')
        return out
    if not force and not due(h,now,config.get('ttl_hours',24)):return out
    h.update(last_attempt=timestamp(now),error=None)
    try:
        board=normalize_aa(transport(AA_URL,{'x-api-key':key}),now.date().isoformat())
        candidate=copy.deepcopy(out);candidate['boards']=[board if b['id']=='aa' else b for b in candidate['boards']]
        candidate['checked']=now.date().isoformat()
        for s in candidate['sources']:
            if s['id']=='aa-api':s['checked']=candidate['checked']
        candidate['sync'].update(status='success',last_success=timestamp(now),error=None,note='已通过官方 API 更新 AA 快照；Arena 保持独立人工快照。')
        validate_models(candidate);return candidate
    except Exception as e:
        h.update(status='error',error=safe_error(e),note='本次未获得有效的新模型数据，保留上一份有效快照。')
        return out

RESET_WORDS=re.compile(r'\b(reset(?:s|ting)?|banked|limits?|quotas?)\b',re.I)
BANKED=re.compile(r'\b(banked|cards?|redeem|reset to use|reset for later)\b',re.I)
FUTURE=re.compile(r'\b(will|soon|tomorrow|next|plan(?:ning)?|tuesday|monday|wednesday|thursday|friday|weekend)\b',re.I)
NEGATIVE=re.compile(r"\b(not|never|no)\b.{0,25}\breset|\bdidn[’']t\b",re.I)

def classify_post(x,account,observed):
    """Heuristic routing ONLY, never confirmation. Replies are retained as candidates."""
    if not isinstance(x,dict):raise ValueError('Invalid post')
    content=x.get('text')
    pid=x.get('id')
    if not isinstance(content,str) or not re.fullmatch(r'\d{1,30}',str(pid)):raise ValueError('Invalid post identity')
    if not RESET_WORDS.search(content):return None
    created=x.get('created_at');instant(created)
    kind='banked' if BANKED.search(content) else 'announcement' if FUTURE.search(content) else 'global'
    reason='关键词命中，需核对完整上下文和适用账号'
    if NEGATIVE.search(content) or '?' in content:reason='含否定或疑问表达，不能据此认定发生了重置'
    return dict(id='x-'+pid,post_id=pid,account=account,url=f'https://x.com/{account}/status/{pid}',
        published_at=created,observed_at=observed,excerpt=content[:240],candidate_kind=kind,
        review_status='pending',reason=reason,conversation_id=x.get('conversation_id'),
        references=x.get('referenced_tweets',x.get('referenced_posts',[])))

def collect_x(data,config,key,now,transport=fetch_json,force=False):
    out=copy.deepcopy(data);h=out['sync']
    if not config.get('enabled'):return out
    if not key:
        h.update(status='not_configured',note='X 采集已配置，但未提供 X_BEARER_TOKEN 或对应接口权限。');return out
    if not force and not due(h,now,config.get('ttl_hours',1)):return out
    h.update(last_attempt=timestamp(now),error=None)
    handle=config.get('username','thsottiaux')
    if handle!=data['account']:raise ValueError('Collector handle must match configured public account')
    try:
        headers={'Authorization':'Bearer '+key}
        user=transport(X_ROOT+'/users/by/username/'+handle,headers).get('data')
        if not isinstance(user,dict) or user.get('username','').lower()!=handle.lower() or not re.fullmatch(r'\d{1,30}',str(user.get('id'))):raise ValueError('Wrong user')
        staged={e['id']:e for e in out.get('inbox',[])}
        max_pages=max(1,min(5,int(config.get('max_pages',3))));page_token=None;newest=None;incomplete=False
        params={'max_results':100,'tweet.fields':'created_at,author_id,conversation_id','exclude':'retweets'}
        # Do NOT exclude replies: reset plans are often in reply threads.
        if h.get('cursor'):params['since_id']=h['cursor']
        for p in range(max_pages):
            if page_token:params['pagination_token']=page_token
            body=transport(X_ROOT+'/users/'+str(user['id'])+'/tweets?'+urlencode(params),headers)
            if not isinstance(body,dict) or body.get('errors'):raise ValueError('Incomplete X response')
            posts=body.get('data',[]);meta=body.get('meta')
            if not isinstance(posts,list) or not isinstance(meta,dict):raise ValueError('Invalid posts response')
            for x in posts:
                if str(x.get('author_id'))!=str(user['id']):raise ValueError('Wrong post author')
                candidate=classify_post(x,handle,timestamp(now))
                if candidate:staged.setdefault(candidate['id'],candidate)
                if newest is None or int(x['id'])>int(newest):newest=x['id']
            page_token=meta.get('next_token')
            if not page_token:break
        if page_token:incomplete=True
        out['inbox']=sorted(staged.values(),key=lambda e:e['published_at'],reverse=True)[:3000]
        # Keep old cursor if page budget was exceeded, so unseen posts are not skipped.
        if not incomplete and newest:h['cursor']=newest
        h.update(status='partial' if incomplete else 'success',
                 note='分页预算已到，仅保存候选，游标不前进。' if incomplete else '官方接口已读取；候选仍待人工核验，不代表账号已重置。')
        if not incomplete:h['last_success']=timestamp(now)
        # checked is the human review date of curated records, not collection time.
        validate_resets(out);return out
    except Exception as e:
        # On any malformed later page, discard staged partial candidates but keep source health.
        original=copy.deepcopy(data);original['sync'].update(last_attempt=timestamp(now),status='error',error=safe_error(e),note='本次抓取失败，保留既有公告与候选。')
        return original

def atomic_json(path,data):
    encoded=json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if path.read_text(encoding='utf-8')==encoded:return False
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(encoded,encoding='utf-8');tmp.replace(path);return True

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--only',choices=['aa','x','all'],default='all');p.add_argument('--force',action='store_true',help='Bypass cache TTL, but not opt-in or credential checks');args=p.parse_args()
    cfg=json.loads((ROOT/'data/model-sync.json').read_text());now=datetime.now(timezone.utc)
    failed=False
    for key,file,fn,secret,validator in [('aa','models.json',collect_aa,'ARTIFICIAL_ANALYSIS_API_KEY',validate_models),('x','resets.json',collect_x,'X_BEARER_TOKEN',validate_resets)]:
        if args.only not in (key,'all'):continue
        path=ROOT/'data'/file;data=json.loads(path.read_text());validator(data)
        out=fn(data,cfg[key],os.getenv(secret,''),now,force=args.force);validator(out);atomic_json(path,out)
        print(key+': '+out['sync']['status']+(' (opt-in disabled)' if not cfg[key].get('enabled') else ''))
        failed|=out['sync']['status']=='error'
    return int(failed)
if __name__=='__main__':raise SystemExit(main())
