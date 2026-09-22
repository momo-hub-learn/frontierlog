'use strict';
(()=>{
let loading=false,xWidgetsPromise=null;
const strengthLabel={high:'强',medium:'中',low:'低'};
const semanticLabel={timing_hint:'时间暗示',explicit_announcement:'明确预告',reset_executed:'已执行表述',propagation_complete:'传播完成',banked_delivery:'重置卡发放',banked_announcement:'重置卡预告',usage_explanation:'用量/修复解释',denial:'否认/纠正',reset_related:'重置相关',non_reset_context:'无关 / 误读纠正'};
function when(x){const raw=x.published_at||x.observed_at||'';if(raw){try{return new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(raw))+' 北京时间'}catch{}}return x.date||'时间未核验'}
function signalRows(){const events=RESET_DATA.events.filter(x=>x.interpretation||x.original_text).map(x=>({...x,_source:'event'}));const inbox=(RESET_DATA.inbox||[]).filter(x=>x.interpretation).map(x=>({...x,_source:'inbox',title:x.title||'Tibo 新帖候选',original_text:x.excerpt,not_proves:x.not_proves||x.reason}));return [...events,...inbox].sort((a,b)=>String(b.published_at||b.date||'').localeCompare(String(a.published_at||a.date||''))).slice(0,8)}
function sourceFor(x){const ids=Array.isArray(x.sources)?x.sources:[];const candidates=ids.map(id=>RESET_DATA.sources.find(s=>s.id===id)).filter(Boolean);return candidates.find(s=>/x\.com\/thsottiaux\/status\//.test(s.url||''))||candidates.find(s=>/Tibo\s*\/\s*X/i.test(s.publisher||''))||candidates[0]||null}
function originalUrl(x){const s=sourceFor(x);if(s?.url)return safeLink(s.url);if(x.url)return safeLink(x.url);if(x.post_id)return safeLink('https://x.com/thsottiaux/status/'+x.post_id);return '#'}
function relationLabel(x){if(x.relation==='reply')return '回复 @'+(x.reply_to_account||'上文');if(x.relation==='quote')return '引用帖'+(x.quote_of_id?' · '+x.quote_of_id:'');return '原帖'}
function sourceState(x){const s=sourceFor(x);return s?((s.publisher||'来源')+' · '+(s.kind||'公开记录')):'来源待补'}
function fallbackQuote(x,url,message='X 原帖当前无法嵌入'){return '<div class="tibo-x-fallback"><strong>'+esc(message)+'</strong><p>下面只显示本站保存的原文摘录，不模拟 X 界面。</p><blockquote>'+esc(x.original_text||x.excerpt||x.summary||'')+'</blockquote>'+(url!=='#'?'<a href="'+url+'" target="_blank" rel="noopener noreferrer">直接打开 X 原帖 '+icon('external')+'</a>':'')+'</div>'}
function evidencePanel(x){
  const url=originalUrl(x),canEmbed=Boolean(x.post_id)&&url!=='#';
  const body=canEmbed?'<div class="tibo-x-embed" data-x-post-id="'+esc(x.post_id)+'" data-x-url="'+url+'"><div class="tibo-x-loading"><span>正在载入 X 官方原帖…</span><a href="'+url+'" target="_blank" rel="noopener noreferrer">直接打开 '+icon('external')+'</a></div></div>':fallbackQuote(x,url,'没有可嵌入的 X 原帖 ID');
  return '<div class="tibo-evidence-source">'+body+'<div class="tibo-source-meta"><span>'+esc(relationLabel(x))+'</span>'+(x.post_id?'<code>'+esc(x.post_id)+'</code>':'')+'<small>'+esc(sourceState(x))+'</small></div></div>'
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
function featuredSignal(){
  const ranked=RESET_DATA.events.filter(x=>x.post_id&&x.original_text).map(x=>({...x,_source:'event'})).sort((a,b)=>{
    const sem={propagation_complete:6,reset_executed:5,banked_delivery:4,explicit_announcement:3,usage_explanation:2,timing_hint:1,non_reset_context:0};
    const status={confirmed:3,announced:2,pending:1};
    const strength={high:3,medium:2,low:1};
    return (sem[b.semantic_type]||0)-(sem[a.semantic_type]||0)||(status[b.status]||0)-(status[a.status]||0)||(strength[b.evidence_strength]||0)-(strength[a.evidence_strength]||0)||String(b.published_at||b.date||'').localeCompare(String(a.published_at||a.date||''))
  });
  return ranked[0]||null
}
function featuredHero(){
  const x=featuredSignal();if(!x)return '';
  const url=originalUrl(x),stamp=when(x);
  const raw=String(x.original_text||x.summary||'').trim();
  const headline=raw.length>96?raw.slice(0,93).trimEnd()+'…':raw;
  const readingRaw=String(x.interpretation||x.summary||'').trim();
  const reading=readingRaw.length>132?readingRaw.slice(0,129).trimEnd()+'…':readingRaw;
  const label=semanticLabel[x.semantic_type]||RESET_KINDS[x.kind]||'公开信号';
  return '<section class="tibo-featured">'+
    '<div class="tibo-featured-bar"><div><span class="tibo-featured-kicker">最近一次明确完成表述</span><span class="tibo-featured-status">'+esc(label)+'</span></div><time>'+esc(stamp)+'</time></div>'+
    '<div class="tibo-featured-grid">'+
      '<div class="tibo-featured-copy"><p class="eyebrow">CURRENT CONCLUSION / STRONGEST PUBLIC EVIDENCE</p>'+
      '<h2>Tibo：'+esc(headline)+'</h2>'+
      '<p class="tibo-featured-reading">'+esc(reading)+'</p>'+
      '<div class="tibo-featured-actions"><a class="tibo-featured-primary" href="'+url+'" target="_blank" rel="noopener noreferrer">打开 X 原帖 '+icon('external')+'</a><button data-ma="reset-detail" data-id="'+esc(x.id)+'">查看上下文 '+icon('arrow')+'</button></div></div>'+
      '<div class="tibo-featured-proof"><div class="tibo-featured-proof-head"><span>X 原帖截图</span><small>仅保留 Tibo 这条消息</small></div>'+
      '<div class="tibo-featured-crop"><a class="tibo-featured-shot" href="'+url+'" target="_blank" rel="noopener noreferrer"><img src="./assets/tibo/'+esc(x.post_id)+'.png" width="1200" height="300" alt="Tibo 在 X 上的原帖截图"></a></div>'+
      '<div class="tibo-featured-proof-foot"><span>点击截图打开原帖</span><span>'+esc(relationLabel(x))+'</span></div></div>'+
    '</div>'+
  '</section>'
}
function intelBlock(){const rows=signalRows();if(!rows.length)return '';return '<section class="tibo-intel"><div class="tibo-intel-head"><div><p class="eyebrow">TIBO / EVIDENCE → INFERENCE</p><h2>完整证据链：原话、上下文、推断分开看。</h2><p>头部只突出最强证据；这里保留其余原帖、回复和引用关系。X 无法加载时只显示本站保存的原文摘录与原帖链接，不模拟截图。</p></div><a href="'+safeLink(RESET_DATA.profile_url)+'" target="_blank" rel="noopener">@thsottiaux '+icon('external')+'</a></div><div class="tibo-evidence-list">'+rows.map(x=>'<article class="tibo-evidence-card '+esc(x.evidence_strength||'low')+'"><div class="tibo-evidence-col"><p class="tibo-col-label">X 官方原帖 / EVIDENCE</p>'+evidencePanel(x)+'</div><div class="tibo-inference-col"><p class="tibo-col-label">我们的推断 / INFERENCE</p>'+readingPanel(x)+'</div></article>').join('')+'</div></section>'}
function loadXWidgets(){
  if(window.twttr?.widgets?.createTweet)return Promise.resolve(window.twttr);
  if(xWidgetsPromise)return xWidgetsPromise;
  xWidgetsPromise=new Promise((resolve,reject)=>{
    const ready=()=>window.twttr?.widgets?.createTweet?resolve(window.twttr):reject(new Error('X widgets unavailable'));
    const existing=document.querySelector('script[data-frontierlog-x-widgets]');
    if(existing){existing.addEventListener('load',ready,{once:true});existing.addEventListener('error',()=>reject(new Error('X widgets blocked')),{once:true});setTimeout(()=>{if(window.twttr?.widgets?.createTweet)resolve(window.twttr)},400);return}
    const s=document.createElement('script');s.src='https://platform.twitter.com/widgets.js';s.async=true;s.charset='utf-8';s.dataset.frontierlogXWidgets='1';s.onload=ready;s.onerror=()=>reject(new Error('X widgets blocked'));document.head.appendChild(s)
  });
  return xWidgetsPromise
}
async function renderXEmbeds(){
  const mounts=[...document.querySelectorAll('.tibo-x-embed[data-x-post-id]:not([data-x-state])')];
  if(!mounts.length)return;
  let api;try{api=await loadXWidgets()}catch{mounts.forEach(m=>{m.dataset.xState='failed';const id=m.dataset.xPostId,url=m.dataset.xUrl||'#';const x=signalRows().find(v=>String(v.post_id||'')===id);m.innerHTML=fallbackQuote(x||{},url)});return}
  for(const mount of mounts){
    mount.dataset.xState='loading';
    const id=mount.dataset.xPostId,url=mount.dataset.xUrl||'#';
    const placeholder=mount.querySelector('.tibo-x-loading');
    try{
      const el=await api.widgets.createTweet(id,mount,{dnt:true,theme:document.documentElement.dataset.theme==='dark'?'dark':'light',conversation:mount.dataset.xConversation||'all',align:'center'});
      if(!el)throw new Error('post unavailable');
      placeholder?.remove();mount.dataset.xState='loaded'
    }catch{
      const x=signalRows().find(v=>String(v.post_id||'')===id);mount.dataset.xState='failed';mount.innerHTML=fallbackQuote(x||{},url)
    }
  }
}
const baseResetPage=resetPage;
resetPage=function(){
  const html=baseResetPage(),feature=featuredHero(),block=intelBlock();
  if(!feature&&!block)return html;
  const start=html.indexOf('<div class="r-summary">'),controls=html.indexOf('<div class="m-controls">',start);
  if(start<0||controls<0)return html.replace('<div class="m-controls">',feature+block+'<div class="m-controls">');
  return html.slice(0,start)+feature+block+html.slice(controls)
};
const baseModuleMain=moduleMain;
moduleMain=function(){baseModuleMain();if(state.view==='tibo')requestAnimationFrame(renderXEmbeds)};
async function refreshTibo(){if(loading||!['http:','https:'].includes(location.protocol))return;loading=true;try{const u=new URL('api/v1/resets.json',location.href.split('#')[0]);const r=await fetch(u,{cache:'no-store',credentials:'omit'});if(!r.ok)throw new Error('HTTP '+r.status);const obj=await r.json();if(!obj||!Array.isArray(obj.events)||!Array.isArray(obj.inbox))throw new Error('invalid');RESET_DATA=obj;if(state.view==='tibo'){lastMain='';moduleMain()}}catch(e){console.warn('Tibo snapshot refresh failed',e)}finally{loading=false}}
window.addEventListener('hashchange',()=>{if(location.hash.startsWith('#/tibo'))refreshTibo()});
if(state.view==='tibo'){refreshTibo();requestAnimationFrame(renderXEmbeds)}
})();