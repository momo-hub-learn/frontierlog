'use strict';
/* Editorial hot list. Heat is a transparent FrontierLog signal, never claimed as web traffic. */
const HOT=APP.hot;
const HOT_ITEMS=new Map(HOT.items.map(x=>[x.id,x]));
const HOT_CATS=new Map(HOT.categories.map(x=>[x.id,x]));
PATHS.fire='<path d="M13 2s1 4-2 6c-1-3-4-3-4-6-3 3-4 7-2 11 2 5 6 8 7 8s6-2 7-7c1-5-2-8-4-10 0 3-1 5-3 6 1-4-1-6 1-8z"/>';
const H_TREND={up:['↗','上升'],flat:['—','持平'],down:['↘','回落']};
const H_ICON={all:'sparkles',model:'cpu',product:'box',industry:'factory',research:'flask',benchmark:'gauge'};
function hParams(){return new URLSearchParams(location.hash.split('?')[1]||'')}
function hState(){const p=hParams();return {cat:HOT_CATS.has(p.get('cat'))?p.get('cat'):'all',q:(p.get('q')||'').slice(0,300).trim(),item:HOT_ITEMS.has(p.get('item'))?p.get('item'):null}}
function hRoute(patch={},replace=false){const p=hParams();for(const [k,v]of Object.entries(patch)){if(v===null||v===undefined||v==='')p.delete(k);else p.set(k,String(v))}const h='#/hot'+(p.size?'?'+p.toString():'');if(replace)history.replaceState(null,'',h);else history.pushState(null,'',h);parseRoute()}
function hRows(){const s=hState(),q=s.q.toLowerCase();return HOT.items.filter(x=>(s.cat==='all'||x.category===s.cat)&&(!q||[x.title,x.summary,x.why,x.source,HOT_CATS.get(x.category)?.title].join(' ').toLowerCase().includes(q))).sort((a,b)=>b.heat-a.heat||b.published.localeCompare(a.published))}
function hTrend(x){const [g,label]=H_TREND[x.trend]||H_TREND.flat;return `<span class="h-trend ${x.trend}" title="${label}">${g}</span>`}
function hTabs(s){return `<nav class="h-tabs" aria-label="热点分类">${HOT.categories.map(c=>`<button class="h-tab ${s.cat===c.id?'active':''}" data-ha="cat" data-id="${c.id}" ${s.cat===c.id?'aria-current="page"':''}>${icon(H_ICON[c.id]||'sparkles')}${esc(c.title)}<small>${c.id==='all'?HOT.items.length:HOT.items.filter(x=>x.category===c.id).length}</small></button>`).join('')}</nav>`}
function hBoard(rows){const top=rows.slice(0,5);return `<section class="h-board"><div class="h-board-head"><h2>${icon('fire')}当前热点</h2><span class="h-info">${icon('info')} 站内热度，不是全网流量</span></div>${top.length?top.map((x,i)=>`<article class="h-row"><div class="h-rank">${i+1}</div><div class="h-main"><button class="h-title" data-ha="detail" data-id="${x.id}">${esc(x.title)}</button><div class="h-sub"><span class="h-cat">${icon(H_ICON[x.category]||'sparkles')}${esc(HOT_CATS.get(x.category).title)}</span><span>${esc(x.source)}</span><span class="h-source-kind">${esc(x.source_kind)}</span><time>${esc(x.published)}</time></div></div><div class="h-heat"><strong>${x.heat}${hTrend(x)}</strong><span>热度</span></div></article>`).join(''):`<div class="h-empty"><h3>没有匹配热点</h3><p>换个关键词或分类。</p></div>`}</section>`}
function hStream(rows){const rest=rows.slice(5);return `<div class="h-below"><section class="h-stream">${rest.length?rest.map(x=>`<article class="h-story"><div class="h-sub"><span class="h-cat">${icon(H_ICON[x.category]||'sparkles')}${esc(HOT_CATS.get(x.category).title)}</span><time>${esc(x.published)}</time><span>${esc(x.source)}</span></div><h3>${esc(x.title)}</h3><p>${esc(x.summary)}</p><div class="h-story-foot"><a href="${safeLink(x.url)}" target="_blank" rel="noopener noreferrer">原始来源 ${icon('external')}</a><button data-ha="detail" data-id="${x.id}">为什么值得看 ${icon('arrow')}</button></div></article>`).join(''):`<div class="h-empty"><h3>前五就是全部匹配项</h3><p>切换分类继续看。</p></div>`}</section><aside class="h-aside"><p class="eyebrow">HOW WE RANK</p><h3>热度不是浏览量。</h3><p>${esc(HOT.method.note)}</p><div class="h-rule"><b>时效</b><span>越新的有效变化越优先。</span></div><div class="h-rule"><b>影响范围</b><span>模型、工具链、业务环节是否真的变化。</span></div><div class="h-rule"><b>主题匹配</b><span>优先医药、制造、模型、Agent 与 Benchmark。</span></div><button class="button" data-ha="method">查看数据状态</button></aside></div>`}
function hotPage(){const s=hState(),rows=hRows();return `<section class="h-wrap"><header class="h-head"><div><p class="eyebrow"><span class="accent">●</span> HIGH-SIGNAL AI / CURATED</p><h1>热点榜<span class="accent">.</span></h1><p>不追所有新闻，只追今天最值得继续看的变化。</p></div><div class="h-meta"><span><i class="state-dot"></i> 人工核对快照</span><span>${esc(HOT.checked)}</span><span>${rows.length} / ${HOT.items.length} 条</span></div></header><div class="h-filterbar">${hTabs(s)}<label class="h-search">${icon('search')}<input id="h-search" type="search" value="${esc(s.q)}" placeholder="搜索标题、来源、摘要…" aria-label="搜索热点"><kbd>/</kbd></label></div>${hBoard(rows)}${hStream(rows)}</section>`}
function hAccessCards(x){
 const rows=Array.isArray(x.access)?x.access:[];
 if(!rows.length)return '';
 return '<section class="h-detail-panel"><div class="h-detail-panel-head"><span>体验与接入</span><small>'+rows.length+' 个入口</small></div><div class="h-access-list">'+rows.map((r,i)=>'<a class="h-access-card '+(i===0?'primary':'')+'" href="'+safeLink(r.url)+'" target="_blank" rel="noopener noreferrer"><span class="h-access-icon">'+icon(i===0?'zap':r.kind==='docs'?'book':r.kind==='gateway'?'box':'external')+'</span><span><strong>'+esc(r.label)+'</strong><small>'+esc(r.note)+'</small></span>'+icon('external')+'</a>').join('')+'</div></section>'
}
function hRelatedCards(x){
 const rows=Array.isArray(x.related)?x.related:[];
 if(!rows.length)return '';
 return '<section class="h-detail-panel"><div class="h-detail-panel-head"><span>相关报道</span><small>'+rows.length+' 篇</small></div><div class="h-news-list">'+rows.map(r=>'<a class="h-news-item" href="'+safeLink(r.url)+'" target="_blank" rel="noopener noreferrer"><span class="h-news-meta"><b>'+esc(r.source)+'</b>'+(r.date?'<time>'+esc(r.date)+'</time>':'')+'</span><strong>'+esc(r.title)+'</strong><span class="h-news-arrow">'+icon('external')+'</span></a>').join('')+'</div></section>'
}
function hDetail(id){
 const x=HOT_ITEMS.get(id);if(!x)return;
 const t=H_TREND[x.trend]||H_TREND.flat;
 const access=Array.isArray(x.access)?x.access:[];
 const primary=access[0];
 const related=hRelatedCards(x),accessCards=hAccessCards(x);
 const secondary=!access.length&&x.secondary_url?'<a class="button" href="'+safeLink(x.secondary_url)+'" target="_blank" rel="noopener noreferrer">补充资料 '+icon('external')+'</a>':'';
 const heroCta=(primary?'<a class="button primary h-try-now" href="'+safeLink(primary.url)+'" target="_blank" rel="noopener noreferrer">'+icon('zap')+' 立即体验</a>':'')+
   '<a class="button" href="'+safeLink(x.url)+'" target="_blank" rel="noopener noreferrer">官方 / 原始来源 '+icon('external')+'</a>'+
   secondary+
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
   '<div class="h-detail-layout">'+
     '<main class="h-detail-main">'+
       '<section class="h-detail-copy"><div class="h-copy-label">WHY IT MATTERS</div><h3>为什么值得看</h3><p>'+esc(x.why)+'</p></section>'+
       '<section class="h-detail-copy h-detail-boundary"><div class="h-copy-label">BOUNDARY</div><h3>不要过度解读</h3><p>'+esc(x.boundary)+'</p></section>'+
     '</main>'+
     '<aside class="h-detail-side">'+accessCards+related+'</aside>'+
   '</div>'+
   '<footer class="h-detail-source"><a href="'+safeLink(x.url)+'" target="_blank" rel="noopener noreferrer">'+esc(x.source)+' · '+esc(x.source_kind)+' '+icon('external')+'</a><p>来源日期 '+esc(x.published)+' · 资料核对 '+esc(x.checked)+'。热度是 AI坐标编辑信号，不代表全网浏览量。</p></footer>'+
 '</article>','hot',true)
}
function hMethod(){showModal('HOT LIST / DATA STATUS',`<h2 id="modal-title">热点榜现在是人工快照。</h2><p class="dialog-intro">${HOT.items.length} 条高信号进展，核对 ${HOT.checked}。热度分只用于本站排序。</p><div class="health-row"><span>自动抓取</span><span>${HOT.method.automatic?'已开启':'未开启'}</span></div><div class="health-row"><span>最后自动成功</span><span>${HOT.method.last_success||'无'}</span></div><div class="health-row"><span>榜单口径</span><span>编辑信号 / 非流量</span></div><section class="detail-section"><h3>为什么不用“全网热度”</h3><p>没有可靠的跨平台统一浏览量，就不制造 145、87 这类看似精确的网络热度。当前分数综合时效、影响范围、主题匹配和来源可信度；每条保留原始链接。</p></section><div class="action-row"><button class="button primary" data-ha="export">导出热点 JSON</button><button class="button" data-ha="rss">RSS</button></div>`,'hot')}
function renderHot(){lastMain='';$('#hero').hidden=true;$('#stats').hidden=true;$('.workspace').hidden=true;$('#legacy-saved').innerHTML='';const root=$('#vertical-root');root.hidden=false;root.innerHTML=hotPage();document.body.classList.remove('nav-open');$('#compare-tray').hidden=true}
document.addEventListener('click',e=>{const el=e.target.closest('[data-ha]');if(!el)return;e.preventDefault();const a=el.dataset.ha,id=el.dataset.id;if(a==='cat')return hRoute({cat:id==='all'?null:id,item:null},true);if(a==='detail')return hRoute({item:id});if(a==='method')return hMethod();if(a==='export')return download('frontierlog-hot.json',JSON.stringify(HOT,null,2),'application/json;charset=utf-8');if(a==='rss'){const url=SITE.base_url+'feeds/hot.xml';return showModal('RSS / HOT LIST',`<h2 id="modal-title">订阅热点榜</h2><p class="dialog-intro">只有本站内容重新发布后才会更新；当前没有自动全网抓取。</p><div class="codebox"><pre>${esc(url)}</pre></div><div class="action-row"><a class="button primary" href="${safeLink(url)}" target="_blank" rel="noopener noreferrer">打开 RSS ${icon('external')}</a><button class="button" data-ha="copy-rss">复制地址</button></div>`,'hot')}if(a==='copy-rss')return copyText(SITE.base_url+'feeds/hot.xml')});
document.addEventListener('input',e=>{if(e.target.id!=='h-search')return;const pos=e.target.selectionStart;hRoute({q:e.target.value,item:null},true);const input=$('#h-search');input?.focus({preventScroll:true});try{input.setSelectionRange(pos,pos)}catch{}});
/* Preserve deep links and inject hot signals into the curated landing page. */
const beforeHotDetails=moduleDetailsFromRoute;
moduleDetailsFromRoute=function(){if(state.view==='hot'){const id=hState().item;if(id)hDetail(id);else if(modal.open&&modal.dataset.type==='hot')hideModal(false);return}if(modal.open&&modal.dataset.type==='hot')hideModal(false);beforeHotDetails()};
const beforeHotFeed=feedPage;
feedPage=function(){const html=beforeHotFeed();const rows=[...HOT.items].sort((a,b)=>b.heat-a.heat).slice(0,5);const board=`<section class="v-hot-entry"><div class="v-sectionline"><h2>${icon('fire')}当前热点</h2><a href="#/hot">完整榜单 ${icon('arrow')}</a></div><div class="v-hot-mini">${rows.map((x,i)=>`<a href="#/hot?item=${encodeURIComponent(x.id)}"><b>${i+1}</b><span>${esc(x.title)}</span><em>${x.heat}${hTrend(x)}</em></a>`).join('')}</div></section>`;return board+html};
