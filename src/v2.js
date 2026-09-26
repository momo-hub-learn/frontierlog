'use strict';
/* AI坐标 v2 UI refactor: fewer templates, denser data, clearer hierarchy. */
(()=>{
pages.models[0]='模型榜'; pages.benchmarks[0]='模型榜 / Benchmark'; pages.activity[0]='前沿现场'; pages.tibo[0]='Tibo 重置';
const MODEL_COMPANIES=[
 {id:'openai',name:'OpenAI',aliases:['OpenAI'],url:'https://openai.com/'},
 {id:'anthropic',name:'Anthropic',aliases:['Anthropic'],url:'https://www.anthropic.com/claude'},
 {id:'google',name:'Google DeepMind',short:'Google',aliases:['Google'],url:'https://deepmind.google/models/'},
 {id:'meta',name:'Meta AI',short:'Meta',aliases:['Meta'],url:'https://ai.meta.com/llama/'},
 {id:'alibaba',name:'Alibaba',aliases:['Alibaba'],url:'https://www.alibabagroup.com/en-US'},
 {id:'deepseek',name:'DeepSeek',aliases:['DeepSeek'],url:'https://www.deepseek.com/en/'},
 {id:'moonshot',name:'Moonshot AI · Kimi',short:'Kimi',aliases:['Kimi','Moonshot'],url:'https://www.kimi.com/'},
 {id:'minimax',name:'MiniMax',aliases:['MiniMax'],url:'https://www.minimax.io/'},
 {id:'zai',name:'Z.ai',aliases:['Z AI','Z.ai'],url:'https://z.ai/'},
 {id:'xai',name:'xAI',aliases:['SpaceXAI','xAI'],url:'https://x.ai/'},
 {id:'microsoft-ai',name:'Microsoft AI',aliases:['Microsoft AI'],url:'https://microsoft.ai/models/'},
 {id:'bytedance-seed',name:'ByteDance Seed',aliases:['ByteDance Seed','ByteDance'],url:'https://seed.bytedance.com/en/'},
 {id:'fal',name:'fal',aliases:['Fal'],url:'https://fal.ai/'},
 {id:'hidream',name:'HiDream',aliases:['HiDream'],url:'https://hidream.ai/'},
 {id:'xgen',name:'XGEN Labs',aliases:['XGEN Labs'],url:'https://xgenlabs.ai/'},
 {id:'kling',name:'Kling AI',aliases:['Kling AI'],url:'https://kling.ai/'},
 {id:'robbyant',name:'Robbyant · Ant Group',short:'Robbyant',aliases:['LingBot'],url:'https://www.robbyant.com/'},
 {id:'nvidia',name:'NVIDIA',aliases:['NVIDIA'],url:'https://www.nvidia.com/en-us/ai/'},
 {id:'tencent-arc',name:'Tencent ARC',aliases:['Research'],url:'https://github.com/TencentARC/RollingForcing'},
 {id:'yume',name:'Yume Project',short:'Yume',aliases:['Yume'],url:'https://stdstu12.github.io/YUME-Project/'},
 {id:'cartesia',name:'Cartesia',aliases:['Cartesia'],url:'https://www.cartesia.ai/'},
 {id:'inworld',name:'Inworld',aliases:['Inworld'],url:'https://inworld.ai/'},
 {id:'speechifyai',name:'SpeechifyAI',aliases:['SpeechifyAI'],url:'https://speechify.ai/'},
 {id:'vui-labs',name:'VUI Labs',aliases:['VUI Labs'],url:'https://doc.vuilabs.ai/api-reference/system-voices/'}
];
window.MODEL_COMPANIES=MODEL_COMPANIES;
const ACTIVITY_RADAR=APP.activity_radar||{sources:[],events:[],media_items:[],sync:{}};
const V2_TOOL_LINKS=[
 {view:'tibo',href:'#/tibo',title:'Tibo 重置',icon:'reset'}
];
const V2_TOOL_DOCK_KEY='aic.v2.toolDockPosition';
let v2ToolDrag=null;
function v2ReadToolDockPosition(){
 try{
  const p=JSON.parse(localStorage.getItem(V2_TOOL_DOCK_KEY)||'null');
  if(p&&Number.isFinite(p.x)&&Number.isFinite(p.y))return p;
 }catch{}
 return null;
}
function v2ClampToolDock(dock,x,y){
 const w=dock?.offsetWidth||48,h=dock?.offsetHeight||48,pad=10;
 return {x:Math.max(pad,Math.min(window.innerWidth-w-pad,x)),y:Math.max(pad,Math.min(window.innerHeight-h-pad,y))};
}
function v2OrientToolDock(dock){
 if(!dock)return;
 const r=dock.getBoundingClientRect();
 dock.dataset.popX=(r.left+r.width/2)>window.innerWidth/2?'left':'right';
 dock.dataset.popY=(r.top+r.height/2)>window.innerHeight/2?'up':'down';
}
function v2ApplyToolDockPosition(dock,pos=v2ReadToolDockPosition()){
 if(!dock)return;
 if(pos){
  const p=v2ClampToolDock(dock,pos.x,pos.y);
  dock.style.left=p.x+'px';dock.style.top=p.y+'px';dock.style.right='auto';dock.style.bottom='auto';
 }else{
  dock.style.removeProperty('left');dock.style.removeProperty('top');dock.style.removeProperty('right');dock.style.removeProperty('bottom');
 }
 requestAnimationFrame(()=>v2OrientToolDock(dock));
}
function v2SaveToolDockPosition(dock){
 if(!dock)return;
 const r=dock.getBoundingClientRect(),p=v2ClampToolDock(dock,r.left,r.top);
 try{localStorage.setItem(V2_TOOL_DOCK_KEY,JSON.stringify(p))}catch{}
}
function v2ToolDock(){
 let dock=document.getElementById('v2-tool-dock');
 const active=state.view==='benchmarks'?'benchmarks':state.view;
 const wasOpen=Boolean(dock?.classList.contains('open'));
 const links=V2_TOOL_LINKS.map(t=>`<a class="v2-tool-link ${active===t.view?'active':''}" href="${t.href}" role="menuitem" ${active===t.view?'aria-current="page"':''}><span class="v2-tool-link-icon">${icon(t.icon)}</span><strong>${t.title}</strong>${icon('arrow')}</a>`).join('');
 const html=`<div id="v2-tool-dock" class="v2-tool-dock ${V2_TOOL_LINKS.some(t=>t.view===active)?'is-tool-page':''} ${wasOpen?'open':''}"><button class="v2-tool-orb" type="button" data-v2-tool-toggle aria-label="Tibo 重置工具，可拖动" title="拖动调整位置；悬停打开 Tibo 重置" aria-expanded="${wasOpen?'true':'false'}">${icon('reset')}<span class="v2-tool-orb-dot" aria-hidden="true"></span></button><div class="v2-tool-popover" role="menu" aria-label="Tibo 重置快捷入口">${links}</div></div>`;
 if(dock)dock.outerHTML=html;else document.body.insertAdjacentHTML('beforeend',html);
 v2ApplyToolDockPosition(document.getElementById('v2-tool-dock'));
}
function v2CloseToolDock(){
 const dock=document.getElementById('v2-tool-dock');if(!dock)return;
 dock.classList.remove('open');
 const button=dock.querySelector('[data-v2-tool-toggle]');if(button)button.setAttribute('aria-expanded','false');
}
if(!window.__AIC_V2_TOOL_DOCK_BOUND){
 window.__AIC_V2_TOOL_DOCK_BOUND=true;
 document.addEventListener('pointerdown',e=>{
  const toggle=e.target.closest('[data-v2-tool-toggle]');
  if(!toggle||(e.pointerType==='mouse'&&e.button!==0))return;
  const dock=toggle.closest('#v2-tool-dock');if(!dock)return;
  const r=dock.getBoundingClientRect();
  v2ToolDrag={pointerId:e.pointerId,dock,toggle,startX:e.clientX,startY:e.clientY,dx:e.clientX-r.left,dy:e.clientY-r.top,moved:false};
  try{toggle.setPointerCapture(e.pointerId)}catch{}
 });
 document.addEventListener('pointermove',e=>{
  const d=v2ToolDrag;if(!d||d.pointerId!==e.pointerId)return;
  if(!d.moved&&Math.hypot(e.clientX-d.startX,e.clientY-d.startY)<5)return;
  if(!d.moved){d.moved=true;d.dock.classList.add('dragging');v2CloseToolDock()}
  const p=v2ClampToolDock(d.dock,e.clientX-d.dx,e.clientY-d.dy);
  d.dock.style.left=p.x+'px';d.dock.style.top=p.y+'px';d.dock.style.right='auto';d.dock.style.bottom='auto';
  v2OrientToolDock(d.dock);
  e.preventDefault();
 },{passive:false});
 const endDrag=e=>{
  const d=v2ToolDrag;if(!d||d.pointerId!==e.pointerId)return;
  try{d.toggle.releasePointerCapture(e.pointerId)}catch{}
  if(d.moved){
   d.dock.classList.remove('dragging');
   d.dock.dataset.justDragged='1';
   v2SaveToolDockPosition(d.dock);v2OrientToolDock(d.dock);
   setTimeout(()=>{if(d.dock)d.dock.removeAttribute('data-just-dragged')},0);
  }
  v2ToolDrag=null;
 };
 document.addEventListener('pointerup',endDrag);
 document.addEventListener('pointercancel',endDrag);
 document.addEventListener('click',e=>{
  const toggle=e.target.closest('[data-v2-tool-toggle]');
  const dock=document.getElementById('v2-tool-dock');
  if(toggle&&dock){
   e.preventDefault();
   if(dock.dataset.justDragged==='1')return;
   const open=!dock.classList.contains('open');
   dock.classList.toggle('open',open);
   toggle.setAttribute('aria-expanded',String(open));
   return;
  }
  if(e.target.closest('#v2-tool-dock a'))return v2CloseToolDock();
  if(dock&&!e.target.closest('#v2-tool-dock'))v2CloseToolDock();
 });
 document.addEventListener('keydown',e=>{if(e.key==='Escape')v2CloseToolDock()});
 window.addEventListener('resize',()=>{
  const dock=document.getElementById('v2-tool-dock');if(!dock)return;
  const saved=v2ReadToolDockPosition();if(saved){v2ApplyToolDockPosition(dock,saved);v2SaveToolDockPosition(dock)}else v2OrientToolDock(dock);
 });
}


function v2Count(key){
 const counts={benchmarks:BENCH.items.length,models:MODEL_DATA.boards.reduce((n,b)=>n+b.rows.length,0),tibo:RESET_DATA.events.length,hot:HOT.items.length,feed:typeof aicCuratedRows==='function'?aicCuratedRows().length:HOT.items.length,progress:DATA.items.length,activity:DATA.events.length+(UP.releases||[]).length+(ACTIVITY_RADAR.events||[]).length+(ACTIVITY_RADAR.media_items||[]).length,toolkit:DATA.items.filter(t=>t.status==='code').length,topics:VERT.topics.length,pharma:VERT.articles.filter(a=>a.sector==='pharma').length,manufacturing:VERT.articles.filter(a=>a.sector==='manufacturing').length,saved:saved.size+articleSaved.size+msaved.size+bSaved.size};
 return counts[key]??0;
}
renderNav=function(){
 const groups=[['内容',['feed','hot','models','progress','activity','toolkit']],['主题',['topics','pharma','manufacturing']]];
 const active=state.view==='benchmarks'?'models':state.view;
 $('#nav').innerHTML=groups.map(([label,keys])=>`<div class="navgroup-label">${label}</div>${keys.map(key=>`<a href="#/${key}" class="navitem ${active===key?'active':''}" ${active===key?'aria-current="page"':''}>${icon(pages[key][1])}<span>${esc(pages[key][0])}</span><small>${String(v2Count(key)).padStart(2,'0')}</small></a>`).join('')}`).join('');
 $('#crumb').textContent=pages[state.view][0];
 $('#source-count').textContent=DATA.sources.length+VERT.sources.length+MODEL_DATA.sources.length+RESET_DATA.sources.length+BENCH.sources.length;
 $('#snapshot-date').textContent=VERT.checked.replaceAll('-','.');
 v2ToolDock();
};

function v2Brand(){
 const brand=document.querySelector('.brand-v9');
 if(!brand||brand.dataset.v2)return;
 brand.dataset.v2='1';
 const copy=brand.querySelector('.brand-copy');
 if(copy)copy.innerHTML='<strong>AI坐标</strong>';
 const version=document.querySelector('.side-tools code'); if(version)version.textContent='v2';
}

function v2Progress(){
 $('#hero').hidden=true; $('#stats').hidden=true; $('.workspace').hidden=false; $('#vertical-root').hidden=true; $('.section-head').hidden=true;
 $('#section-eyebrow').textContent='CAPABILITY STATUS';
 $('#section-title').innerHTML=`<span class="mini-icon">${icon('zap')}</span><span>AI 能力进度</span>`;
 $('#layout-buttons').hidden=true; $('#toolbar').hidden=true; $('#contextline').hidden=true;
 const usable=DATA.items.filter(t=>t.status==='code');
 const research=DATA.items.filter(t=>t.status==='research');
 const item=(t,mode)=>{const label=mode==='open'?'可运行':'研究阶段';return `<button class="v2-cap-row" data-action="task" data-id="${t.id}"><span class="v2-cap-state ${mode}"></span><span><strong>${esc(t.title)}</strong><small>${label} · ${esc(t.category)} · ${esc(t.name)}</small></span><span class="v2-cap-copy"><b style="color:var(--text);font-weight:650">能做：</b>${esc(t.summary)}<br><span style="color:var(--muted)">最大限制：</span>${esc(t.boundary)}</span>${icon('arrow')}</button>`};
 $('#content').innerHTML=`<div class="v2-pageintro v2-single-title"><div><h1>AI，又能干什么了？</h1><p>看现在能做什么、成熟到哪、还卡在哪里。</p><small>项目名只做次级信息；公开实现不等于已经通过业务验收。</small></div><span class="v2-pagecount">${DATA.items.length} 个任务</span></div>
 <div class="v2-cap-status-grid">
  <section class="wide"><header><span class="v2-status-dot open"></span><div><h2>现在能用</h2><p>有公开实现或可运行路径；仍需你自己的业务验收。</p></div><b>${usable.length}</b></header><div>${usable.map(t=>item(t,'open')).join('')}</div></section>
  <section class="wide"><header><span class="v2-status-dot research"></span><div><h2>还在研究</h2><p>有研究证据，但访问、稳定性或复现条件还不够成熟。</p></div><b>${research.length}</b></header><div>${research.map(t=>item(t,'research')).join('')||'<p class="v2-emptyline">暂无单独研究阶段任务。</p>'}</div></section>
 </div>`;
}

const V2_ACTIVITY_TYPES=[
 {id:'all',title:'全部',sub:'All'},
 {id:'events',title:'官方发布',sub:'Official'},
 {id:'technical',title:'技术深读',sub:'Engineering / Research'},
 {id:'conversation',title:'深度对谈',sub:'Interviews'},
 {id:'talks',title:'技术演讲',sub:'Talks'},
 {id:'demo',title:'实战 Demo',sub:'Hands-on'}
];
function v2ActivityState(){
 const p=new URLSearchParams(location.hash.split('?')[1]||''),rawType=p.get('type'),rawSource=p.get('source');
 const type=V2_ACTIVITY_TYPES.some(x=>x.id===rawType)?rawType:'all';
 const sources=ACTIVITY_RADAR.sources||[];
 const source=sources.some(x=>x.id===rawSource&&v2ActivitySourceFits(type,x))?rawSource:'all';
 return {type,source}
}
function v2ActivitySourceFits(type,s){
 if(type==='events')return s.kind==='event';
 if(type==='technical')return s.kind==='technical';
 if(type==='conversation')return s.kind==='media';
 if(type==='talks')return s.kind==='talk';
 if(type==='demo')return s.kind==='demo';
 return true
}
function v2ActivityTypeHref(type){return type==='all'?'#/activity':'#/activity?type='+encodeURIComponent(type)}
function v2ActivitySourceHref(type,id){
 const p=new URLSearchParams();
 if(type!=='all')p.set('type',type);
 if(id!=='all')p.set('source',id);
 return '#/activity'+(p.size?'?'+p.toString():'')
}
function v2Activity(){
 $('#hero').hidden=true; $('#stats').hidden=true; $('.workspace').hidden=false; $('#vertical-root').hidden=true; $('.section-head').hidden=true;
 $('#section-eyebrow').textContent='FRONTIER LIVE / FIRST-PARTY SIGNALS'; $('#section-title').innerHTML=`<span class="mini-icon">${icon('history')}</span><span>前沿现场</span>`;
 $('#layout-buttons').hidden=true; $('#toolbar').hidden=true; $('#contextline').hidden=true;

 const sources=ACTIVITY_RADAR.sources||[],sourceMap=new Map(sources.map(x=>[x.id,x])),view=v2ActivityState(),activeType=view.type,activeSource=view.source;
 const allEvents=[...(ACTIVITY_RADAR.events||[])].sort((a,b)=>(a.status==='upcoming'?0:1)-(b.status==='upcoming'?0:1)||b.date.localeCompare(a.date));
 const allMedia=[...(ACTIVITY_RADAR.media_items||[])].sort((a,b)=>b.published.localeCompare(a.published));
 const mediaForType=type=>allMedia.filter(x=>{const s=sourceMap.get(x.source_id)||{};return type==='all'||v2ActivitySourceFits(type,s)});
 const countForType=type=>type==='all'?allEvents.length+allMedia.length:type==='events'?allEvents.length:mediaForType(type).length;
 const visibleTypes=V2_ACTIVITY_TYPES.filter(t=>t.id==='all'||countForType(t.id)>0);
 const typeTab=t=>`<a class="v2-radar-tab ${activeType===t.id?'active':''}" href="${v2ActivityTypeHref(t.id)}" ${activeType===t.id?'aria-current="page"':''}><span><strong>${esc(t.title)}</strong><em>${esc(t.sub)}</em></span><small>${countForType(t.id)}</small></a>`;
 const typeTabs='<nav class="v2-radar-tabs" aria-label="前沿现场分类">'+visibleTypes.map(typeTab).join('')+'</nav>';

 const allowedSources=activeType==='all'?[]:sources.filter(s=>v2ActivitySourceFits(activeType,s)&&(
  activeType==='events'?allEvents.some(x=>x.source_id===s.id):mediaForType(activeType).some(x=>x.source_id===s.id)
 ));
 const sourceCount=id=>activeType==='events'?allEvents.filter(x=>x.source_id===id).length:mediaForType(activeType).filter(x=>x.source_id===id).length;
 const allSourceLabel=activeType==='events'?'全部官方发布':activeType==='technical'?'全部技术源':activeType==='conversation'?'全部对谈':activeType==='talks'?'全部演讲':'全部 Demo';
 const sourceTab=(id,title,count)=>`<a class="v2-radar-subtab ${activeSource===id?'active':''}" href="${v2ActivitySourceHref(activeType,id)}" ${activeSource===id?'aria-current="page"':''}>${esc(title)}<small>${count}</small></a>`;
 const sourceTabs=allowedSources.length?'<nav class="v2-radar-subtabs" aria-label="当前分类的来源筛选">'+sourceTab('all',allSourceLabel,countForType(activeType))+allowedSources.map(s=>sourceTab(s.id,s.name,sourceCount(s.id))).join('')+'</nav>':'';

 const eventRows=(activeType==='all'||activeType==='events'?allEvents:[]).filter(x=>activeSource==='all'||x.source_id===activeSource);
 const technicalRows=(activeType==='all'||activeType==='technical'?mediaForType('technical'):[]).filter(x=>activeSource==='all'||x.source_id===activeSource).slice(0,activeType==='all'?6:14);
 const conversationRows=(activeType==='all'||activeType==='conversation'?mediaForType('conversation'):[]).filter(x=>activeSource==='all'||x.source_id===activeSource).slice(0,activeType==='all'?10:16);
 const talkRows=(activeType==='talks'?mediaForType('talks'):[]).filter(x=>activeSource==='all'||x.source_id===activeSource).slice(0,14);
 const demoRows=(activeType==='demo'?mediaForType('demo'):[]).filter(x=>activeSource==='all'||x.source_id===activeSource).slice(0,14);

 const eventCard=e=>{const s=sourceMap.get(e.source_id)||{};return `<a class="v2-event-card ${e.status}" href="${safeLink(e.url)}" target="_blank" rel="noopener noreferrer"><div class="v2-event-date"><b>${esc(e.date.slice(5).replace('-','月')+'日')}</b><span>${esc(e.date.slice(0,4))}</span></div><div><div class="v2-radar-meta"><span>${e.status==='upcoming'?'下一场':'回放'}</span><small>${esc(s.publisher||s.name||'官方')}</small></div><h3>${esc(e.title)}</h3><p>${esc(e.summary)}</p><div class="v2-radar-tags">${(e.tags||[]).map(t=>`<span>${esc(t)}</span>`).join('')}</div></div>${icon('external')}</a>`};
 const mediaCard=m=>{
  const s=sourceMap.get(m.source_id)||{},formats=(s.formats||[]).join(' / '),limit=activeType==='all'?2:3,highlights=(m.highlights||[]).slice(0,limit);
  const takeaways=highlights.length?'<div class="v2-media-takeaways"><div><span>值得看</span>'+(m.value_hint?'<em>'+esc(m.value_hint)+'</em>':'')+'</div><ul>'+highlights.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul></div>':'';
  return `<a class="v2-media-card ${m.editor_pick?'editor-pick':''}" href="${safeLink(m.url)}" target="_blank" rel="noopener noreferrer"><div class="v2-media-top"><span>${esc(s.name||m.source_id)}</span><time>${esc(m.published.replaceAll('-','.'))}</time></div><h3>${esc(m.title)}</h3><p>${esc(m.summary||'')}</p>${takeaways}<div class="v2-radar-tags">${(m.tags||[]).map(t=>`<span>${esc(t)}</span>`).join('')}</div><div class="v2-media-foot"><small>${esc(formats)}</small><span>打开一手内容 ${icon('external')}</span></div></a>`
 };
 const section=(kicker,title,note,rows,cls='')=>rows.length?`<section class="v2-radar-section ${cls}"><header><div><p class="eyebrow">${esc(kicker)}</p><h2>${esc(title)}</h2></div><small>${esc(note)}</small></header><div class="v2-media-grid">${rows.map(mediaCard).join('')}</div></section>`:'';

 const eventSection=eventRows.length?`<section class="v2-radar-section"><header><div><p class="eyebrow">OFFICIAL / KEYNOTES</p><h2>官方发布</h2></div><small>${activeSource==='all'?'只收官方直播、回放与公告页':esc(sourceMap.get(activeSource)?.name||'官方来源')}</small></header><div class="v2-event-grid">${eventRows.map(eventCard).join('')}</div></section>`:'';
 const technicalSection=section('ENGINEERING / RESEARCH','技术深读','官方 Engineering / Research / Technical Blog',technicalRows,'technical');
 const conversationSection=section('LONG-FORM / INTERVIEWS','深度对谈','Podcast / 视频只是载体，优先保留能改变判断的长对谈',conversationRows,'conversation');
 const talkSection=section('TECH TALKS','技术演讲','Conference talk / Lab seminar / 技术分享',talkRows,'talks');
 const demoSection=section('HANDS-ON / DEMO','实战 Demo','真实产品、Agent、机器人或工作流演示',demoRows,'demo');

 const groups={}; DATA.events.forEach(e=>(groups[e.task]??=[]).push(e)); (UP.releases||[]).forEach(e=>(groups[e.task]??=[]).push({...e,kind:'upstream',date:(e.published_at||'').slice(0,10),summary:e.name||'上游版本发布',delta:'机器收录，尚未人工核验。'}));
 const rows=Object.entries(groups).map(([id,ev])=>({task:tasks.get(id),events:ev.sort((a,b)=>b.date.localeCompare(a.date))})).filter(x=>x.task).sort((a,b)=>(b.events[0]?.date||'').localeCompare(a.events[0]?.date||''));
 const publicationBadge=e=>{
  const p=e.publication;if(!p)return '';
  const prefix=p.ccf?'CCF '+p.ccf:(p.venue==='Nature'||p.venue==='Science'||p.tier==='top-journal')?'顶刊':p.tier==='top-conference'?'顶会':p.status==='preprint'?'预印本':p.status==='accepted'?'已录用':'已发表';
  const cls=p.ccf?'ccf-'+p.ccf.toLowerCase():p.status;
  return '<a class="v2-pub-badge '+cls+'" href="'+safeLink(p.url)+'" target="_blank" rel="noopener noreferrer" title="论文收录状态已核验">'+esc(prefix+' · '+p.venue)+icon('external')+'</a>'
 };
 const status=e=>e.publication?[e.publication.status==='preprint'?'预印本':e.publication.status==='accepted'?'录用':'发表','publication']:e.kind==='research'?['研究','research']:e.kind==='upstream'?['待核验','pending']:['公开发布','release'];
 const lifecycleSection=activeType==='all'&&activeSource==='all'?`<section class="v2-radar-section"><header><div><p class="eyebrow">PROMISE → REALITY</p><h2>发布后兑现</h2></div><small>宣布、研究、落地分开记</small></header><div class="v2-lifecycle-list">${rows.map(({task,events})=>`<article class="v2-lifecycle"><header><div>${identity(task)}<h2>${esc(task.title)}</h2></div><button class="textlink" data-action="task" data-id="${task.id}">打开档案 ${icon('arrow')}</button></header><div class="v2-life-track">${events.map(e=>{const [label,cls]=status(e);return `<div class="v2-life-node ${cls}"><time>${esc(e.date)}</time><i></i><div><div class="v2-life-labels"><span class="v2-life-chip">${label}</span>${publicationBadge(e)}</div><strong>${esc(e.title||e.short_title||e.tag||'版本变化')}</strong><p>${esc(e.summary||'')}</p><small>${esc(e.delta||'')}</small></div></div>`}).join('')}</div></article>`).join('')}</div></section>`:'';

 const visibleCount=eventRows.length+technicalRows.length+conversationRows.length+talkRows.length+demoRows.length;
 const activeTypeTitle=V2_ACTIVITY_TYPES.find(x=>x.id===activeType)?.title||'全部';
 const emptySection=!visibleCount?'<div class="v2-radar-empty"><h3>这个分类暂时没有已核验内容</h3><p>先切回“全部”；技术演讲和实战 Demo 会在有高质量一手内容后自动出现。</p></div>':'';
 $('#content').innerHTML=`<div class="v2-pageintro v2-activity-intro"><div><h1>AI 前沿现场</h1><p>先按“为什么值得看”分类：官方发布、技术深读、深度对谈；Podcast / YouTube 只作为内容格式，不再决定一级分类。</p><small>有公开 RSS 的节目每 2 小时检查；官方技术博客与发布会按一手页面核验。技术演讲 / 实战 Demo 已预留分类，有高质量内容后自动出现。论文收录继续单独核验：正式录用 / 发表后才标 CCF A/B/C、Nature / Science / 顶刊；arXiv 只标预印本。</small></div><span class="v2-pagecount">${activeType==='all'?sources.length+' 个高信号源':esc(activeTypeTitle)+' · '+visibleCount+' 条'}</span></div>
 ${typeTabs}${sourceTabs}
 ${eventSection}${technicalSection}${conversationSection}${talkSection}${demoSection}${emptySection}${lifecycleSection}`;
}


function v2Toolkit(){
 $('#hero').hidden=true; $('#stats').hidden=true; $('.workspace').hidden=false; $('#vertical-root').hidden=true; $('.section-head').hidden=true;
 $('#section-eyebrow').textContent='RUN IT TODAY'; $('#section-title').innerHTML=`<span class="mini-icon">${icon('wrench')}</span><span>今天能跑</span>`;
 $('#layout-buttons').hidden=true; $('#toolbar').hidden=true; $('#contextline').hidden=true;
 const tools=DATA.items.filter(t=>t.status==='code');
 $('#content').innerHTML=`<div class="v2-pageintro v2-single-title"><div><h1>今天能跑</h1><p>少解释，先找到入口。</p><small>只列有公开实现的任务；运行条件、命令和验收清单放在一张卡里。</small></div><span class="v2-pagecount">${tools.length} 个工具</span></div>
 <div class="v2-tool-grid">${tools.map(t=>`<article class="v2-tool"><header>${identity(t,true)}<span class="v2-tool-state">${t.tested?'本站已实测':'官方路径 · 未实测'}</span></header><h2>${esc(t.title)}</h2><p>${esc(t.summary)}</p><dl><dt>准备</dt><dd>${esc(t.requirements)}</dd><dt>验收</dt><dd>${esc(t.checks.slice(0,2).join(' · '))}</dd></dl>${t.command?`<div class="v2-command"><code>${esc(t.command.split('\n')[0])}</code><button data-action="run" data-id="${t.id}">${icon('copy')}</button></div>`:''}<footer><span>${esc(t.effort)}</span><button class="button small" data-action="run" data-id="${t.id}">上手路径 ${icon('arrow')}</button></footer></article>`).join('')}</div>`;
}

function v2TopicMap(){
 const sectorBlock=s=>{const topics=VERT.topics.filter(t=>t.sector===s.id);const groups=[...new Set(topics.map(t=>t.group))];return `<section class="v2-sector-map ${s.id}"><header><div><p class="eyebrow">${esc(s.eyebrow)}</p><h2>${esc(s.title)}</h2><p>${esc(s.description)}</p></div><a class="button small" href="#/${s.id}">进入专题 ${icon('arrow')}</a></header>${groups.map(g=>`<div class="v2-topic-group"><b>${esc(g)}</b><div>${topics.filter(t=>t.group===g).map(t=>{const n=VERT.articles.filter(a=>a.topics.includes(t.id)).length;return `<a href="${topicHref(t.id)}"><span><strong>${esc(t.title)}</strong><small>${esc(t.description)}</small></span><em>${n} 条</em>${icon('arrow')}</a>`}).join('')}</div></div>`).join('')}</section>`};
 return `<div class="v2-pageintro"><div><p class="eyebrow">VERTICAL INTELLIGENCE MAP</p><h1>按业务环节，而不是按“行业新闻”。</h1><p>医药从靶点到 CSR；制造从晶圆良率到装备与数字孪生。</p></div><span class="v2-pagecount">${VERT.topics.length} 个主题</span></div><div class="v2-topic-map">${VERT.sectors.map(sectorBlock).join('')}</div>`;
}
topicHub=function(){return v2TopicMap()};

const v2OldSectorPage=sectorPage;
sectorPage=function(sector){
 const topics=VERT.topics.filter(t=>t.sector===sector),current=VTOPICS.get(state.topic);
 const chain=`<nav class="v2-business-chain" aria-label="${esc(VSECTORS.get(sector).title)}业务环节"><a class="${state.topic==='all'?'active':''}" href="#/${sector}">全部</a>${topics.map(t=>`<a class="${state.topic===t.id?'active':''}" href="${topicHref(t.id)}"><strong>${esc(t.title)}</strong><small>${esc(t.group)}</small></a>`).join('')}</nav>`;
 return `${topicHeader(sector)}${chain}${current?`<div class="v2-topic-focus"><span>${icon(sector==='pharma'?'pill':'factory')}</span><div><b>${esc(current.title)}</b><p>${esc(current.description)}</p></div></div>`:''}${vToolbar()}<div class="v-feed-layout"><div class="v-article-list">${filterArticles({sector}).length?filterArticles({sector}).map(articleCard).join(''):vEmpty()}</div>${vRail(sector,filterArticles({sector}))}</div><div class="v-bottom-note">${VSECTORS.get(sector).note}</div>`;
};

const v2OldBHeading=bHeading;
bHeading=function(){
 const cards=BENCH.groups.filter(g=>g.id!=='all').map(g=>`<button data-ba="group" data-id="${g.id}"><span style="--tone:var(--${g.color==='green'?'accent':g.color})">${icon(B_ICON[g.id]||'gauge')}</span><strong>${esc(g.title)}</strong><small>${BENCH.items.filter(b=>b.group===g.id).length} 项</small></button>`).join('');
 return `<header class="v2-bench-head"><div><p class="b-kicker"><i class="b-light"></i> MODEL CENTER / BENCHMARK</p><h1>你想测什么？</h1><p>先选能力问题，再看 Benchmark。每项都保留“测什么 / 不能证明什么 / 为什么值得看”。</p></div><div class="v2-bench-count"><b>${BENCH.items.length}</b><span>公开基准与数据集</span></div></header><div class="v2-bench-entry">${cards}</div>`;
};

const v2OldModelPage=modelPage;
modelPage=function(){
 const p=new URLSearchParams(location.hash.split('?')[1]||''),cap=p.get('cap');
 if(cap)return v2OldModelPage();
 const {b,metric,legal,q,maker,only}=mBoardState();
 if(compareBoard!==b.id){modelCompare.clear();compareBoard=b.id}
 const rows=mRows(),info=M_METRICS[metric],providers=[...new Set(b.rows.map(r=>r.maker))].sort(),top=rows.find(r=>typeof r[metric]==='number');
 return `<div class="m-wrap v2-model-wrap">${modelHubTabs('rankings')}<header class="v2-model-head"><div><p class="eyebrow">BASE MODELS / ${esc(b.provider.toUpperCase())}</p><h1>基础模型</h1><p>先选来源，再选指标。速度、成本和偏好不混成一个总分。</p></div><div class="v2-model-meta"><span>${b.rows.length} 配置</span><span>${providers.length} 厂商</span><span>${esc((b.as_of||b.checked).replaceAll('-','.'))}</span></div></header><nav class="m-tabs v2-source-tabs" aria-label="评测来源">${MODEL_DATA.boards.map(x=>`<button class="m-tab ${x.id===b.id?'active':''}" data-ma="board" data-id="${x.id}">${esc(x.title)}<small>${esc(x.provider==='Arena'?'ARENA':'AA')}</small></button>`).join('')}</nav><div class="v2-rankbar"><div class="m-segments">${legal.map(k=>`<button class="m-segment ${metric===k?'active':''}" data-ma="metric" data-id="${k}">${M_METRICS[k][0]}</button>`).join('')}</div><div class="m-tools"><label class="m-search">${icon('search')}<input id="m-search" type="search" value="${esc(q)}" placeholder="搜索模型、厂商…"></label><select class="m-select" id="m-maker"><option value="all">全部厂商</option>${providers.map(x=>`<option value="${esc(x)}" ${x===maker?'selected':''}>${esc(x)}</option>`).join('')}</select><label class="m-check"><input id="m-only" type="checkbox" ${only?'checked':''}>只看关注</label></div></div>${top?`<div class="v2-current-first"><span>#1 当前样本</span><strong>${esc(top.name)}</strong><em>${esc(mMetricValue(top,metric))} ${esc(info[2])}</em></div>`:''}<section class="m-tablebox v2-model-table"><div class="m-tablehead"><h2>${esc(b.title)}<small>${esc(info[1])}${info[3]?'由低到高':'由高到低'}</small></h2>${mSourceLink(b.source)}</div>${rows.length?modelTable(rows,b,metric):`<div class="m-empty"><h3>没有匹配模型</h3></div>`}<div class="m-tablefoot"><span>${esc(b.scope)}</span><button class="plain" data-ma="model-method">如何读这份榜单 ${icon('info')}</button></div></section>${modelCompare.size?`<div class="m-comparebar"><span>${modelCompare.size} / 3 个配置</span>${mButton('比较','compare','','primary')}${mButton('清空','compare-clear')}</div>`:''}</div>`;
};

// 热点页固定按时间倒序；不再提供“最新 / 热度”二次排序。
function v2SavedSummary(){
 if(state.view!=='saved')return;
 const host=$('#legacy-saved'); if(!host||host.querySelector('.v2-saved-head'))return;
 host.insertAdjacentHTML('afterbegin',`<section class="v2-saved-head"><div><p class="eyebrow">YOUR PERSONAL INDEX</p><h1>我的关注</h1><p>主题、模型、文章和 Benchmark 汇到一个地方。</p></div><div class="v2-saved-stats"><span><b>${topicFollows.size}</b>主题</span><span><b>${msaved.size}</b>模型</span><span><b>${articleSaved.size}</b>文章</span><span><b>${bSaved.size}</b>Benchmark</span></div></section>`);
}

const v2BaseRenderMain=renderMain;
renderMain=function(){
 v2BaseRenderMain();
 v2Brand();
 $('.section-head').hidden=false;
 if(state.view==='progress')v2Progress();
 if(state.view==='activity')v2Activity();
 if(state.view==='toolkit')v2Toolkit();
 if(state.view==='saved')v2SavedSummary();
};

const observer=new MutationObserver(()=>{v2Brand();v2SavedSummary();});
observer.observe(document.body,{childList:true,subtree:true});
v2Brand();
if(typeof renderMain==='function'){lastMain='';renderMain()}
})();
/* TASK_FIRST_TOOLKIT_20260926 */

