'use strict';
(()=>{
/* Progress v5 — changes, capability map, and an independent research archive. */
const P5_RESEARCH=APP.research_radar||{lanes:[],items:[],checked:'',note:''};
const P5_TASKS=new Map((DATA.items||[]).map(x=>[x.id,x]));
const P5_SOURCES=new Map((DATA.sources||[]).map(x=>[x.id,x]));
function p5Params(){return new URLSearchParams(location.hash.split('?')[1]||'')}
function p5State(){
 const p=p5Params(),view=['updates','map','research'].includes(p.get('view'))?p.get('view'):'updates';
 return {view,cat:(p.get('cap')||'all').slice(0,80),q:(p.get('q')||'').slice(0,200).trim()}
}
function p5Href(patch={}){
 const s=p5State(),p=new URLSearchParams();
 const next={view:s.view,cat:s.cat,q:s.q,...patch};
 if(next.view&&next.view!=='updates')p.set('view',next.view);
 if(next.cat&&next.cat!=='all')p.set('cap',next.cat);
 if(next.q)p.set('q',next.q);
 return '#/progress'+(p.size?'?'+p.toString():'')
}
function p5Date(d){return String(d||'').replaceAll('-','.')}
function p5SourceRows(t){return (t.sources||[]).map(id=>P5_SOURCES.get(id)).filter(Boolean)}
function p5PrimarySource(t){return p5SourceRows(t).find(x=>x.published)||p5SourceRows(t)[0]||null}
function p5Access(t){
 if(t.id==='gemini-38-flash-tts')return {label:'网页 / API',cls:'direct'};
 if(t.id==='gemini-connected-apps')return {label:'灰度开放',cls:'limited'};
 if(t.id==='chatgpt-voice-work')return {label:'网页 / 移动端',cls:'direct'};
 if(/本地运行|Lean 环境|GPU 环境|沙箱环境/.test(t.effort||''))return {label:t.effort,cls:'local'};
 if(t.repo)return {label:'开源可部署',cls:'local'};
 return {label:t.effort||'公开路径',cls:'direct'}
}
function p5Experience(t){
 if(t.id==='gemini-38-flash-tts')return ['https://aistudio.google.com/','立即体验'];
 if(t.id==='gemini-connected-apps')return ['https://gemini.google.com/','打开 Gemini'];
 if(t.id==='chatgpt-voice-work')return ['https://chatgpt.com/','打开 ChatGPT'];
 if(t.repo)return ['https://github.com/'+t.repo,'打开项目'];
 const s=p5SourceRows(t)[0];return s?[s.url,'查看来源']:null
}
function p5Actions(t){
 const exp=p5Experience(t),src=p5PrimarySource(t);
 return '<div class="p5-actions">'+
  (exp?'<a class="p5-btn primary" href="'+safeLink(exp[0])+'" target="_blank" rel="noopener noreferrer">'+esc(exp[1])+' '+icon('external')+'</a>':'')+
  (src&&(!exp||src.url!==exp[0])?'<a class="p5-btn" href="'+safeLink(src.url)+'" target="_blank" rel="noopener noreferrer">来源 '+icon('external')+'</a>':'')+
  '<button class="p5-btn" data-action="task" data-id="'+esc(t.id)+'">详情 '+icon('arrow')+'</button></div>'
}
function p5Categories(){
 const rows=(DATA.items||[]).filter(x=>x.status==='code');
 return ['all',...new Set(rows.map(x=>x.category))]
}
function p5FilterTasks(rows,s){
 const q=s.q.toLowerCase();
 return rows.filter(x=>(s.cat==='all'||x.category===s.cat)&&(!q||[x.title,x.name,x.category,x.summary,x.boundary,x.test].join(' ').toLowerCase().includes(q)))
}
function p5Tabs(s){
 const tabs=[['updates','能力进展','最近真正多了什么'],['map','能力地图','现在能做到哪'],['research','研究雷达','下一步可能突破什么']];
 return '<nav class="p5-tabs">'+tabs.map(([id,title,sub])=>'<a class="'+(s.view===id?'active':'')+'" href="'+p5Href({view:id})+'"><strong>'+title+'</strong><small>'+sub+'</small></a>').join('')+'</nav>'
}
function p5Filters(s){
 if(s.view==='research')return '';
 const cats=p5Categories();
 return '<div class="p5-tools"><div class="p5-chips">'+cats.map(c=>'<a class="'+(s.cat===c?'active':'')+'" href="'+p5Href({cat:c})+'">'+esc(c==='all'?'全部能力':c)+'</a>').join('')+'</div><label class="p5-search">'+icon('search')+'<input id="p5-search" value="'+esc(s.q)+'" placeholder="搜索能力、限制、验收方法…"></label></div>'
}
function p5Changes(){
 return (DATA.events||[]).map(e=>{
  const t=P5_TASKS.get(e.task),src=(e.sources||[]).map(id=>P5_SOURCES.get(id)).find(Boolean);
  return t?{...e,task:t,source:src}:null
 }).filter(Boolean).sort((a,b)=>b.date.localeCompare(a.date)||a.title.localeCompare(b.title))
}
function p5ChangeCard(x){
 const t=x.task,access=p5Access(t);
 return '<article class="p5-change-card"><div class="p5-change-date"><time>'+p5Date(x.date)+'</time><span>'+esc(x.kind==='release'?'能力更新':'研究节点')+'</span></div><div class="p5-change-main"><div class="p5-meta"><span>'+esc(t.category)+'</span><span>'+esc(x.source?.publisher||t.name)+'</span></div><h3>'+esc(x.title)+'</h3><p class="p5-before"><b>这次变化</b>'+esc(x.delta||x.summary)+'</p><p class="p5-now"><b>现在能做</b>'+esc(t.summary)+'</p><div class="p5-verify"><b>怎么验</b><span>'+esc(t.test)+'</span></div></div><aside><span class="p5-access '+access.cls+'">'+esc(access.label)+'</span><p>'+esc(t.boundary)+'</p>'+p5Actions(t)+'</aside></article>'
}
function p5Updates(s){
 const rows=p5FilterTasks(p5Changes().map(x=>x.task),s);
 const ids=new Set(rows.map(x=>x.id)),events=p5Changes().filter(x=>ids.has(x.task.id));
 const today=new Date(),cut=new Date(today.getFullYear(),today.getMonth(),today.getDate()-7),recent=events.filter(x=>new Date(x.date+'T12:00:00')>=cut),older=events.filter(x=>!recent.includes(x));
 return '<section class="p5-view"><div class="p5-view-head"><div><p class="eyebrow">CAPABILITY CHANGES / PUBLISHED DATE</p><h2>能力进展</h2><p>只用原始发布 / 研究节点日期判断变化；“资料核对日”不会再冒充能力新增。</p></div><b>'+events.length+' 个已核验节点</b></div>'+
  (recent.length?'<div class="p5-change-list">'+recent.map(p5ChangeCard).join('')+'</div>':'<div class="p5-empty">最近 7 天没有匹配的已核验能力变化；不会用核对日期凑“本周新增”。</div>')+
  (older.length?'<details class="p5-history"><summary>更早的已核验进展 · '+older.length+' '+icon('chevron')+'</summary><div class="p5-change-list">'+older.map(p5ChangeCard).join('')+'</div></details>':'')+'</section>'
}
function p5MapCard(t){
 const access=p5Access(t),src=p5PrimarySource(t);
 return '<article class="p5-map-card"><header><div><span class="p5-access '+access.cls+'">'+esc(access.label)+'</span><small>'+esc(t.category)+'</small></div><button data-action="task" data-id="'+esc(t.id)+'">'+icon('arrow')+'</button></header><h3>'+esc(t.title)+'</h3><p class="p5-project">'+esc(t.name)+(src?' · '+esc(src.publisher):'')+'</p><div class="p5-answer"><b>现在能做</b><p>'+esc(t.summary)+'</p></div><div class="p5-answer condition"><b>需要什么</b><p>'+esc(t.requirements||t.effort||'查看官方说明')+'</p></div><div class="p5-answer limit"><b>最大限制</b><p>'+esc(t.boundary)+'</p></div><div class="p5-verify big"><b>怎么验证</b><span>'+esc(t.test)+'</span></div><footer>'+p5Actions(t)+'</footer></article>'
}
function p5Map(s){
 const rows=p5FilterTasks((DATA.items||[]).filter(x=>x.status==='code'),s);
 const groups={};rows.forEach(x=>(groups[x.category]??=[]).push(x));
 return '<section class="p5-view"><div class="p5-view-head"><div><p class="eyebrow">CAPABILITY MAP / TASK FIRST</p><h2>能力地图</h2><p>按任务看“能做什么 / 需要什么 / 最大限制 / 怎么验”。访问方式与成熟度分开，不把“有仓库”写成“已经成熟”。</p></div><b>'+rows.length+' 项公开路径</b></div>'+
 Object.entries(groups).map(([cat,list])=>'<section class="p5-map-group"><div class="p5-group-head"><h3>'+esc(cat)+'</h3><span>'+list.length+'</span></div><div class="p5-map-grid">'+list.map(p5MapCard).join('')+'</div></section>').join('')+
 (!rows.length?'<div class="p5-empty">没有匹配能力。</div>':'')+'</section>'
}
function p5ResearchCard(x){
 const primary=(x.sources||[]).filter(s=>s.strength==='primary'),lead=(x.sources||[]).filter(s=>s.strength==='lead');
 return '<article class="p5-research-card"><div class="p5-research-top"><div class="p5-tags">'+(x.tags||[]).slice(0,3).map(t=>'<span>'+esc(t)+'</span>').join('')+'</div><time>'+p5Date(x.date)+'</time></div><h3>'+esc(x.title)+'</h3><p class="p5-maker">'+esc(x.maker)+'</p><div class="p5-rline"><b>在研究什么</b><p>'+esc(x.fact)+'</p></div><div class="p5-rline insight"><b>我们的解读</b><p>'+esc(x.insight)+'</p></div><div class="p5-rline boundary"><b>现在还不能推出</b><p>'+esc(x.boundary)+'</p></div><div class="p5-rline next"><b>下一步看什么</b><p>'+esc(x.next_watch)+'</p></div><footer>'+
 primary.map(s=>'<a href="'+safeLink(s.url)+'" target="_blank" rel="noopener noreferrer">'+esc(s.label)+' · '+esc(s.kind)+' '+icon('external')+'</a>').join('')+
 lead.map(s=>'<a class="lead" href="'+safeLink(s.url)+'" target="_blank" rel="noopener noreferrer">待核验线索 · '+esc(s.label)+' '+icon('external')+'</a>').join('')+'</footer></article>'
}
function p5Research(s){
 const q=s.q.toLowerCase(),lanes=P5_RESEARCH.lanes||[],items=(P5_RESEARCH.items||[]).filter(x=>!q||[x.title,x.maker,x.fact,x.insight,x.next_watch,...(x.tags||[])].join(' ').toLowerCase().includes(q));
 return '<section class="p5-view"><div class="p5-view-head"><div><p class="eyebrow">RESEARCH RADAR / INDEPENDENT ARCHIVE</p><h2>研究雷达</h2><p>长期研究档案不再依赖热点榜；热点只负责给这些档案增加新节点。第三方线索明确标记为待核验。</p></div><b>'+items.length+' 个研究档案</b></div><label class="p5-search research">'+icon('search')+'<input id="p5-search" value="'+esc(s.q)+'" placeholder="搜索范式、实验室、跨学科方向…"></label>'+
 lanes.map(l=>{const rows=items.filter(x=>x.lane===l.id);return rows.length?'<section class="p5-research-group"><div class="p5-group-head"><div><h3>'+esc(l.title)+'</h3><p>'+esc(l.description)+'</p></div><span>'+rows.length+'</span></div><div class="p5-research-grid">'+rows.map(p5ResearchCard).join('')+'</div></section>':''}).join('')+
 '<p class="p5-research-note">'+esc(P5_RESEARCH.note||'')+' · 核对 '+esc(P5_RESEARCH.checked||'—')+'</p></section>'
}
function p5Progress(){
 $('#hero').hidden=true;$('#stats').hidden=true;$('.workspace').hidden=false;$('#vertical-root').hidden=true;$('.section-head').hidden=true;$('#layout-buttons').hidden=true;$('#toolbar').hidden=true;$('#contextline').hidden=true;
 const s=p5State(),usable=(DATA.items||[]).filter(x=>x.status==='code');
 $('#content').innerHTML='<div class="p5-progress"><header class="p5-head"><div><p class="eyebrow">CAPABILITY MAP / EVIDENCE FIRST</p><h1>AI，又能干什么了？</h1><p>热点看事件，产品页看产品；这里专门看任务能力和技术边界。</p></div><div class="p5-stats"><span><b>'+p5Changes().length+'</b>能力节点</span><span><b>'+usable.length+'</b>公开路径</span><span><b>'+(P5_RESEARCH.items||[]).length+'</b>研究档案</span></div></header>'+p5Tabs(s)+p5Filters(s)+(s.view==='updates'?p5Updates(s):s.view==='map'?p5Map(s):p5Research(s))+'</div>'
}
const p5BaseRenderMain=renderMain;
renderMain=function(){p5BaseRenderMain();if(state.view==='progress')p5Progress()};
document.addEventListener('input',e=>{if(e.target.id!=='p5-search')return;const pos=e.target.selectionStart,p=p5Params();const v=e.target.value.trim();if(v)p.set('q',v);else p.delete('q');history.replaceState(null,'','#/progress'+(p.size?'?'+p.toString():''));p5Progress();const input=$('#p5-search');input?.focus({preventScroll:true});try{input.setSelectionRange(pos,pos)}catch{}});
if(state.view==='progress'){lastMain='';renderMain()}
})();