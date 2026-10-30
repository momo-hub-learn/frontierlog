'use strict';
/* Editorial hot list. Heat is a transparent FrontierLog signal, never claimed as web traffic. */
const HOT=APP.hot;
const PRODUCT_RADAR=APP.product_radar||{groups:[],items:[],checked:'',note:''};
const PRODUCT_GROUPS=new Map((PRODUCT_RADAR.groups||[]).map(x=>[x.id,x]));
const HOT_ITEMS=new Map(HOT.items.map(x=>[x.id,x]));
const HOT_CATS=new Map(HOT.categories.map(x=>[x.id,x]));
PATHS.fire='<path d="M13 2s1 4-2 6c-1-3-4-3-4-6-3 3-4 7-2 11 2 5 6 8 7 8s6-2 7-7c1-5-2-8-4-10 0 3-1 5-3 6 1-4-1-6 1-8z"/>';
const H_TREND={up:['↗','上升'],flat:['—','持平'],down:['↘','回落']};
function hHeatBand(score){
 const n=Number(score);
 return n>=98?{key:'extreme',label:'爆热'}:n>=95?{key:'high',label:'高热'}:n>=90?{key:'rising',label:'升温'}:{key:'watch',label:'关注'};
}
const H_ICON={all:'sparkles',model:'cpu',product:'box',industry:'factory',research:'flask',benchmark:'gauge',open:'github','research-eval':'flask'};
const H_PRIMARY_TABS=[
 {id:'all',title:'全部',icon:'sparkles'},
 {id:'open',title:'平台热榜',icon:'github',href:'#/hot?tab=github'},
 {id:'model',title:'模型',icon:'cpu'},
 {id:'product',title:'产品',icon:'box'},
 {id:'industry',title:'行业',icon:'factory'},
 {id:'research-eval',title:'研究 / 评测',icon:'flask'}
];
function hParams(){return new URLSearchParams(location.hash.split('?')[1]||'')}
function hNormalizeCat(raw){return ['research','benchmark','research-eval'].includes(raw)?'research-eval':HOT_CATS.has(raw)?raw:'all'}
function hState(){const p=hParams(),ptag=p.get('ptag');return {cat:hNormalizeCat(p.get('cat')),q:(p.get('q')||'').slice(0,300).trim(),ptag:(PRODUCT_RADAR.filters||[]).some(x=>x.id===ptag)?ptag:'all',item:HOT_ITEMS.has(p.get('item'))?p.get('item'):null}}
function hRoute(patch={},replace=false){
 const p=hParams();
 // Category navigation leaves the platform view, including its private filters.
 // Keep a news search across news categories, but never carry a repository query over.
 if(Object.prototype.hasOwnProperty.call(patch,'cat')){
  const current=hNormalizeCat(p.get('cat')),next=hNormalizeCat(patch.cat);
  if(['github','hf'].includes(p.get('tab'))||current==='product'||next==='product')p.delete('q');
  for(const key of ['tab','ghcat','hftype','hfq','pview','scene','investor','kind','product','legacy'])p.delete(key)
 }
 for(const [k,v]of Object.entries(patch)){
  if(v===null||v===undefined||v==='')p.delete(k);else p.set(k,String(v))
 }
 const h='#/hot'+(p.size?'?'+p.toString():'');
 if(replace||h===location.hash)history.replaceState(null,'',h);else history.pushState(null,'',h);
 parseRoute()
}
function hCatMatches(cat,itemCat){return cat==='all'||cat===itemCat||(cat==='research-eval'&&['research','benchmark'].includes(itemCat))}
function hRows(){const s=hState(),q=s.q.toLowerCase();return HOT.items.filter(x=>hCatMatches(s.cat,x.category)&&(!q||[x.title,x.summary,x.why,x.source,HOT_CATS.get(x.category)?.title].join(' ').toLowerCase().includes(q))).sort((a,b)=>b.heat-a.heat||b.published.localeCompare(a.published))}
function hTrend(x){const [g,label]=H_TREND[x.trend]||H_TREND.flat;return `<span class="h-trend ${x.trend}" title="${label}">${g}</span>`}
function hCategoryCount(id){
 if(id==='open')return (APP.github_hot?.items||[]).length+(APP.huggingface_hot?.items||[]).length;
 const cats=id==='research-eval'?['research','benchmark']:[id];
 const news=id==='all'?HOT.items.length:HOT.items.filter(x=>cats.includes(x.category)).length;
 return id==='product'?news+(PRODUCT_RADAR.items||[]).length:news
}
function hTabs(s){
 const platform=hParams().get('tab'),openActive=['github','hf'].includes(platform);
 return '<nav class="h-tabs" aria-label="热点分类">'+H_PRIMARY_TABS.map(t=>{
  const active=t.id==='open'?openActive:!openActive&&s.cat===t.id;
  if(t.href)return '<a class="h-tab '+(active?'active':'')+'" href="'+t.href+'" '+(active?'aria-current="page"':'')+'>'+icon(t.icon)+esc(t.title)+'<small>'+hCategoryCount(t.id)+'</small></a>';
  return '<button class="h-tab '+(active?'active':'')+'" data-ha="cat" data-id="'+t.id+'" aria-pressed="'+(active?'true':'false')+'">'+icon(t.icon)+esc(t.title)+'<small>'+hCategoryCount(t.id)+'</small></button>'
 }).join('')+'</nav>'
}
function hOpenTabs(active){
 const gh=(APP.github_hot?.items||[]).length,hf=(APP.huggingface_hot?.items||[]).length;
 const current=id=>active===id?' aria-current="page"':'';
 return '<nav class="h-open-tabs" aria-label="平台热榜">'+
  '<a class="'+(active==='github'?'active':'')+'" href="#/hot?tab=github"'+current('github')+'>'+icon('github')+'GitHub<small>'+gh+'</small></a>'+
  '<a class="'+(active==='hf'?'active':'')+'" href="#/hot?tab=hf"'+current('hf')+'>'+icon('layers')+'Hugging Face<small>'+hf+'</small></a>'+
 '</nav>'
}
function hProductLatest(x){return Array.isArray(x.timeline)&&x.timeline.length?x.timeline[0]:null}
function hProductEvents(rows){
 return rows.flatMap(x=>(x.timeline||[]).map(e=>({...e,product:x.name,product_id:x.id,filter_ids:x.filter_ids||[]})))
  .sort((a,b)=>b.date.localeCompare(a.date)||a.product.localeCompare(b.product)).slice(0,10)
}
function hProductFilters(s,rows){
 const all=PRODUCT_RADAR.items||[],filters=PRODUCT_RADAR.filters||[];
 const one=(id,title,count)=>'<button class="h-product-filter '+(s.ptag===id?'active':'')+'" data-ha="product-tag" data-id="'+esc(id)+'" '+(s.ptag===id?'aria-pressed="true"':'aria-pressed="false"')+'><span>'+esc(title)+'</span><small>'+count+'</small></button>';
 return '<nav class="h-product-filters" aria-label="产品标签筛选">'+one('all','全部',all.length)+filters.map(f=>one(f.id,f.title,all.filter(x=>(x.filter_ids||[]).includes(f.id)).length)).join('')+'</nav>'
}
function hProductTimeline(rows){
 const events=hProductEvents(rows);
 if(!events.length)return '<section class="h-product-moves empty"><div class="h-product-moves-head"><div><p class="eyebrow">RECENT MOVES</p><h3>近期进展</h3></div><span>暂无带日期的一手进展</span></div></section>';
 return '<section class="h-product-moves"><div class="h-product-moves-head"><div><p class="eyebrow">RECENT MOVES / VERIFIED</p><h3>近期进展</h3><p>只放可回到一手来源的发布、采用、治理、Benchmark 或融资节点。</p></div><span>'+events.length+' 条</span></div><div class="h-product-move-list">'+events.map(e=>'<a class="h-product-move" href="'+safeLink(e.url)+'" target="_blank" rel="noopener noreferrer"><time>'+esc(e.date.slice(5).replace('-','.'))+'</time><span class="h-product-move-kind">'+esc(e.kind)+'</span><strong>'+esc(e.product)+'</strong><p>'+esc(e.title)+'</p>'+icon('external')+'</a>').join('')+'</div></section>'
}
function hProductRadar(s){
 if(s.cat!=='product')return '';
 const q=String(s.q||'').toLowerCase();
 const rows=(PRODUCT_RADAR.items||[]).filter(x=>
  (s.ptag==='all'||(x.filter_ids||[]).includes(s.ptag))&&
  (!q||[x.name,x.company,x.summary,x.source_label,...(x.tags||[]),...(x.timeline||[]).map(e=>e.title)].join(' ').toLowerCase().includes(q))
 );
 const groups=(PRODUCT_RADAR.groups||[]).map(g=>({...g,items:rows.filter(x=>x.group===g.id)})).filter(g=>g.items.length);
 const card=x=>{const latest=hProductLatest(x);return '<article class="h-product-card">'+
  '<div class="h-product-cardtop"><div class="h-product-tags">'+(x.tags||[]).map((t,i)=>'<span class="'+(i===0?'primary':'')+'">'+esc(t)+'</span>').join('')+'</div><small>'+esc(x.source_label)+'</small></div>'+
  '<h3>'+esc(x.name)+'</h3><p class="h-product-company">'+esc(x.company)+'</p>'+
  '<p class="h-product-summary">'+esc(x.summary)+'</p>'+
  (latest?'<a class="h-product-latest" href="'+safeLink(latest.url)+'" target="_blank" rel="noopener noreferrer"><span>最近进展</span><time>'+esc(latest.date.slice(5).replace('-','.'))+'</time><strong>'+esc(latest.title)+'</strong>'+icon('external')+'</a>':'<div class="h-product-latest empty"><span>最近进展</span><strong>近期一手进展待补；不拿投资标签冒充产品更新。</strong></div>')+
  '<div class="h-product-evidence"><b>验证</b><span>'+esc(x.evidence)+'</span></div>'+
  '<div class="h-product-boundary"><b>边界</b><span>'+esc(x.boundary)+'</span></div>'+
  '<footer><a href="'+safeLink(x.product_url)+'" target="_blank" rel="noopener noreferrer">产品官网 '+icon('external')+'</a><a href="'+safeLink(x.source_url)+'" target="_blank" rel="noopener noreferrer">验证标签 '+icon('external')+'</a></footer>'+
 '</article>'};
 return '<section class="h-product-radar">'+
  '<header class="h-product-radar-head"><div><p class="eyebrow">AI PRODUCT RADAR / VERIFIED PORTFOLIO SIGNALS</p><h2>'+esc(PRODUCT_RADAR.title||'AI 产品雷达')+'</h2><p>热点流看“今天发生了什么”；产品雷达继续追踪这些 AI-native 产品最近又发生了什么，并把投资 / 孵化背景和产品能力分开。</p></div><span>'+rows.length+' / '+(PRODUCT_RADAR.items||[]).length+' 个产品</span></header>'+
  hProductFilters(s,rows)+hProductTimeline(rows)+
  (groups.length?groups.map(g=>'<section class="h-product-group"><div class="h-product-grouphead"><div><h3>'+esc(g.title)+'</h3><p>'+esc(g.description)+'</p></div><b>'+g.items.length+'</b></div><div class="h-product-grid">'+g.items.map(card).join('')+'</div></section>').join(''):'<div class="h-product-radar-empty"><h3>这个标签下暂无匹配产品</h3><p>切换标签或清除搜索。</p></div>')+
  '<footer class="h-product-radar-note">'+esc(PRODUCT_RADAR.note||'')+' · 核对 '+esc(PRODUCT_RADAR.checked||'—')+'</footer>'+
 '</section>'
}
function hEmpty(title,copy){return `<div class="h-empty"><h3>${esc(title)}</h3><p>${esc(copy)}</p><button class="button" data-ha="hot-clear-search">清除搜索与筛选</button></div>`}
function hBoard(rows){const top=rows.slice(0,5);return `<section class="h-board"><div class="h-board-head"><h2>${icon('fire')}当前热点</h2><span class="h-info">${icon('info')} 站内热度，不是全网流量</span></div>${top.length?top.map((x,i)=>`<article class="h-row"><div class="h-rank">${i+1}</div><div class="h-main"><button class="h-title" data-ha="detail" data-id="${x.id}">${esc(x.title)}</button><div class="h-sub"><span class="h-cat">${icon(H_ICON[x.category]||'sparkles')}${esc(HOT_CATS.get(x.category).title)}</span><span>${esc(x.source)}</span><span class="h-source-kind">${esc(x.source_kind)}</span><time>${esc(x.published)}</time></div></div><div class="h-heat"><strong>${x.heat}${hTrend(x)}</strong><span>热度</span></div></article>`).join(''):hEmpty('没有匹配热点','换个关键词或分类。')}</section>`}
function hStream(rows){const rest=rows.slice(5);return `<div class="h-below"><section class="h-stream">${rest.length?rest.map(x=>`<article class="h-story"><div class="h-sub"><span class="h-cat">${icon(H_ICON[x.category]||'sparkles')}${esc(HOT_CATS.get(x.category).title)}</span><time>${esc(x.published)}</time><span>${esc(x.source)}</span></div><h3>${esc(x.title)}</h3><p>${esc(x.summary)}</p><div class="h-story-foot"><a href="${safeLink(x.url)}" target="_blank" rel="noopener noreferrer">原始来源 ${icon('external')}</a><button data-ha="detail" data-id="${x.id}">为什么值得看 ${icon('arrow')}</button></div></article>`).join(''):rows.length?`<div class="h-empty"><h3>前五就是全部匹配项</h3><p>切换分类继续看。</p></div>`:''}</section><aside class="h-aside"><p class="eyebrow">HOW WE RANK</p><h3>热度不是浏览量。</h3><p>${esc(HOT.method.note)}</p><div class="h-rule"><b>时效</b><span>越新的有效变化越优先。</span></div><div class="h-rule"><b>影响范围</b><span>模型、工具链、业务环节是否真的变化。</span></div><div class="h-rule"><b>主题匹配</b><span>优先医药、制造、模型、Agent 与 Benchmark。</span></div><button class="button" data-ha="method">查看数据状态</button></aside></div>`}
function hotPage(){const s=hState(),rows=hRows();return `<section class="h-wrap"><header class="h-head"><div><p class="eyebrow"><span class="accent">●</span> HIGH-SIGNAL AI / CURATED</p><h1>热点榜<span class="accent">.</span></h1><p>不追所有新闻，只追今天最值得继续看的变化。</p></div><div class="h-meta"><span><i class="state-dot"></i> 人工核对快照</span><span>${esc(HOT.checked)}</span><span>${rows.length} / ${HOT.items.length} 条</span></div></header><div class="h-filterbar">${hTabs(s)}<label class="h-search">${icon('search')}<input id="h-search" type="search" value="${esc(s.q)}" placeholder="搜索标题、来源、摘要…" aria-label="搜索热点"><kbd>/</kbd></label></div>${hBoard(rows)}${hStream(rows)}</section>`}
function hResourceMeta(url){
 let host='';try{host=new URL(url).hostname.replace(/^www\./,'')}catch{}
 if(host.includes('artificialanalysis.ai'))return {source:'Artificial Analysis',title:'独立公开评测 / 模型页'};
 if(host==='github.com')return {source:'GitHub',title:'开源仓库 / 实现'};
 if(host.includes('cdn.openai.com'))return {source:'OpenAI',title:'论文 / PDF'};
 if(host.includes('ai.google.dev'))return {source:'Google AI for Developers',title:'开发者文档 / 发布说明'};
 if(host.includes('huggingface.co'))return {source:'Hugging Face',title:'模型 / 数据资源'};
 return {source:host||'补充资料',title:'补充资料 / 延伸阅读'}
}
function hUrlKey(raw){
 try{const u=new URL(raw);u.hash='';for(const k of [...u.searchParams.keys()])if(/^utm_/i.test(k))u.searchParams.delete(k);u.pathname=u.pathname.replace(/\/+$/,'')||'/';return u.toString().replace(/\/$/,'')}
 catch{return String(raw||'').replace(/\/$/,'')}
}
function hAccessRows(x){
 const rows=Array.isArray(x.access)?x.access.map(r=>({...r})):[];
 const seen=new Set(rows.map(r=>r.url));
 const push=(r)=>{if(r?.url&&!seen.has(r.url)){seen.add(r.url);rows.push(r)}};
 push({label:'官方 / 原始来源',note:x.source_kind||x.source||'原始资料',url:x.url,kind:'source'});
 if(x.secondary_url){const m=hResourceMeta(x.secondary_url);push({label:m.title,note:m.source,url:x.secondary_url,kind:'docs'})}
 return rows.slice(0,5)
}
function hRelatedRows(x){
 const primary=hUrlKey(x.url),seen=new Set([primary]);
 const rows=[];
 for(const r of (Array.isArray(x.related)?x.related:[])){const key=hUrlKey(r.url);if(!key||seen.has(key))continue;seen.add(key);rows.push({...r})}
 if(x.secondary_url){const key=hUrlKey(x.secondary_url);if(key&&!seen.has(key)){const m=hResourceMeta(x.secondary_url);seen.add(key);rows.push({source:m.source,title:m.title,url:x.secondary_url})}}
 return rows.slice(0,5)
}
function hAccessCards(x){
 const rows=hAccessRows(x);
 const hasTry=rows.some(r=>['try','demo','gateway'].includes(r.kind));
 const hasProductGate=rows.some(r=>r.kind==='product');
 const hasInternalGuide=rows.some(r=>String(r.url||'').startsWith('#/'));
 const status=hasTry?'':hasProductGate?'当前入口是候补或产品资料页，尚不能直接体验；开放范围以官方页面为准。':hasInternalGuide?'当前提供站内核验路径与官方资料；这是验证指南，不代表本站已经运行或产品可直接体验。':'当前没有独立可体验入口，先提供官方材料 / 代码 / 论文。';
 const card=(r,i)=>{
  const internal=String(r.url||'').startsWith('#/'),href=internal?esc(r.url):safeLink(r.url);
  const attrs=internal?' onclick="document.getElementById(\'modal\').close();document.body.style.overflow=\'\'"':' target="_blank" rel="noopener noreferrer"';
  const glyph=internal?'arrow':r.kind==='try'?'zap':r.kind==='docs'?'book':r.kind==='gateway'?'box':'external';
  return '<a class="h-access-card '+(i===0?'primary':'')+'" href="'+href+'"'+attrs+'><span class="h-access-icon">'+icon(glyph)+'</span><span><strong>'+esc(r.label)+'</strong><small>'+esc(r.note)+'</small></span>'+icon(internal?'arrow':'external')+'</a>'
 };
 return '<section class="h-detail-panel"><div class="h-detail-panel-head"><span>体验 / 查看入口</span><small>'+rows.length+' 个</small></div><div class="h-access-list">'+rows.map(card).join('')+'</div>'+(status?'<div class="h-access-status">'+status+'</div>':'')+'</section>'
}
function hPrimaryCta(r){
 if(!r)return '';
 const interactive=['try','demo','gateway'].includes(r.kind);
 const label=interactive?'立即体验':r.kind==='docs'?'查看资料':'阅读官方资料';
 return '<a class="button primary h-try-now" href="'+safeLink(r.url)+'" target="_blank" rel="noopener noreferrer">'+icon(interactive?'zap':'book')+' '+label+'</a>'
}
function hRelatedCards(x){
 const rows=hRelatedRows(x);
 if(!rows.length)return '';
 return '<section class="h-detail-panel"><div class="h-detail-panel-head"><span>相关报道 / 资料</span><small>'+rows.length+' 条</small></div><div class="h-news-list">'+rows.map(r=>'<a class="h-news-item" href="'+safeLink(r.url)+'" target="_blank" rel="noopener noreferrer"><span class="h-news-meta"><b>'+esc(r.source)+'</b>'+(r.date?'<time>'+esc(r.date)+'</time>':'')+'</span><strong>'+esc(r.title)+'</strong><span class="h-news-arrow">'+icon('external')+'</span></a>').join('')+'</div></section>'
}
function hMoment(raw){
 const s=String(raw||'');if(!s)return '';
 return s.includes('T')?s.slice(0,16).replace('T',' ').replaceAll('-','.') : s.replaceAll('-','.')
}
function hTimelineRows(x){
 const rows=[];
 const evidence=new Set();
 const add=(date,kind,title,url='')=>{if(!date)return;const key=url?date+'|'+hUrlKey(url):'';if(key&&evidence.has(key))return;if(key)evidence.add(key);rows.push({date,kind,title,url})};
 add(x.published,'发布',x.source+' 发布 / 公布',x.url);
 for(const r of (Array.isArray(x.related)?x.related:[]))if(r.date)add(r.date,'跟进',r.source+'：'+r.title,r.url);
 for(const r of (Array.isArray(x.timeline)?x.timeline:[]))add(r.date||r.at,r.kind||'进展',r.title||r.note||'进展',r.url||'');
 add(x.first_seen_at,'收录','AI坐标首次收录');
 add(x.checked,'核验','最新资料核验');
 const rank=v=>{const t=Date.parse(String(v).length===10?v+'T00:00:00Z':v);return Number.isFinite(t)?t:0};
 return rows.sort((a,b)=>rank(a.date)-rank(b.date)).filter((r,i,a)=>i===0||!(r.date===a[i-1].date&&r.kind===a[i-1].kind&&r.title===a[i-1].title)).slice(-8)
}
function hTimeline(x){
 const rows=hTimelineRows(x);
 return '<section class="h-detail-timeline"><div class="h-detail-timeline-head"><div><span class="h-copy-label">TIMELINE</span><h3>这个热点是怎么走到现在的</h3></div><small>'+rows.length+' 个节点</small></div><div class="h-timeline-list">'+rows.map(r=>'<div class="h-timeline-node"><time>'+esc(hMoment(r.date))+'</time><span>'+esc(r.kind)+'</span>'+(r.url?'<a href="'+safeLink(r.url)+'" target="_blank" rel="noopener noreferrer">'+esc(r.title)+' '+icon('external')+'</a>':'<strong>'+esc(r.title)+'</strong>')+'</div>').join('')+'</div></section>'
}
function hDetail(id){
 const x=HOT_ITEMS.get(id);if(!x)return;
 const t=H_TREND[x.trend]||H_TREND.flat;
 const access=hAccessRows(x),primary=access.find(r=>['try','demo','gateway'].includes(r.kind)&&!String(r.url||'').startsWith('#/'))||access.find(r=>!String(r.url||'').startsWith('#/'))||access[0];
 const heroCta=hPrimaryCta(primary)+
   '<a class="button" href="'+safeLink(x.url)+'" target="_blank" rel="noopener noreferrer">官方 / 原始来源 '+icon('external')+'</a>'+
   (x.link?'<a class="button subtle" href="'+esc(x.link)+'" onclick="document.getElementById(\'modal\').close();document.body.style.overflow=\'\'">相关专题 '+icon('arrow')+'</a>':'');
 showModal('HOT SIGNAL / '+HOT_CATS.get(x.category).title,
 '<article class="h-detail-shell">'+
   '<header class="h-detail-hero">'+
     '<div class="h-detail-kicker"><span>'+esc(x.source)+'</span><i></i><span>'+esc(x.source_kind)+'</span></div>'+
     '<h2 id="modal-title">'+esc(x.title)+'</h2>'+
     '<p class="h-detail-summary">'+esc(x.summary)+'</p>'+
     '<div class="h-detail-facts">'+
       '<div class="h-detail-fact heat"><strong>'+x.heat+hTrend(x)+'</strong><span>站内热度 · '+t[1]+'</span></div>'+
       '<div class="h-detail-fact"><strong>'+esc(x.published.slice(5).replace('-','.'))+'</strong><span>原始发布</span></div>'+
       '<div class="h-detail-fact"><strong>'+esc(x.checked.slice(5).replace('-','.'))+'</strong><span>资料核对</span></div>'+
     '</div>'+
     '<div class="h-detail-cta">'+heroCta+'</div>'+
   '</header>'+
   hTimeline(x)+
   '<div class="h-detail-layout">'+
     '<main class="h-detail-main">'+
       '<section class="h-detail-copy"><div class="h-copy-label">WHY IT MATTERS</div><h3>为什么值得看</h3><p>'+esc(x.why)+'</p></section>'+
     '</main>'+
     '<aside class="h-detail-side">'+hAccessCards(x)+hRelatedCards(x)+'</aside>'+
   '</div>'+
   '<section class="h-detail-conclusion"><div class="h-copy-label">FINAL CHECK</div><h3>不要过度解读</h3><p>'+esc(x.boundary)+'</p></section>'+
   '<footer class="h-detail-source"><a href="'+safeLink(x.url)+'" target="_blank" rel="noopener noreferrer">'+esc(x.source)+' · '+esc(x.source_kind)+' '+icon('external')+'</a><p>来源日期 '+esc(x.published)+' · 资料核对 '+esc(x.checked)+'。热度是 AI坐标编辑信号，不代表全网浏览量。</p></footer>'+
 '</article>','hot',true)
}
function hMethod(){showModal('HOT LIST / DATA STATUS',`<h2 id="modal-title">热点榜现在是人工快照。</h2><p class="dialog-intro">${HOT.items.length} 条高信号进展，核对 ${HOT.checked}。热度分只用于本站排序。</p><div class="health-row"><span>自动抓取</span><span>${HOT.method.automatic?'已开启':'未开启'}</span></div><div class="health-row"><span>最后自动成功</span><span>${HOT.method.last_success||'无'}</span></div><div class="health-row"><span>榜单口径</span><span>编辑信号 / 非流量</span></div><section class="detail-section"><h3>为什么不用“全网热度”</h3><p>没有可靠的跨平台统一浏览量，就不制造 145、87 这类看似精确的网络热度。当前分数综合时效、影响范围、主题匹配和来源可信度；每条保留原始链接。</p></section><div class="action-row"><button class="button primary" data-ha="export">导出热点 JSON</button><button class="button" data-ha="rss">RSS</button></div>`,'hot')}
function renderHot(){lastMain='';$('#hero').hidden=true;$('#stats').hidden=true;$('.workspace').hidden=true;$('#legacy-saved').innerHTML='';const root=$('#vertical-root');root.hidden=false;root.innerHTML=hotPage();document.body.classList.remove('nav-open');$('#compare-tray').hidden=true}
document.addEventListener('click',e=>{const el=e.target.closest('[data-ha]');if(!el)return;e.preventDefault();const a=el.dataset.ha,id=el.dataset.id;if(a==='cat')return hRoute({cat:id==='all'?null:id,item:null,ptag:null});if(a==='product-tag')return hRoute({cat:'product',ptag:id==='all'?null:id,item:null},true);if(a==='hot-clear-search')return hRoute({cat:null,q:null,item:null,ptag:null});if(a==='detail')return hRoute({item:id});if(a==='method')return hMethod();if(a==='export')return download('frontierlog-hot.json',JSON.stringify(HOT,null,2),'application/json;charset=utf-8');if(a==='rss'){const url=SITE.base_url+'feeds/hot.xml';return showModal('RSS / HOT LIST',`<h2 id="modal-title">订阅热点榜</h2><p class="dialog-intro">只有本站内容重新发布后才会更新；当前没有自动全网抓取。</p><div class="codebox"><pre>${esc(url)}</pre></div><div class="action-row"><a class="button primary" href="${safeLink(url)}" target="_blank" rel="noopener noreferrer">打开 RSS ${icon('external')}</a><button class="button" data-ha="copy-rss">复制地址</button></div>`,'hot')}if(a==='copy-rss')return copyText(SITE.base_url+'feeds/hot.xml')});
document.addEventListener('input',e=>{if(e.target.id!=='h-search')return;const pos=e.target.selectionStart;hRoute({q:e.target.value,item:null},true);const input=$('#h-search');input?.focus({preventScroll:true});try{input.setSelectionRange(pos,pos)}catch{}});
/* Preserve deep links and inject hot signals into the curated landing page. */
const beforeHotDetails=moduleDetailsFromRoute;
moduleDetailsFromRoute=function(){if(state.view==='hot'){const id=hState().item;if(id)hDetail(id);else if(modal.open&&modal.dataset.type==='hot')hideModal(false);return}if(modal.open&&modal.dataset.type==='hot')hideModal(false);beforeHotDetails()};
/* Closing a deep-linked drawer must leave a truthful, refresh-safe route. */
modal.addEventListener('close',()=>{
 if(modal.open)return;
 if(modal.dataset.type==='hot'&&state.view==='hot'&&hState().item)hRoute({item:null},true)
});
const beforeHotFeed=feedPage;
feedPage=function(){const html=beforeHotFeed();const rows=[...HOT.items].sort((a,b)=>b.heat-a.heat).slice(0,5);const board=`<section class="v-hot-entry"><div class="v-sectionline"><h2>${icon('fire')}当前热点</h2><a href="#/hot">完整榜单 ${icon('arrow')}</a></div><div class="v-hot-mini">${rows.map((x,i)=>`<a href="#/hot?item=${encodeURIComponent(x.id)}"><b>${i+1}</b><span>${esc(x.title)}</span><em>${x.heat}${hTrend(x)}</em></a>`).join('')}</div></section>`;return board+html};