(()=>{if(document.getElementById('tk-task-first-style'))return;const s=document.createElement('style');s.id='tk-task-first-style';s.textContent="/* Toolkit only: keep typography, controls and conditions readable without enlarging other pages. */\n.tk-wrap{max-width:1440px;margin:0 auto;color:var(--text);min-width:0}\n.tk-wrap *{box-sizing:border-box}\n.tk-wrap [hidden]{display:none!important}\n.tk-head{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:4px 0 22px}\n.tk-head h1{font-size:2rem;font-weight:750;line-height:1.3;margin:0 0 7px;letter-spacing:-.03em}\n.tk-head p{font-size:1rem;color:var(--sub);line-height:1.6;margin:0}\n.tk-boundary{font-size:.8125rem;color:var(--sub);border:1px solid var(--line);border-radius:7px;padding:8px 12px;white-space:nowrap}\n.tk-groups{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}\n.tk-groups button{font-size:.9375rem;min-height:42px;border:1px solid var(--line);border-radius:9px;padding:8px 13px;color:var(--sub);background:var(--panel);display:inline-flex;align-items:center;gap:8px}\n.tk-groups button[aria-pressed=true]{background:var(--accent-bg);color:var(--accent);border-color:var(--accent);font-weight:650}\n.tk-groups small{font-size:.8125rem;font-variant-numeric:tabular-nums;opacity:.8}\n.tk-toolbar{display:flex;align-items:center;gap:12px;padding:0 0 12px;min-width:0}\n.tk-search{display:flex;align-items:center;gap:10px;flex:1;min-width:120px;max-width:520px;border:1px solid var(--line);background:var(--panel);border-radius:9px;padding:0 12px;color:var(--sub)}\n.tk-search input{width:100%;min-width:0;font-size:1rem;line-height:1.5;padding:11px 0;color:var(--text);background:transparent;border:0;outline:none}\n.tk-search:focus-within{outline:2px solid var(--accent);outline-offset:2px}\n.tk-access select{min-height:46px;max-width:100%;font-size:.9375rem;border:1px solid var(--line);border-radius:9px;padding:9px 12px;background:var(--panel);color:var(--text)}\n.tk-saved{display:flex;gap:7px;align-items:center;font-size:.9375rem;white-space:nowrap;min-height:44px;cursor:pointer}\n.tk-saved input{height:17px;width:17px;accent-color:var(--accent)}\n.tk-resultline{display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px;font-size:.8125rem;color:var(--sub);margin:2px 0 14px}\n#tk-count{font-weight:600;color:var(--text);font-variant-numeric:tabular-nums}\n.tk-order{margin-right:auto}\n.tk-resultline button{font-size:.8125rem;text-decoration:underline;text-underline-offset:3px;color:var(--accent);min-height:36px}\n.tk-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));align-items:start;gap:18px}\n.tk-card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px 22px 0;min-width:0;overflow-wrap:anywhere}\n.tk-card.is-open{grid-column:1/-1;border-color:var(--accent)}\n.tk-cardtop{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}\n.tk-identity{display:flex;align-items:center;gap:10px;min-width:0}\n.tk-identity>div{min-width:0}\n.tk-identity strong{display:block;font-size:1rem;font-weight:650;line-height:1.5}\n.tk-identity div>span{display:block;font-size:.8125rem;line-height:1.5;color:var(--sub)}\n.tk-mark{width:38px;min-width:38px;height:38px;background:var(--accent-bg);color:var(--accent);font:600 .9375rem var(--mono);border-radius:9px;display:grid;place-items:center}\n.tk-mode{font-size:.8125rem;line-height:1.5;color:var(--sub);padding:4px 8px;border-radius:6px;background:var(--raised);flex-shrink:0;max-width:50%}\n.tk-mode[data-mode=local]{background:var(--accent-bg);color:var(--accent)}\n.tk-card h2{font-size:1.25rem;line-height:1.5;font-weight:700;letter-spacing:-.015em;margin:16px 0}\n.tk-io{display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);gap:12px;background:var(--raised);border-radius:9px;padding:13px 15px;align-items:center;margin-bottom:17px}\n.tk-io dl{margin:0;min-width:0}\n.tk-io dt{font-size:.8125rem;color:var(--sub);margin-bottom:5px}\n.tk-io dd{margin:0;font-size:1rem;line-height:1.65;color:var(--text)}\n.tk-io>span{color:var(--accent)}\n.tk-conditions{margin:0;display:grid;gap:10px}\n.tk-conditions>div{display:grid;grid-template-columns:4.25em minmax(0,1fr);gap:10px;align-items:baseline}\n.tk-conditions dt{font-size:.8125rem;line-height:1.7;color:var(--sub)}\n.tk-conditions dd{margin:0;font-size:.9375rem;line-height:1.75;color:var(--text)}\n.tk-actions{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin:12px 0 9px}\n.tk-link{font-size:.875rem;display:inline-flex;align-items:center;gap:5px;min-height:42px;color:var(--accent);text-decoration:underline;text-underline-offset:4px;overflow-wrap:anywhere}\n.tk-link .ico{height:14px;width:14px;flex:none}\n.tk-actions .save{margin-left:auto;position:static;min-width:42px;min-height:42px;background:var(--raised);border:1px solid var(--line);border-radius:8px}\n.tk-guide{border-top:1px solid var(--line)}\n.tk-guide>summary{display:flex;justify-content:space-between;align-items:center;gap:12px;list-style:none;cursor:pointer;font-size:.9375rem;min-height:52px;color:var(--accent);font-weight:550}\n.tk-guide>summary::-webkit-details-marker{display:none}\n.tk-guide>summary>span:first-child{display:flex;align-items:center;gap:8px}\n.tk-expand{font-size:1.2rem;font-weight:400}\n.tk-guide[open] .tk-expand{transform:rotate(45deg)}\n.tk-guide-content{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:28px;padding:15px 0 22px}\n.tk-guide h3{font-size:1.0625rem;font-weight:650;line-height:1.6;margin:0 0 14px}\n.tk-guide h4{font-size:1rem;font-weight:650;line-height:1.65;margin:0 0 6px}\n.tk-guide p{font-size:.9375rem;line-height:1.8;margin:0;color:var(--sub)}\n.tk-steps{list-style:decimal-leading-zero;padding-left:1.85em;margin:0}\n.tk-steps li{padding-left:5px;margin:0 0 18px}\n.tk-steps li::marker{color:var(--accent);font:600 .875rem var(--mono)}\n.tk-command{margin-top:12px;background:var(--bg);border:1px solid var(--line);border-radius:8px;overflow:hidden}\n.tk-command>div{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:6px 12px;border-bottom:1px solid var(--line);flex-wrap:wrap}\n.tk-command>div>span{font-size:.8125rem;color:var(--sub)}\n.tk-command button{display:inline-flex;align-items:center;gap:5px;font-size:.8125rem;min-height:38px;color:var(--accent)}\n.tk-command pre{padding:12px;margin:0;white-space:pre-wrap;overflow-wrap:anywhere;word-break:normal;font:.875rem/1.8 var(--mono)}\n.tk-command code{font:inherit;color:var(--text)}\n.tk-command .tk-copy-status{font-size:.8125rem;padding:0 12px 8px}\n.tk-command .tk-copy-status:empty{display:none}\n.tk-validation{min-width:0;border-left:1px solid var(--line);padding-left:24px}\n.tk-validation .tk-note{font-size:.8125rem}\n.tk-validation .checklist{margin:14px 0 24px;gap:13px}\n.tk-validation .checklist label{align-items:flex-start;font-size:.9375rem;line-height:1.8;min-height:32px}\n.tk-validation .checklist input{flex:none;width:17px;height:17px;margin-top:5px;accent-color:var(--accent)}\n.tk-validation>h4{margin-top:18px}\n.tk-evidence{border-top:1px solid var(--line);padding:17px 0 20px}\n.tk-evidence h3{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:6px}\n.tk-evidence h3>span{font-size:.8125rem;font-weight:400;color:var(--sub)}\n.tk-evidence>div{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}\n.tk-evidence>div>span{font-size:.8125rem;color:var(--sub);line-height:1.8}\n.tk-evidence>p{font-size:.8125rem;margin-top:8px}\n.tk-empty{grid-column:1/-1;border:1px dashed var(--line);border-radius:12px;padding:36px;text-align:center}\n.tk-empty h2{font-size:1.2rem;margin:0 0 10px}\n.tk-empty p{font-size:1rem;color:var(--sub);line-height:1.8;margin-bottom:16px}\n.tk-footnote{font-size:.8125rem;color:var(--sub);line-height:1.8;margin:22px 0}\n.tk-sr{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}\n.tk-wrap :is(button,a,summary,select,input):focus-visible{outline:2px solid var(--accent);outline-offset:3px}\n@media(max-width:70rem){.tk-grid{grid-template-columns:minmax(0,1fr)}.tk-card{padding:20px 20px 0}}\n@media(max-width:48rem){.tk-head{position:relative;align-items:flex-start;flex-direction:column;gap:9px;margin-bottom:16px}.tk-head h1{font-size:1.75rem}.tk-boundary{position:absolute;right:0;top:5px;border:0;padding:4px 6px;font-size:.75rem}.tk-boundary-wide{display:none}.tk-head p{font-size:.9375rem}.tk-groups{gap:6px;margin-bottom:12px}.tk-groups button{font-size:.875rem;padding:6px 9px;min-height:38px;gap:5px}.tk-toolbar{flex-wrap:wrap;gap:8px 12px}.tk-search{flex-basis:100%;max-width:none}.tk-access{flex:1;min-width:0}.tk-access select{width:100%;font-size:.875rem}.tk-saved{font-size:.875rem}.tk-resultline{gap:4px 10px}.tk-order{font-size:.75rem}.tk-card{padding:16px 16px 0}.tk-cardtop{gap:8px}.tk-mode{max-width:42%;font-size:.75rem}.tk-card h2{font-size:1.1875rem;margin:13px 0}.tk-io{gap:8px;padding:10px 12px;margin-bottom:13px}.tk-io dd{font-size:.9375rem}.tk-conditions>div{gap:8px;grid-template-columns:4em minmax(0,1fr)}.tk-actions{gap:9px;margin-top:8px}.tk-actions .tk-link{font-size:.8125rem}.tk-guide-content{grid-template-columns:minmax(0,1fr);gap:10px}.tk-validation{border-left:0;border-top:1px solid var(--line);padding:18px 0 0}.tk-evidence>div{gap:0}.tk-evidence .tk-link{min-height:36px}.tk-empty{padding:26px 16px}}\n@media(prefers-reduced-motion:reduce){.tk-wrap *{scroll-behavior:auto;transition:none}}\n";document.head.appendChild(s)})();

