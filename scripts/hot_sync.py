"""Build a two-hour hot-candidate inbox from already verified FrontierLog data.

Network-free by design: upstream workflows collect public sources first. This
script aggregates those verified records, records shadow publish|merge|hold
decisions, and never invents a heat score or auto-rewrites curated hot items.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

ROOT=Path(__file__).resolve().parents[1]

def load(name):
    return json.loads((ROOT/'data'/name).read_text(encoding='utf-8'))

def stamp(now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None: now=now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

def parse_day(raw):
    try:return datetime.fromisoformat(str(raw)[:10]).date()
    except Exception:return None

def canonical(raw):
    try:
        u=urlparse(str(raw))
        if u.scheme!='https' or not u.hostname or u.username or u.password:return ''
        path=re.sub(r'/+$','',u.path or '')
        return urlunparse(('https',u.hostname.lower(),path,'','',''))
    except Exception:return ''

def norm_title(v):
    return re.sub(r'[^0-9a-z\u4e00-\u9fff]+','',str(v).lower())

def cid(category,url,published,title):
    raw='|'.join([category,canonical(url),published,norm_title(title)])
    return 'candidate-'+hashlib.sha1(raw.encode()).hexdigest()[:16]

def authority(kind='',publisher=''):
    q=(str(kind)+' '+str(publisher)).lower()
    if any(x in q for x in ('官方','official','作者研究','公司公告','company')):return 1.0
    if any(x in q for x in ('independent','独立','论文','paper')):return .88
    return .72

def freshness(published,now):
    d=parse_day(published)
    if not d:return 0.0
    age=(now.date()-d).days
    if age<0:return 0.0
    return max(0.0,1.0-age/14.0)

def impact(category):
    return {'model':.94,'benchmark':.94,'industry':.9,'product':.86,'research':.82}.get(category,.76)

def collect_candidates(now=None):
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    hot=load('hot.json'); products=load('product-radar.json'); catalog=load('catalog.json')
    models=load('models.json'); industry=load('industry.json'); activity=load('activity-radar.json')
    existing_urls={canonical(x.get('url')) for x in hot.get('items',[]) if canonical(x.get('url'))}
    existing_titles={norm_title(x.get('title')) for x in hot.get('items',[])}
    rows=[]
    def add(category,published,title,summary,why,boundary,source,source_kind,url,publishable=False,extra=None):
        d=parse_day(published)
        if not d or d>now.date() or (now.date()-d).days>14:return
        u=canonical(url)
        if not u:return
        duplicate=u in existing_urls or norm_title(title) in existing_titles
        a=authority(source_kind,source); f=freshness(published,now); im=impact(category); nov=.15 if duplicate else 1.0
        score=round(.30*f+.27*a+.27*im+.16*nov,3)
        action='merge' if duplicate else ('publish' if publishable and score>=.78 else 'hold')
        reason='已有同源热点，建议合并更新。' if duplicate else ('一手证据、时效和影响达到 shadow 发布阈值；仍需编辑确认标题与热度。' if action=='publish' else '保留候选，等待更强证据、影响或更新。')
        rows.append({'id':cid(category,u,str(published),title),'category':category,'published':str(published),
          'title':str(title),'summary':str(summary),'why':str(why),'boundary':str(boundary),
          'source':str(source),'source_kind':str(source_kind),'url':u,'publishable':bool(publishable),
          'features':{'freshness':round(f,3),'authority':round(a,3),'impact':round(im,3),'novelty':round(nov,3)},
          'priority_score':score,'action':action,'reason':reason,**(extra or {})})
    for p in products.get('items',[]):
        for e in p.get('timeline',[]):
            rich=e.get('evidence_level')=='primary_source' and bool(e.get('verified_at'))
            add('product',e.get('date'),e.get('title'),e.get('summary') or p.get('summary',''),
                e.get('interpretation') or '产品出现新的公开变化。',e.get('limitations') or p.get('boundary',''),
                p.get('company') or p.get('name'),'官方产品节点' if rich else '已收录产品节点',e.get('url'),
                publishable=rich and all(e.get(k) for k in ('summary','interpretation','limitations')),
                extra={'product_id':p.get('id')})
    srcs={x.get('id'):x for x in industry.get('sources',[])}
    for arow in industry.get('articles',[]):
        src=next((srcs.get(i) for i in arow.get('sources',[]) if srcs.get(i)),None)
        if not src:continue
        sk=src.get('kind',''); official=authority(sk,src.get('publisher'))>=.98
        add('industry',arow.get('published'),arow.get('title'),arow.get('summary'),arow.get('why'),arow.get('boundary'),
            src.get('publisher','行业来源'),sk,src.get('url'),publishable=official)
    csrc={x.get('id'):x for x in catalog.get('sources',[])}; tasks={x.get('id'):x for x in catalog.get('items',[])}
    for e in catalog.get('events',[]):
        t=tasks.get(e.get('task')); src=next((csrc.get(i) for i in e.get('sources',[]) if csrc.get(i)),None)
        if not t or not src:continue
        cat='research' if e.get('kind')=='research' or t.get('status')=='research' else 'product'
        off=authority(src.get('kind'),src.get('publisher'))>=.98
        add(cat,e.get('date'),e.get('title'),e.get('summary'),e.get('delta'),t.get('boundary'),
            src.get('publisher',t.get('name')),src.get('kind','公开资料'),src.get('url'),
            publishable=off and e.get('kind')=='release',extra={'task_id':t.get('id')})
    msrc={x.get('id'):x for x in models.get('sources',[])}
    for track in models.get('frontier_tracks',[]):
        for x in track.get('items',[]):
            src=next((msrc.get(i) for i in x.get('sources',[]) if msrc.get(i)),None)
            if not src:continue
            cat='research' if x.get('status')=='research' or track.get('id')=='neo-labs' else 'model'
            add(cat,x.get('date'),x.get('name'),x.get('summary'),track.get('description'),
                '不同评测、机器人或任务不可直接用单一分数外推；研究演示和 early access 也不等于稳定生产能力。',
                src.get('publisher',x.get('maker')),src.get('kind','公开来源'),src.get('url'),False,
                extra={'track_id':track.get('id'),'maker':x.get('maker')})
    asrc={x.get('id'):x for x in activity.get('sources',[])}
    for m in activity.get('media_items',[]):
        src=asrc.get(m.get('source_id'))
        if not src or src.get('authority')!='official' or src.get('kind')!='technical':continue
        add('research',m.get('published'),m.get('title'),m.get('summary'),'官方技术文章出现新的能力或系统信号。',
            '技术文章本身不等于产品已经普遍上线，也不构成本站独立复现。',
            src.get('publisher',src.get('name')),'官方技术博客',m.get('url'),False)
    unique={}
    for row in rows:
        old=unique.get(row['id'])
        if old is None or row['priority_score']>old['priority_score']:unique[row['id']]=row
    return sorted(unique.values(),key=lambda x:(x['action']!='publish',-x['priority_score'],x['published'],x['id']))

def evaluate(now=None,previous=None):
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc); ts=stamp(now)
    previous=previous or {}
    first={x.get('id'):x.get('first_seen_at') for x in previous.get('candidates',[])}
    rows=collect_candidates(now)
    for x in rows:x['first_seen_at']=first.get(x['id']) or ts
    counts={k:sum(1 for x in rows if x['action']==k) for k in ('publish','merge','hold')}
    inbox={'version':1,'generated_at':ts,'mode':'shadow','automatic_publish':False,
      'note':'候选只来自站内已核验结构化数据；publish / merge / hold 为影子决策，不等于热点已发布。',
      'counts':counts,'candidates':rows[:40]}
    decision={'action':'publish' if counts['publish'] else ('merge' if counts['merge'] else 'hold'),
      'candidate_count':len(rows),'publish_ready_count':counts['publish'],'merge_count':counts['merge'],
      'best_candidate':rows[0]['id'] if rows else None,
      'reason':'存在达到严格阈值的一手候选，等待编辑确认标题与热度。' if counts['publish'] else ('发现与现有热点同源的新节点，建议合并。' if counts['merge'] else '本轮没有达到发布阈值的新增候选。')}
    return inbox,decision

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--now',default='');args=ap.parse_args()
    now=datetime.fromisoformat(args.now.replace('Z','+00:00')) if args.now else datetime.now(timezone.utc)
    old_path=ROOT/'data/hot-inbox.json'
    previous=json.loads(old_path.read_text(encoding='utf-8')) if old_path.exists() else {}
    inbox,decision=evaluate(now,previous);ts=stamp(now)
    hot=load('hot.json');policy=load('hot-policy.json')
    hot['checked']=now.astimezone(timezone.utc).date().isoformat()
    hot['sync']={'last_checked_at':ts,'status':'success','mode':'shadow',
      'candidate_count':decision['candidate_count'],'publish_ready_count':decision['publish_ready_count'],
      'note':'自动候选采集已完成；热点正文和热度仍保持人工 / 高门槛精选。'}
    policy['status']='shadow-running';policy['last_evaluated']=ts;policy['last_decision']=decision
    (ROOT/'data/hot.json').write_text(json.dumps(hot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'data/hot-policy.json').write_text(json.dumps(policy,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    old_path.write_text(json.dumps(inbox,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('hot sync:',len(inbox['candidates']),'candidates;',decision['publish_ready_count'],'publish-ready; decision',decision['action'])

if __name__=='__main__':main()
