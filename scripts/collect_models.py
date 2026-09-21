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

RESET_WORDS=re.compile(r'\b(reset(?:s|ting|ted)?|banked|limits?|quotas?|usage)\b',re.I)
BANKED=re.compile(r'\b(banked|cards?|redeem|save(?:d)? for later|reset to use)\b',re.I)
FUTURE=re.compile(r'\b(will|soon|tomorrow|next|plan(?:ning)?|later|tuesday|monday|wednesday|thursday|friday|weekend|in ~?\d+ hours?)\b',re.I)
COMPLETED=re.compile(r'\b(reset(?:ted)?|all reset|has been reset|have now reset|completed|done)\b',re.I)
PROPAGATED=re.compile(r'\b(propagat(?:ed|ing)|rolled? out|landed|reached accounts?|for everyone)\b',re.I)
FIXES=re.compile(r'\b(fix(?:ed|es)?|compaction|background requests?|token usage|consumption|usage limits?|capacity|bug|regression)\b',re.I)
NEGATIVE=re.compile(r"\b(not|never|no)\b.{0,30}\b(reset|limits?)|\bdidn[’']t\b",re.I)
TIME_HINT=re.compile(r'\b(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)?|monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|tonight|morning|afternoon)\b',re.I)

def semantic_reset_reading(content,context=''):
    """Conservative semantic routing for a public post + referenced context.

    This never turns a candidate into a confirmed event. It only helps reviewers
    understand what kind of claim the post appears to make.
    """
    c=content.strip();ctx=(context or '').strip();joined=(c+' '+ctx).strip()
    has_reset=bool(RESET_WORDS.search(joined))
    if not has_reset:return None
    if NEGATIVE.search(c):
        return ('announcement','denial','high',
            '这句话在否认或限制重置相关说法，应该作为纠正信息阅读。',
            '不能据此认定发生了重置，也不能把被否认的说法继续当作预告。')
    if BANKED.search(joined):
        if COMPLETED.search(c) or re.search(r'\b(give|provided?|land(?:ed)?)\b',c,re.I):
            return ('banked','banked_delivery','high',
                '这更像在说一张可留待主动使用的 banked reset 已发放或正在发放。',
                'banked reset 不等于额度已经自动恢复；资格、到账与过期时间仍以个人账号为准。')
        return ('banked','banked_announcement','medium',
            '这更像 banked reset 的安排或说明，而不是一次全局额度已经刷新。',
            '不能把“会发卡”写成“额度已自动重置”。')
    if PROPAGATED.search(c) and RESET_WORDS.search(c):
        return ('global','propagation_complete','high',
            '这句话更像在确认一次全局重置已经传播到目标账号，而不是单纯预告。',
            '仍不能证明每个具体账号的页面已经即时刷新，也不能外推到未写明的套餐。')
    if COMPLETED.search(c) and RESET_WORDS.search(c) and not FUTURE.search(c):
        return ('global','reset_executed','high',
            '这句话更像在确认重置动作已经执行。',
            '仍要核对适用套餐/产品范围；执行完成不等于所有客户端 UI 同时更新。')
    if FIXES.search(joined) and RESET_WORDS.search(joined):
        return ('announcement','usage_explanation','medium',
            '重点可能不是“送一次额度”，而是在解释为什么用量异常、修了哪些计费/上下文问题，以及是否用重置作补偿。',
            '不能只摘出 reset 一词而忽略修复范围，也不能把性能/用量改善外推到所有工作流。')
    if FUTURE.search(c) and RESET_WORDS.search(joined):
        return ('announcement','explicit_announcement','medium',
            '这更像未来安排或时间预告；需要等待后续“已执行/已传播”证据。',
            '预告时间到了也不会自动升级成“已经重置”。')
    if TIME_HINT.search(c) and RESET_WORDS.search(ctx):
        return ('announcement','timing_hint','low',
            '这是一条依赖上文才能理解的时间暗示，可能在回答“什么时候重置”，但正文没有独立确认 reset、时区或适用范围。',
            '不能把含糊时间直接换算成确定的重置时刻；必须保留回复对象、时区不确定性和后续确认状态。')
    if RESET_WORDS.search(c):
        return ('announcement','reset_related','low',
            '帖子与 reset / usage limit 有关，但仅凭这一句不足以判断是预告、执行完成还是解释。',
            '需要读取回复链、引用帖和后续更新，不能自动认定重置发生。')
    return None

def classify_post(x,account,observed,context_text=''):
    """Semantic routing ONLY, never confirmation. Replies/quotes stay pending."""
    if not isinstance(x,dict):raise ValueError('Invalid post')
    content=x.get('text');pid=x.get('id')
    if not isinstance(content,str) or not re.fullmatch(r'\d{1,30}',str(pid)):raise ValueError('Invalid post identity')
    created=x.get('created_at');instant(created)
    reading=semantic_reset_reading(content,context_text)
    if reading is None:return None
    kind,speech,strength,interpretation,not_proves=reading
    refs=x.get('referenced_tweets',x.get('referenced_posts',[]))
    return dict(id='x-'+str(pid),post_id=str(pid),account=account,url=f'https://x.com/{account}/status/{pid}',
        published_at=created,observed_at=observed,excerpt=content[:240],candidate_kind=kind,
        semantic_type=speech,evidence_strength=strength,interpretation=interpretation,
        not_proves=not_proves,context_excerpt=(context_text or '')[:240],
        review_status='pending',reason='语义分类只帮助人工复核，不自动升级为确认事件',
        conversation_id=x.get('conversation_id'),references=refs)

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
        params={'max_results':100,'tweet.fields':'created_at,author_id,conversation_id,referenced_tweets,in_reply_to_user_id','expansions':'referenced_tweets.id','exclude':'retweets'}
        # Do NOT exclude replies: reset plans are often in reply threads.
        if h.get('cursor'):params['since_id']=h['cursor']
        for p in range(max_pages):
            if page_token:params['pagination_token']=page_token
            body=transport(X_ROOT+'/users/'+str(user['id'])+'/tweets?'+urlencode(params),headers)
            if not isinstance(body,dict) or body.get('errors'):raise ValueError('Incomplete X response')
            posts=body.get('data',[]);meta=body.get('meta')
            if not isinstance(posts,list) or not isinstance(meta,dict):raise ValueError('Invalid posts response')
            includes=body.get('includes') or {};context_map={str(t.get('id')):t.get('text','') for t in includes.get('tweets',[]) if isinstance(t,dict)}
            for x in posts:
                if str(x.get('author_id'))!=str(user['id']):raise ValueError('Wrong post author')
                refs=x.get('referenced_tweets') or []
                context='\n'.join(context_map.get(str(ref.get('id')),'') for ref in refs if isinstance(ref,dict))
                candidate=classify_post(x,handle,timestamp(now),context)
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