'use strict';
/* Task-first toolkit. Editorial guides are separate from runtime verification. */
const TK = (()=>{
 const TK_SOURCE_MAP=new Map((APP.catalog.sources||[]).map(s=>[s.id,s]));
 const TK_META={
  docling:{publisher:'Docling Project',group:'documents',access:'local',input:'一份获授权的 PDF',output:'结构化文档 / Markdown',cost:'本地计算；预留模型下载与存储空间。'},
  whisper:{publisher:'OpenAI',group:'audio',access:'local',input:'获授权的短音频',output:'转写文本与字幕文件',cost:'本地计算；模型大小影响内存、速度与存储。'},
  graphrag:{publisher:'Microsoft',group:'documents',access:'model',input:'少量获授权文本 + 问题',output:'基于索引的答案与可核对依据',cost:'索引、嵌入与查询可能产生模型费用。'},
  'gemini-38-flash-tts':{publisher:'Google',group:'audio',access:'web',input:'一段自有文稿 + 语气指令',output:'可试听的生成语音',cost:'用量、配额与计费以账号内官方信息为准。',entry_url:'https://aistudio.google.com/'},
  'chatgpt-voice-work':{publisher:'OpenAI',group:'office',access:'web',input:'语音指令 + 授权的工作材料',output:'任务结果，可接续文字对话',cost:'套餐、限额与工作区设置以账号内显示为准。',entry_url:'https://chatgpt.com/'},
  'gemini-connected-apps':{publisher:'Google',group:'office',access:'web',input:'指令 + 已授权应用的测试数据',output:'跨应用查询或操作结果',cost:'账号和接入应用的套餐、额度分别适用。',entry_url:'https://gemini.google.com/'},
  openhands:{publisher:'OpenHands',group:'agents',access:'model',input:'隔离仓库 + 问题描述 + 测试',output:'代码变更与可检查的执行记录',cost:'模型调用与后端运行可能分别产生费用。'},
  'browser-use':{publisher:'Browser Use',group:'agents',access:'model',input:'授权测试网站 + 清晰任务',output:'浏览器操作与可核对结果',cost:'模型调用与可选云端浏览器可能另行计费。'},
  mathlib:{publisher:'Lean Community',group:'research',access:'research',input:'形式化命题 + 证明代码',output:'Lean 检查结果或错误信息',cost:'本地环境与依赖下载；运行条件按选用入口确认。',entry_url:'https://live.lean-lang.org/'},
  'ai-scientist':{publisher:'Sakana AI',group:'research',access:'research',input:'官方实验模板 + 数据 + 模型配置',output:'实验日志、图表和报告草稿',cost:'计算资源、模型调用及依赖安装成本；先限制实验规模。'}
 };
 const data={version:1,
  groups:[{id:'documents',label:'文档与知识'},{id:'audio',label:'语音处理'},{id:'office',label:'办公自动化'},{id:'agents',label:'开发与浏览器'},{id:'research',label:'科研验证'}],
  access_modes:[{id:'local',label:'本地工具'},{id:'model',label:'模型服务 · 需配置'},{id:'web',label:'网页 · 需权限'},{id:'research',label:'科研环境'}],
  items:(APP.catalog.items||[]).filter(t=>t.status==='code'&&TK_META[t.id]).map(t=>{
   const m=TK_META[t.id],srcs=(t.sources||[]).map(id=>TK_SOURCE_MAP.get(id)).filter(Boolean);
   return {id:t.id,publisher:m.publisher,group:m.group,access:m.access,headline:t.title,input:m.input,output:m.output,
    requirements:t.requirements||'按官方资料准备环境。',limitation:t.boundary||t.scope||'需按官方限制使用。',cost:m.cost,
    steps:[{title:'先看官方入口',body:'先阅读一手资料，确认当前版本、账号或环境条件。'},
     {title:'从一个小任务开始',body:t.test||'用可核对的小样本完成第一轮验证。',command:t.command||undefined},
     {title:'按结果验收',body:(t.checks||[]).join('；')||'核对实际输出并记录结果。'}],
    troubleshooting:'先检查版本、权限、输入和运行环境，再缩小到可复现的小样本。',
    sources:srcs.map(s=>({title:s.title,url:s.url,published_at:s.published||null,verified_at:s.checked||t.reviewed||APP.catalog.snapshot})),
    entry_url:m.entry_url||null,evidence_level:'primary-docs',runtime_tested:false};
  })
 };
 const guides=new Map(data.items.map(x=>[x.id,x]));
 const openIds=new Set();
 const groupIds=new Set(data.groups.map(x=>x.id)),modeIds=new Set(data.access_modes.map(x=>x.id));
 const label=(rows,id)=>rows.find(x=>x.id===id)?.label||'';
 function read(hash=location.hash){
  const p=new URLSearchParams(hash.split('?')[1]||'');
  const tool=p.get('tool')||p.get('task')||'';
  return {group:groupIds.has(p.get('group'))?p.get('group'):'all',access:modeIds.has(p.get('access'))?p.get('access'):'all',q:(p.get('q')||'').slice(0,300),only:p.get('saved')==='1',tool:guides.has(tool)?tool:''};
 }
 function href(s,patch={}){
  const next={...s,...patch},p=new URLSearchParams();
  if(groupIds.has(next.group))p.set('group',next.group);
  if(modeIds.has(next.access))p.set('access',next.access);
  if(next.q)p.set('q',next.q.slice(0,300));
  if(next.only)p.set('saved','1');
  if(guides.has(next.tool))p.set('tool',next.tool);
  return '#/toolkit'+(p.size?'?'+p.toString():'');
 }
 function rows(s){
  const q=s.q.trim().toLocaleLowerCase();
  return data.items.filter(g=>{
   const t=tasks.get(g.id);
   return (s.group==='all'||g.group===s.group)&&(s.access==='all'||g.access===s.access)&&(!s.only||saved.has(g.id))&&(!q||[t.name,g.publisher,g.headline,g.input,g.output,label(data.groups,g.group)].join(' ').toLocaleLowerCase().includes(q));
  });
 }
 function route(patch,replace=false,resultsOnly=false){
  const hash=href(read(),patch);
  if(location.hash!==hash)history[replace?'replaceState':'pushState'](null,'',hash);
  if(resultsOnly){state.q=read().q;renderResults()}else{lastMain='';parseRoute()}
 }
 function external(url,text,cls='tk-link'){
  return `<a class="${cls}" href="${safeLink(url)}" target="_blank" rel="noopener noreferrer">${esc(text)} ${icon('external')}</a>`;
 }
 function card(g){
  const t=tasks.get(g.id),opened=openIds.has(g.id)||read().tool===g.id;
  const doc=g.sources[0];
  return `<article class="tk-card ${opened?'is-open':''}" data-tk-id="${g.id}">
   <div class="tk-cardtop"><div class="tk-identity"><span class="tk-mark" aria-hidden="true">${esc(t.mark||t.name.slice(0,2))}</span><div><strong>${esc(t.name)}</strong><span>${esc(g.publisher)}</span></div></div><span class="tk-mode" data-mode="${g.access}">${esc(label(data.access_modes,g.access))}</span></div>
   <h2>${esc(g.headline)}</h2>
   <div class="tk-io"><dl><dt>输入</dt><dd>${esc(g.input)}</dd></dl><span aria-hidden="true">→</span><dl><dt>输出</dt><dd>${esc(g.output)}</dd></dl></div>
   <dl class="tk-conditions"><div><dt>先准备</dt><dd>${esc(g.requirements)}</dd></div><div><dt>最大限制</dt><dd>${esc(g.limitation)}</dd></div></dl>
   <div class="tk-actions">${external(doc.url,'官方上手文档')}${g.entry_url?external(g.entry_url,'打开入口'):''}<button type="button" class="save ${saved.has(g.id)?'active':''}" data-tk-save="${g.id}" aria-label="${saved.has(g.id)?'取消关注':'关注'} ${esc(t.name)}" aria-pressed="${saved.has(g.id)}">${icon('bookmark')}</button></div>
   <details class="tk-guide" data-tk-guide="${g.id}" ${opened?'open':''}>
    <summary><span>${icon('code')} 步骤与验收</span><span class="tk-expand" aria-hidden="true">＋</span></summary>
    <div class="tk-guide-content"><div><h3>从一个小任务开始</h3><ol class="tk-steps">${g.steps.map((step,i)=>`<li><h4>${esc(step.title)}</h4><p>${esc(step.body)}</p>${step.command?`<div class="tk-command"><div><span>示例命令 · 未在本站执行</span><button type="button" data-tk-copy="${i}" data-tk-tool="${g.id}" aria-label="复制 ${esc(t.name)} 第 ${i+1} 步完整命令">${icon('copy')} 复制全部</button></div><pre><code>${esc(step.command)}</code></pre><p class="tk-copy-status" role="status"></p></div>`:''}</li>`).join('')}</ol></div>
     <aside class="tk-validation"><h3>怎样算跑通</h3><p class="tk-note">以下为你的本机验收清单，不是本站测试结果。</p><div class="checklist">${t.checks.map((text,i)=>`<label class="${checks[g.id]?.includes(i)?'done':''}"><input type="checkbox" data-check-task="${g.id}" data-check-index="${i}" ${checks[g.id]?.includes(i)?'checked':''}><span>${esc(text)}</span></label>`).join('')}</div>
     <h4>成本与运行条件</h4><p>${esc(g.cost)}</p><h4>卡住时先检查</h4><p>${esc(g.troubleshooting)}</p></aside>
    </div>
    <section class="tk-evidence" aria-label="${esc(t.name)} 的证据与核验日期"><h3>原始来源 <span>资料已核验 · 运行未实测</span></h3>${g.sources.map(s=>`<div>${external(s.url,s.title)}<span>${s.published_at?'原文发布 <time datetime="'+s.published_at+'">'+s.published_at+'</time> · ':''}资料核验 <time datetime="${s.verified_at}">${s.verified_at}</time></span></div>`).join('')}<p>未提供可复现运行日志，不标记为“本站已实测”；核验日期不是软件发布日期。安装页随版本变化，请记录实际版本与环境。</p></section>
   </details></article>`;
 }
 function renderResults(){
  const s=read(),visible=rows(s),target=document.getElementById('tk-results');
  if(!target)return;
  document.getElementById('tk-count').textContent=`${visible.length} / ${data.items.length} 条上手路径`;
  document.getElementById('tk-clear').hidden=!(s.q||s.group!=='all'||s.access!=='all'||s.only);
  target.innerHTML=visible.length?visible.map(card).join(''):`<div class="tk-empty"><h2>没有匹配的上手路径</h2><p>试试项目名、输入文件或想完成的任务，也可以清除当前筛选。</p><button type="button" class="button" data-tk-clear>清除筛选</button></div>`;
 }
 function page(){
  const s=read();if(s.tool)openIds.add(s.tool);
  renderNav();
  for(const selector of ['#hero','#stats','#vertical-root','.section-head','#toolbar','#layout-buttons','#contextline']){const el=$(selector);if(el)el.hidden=true}
  $('#legacy-saved').innerHTML='';$('.workspace').hidden=false;
  const content=$('#content');content.setAttribute('aria-live','off');
  content.innerHTML=`<div class="tk-wrap"><header class="tk-head"><div><h1>今天能跑<span class="accent">.</span></h1><p>先选任务，再看输入、输出和使用条件。</p></div><span class="tk-boundary"><span class="tk-boundary-wide">官方上手路径 · </span>未实测</span></header>
   <nav class="tk-groups" aria-label="按任务筛选"><button type="button" data-tk-group="all" aria-pressed="${s.group==='all'}">全部 <small>${data.items.length}</small></button>${data.groups.map(g=>`<button type="button" data-tk-group="${g.id}" aria-pressed="${s.group===g.id}">${esc(g.label)} <small>${data.items.filter(x=>x.group===g.id).length}</small></button>`).join('')}</nav>
   <div class="tk-toolbar"><label class="tk-search">${icon('search')}<input id="tk-search" type="search" aria-label="搜索工具、任务、输入或输出" placeholder="搜索工具、任务、输入或输出…" maxlength="300" value="${esc(s.q)}"></label><label class="tk-access"><span class="tk-sr">使用方式</span><select id="tk-access" aria-label="使用方式"><option value="all">全部使用方式</option>${data.access_modes.map(x=>`<option value="${x.id}" ${s.access===x.id?'selected':''}>${esc(x.label)}</option>`).join('')}</select></label><label class="tk-saved"><input id="tk-only" type="checkbox" ${s.only?'checked':''}>只看关注</label></div>
   <div class="tk-resultline"><span id="tk-count" role="status"></span><span class="tk-order">按上手路径编排，非能力排名</span><button type="button" id="tk-clear" data-tk-clear>清除筛选</button></div>
   <div class="tk-grid" id="tk-results"></div><p class="tk-footnote">网页能力以账号内实际开放为准；命令需在自己的环境运行。清单与关注仅保存在当前浏览器，不会改变证据等级。</p></div>`;
  renderResults();document.body.classList.remove('nav-open');renderTray();
 }
 async function copy(button){
  const g=guides.get(button.dataset.tkTool),step=g?.steps[Number(button.dataset.tkCopy)];
  if(!step?.command)return;
  const status=button.closest('.tk-command').querySelector('.tk-copy-status');
  button.disabled=true;
  try{
   if(!navigator.clipboard?.writeText)throw new Error('Clipboard unavailable');
   await navigator.clipboard.writeText(step.command);status.textContent='已复制这一整段命令。';
  }catch{status.textContent='未能访问剪贴板，请手动选择上方完整命令复制。'}
  finally{button.disabled=false;button.focus({preventScroll:true})}
 }
 let composing=false;
 document.addEventListener('compositionstart',e=>{if(e.target.id==='tk-search')composing=true});
 document.addEventListener('compositionend',e=>{if(e.target.id==='tk-search'){composing=false;route({q:e.target.value,tool:''},true,true)}});
 document.addEventListener('input',e=>{if(state.view==='toolkit'&&e.target.id==='tk-search'&&!composing&&!e.isComposing)route({q:e.target.value,tool:''},true,true)});
 document.addEventListener('change',e=>{
  if(state.view!=='toolkit')return;
  if(e.target.id==='tk-access'){route({access:e.target.value,tool:''});$('#tk-access').focus()}
  if(e.target.id==='tk-only'){route({only:e.target.checked,tool:''});$('#tk-only').focus()}
 });
 document.addEventListener('click',e=>{
  if(state.view!=='toolkit')return;
  const b=e.target.closest('button');if(!b)return;
  if(b.hasAttribute('data-tk-group')){route({group:b.dataset.tkGroup,tool:''});$("[data-tk-group='"+read().group+"']").focus()}
  if(b.hasAttribute('data-tk-clear')){route({q:'',group:'all',access:'all',only:false,tool:''});$('#tk-search').focus()}
  if(b.hasAttribute('data-tk-copy'))copy(b);
  if(b.hasAttribute('data-tk-save')){
   const id=b.dataset.tkSave;if(!guides.has(id))return;
   saved.has(id)?saved.delete(id):saved.add(id);
   const ok=store('aip.saved',[...saved]);renderNav();
   if(read().only){renderResults();$('#tk-only').focus({preventScroll:true})}
   else{b.classList.toggle('active',saved.has(id));b.setAttribute('aria-pressed',String(saved.has(id)));b.setAttribute('aria-label',(saved.has(id)?'取消关注':'关注')+' '+tasks.get(id).name)}
   toast(ok?(saved.has(id)?'已加入我的关注':'已取消关注'):'关注仅在本次会话有效');
  }
 });
 document.addEventListener('toggle',e=>{
  const el=e.target;
  if(!el.matches?.('[data-tk-guide]'))return;
  el.open?openIds.add(el.dataset.tkGuide):openIds.delete(el.dataset.tkGuide);
  el.closest('.tk-card').classList.toggle('is-open',el.open);
  if(!el.open&&state.view==='toolkit'&&read().tool===el.dataset.tkGuide){history.replaceState(null,'',href(read(),{tool:''}));state.task=null}
 },true);
 document.addEventListener('keydown',e=>{
  if(state.view==='toolkit'&&e.key==='/'&&!e.ctrlKey&&!e.metaKey&&!e.altKey&&!modal.open&&!palette.open&&!e.target.matches('input,textarea,select,[contenteditable=true]')){
   e.preventDefault();e.stopImmediatePropagation();$('#tk-search')?.focus();
  }
 },true);
 const previous=renderMain;
 let wasToolkit=false;
 renderMain=function(){
  if(state.view==='toolkit'){wasToolkit=true;lastMain='';page();return}
  if(wasToolkit){lastMain='';$('#content').setAttribute('aria-live','polite');wasToolkit=false}
  return previous();
 };
 const previousTask=renderTask;
 renderTask=function(){
  if(state.view==='toolkit'&&guides.has(state.task)){
   const el=$("[data-tk-guide='"+state.task+"']");if(el){el.open=true;openIds.add(state.task)}
   if(modal.open&&modal.dataset.type==='task')hideModal(false);
   return;
  }
  return previousTask();
 };
 const previousExport=exportView;
 exportView=function(){
  if(state.view!=='toolkit')return previousExport();
  download('toolkit-guides.json',JSON.stringify({...data,items:rows(read()),scope:'当前筛选的官方上手指南；运行未实测'},null,2),'application/json;charset=utf-8');
 };
 if(state.view==='toolkit')page();
 return {read,href,rows,card,copy};
})();

