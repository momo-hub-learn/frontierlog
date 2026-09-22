'use strict';
(()=>{
let loading=false;
const strengthLabel={high:'强',medium:'中',low:'低'};
const semanticLabel={timing_hint:'时间暗示',explicit_announcement:'明确预告',reset_executed:'已执行表述',propagation_complete:'传播完成',banked_delivery:'重置卡发放',banked_announcement:'重置卡预告',usage_explanation:'用量/修复解释',denial:'否认/纠正',reset_related:'重置相关'};
function when(x){const raw=x.published_at||x.observed_at||'';if(raw){try{return new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(raw))+' 北京时间'}catch{}}return x.date||'时间未核验'}
function signalRows(){const events=RESET_DATA.events.filter(x=>x.interpretation||x.original_text).map(x=>({...x,_source:'event'}));const inbox=(RESET_DATA.inbox||[]).filter(x=>x.interpretation).map(x=>({...x,_source:'inbox',title:x.title||'Tibo 新帖候选',original_text:x.excerpt,not_proves:x.not_proves||x.reason}));return [...events,...inbox].sort((a,b)=>String(b.published_at||b.date||'').localeCompare(String(a.published_at||a.date||''))).slice(0,8)}
function sourceFor(x){const ids=Array.isArray(x.sources)?x.sources:[];const candidates=ids.map(id=>RESET_DATA.sources.find(s=>s.id===id)).filter(Boolean);return candidates.find(s=>/x\.com\/thsottiaux\/status\//.test(s.url||''))||candidates.find(s=>/Tibo\s*\/\s*X/i.test(s.publisher||''))||candidates[0]||null}
function originalUrl(x){const s=sourceFor(x);if(s?.url)return safeLink(s.url);if(x.url)return safeLink(x.url);if(x.post_id)return safeLink('https://x.com/thsottiaux/status/'+x.post_id);return '#'}
function relationLabel(x){if(x.relation==='reply')return '回复 @'+(x.reply_to_account||'上文');if(x.relation==='quote')return '引用帖'+(x.quote_of_id?' · '+x.quote_of_id:'');return '原帖'}
function sourceState(x){const s=sourceFor(x);return s?((s.publisher||'来源')+' · '+(s.kind||'公开记录')):'来源待补'}
function evidenceShot(x){
  const url=originalUrl(x),hasUrl=url!=='#';
  return '<figure class="tibo-evidence-shot">'+
    '<div class="tibo-shot-bar"><span class="tibo-shot-label">原帖证据 · 文本快照</span><span class="tibo-shot-x">X</span></div>'+
    '<div class="tibo-shot-author"><span class="tibo-shot-avatar" aria-hidden="true">T</span><span><b>Tibo</b><small>@thsottiaux</small></span><time>'+esc(when(x))+'</time></div>'+
    '<blockquote>'+esc(x.original_text||x.excerpt||x.summary||'')+'</blockquote>'+
    '<div class="tibo-shot-meta"><span>'+esc(relationLabel(x))+'</span>'+(x.post_id?'<code>'+esc(x.post_id)+'</code>':'')+'</div>'+
    '<figcaption><span>'+esc(sourceState(x))+'</span>'+(hasUrl?'<a href="'+url+'" target="_blank" rel="noopener noreferrer">打开 X 原帖 '+icon('external')+'</a>':'')+'</figcaption>'+
  '</figure>'
}
function readingPanel(x){
  return '<div class="tibo-inference">'+
    '<div class="tibo-inference-head"><span>'+esc(semanticLabel[x.semantic_type]||RESET_KINDS[x.kind]||'待分类')+'</span><b>证据强度 '+esc(strengthLabel[x.evidence_strength]||'待评估')+'</b></div>'+
    '<section><strong>我们理解</strong><p>'+esc(x.interpretation||x.summary||'')+'</p></section>'+
    (x.conversation_context?'<section class="context"><strong>上下文</strong><p>'+esc(x.conversation_context)+'</p></section>':'')+
    '<section class="limit"><strong>仍不能推出什么</strong><p>'+esc(x.not_proves||x.boundary||x.reason||'需要更多上下文。')+'</p></section>'+
    '<footer>'+(x._source==='event'?'<button data-ma="reset-detail" data-id="'+esc(x.id)+'">查看完整记录 '+icon('arrow')+'</button>':'<span>机器候选 · 待核验</span>')+'</footer>'+
  '</div>'
}
function intelBlock(){const rows=signalRows();if(!rows.length)return '';return '<section class="tibo-intel"><div class="tibo-intel-head"><div><p class="eyebrow">TIBO / EVIDENCE → INFERENCE</p><h2>先看原话和上下文，再看我们的判断。</h2><p>左边是按已收录原文生成的证据快照，右边才是推断。快照不是伪造的 X 截图；能定位原帖时保留直达链接，确认状态仍只接受 Tibo 原帖或 OpenAI 官方说明。</p></div><a href="'+safeLink(RESET_DATA.profile_url)+'" target="_blank" rel="noopener">@thsottiaux '+icon('external')+'</a></div><div class="tibo-evidence-list">'+rows.map(x=>'<article class="tibo-evidence-card '+esc(x.evidence_strength||'low')+'"><div class="tibo-evidence-col"><p class="tibo-col-label">EVIDENCE / 证据</p>'+evidenceShot(x)+'</div><div class="tibo-inference-col"><p class="tibo-col-label">INFERENCE / 推断</p>'+readingPanel(x)+'</div></article>').join('')+'</div></section>'}
const baseResetPage=resetPage;
resetPage=function(){const html=baseResetPage();const block=intelBlock();return block?html.replace('<div class="m-controls">',block+'<div class="m-controls">'):html};
async function refreshTibo(){if(loading||!['http:','https:'].includes(location.protocol))return;loading=true;try{const u=new URL('api/v1/resets.json',location.href.split('#')[0]);const r=await fetch(u,{cache:'no-store',credentials:'omit'});if(!r.ok)throw new Error('HTTP '+r.status);const obj=await r.json();if(!obj||!Array.isArray(obj.events)||!Array.isArray(obj.inbox))throw new Error('invalid');RESET_DATA=obj;if(state.view==='tibo'){lastMain='';moduleMain()}}catch(e){console.warn('Tibo snapshot refresh failed',e)}finally{loading=false}}
window.addEventListener('hashchange',()=>{if(location.hash.startsWith('#/tibo'))refreshTibo()});
if(state.view==='tibo')refreshTibo();
})();