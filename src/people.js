'use strict';
/* Public work -> person -> related work. No inferred employers or talent scores. */
const PeopleUI = (() => {
 const h = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const https = raw => {try {const u = new URL(raw);return u.protocol === 'https:' && !u.username && !u.password && !/[\s\x00-\x1f]/.test(raw) ? u.href : ''} catch {return ''}};
 const labels = rows => new Map((rows || []).map(x => [x.id,x.title]));
 const day = raw => /^\d{4}-\d{2}-\d{2}$/.test(raw || '') && Number.isFinite(Date.parse(raw)) && new Date(raw).toISOString().slice(0,10) === raw;
 const today = (now = Date.now()) => new Date(Number(now) + 8*3600000).toISOString().slice(0,10);
 function read(hash, data) {
  const p = new URLSearchParams(String(hash || '').split('?')[1] || '');
  return {view:['updates','influence'].includes(p.get('view')) ? p.get('view') : 'directory',
   dim:['research','ecosystem','industry'].includes(p.get('dim')) ? p.get('dim') : 'all',
   type:labels(data.influence_types).has(p.get('type')) ? p.get('type') : 'all',
   area:labels(data.areas).has(p.get('area')) ? p.get('area') : 'all',
   role:labels(data.roles).has(p.get('role')) ? p.get('role') : 'all',
   q:(p.get('q') || '').trim().slice(0,200), following:p.get('following') === '1',
   discover:p.get('discover') === '1', person:(p.get('person') || '').slice(0,100)};
 }
 function href(s = {}, patch = {}) {
  const n = {...s,...patch}, p = new URLSearchParams();
  for (const k of ['view','type','area','role','dim','q','person']) if(n[k] && n[k] !== 'all' && !(k === 'view' && n[k] === 'directory')) p.set(k,n[k]);
  if(n.following)p.set('following','1');if(n.discover)p.set('discover','1');
  return '#/people'+(p.size?'?'+p:'');
 }
 function followIds(raw, data) {
  const all = new Set((data.people || []).map(p => p.id));
  return new Set(Array.isArray(raw) ? raw.filter(x => typeof x === 'string' && all.has(x)) : []);
 }
 function text(p) {return [p.name,...(p.aliases || []),p.intro,p.watch,...(p.works || []).map(w => w.title)].join(' ').toLowerCase()}
 function influenceTypes(p) {
  const ids=[];
  if(p.roles.includes('educator') || p.areas.includes('evaluation') || ['sam-altman','dario-amodei','ethan-mollick','yoshua-bengio','geoffrey-hinton','yann-lecun'].includes(p.id))ids.push('ideas');
  if(p.roles.includes('builder') || p.impact.dimensions.includes('ecosystem') || p.areas.includes('systems'))ids.push('technology');
  if(p.roles.includes('researcher') || p.impact.dimensions.includes('research'))ids.push('research');
  if(p.roles.includes('founder') || p.impact.dimensions.includes('industry') || p.areas.includes('product'))ids.push('industry');
  if(p.areas.includes('robotics') || p.areas.includes('multimodal') || ['demis-hassabis','jensen-huang','ethan-mollick','sam-altman'].includes(p.id))ids.push('future');
  return [...new Set(ids)];
 }
 function rows(data,s,saved = new Set(),now = Date.now()) {
  const matches=(data.people || []).filter(p => (s.type === 'all' || influenceTypes(p).includes(s.type)) && (s.dim === 'all' || (p.impact?.dimensions || []).includes(s.dim)) && (s.area === 'all' || p.areas.includes(s.area)) &&
   (s.role === 'all' || p.roles.includes(s.role)) && (!s.discover || p.discovery === 'work') &&
   (!s.following || saved.has(p.id)) && (!s.q || text(p).includes(s.q.toLowerCase())));
  // Only original dates of real, non-future events affect order. Reviews never bump a person.
  const latest=new Map(matches.map(p=>[p.id,latestSignal(p,data,now)?.date||'']));
  return matches.sort((a,b)=>latest.get(b.id).localeCompare(latest.get(a.id))||a.id.localeCompare(b.id));
 }
 function events(data,s,saved = new Set(),now = Date.now()) {
  const allowed = new Set(rows(data,{...s,q:''},saved,now).map(x => x.id)), persons = new Map(data.people.map(x=>[x.id,x]));
  const q = s.q.toLowerCase();
  return (data.events || []).filter(e => day(e.date) && e.date <= today(now) && e.people.some(id => allowed.has(id)) &&
   (!q || [e.title,e.summary,...e.people.map(id => persons.has(id)?text(persons.get(id)):'')].join(' ').toLowerCase().includes(q)))
   .sort((a,b)=>b.date.localeCompare(a.date)||a.id.localeCompare(b.id));
 }

 const impactTitles={research:'学术与研究',ecosystem:'开源与技术生态',industry:'产品与产业落地'};
 function influenceBlock(p,data,s){
  const titles=labels(data.influence_types);
  return '<div class="pp-influence-types" aria-label="影响力类型">'+influenceTypes(p).map(id=>nav(s,{type:id,person:''},h(titles.get(id)),'pp-influence-type')).join('')+'</div>';
 }
 function latestSignal(p,data,now=Date.now()){
  return (data.events||[]).filter(e=>e.people.includes(p.id)&&day(e.date)&&e.date<=today(now)).sort((a,b)=>b.date.localeCompare(a.date)||a.id.localeCompare(b.id))[0]||null;
 }
 function latestBlock(p,data,now=Date.now(),expanded=false){
  const e=latestSignal(p,data,now), source=p.works[0],date=e?.date||'',age=e?Math.floor((Date.parse(today(now))-Date.parse(date))/86400000):null;
  if(!e)return '<section class="pp-latest pp-latest-unverified"><span>最新进展 · 待补证据</span><strong>暂无本站已核验的独立动态</strong><p>最后已知贡献：'+h(source.title)+'。这不是“本人近期没有新工作”。</p><small>人物档案上次核对 '+h(p.checked)+' · <a href="'+h(https(source.url))+'" target="_blank" rel="noopener noreferrer">查看原始作品 ↗</a></small></section>';
  return '<section class="pp-latest"><span>最新已收录进展'+(age!==null&&age>90?' · 历史记录':'')+'</span><time datetime="'+h(date)+'">'+h(date.replaceAll('-','.'))+'</time><strong>'+h(e.title)+'</strong>'+(expanded?'<p>'+h(e.summary)+'</p><p class="pp-latest-boundary">证据边界：'+h(e.boundary)+'</p>':'')+'<small>原始发布 '+h(e.date)+' · 核验 '+h(e.checked)+' · <a href="'+h(https(e.url))+'" target="_blank" rel="noopener noreferrer">'+h(e.source)+' ↗</a></small></section>';
 }
 function impactBlock(p,expanded=false){
  const i=p.impact||{dimensions:[],basis:''};
  return '<section class="pp-impact"><span>影响力证据方向 · 非综合分</span><div class="pp-impact-tags">'+i.dimensions.map(d=>'<em>'+h(impactTitles[d]||d)+'</em>').join('')+'</div>'+(expanded?'<p>归类依据：'+h(i.basis)+'</p>':'')+'</section>';
 }
 const outgoing = (url,label) => https(url)?'<a href="'+h(https(url))+'" target="_blank" rel="noopener noreferrer">'+h(label)+' <span aria-hidden="true">↗</span></a>':'<span>来源待补</span>';
 const nav = (s,patch,label,cls='') => '<a class="'+cls+'" data-people-link href="'+h(href(s,patch))+'">'+label+'</a>';
 const initials = p => (p.aliases.find(a=>/[A-Za-z]/.test(a)) || p.name).split(/\s+/).map(x=>x[0]).slice(0,2).join('').toUpperCase();
 const follow = (p,saved) => '<button type="button" class="pp-follow '+(saved.has(p.id)?'is-followed':'')+'" data-people-follow="'+h(p.id)+'" aria-pressed="'+saved.has(p.id)+'" aria-label="'+(saved.has(p.id)?'取消关注 ':'关注 ')+h(p.name)+'">'+(saved.has(p.id)?'✓ 已关注':'＋ 关注')+'</button>';
 function chips(p,data,s) {
  const areas = labels(data.areas);
  return '<div class="pp-tags">'+p.areas.map(id=>nav(s,{area:id,person:''},h(areas.get(id)),'pp-tag')).join('')+'</div>';
 }
 function card(p,data,s,saved,now=Date.now()) {
  const roles=labels(data.roles),e=latestSignal(p,data,now),source=p.sources[0];
  return '<article class="pp-card" data-person-card="'+h(p.id)+'" data-latest-date="'+h(e?.date||'')+'"><header><span class="pp-avatar" aria-hidden="true">'+h(initials(p))+'</span><div class="pp-identity">'+nav(s,{person:p.id},'<h2>'+h(p.name)+'</h2>','pp-name')+'<p>'+h(p.aliases.join(' · ') || p.roles.map(id=>roles.get(id)).join(' · '))+'</p></div>'+follow(p,saved)+'</header>'+influenceBlock(p,data,s)+chips(p,data,s)+
   latestBlock(p,data,now)+'<section class="pp-work-preview"><h3>代表作</h3><ul>'+p.works.map(w=>'<li><strong>'+outgoing(w.url,w.title)+'</strong><small>'+h(w.relation)+'</small></li>').join('')+'</ul></section>'+
   '<section class="pp-achievements"><h3>为什么值得关注</h3><p class="pp-intro">'+h(p.intro)+'</p><p class="pp-card-watch"><strong>接下来验证：</strong>'+h(p.watch)+'</p>'+(source?'<div class="pp-achievement-source">'+outgoing(source.url,'查看人物资料')+'</div>':'')+'</section>'+
   ((s.view==='influence')?impactBlock(p,true):'')+
   '<footer><span>'+h(p.discovery==='work'?'从作品发现':'公开贡献档案')+'</span>'+nav(s,{person:p.id},'人物档案 <span aria-hidden="true">→</span>','pp-more')+'</footer></article>';
 }
 function eventCard(e,data,s) {
  const persons = new Map(data.people.map(x=>[x.id,x])), kinds={paper:'论文',article:'作者文章',talk:'公开演讲',release:'项目发布'};
  return '<article class="pp-event" data-person-event="'+h(e.id)+'"><time datetime="'+h(e.date)+'">'+h(e.date.replaceAll('-','.'))+'</time><div><div class="pp-event-meta"><span>'+h(kinds[e.kind])+'</span><span>'+h(e.source)+'</span></div><h3>'+outgoing(e.url,e.title)+'</h3><p>'+h(e.summary)+'</p><div class="pp-event-people">'+e.people.filter(id=>persons.has(id)).map(id=>nav(s,{person:id},h(persons.get(id).name),'pp-person-chip')).join('')+'</div><details><summary>来源与边界</summary><p>'+h(e.boundary)+'</p><p>原始发布 '+h(e.date)+' · 资料核对 '+h(e.checked)+'。仅关联本站已建档作者，完整名单见原文。</p>'+outgoing(e.url,e.source)+'</details></div></article>';
 }
 function stream(data,s,saved,now=Date.now(),person='') {
  const all=events(data,s,saved,now).filter(e=>!person||e.people.includes(person));
  const cut = new Date(Date.parse(today(now))-29*86400000).toISOString().slice(0,10);
  const recent=all.filter(e=>e.date>=cut),old=all.filter(e=>e.date<cut);
  if(!all.length)return '<div class="pp-empty"><h3>暂无已收录动态</h3><p>人物档案持续保留；未收录不代表本人没有新工作。</p></div>';
  return '<section class="pp-stream"><h2 class="pp-section-title">近 30 日 <small>'+recent.length+' 条已收录</small></h2>'+
   (recent.length?recent.map(e=>eventCard(e,data,s)).join(''):'<p class="pp-note">近 30 日暂无匹配记录。更早的作品保留在下方。</p>')+
   (old.length?'<details class="pp-archive"'+(!recent.length?' open':'')+'><summary>历史作品与观点 <span>'+old.length+' 条 · 保留原始日期</span></summary>'+old.map(e=>eventCard(e,data,s)).join('')+'</details>':'')+'</section>';
 }
 function profile(p,data,s,saved,now) {
  const mine=data.events.filter(e=>e.people.includes(p.id)),co=new Set(mine.filter(e=>e.kind==='paper').flatMap(e=>e.people).filter(id=>id!==p.id));
  const collaborators=data.people.filter(x=>co.has(x.id));
  return nav(s,{person:''},'← 返回'+(s.view==='updates'?'人物动态':'人物目录'),'pp-back')+
   '<article class="pp-profile" data-profile="'+h(p.id)+'"><header class="pp-profile-head"><span class="pp-avatar large" aria-hidden="true">'+h(initials(p))+'</span><div><p class="pp-kicker">PEOPLE / IDEAS / WORK</p><h1>'+h(p.name)+'</h1><p>'+h(p.aliases.join(' · ') || p.roles.map(id=>labels(data.roles).get(id)).join(' · '))+'</p></div>'+follow(p,saved)+'</header>'+influenceBlock(p,data,s)+chips(p,data,s)+
   '<p class="pp-profile-intro">'+h(p.intro)+'</p>'+latestBlock(p,data,now,true)+impactBlock(p,true)+'<div class="pp-profile-columns"><section><h2>做过什么</h2><div class="pp-works">'+p.works.map(w=>'<article><span>'+h(w.relation)+'</span><h3>'+outgoing(w.url,w.title)+'</h3></article>').join('')+'</div></section><aside class="pp-watch"><span>编辑观察 · 不是本人引语</span><h2>接下来关注什么？</h2><p>'+h(p.watch)+'</p></aside></div>'+
   '<section class="pp-sources"><h2>直接关注一手资料</h2>'+p.sources.map(x=>'<div>'+outgoing(x.url,x.label)+'<small>'+h(({personal:'本人主页',institution:'机构资料',paper:'原始论文',project:'作者项目',article:'本人文章'})[x.kind])+'</small></div>').join('')+'<p class="pp-note">资料核对 '+h(p.checked)+'。作品列表不是完整履历，未逐项核验的任职不显示为现职。</p></section>'+
   (p.related.length?'<section class="pp-profile-related"><h2>继续看站内档案</h2><p class="pp-note">组织与技术方向的延伸阅读，不代表这些版本或成果由该人物独自完成。</p>'+p.related.filter(r=>/^#\/(hot|progress|benchmarks)\?/.test(r.href||'')).map(r=>'<a class="pp-related-link" href="'+h(r.href)+'">'+h(r.label)+' <span aria-hidden="true">→</span></a>').join('')+'</section>':'')+
   (collaborators.length?'<section class="pp-coauthors"><h2>从同篇论文继续发现</h2><p class="pp-note">仅表示共同署名；不据此推断师生关系、贡献比例或当前同事关系。</p><div>'+collaborators.map(x=>nav(s,{person:x.id},h(x.name),'pp-person-chip')).join('')+'</div></section>':'')+
   stream(data,{...s,type:'all',area:'all',role:'all',q:'',following:false,discover:false},saved,now,p.id)+'</article>';
 }
 function controls(data,s,saved) {
  const chip=(field,id,title)=>{
   const active=s[field]===id;
   return '<a class="pp-filter '+(active?'active':'')+'" data-people-link href="'+h(href(s,{[field]:id,person:''}))+'"'+(active?' aria-current="true"':'')+'>'+h(title)+'</a>';
  };
  return '<nav class="pp-type-filters" aria-label="人物影响力类型">'+chip('type','all','全部类型')+data.influence_types.map(x=>chip('type',x.id,x.title)).join('')+'</nav><div class="pp-controls"><label class="pp-search"><span aria-hidden="true">⌕</span><input id="pp-search" type="search" autocomplete="off" aria-label="搜索人物、作品与观点" placeholder="搜索姓名、作品、观点或问题…" value="'+h(s.q)+'"><kbd>/</kbd></label><label class="pp-role">公开身份<select id="pp-role"><option value="all">全部身份</option>'+data.roles.map(x=>'<option value="'+x.id+'"'+(s.role===x.id?' selected':'')+'>'+h(x.title)+'</option>').join('')+'</select></label></div><nav class="pp-filters" aria-label="人物研究方向">'+chip('area','all','全部方向')+data.areas.map(x=>chip('area',x.id,x.title)).join('')+'</nav><div class="pp-options"><label><input id="pp-following" type="checkbox"'+(s.following?' checked':'')+'>只看关注 <span>'+saved.size+'</span></label><label><input id="pp-discover" type="checkbox"'+(s.discover?' checked':'')+'>从作品发现</label>'+nav(s,{q:'',type:'all',area:'all',role:'all',following:false,discover:false,person:''},'清除筛选','pp-reset')+'</div>';
 }
 function page(data,s,saved=new Set(),now=Date.now()) {
  let content='';
  if(s.person){const p=data.people.find(x=>x.id===s.person);content=p?profile(p,data,s,saved,now):'<div class="pp-empty"><h1>未找到这个人物档案</h1>'+nav(s,{person:''},'返回人物目录','pp-more')+'</div>'}
  else {
   const list=rows(data,s,saved,now),n=s.view==='updates'?events(data,s,saved,now).length:list.length;
   content='<header class="pp-head"><div><p class="pp-kicker">PEOPLE / IDEAS / WORK</p><h1>AI 影响力人物图谱</h1><p>从思想、技术、科研、产业与未来议题，找到值得持续关注的人。</p></div><div class="pp-stats"><span><b>'+data.people.length+'</b>人物档案</span><span><b>'+data.events.length+'</b>公开记录</span><span><b>'+saved.size+'</b>我的关注</span></div></header>'+
   '<div class="pp-principle"><strong>先看为什么值得关注</strong><span>类型可以并列，档案按已收录动态的原始发布日期排序；没有新动态不等于本人没有新工作。</span></div>'+
   '<nav class="pp-tabs" aria-label="人物视图">'+[['directory','人物图谱'],['influence','影响力证据'],['updates','人物动态']].map(([id,title])=>'<a data-people-link href="'+h(href(s,{view:id,person:''}))+'"'+(s.view===id?' aria-current="page"':'')+'>'+title+'</a>').join('')+'</nav>'+(s.view==='influence'?'<section class="pp-influence-guide"><h2>按证据看影响，而不是给人打分</h2><p>五类回答“为什么关注”；学术、生态、产业三种证据方向回答“依据是什么”。类型可并列，不按名气、作品数量或主观印象生成总分。</p><nav aria-label="影响力证据方向">'+[['all','全部证据'],...Object.entries(impactTitles)].map(([id,label])=>{const active=s.dim===id;return '<a class="pp-filter '+(active?'active':'')+'" data-people-link href="'+h(href(s,{dim:id,person:''}))+'"'+(active?' aria-current="true"':'')+'>'+h(label)+'</a>'}).join('')+'</nav></section>':'')+controls(data,s,saved)+
   '<p class="pp-results" role="status">'+n+(s.view==='updates'?' 条已收录记录 · 按原始日期排列':s.view==='influence'?' 位人物 · 最近更新优先 · 影响力维度不是名次':' 位匹配人物 · 最近更新优先 · 暂无动态者置后')+'</p>'+
   (s.view==='updates'?stream(data,s,saved,now):list.length?'<div class="pp-grid">'+list.map(p=>card(p,data,s,saved,now)).join('')+'</div>':'<div class="pp-empty"><h2>'+(s.following&&!saved.size?'还没有关注人物':'没有匹配人物')+'</h2><p>可以搜索作品，也可以放宽筛选条件。</p>'+nav(s,{q:'',type:'all',area:'all',role:'all',following:false,discover:false},'浏览全部人物','pp-more')+'</div>');
  }
  return '<div class="pp-page">'+content+'<footer class="pp-foot"><details><summary>收录、时间与隐私规则</summary><p>'+h(data.note)+'</p><p>只整理公开职业资料与作品，不收集私人联系方式。作者观点与研究结果分开；共同署名不等于全部贡献。</p><p>关注仅保存在当前浏览器，不会自动订阅社交账号，不向服务器上传。核对日期不是作品发布日期。</p></details><span>资料核对 '+h(data.checked)+' · 人工编选</span></footer></div>';
 }
 return {h,https,read,href,followIds,influenceTypes,rows,events,latestSignal,latestBlock,impactBlock,card,page,profile,today,day};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=PeopleUI;

if(typeof document!=='undefined'&&typeof APP!=='undefined'&&APP.people)(()=>{
 const data=APP.people,key='aic.people.follows.v1',byid=new Map(data.people.map(x=>[x.id,x]));
 let followed=new Set(),composing=false;
 try{followed=PeopleUI.followIds(JSON.parse(localStorage.getItem(key)||'[]'),data)}catch{}
 pages.people=['AI 人物','people'];
 PATHS.people='<circle cx="9" cy="7" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 4a3 3 0 0 1 0 6M18 14a5 5 0 0 1 3 4v3"/>';
 const read=()=>PeopleUI.read(location.hash,data);
 const previousNav=renderNav;
 renderNav=function(){
  previousNav();
  const link=document.createElement('a');link.href='#/people';link.className='navitem'+(state.view==='people'?' active':'');link.dataset.peopleNav='';
  if(state.view==='people')link.setAttribute('aria-current','page');
  link.innerHTML=icon('people')+'<span>AI 人物</span><small>'+data.people.length+'</small>';
  const anchor=document.querySelector('#nav a[href="#/activity"]');
  if(anchor)anchor.after(link);else document.getElementById('nav').appendChild(link);
 };
 function renderPeople(){
  renderNav();lastMain='';document.body.classList.remove('nav-open');
  $('#hero').hidden=true;$('#stats').hidden=true;$('.workspace').hidden=true;$('#compare-tray').hidden=true;
  $('#legacy-saved').innerHTML='';const root=$('#vertical-root');root.hidden=false;root.innerHTML=PeopleUI.page(data,read(),followed);
 }
 function savedPanel(){
  document.getElementById('pp-saved')?.remove();
  const root=$('#legacy-saved');if(!root)return;
  const section=document.createElement('section');section.id='pp-saved';section.className='pp-saved';
  const matches=PeopleUI.rows(data,{...read(),dim:'all',area:'all',role:'all',q:'',discover:false,following:true},followed);
  section.innerHTML='<h2>已关注人物 <small>'+matches.length+'</small></h2><p>人物关注保存在本机，与项目、模型关注分开维护。</p><div>'+matches.map(p=>'<a href="'+PeopleUI.href({person:p.id})+'">'+PeopleUI.h(p.name)+'</a>').join('')+'</div><a class="pp-more" href="#/people?following=1">管理人物关注 →</a>';
  root.prepend(section);
 }
 function reverseLinks(){
  if(state.view!=='hot')return;
  document.querySelectorAll('[data-product-id]').forEach(card=>{
   const matches=data.people.filter(p=>p.related.some(r=>r.kind==='product'&&r.id===card.dataset.productId));
   if(!matches.length||card.querySelector('.pp-reverse'))return;
   const aside=document.createElement('aside');aside.className='pp-reverse';
   aside.innerHTML='<span>相关人物 · 公开组织关系</span>'+matches.map(p=>'<a href="'+PeopleUI.href({person:p.id})+'">'+PeopleUI.h(p.name)+' ↗</a>').join('');
   card.appendChild(aside);
  });
 }
 const previousRender=renderMain;
 renderMain=function(){if(state.view==='people')return renderPeople();const result=previousRender();if(state.view==='saved')savedPanel();reverseLinks();return result};
 function route(patch,replace=false){
  const hash=PeopleUI.href(read(),patch);history[replace?'replaceState':'pushState'](null,'',hash);lastMain='';parseRoute();
 }
 function search(input){
  const pos=input.selectionStart;route({q:input.value,person:''},true);const next=$('#pp-search');next?.focus({preventScroll:true});try{next?.setSelectionRange(pos,pos)}catch{}
 }
 document.addEventListener('compositionstart',e=>{if(e.target.id==='pp-search')composing=true});
 document.addEventListener('compositionend',e=>{if(e.target.id==='pp-search'){composing=false;search(e.target)}});
 document.addEventListener('input',e=>{if(e.target.id==='pp-search'&&!composing&&!e.isComposing)search(e.target)});
 document.addEventListener('change',e=>{
  const fields={'pp-role':'role','pp-following':'following','pp-discover':'discover'},field=fields[e.target.id];if(!field)return;
  const id=e.target.id;route({[field]:field==='role'?e.target.value:e.target.checked,person:''});document.getElementById(id)?.focus({preventScroll:true});
 });
 document.addEventListener('click',e=>{
  const a=e.target.closest('a[data-people-link]');
  if(a&&e.button===0&&!e.metaKey&&!e.ctrlKey&&!e.altKey&&!e.shiftKey){
   e.preventDefault();const before=read();history.pushState(null,'',a.getAttribute('href'));lastMain='';parseRoute();
   if(before.person!==read().person){window.scrollTo({top:0,behavior:'instant'});$('#main').focus({preventScroll:true})}return;
  }
  const b=e.target.closest('[data-people-follow]');if(!b||!byid.has(b.dataset.peopleFollow))return;
  const id=b.dataset.peopleFollow;followed.has(id)?followed.delete(id):followed.add(id);
  let persisted=true;try{localStorage.setItem(key,JSON.stringify([...followed]))}catch{persisted=false}
  if(state.view==='people')renderPeople();else if(state.view==='saved')savedPanel();
  (document.querySelector('[data-people-follow="'+id+'"]')||$('#pp-following'))?.focus({preventScroll:true});
  toast(persisted?(followed.has(id)?'已关注 '+byid.get(id).name:'已取消人物关注'):'本次会话已更新；浏览器不允许持久保存');
 });
 document.addEventListener('keydown',e=>{
  if(state.view==='people'&&e.key==='/'&&!e.metaKey&&!e.ctrlKey&&!e.altKey&&!modal.open&&!palette.open&&!e.target.matches('input,textarea,select,[contenteditable=true]')){e.preventDefault();e.stopImmediatePropagation();$('#pp-search')?.focus()}
 },true);
 window.addEventListener('storage',e=>{if(e.key!==key)return;try{followed=PeopleUI.followIds(JSON.parse(e.newValue||'[]'),data)}catch{followed=new Set()}if(state.view==='people')renderPeople();else if(state.view==='saved')savedPanel()});
 // Register before reparsing, so direct hash links and browser back both work.
 lastMain='';parseRoute();
})();
