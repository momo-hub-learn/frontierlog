'use strict';
/* AI坐标 v2 UI refactor: fewer templates, denser data, clearer hierarchy. */
(()=>{
pages.models[0]='模型榜'; pages.benchmarks[0]='模型榜 / Benchmark'; pages.tibo[0]='Tibo 重置';

function v2Count(key){
 const counts={benchmarks:BENCH.items.length,models:MODEL_DATA.boards.reduce((n,b)=>n+b.rows.length,0),tibo:RESET_DATA.events.length,hot:HOT.items.length,feed:typeof aicCuratedRows==='function'?aicCuratedRows().length:HOT.items.length,progress:DATA.items.length,activity:DATA.events.length+(UP.releases||[]).length,toolkit:DATA.items.filter(t=>t.status==='code').length,topics:VERT.topics.length,pharma:VERT.articles.filter(a=>a.sector==='pharma').length,manufacturing:VERT.articles.filter(a=>a.sector==='manufacturing').length,saved:saved.size+articleSaved.size+msaved.size+bSaved.size};
 return counts[key]??0;
}
renderNav=function(){
 const groups=[['内容',['feed','hot','progress','activity','toolkit']],['主题',['topics','pharma','manufacturing']],['模型',['models']],['我的',['saved']],['工具',['tibo']]];
 const active=state.view==='benchmarks'?'models':state.view;
 $('#nav').innerHTML=groups.map(([label,keys])=>`<div class="navgroup-label">${label}</div>${keys.map(key=>`<a href="#/${key}" class="navitem ${active===key?'active':''}" ${active===key?'aria-current="page"':''}>${icon(pages[key][1])}<span>${esc(pages[key][0])}</span><small>${String(v2Count(key)).padStart(2,'0')}</small></a>`).join('')}`).join('');
 $('#crumb').textContent=pages[state.view][0];
 $('#source-count').textContent=DATA.sources.length+VERT.sources.length+MODEL_DATA.sources.length+RESET_DATA.sources.length+BENCH.sources.length;
 $('#snapshot-date').textContent=VERT.checked.replaceAll('-','.');
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
 $('#hero').hidden=true; $('#stats').hidden=true; $('.workspace').hidden=false; $('#vertical-root').hidden=true;
 $('#section-eyebrow').textContent='CAPABILITY STATUS';
 $('#section-title').innerHTML=`<span class="mini-icon">${icon('zap')}</span><span>AI 能力进度</span>`;
 $('#layout-buttons').hidden=true; $('#toolbar').hidden=true; $('#contextline').hidden=true;
 const usable=DATA.items.filter(t=>t.status==='code');
 const research=DATA.items.filter(t=>t.status==='research');
 const item=(t,mode)=>{const now=mode==='open'?t.summary:t.scope,label=mode==='open'?'现在可跑':'研究中';return `<button class="v2-cap-row" data-action="task" data-id="${t.id}"><span class="v2-cap-state ${mode}"></span><span><strong>${esc(t.title)}</strong><small>${label} · ${esc(t.name)} · ${esc(t.category)}</small></span><span class="v2-cap-copy"><b style="color:var(--text);font-weight:650">现在：</b>${esc(now)}<br><span style="color:var(--muted)">边界：</span>${esc(t.boundary)}</span>${icon('arrow')}</button>`};
 $('#content').innerHTML=`<div class="v2-pageintro"><div><p class="eyebrow">WHAT AI CAN ACTUALLY DO</p><h1>AI 又能干什么了？</h1><p>每项能力只出现一次：先看现在能做什么，再看还卡在哪里。</p></div><span class="v2-pagecount">${DATA.items.length} 个任务</span></div>
 <div class="v2-cap-status-grid">
  <section><header><span class="v2-status-dot open"></span><div><h2>已经能跑</h2><p>有公开实现或可运行路径；仍需你自己的业务验收。</p></div><b>${usable.length}</b></header><div>${usable.map(t=>item(t,'open')).join('')}</div></section>
  <section><header><span class="v2-status-dot research"></span><div><h2>还在研究</h2><p>有研究证据，但访问、稳定性或复现条件还不够成熟。</p></div><b>${research.length}</b></header><div>${research.map(t=>item(t,'research')).join('')||'<p class="v2-emptyline">暂无单独研究阶段任务。</p>'}</div></section>
 </div>`;
}

function v2Activity(){
 $('#hero').hidden=true; $('#stats').hidden=true; $('.workspace').hidden=false; $('#vertical-root').hidden=true;
 $('#section-eyebrow').textContent='PROMISE TRACKER'; $('#section-title').innerHTML=`<span class="mini-icon">${icon('history')}</span><span>发布会之后</span>`;
 $('#layout-buttons').hidden=true; $('#toolbar').hidden=true; $('#contextline').hidden=true;
 const groups={}; DATA.events.forEach(e=>(groups[e.task]??=[]).push(e)); (UP.releases||[]).forEach(e=>(groups[e.task]??=[]).push({...e,kind:'upstream',date:(e.published_at||'').slice(0,10),summary:e.name||'上游版本发布',delta:'机器收录，尚未人工核验。'}));
 const rows=Object.entries(groups).map(([id,ev])=>({task:tasks.get(id),events:ev.sort((a,b)=>b.date.localeCompare(a.date))})).filter(x=>x.task).sort((a,b)=>(b.events[0]?.date||'').localeCompare(a.events[0]?.date||''));
 const status=e=>e.kind==='research'?['研究','research']:e.kind==='upstream'?['待核验','pending']:['公开发布','release'];
 $('#content').innerHTML=`<div class="v2-pageintro"><div><p class="eyebrow">FROM ANNOUNCEMENT TO REAL USE</p><h1>当时说了什么，后来真的发生了什么。</h1><p>按项目保留公开发布、研究变化和待核验版本，不把“宣布”写成“已可用”。</p></div><span class="v2-pagecount">${DATA.events.length} 条已核对事件</span></div>
 <div class="v2-lifecycle-list">${rows.map(({task,events})=>`<article class="v2-lifecycle"><header><div>${identity(task)}<h2>${esc(task.title)}</h2></div><button class="textlink" data-action="task" data-id="${task.id}">打开档案 ${icon('arrow')}</button></header><div class="v2-life-track">${events.map((e,i)=>{const [label,cls]=status(e);return `<div class="v2-life-node ${cls}"><time>${esc(e.date)}</time><i></i><div><span class="v2-life-chip">${label}</span><strong>${esc(e.title||e.short_title||e.tag||'版本变化')}</strong><p>${esc(e.summary||'')}</p><small>${esc(e.delta||'')}</small></div></div>`}).join('')}</div></article>`).join('')}</div>`;
}

function v2Toolkit(){
 $('#hero').hidden=true; $('#stats').hidden=true; $('.workspace').hidden=false; $('#vertical-root').hidden=true;
 $('#section-eyebrow').textContent='RUN IT TODAY'; $('#section-title').innerHTML=`<span class="mini-icon">${icon('wrench')}</span><span>今天能跑</span>`;
 $('#layout-buttons').hidden=true; $('#toolbar').hidden=true; $('#contextline').hidden=true;
 const tools=DATA.items.filter(t=>t.status==='code');
 $('#content').innerHTML=`<div class="v2-pageintro"><div><p class="eyebrow">PUBLIC PATHS / NOT SITE-TESTED</p><h1>少解释，先找到入口。</h1><p>只列有公开实现的任务；运行条件、命令和验收清单放在一张卡里。</p></div><span class="v2-pagecount">${tools.length} 个工具</span></div>
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

const v2BaseHotRows=hRows;
hRows=function(){
 const rows=v2BaseHotRows(),sort=new URLSearchParams(location.hash.split('?')[1]||'').get('sort')||'latest';
 return sort==='heat'?[...rows].sort((a,b)=>b.heat-a.heat||b.published.localeCompare(a.published)):rows;
};
const v2BaseHotPage=hotPage;
hotPage=function(){
 const sort=new URLSearchParams(location.hash.split('?')[1]||'').get('sort')||'latest';
 let html=v2BaseHotPage();
 const switcher=`<div class="v2-hot-sort"><span>排序</span><button class="${sort==='latest'?'active':''}" data-v2-hot-sort="latest">${icon('clock')}最新</button><button class="${sort==='heat'?'active':''}" data-v2-hot-sort="heat">${icon('fire')}热度</button></div>`;
 return html.replace('<div class="h-filterbar">',switcher+'<div class="h-filterbar">');
};

function v2SavedSummary(){
 if(state.view!=='saved')return;
 const host=$('#legacy-saved'); if(!host||host.querySelector('.v2-saved-head'))return;
 host.insertAdjacentHTML('afterbegin',`<section class="v2-saved-head"><div><p class="eyebrow">YOUR PERSONAL INDEX</p><h1>我的关注</h1><p>主题、模型、文章和 Benchmark 汇到一个地方。</p></div><div class="v2-saved-stats"><span><b>${topicFollows.size}</b>主题</span><span><b>${msaved.size}</b>模型</span><span><b>${articleSaved.size}</b>文章</span><span><b>${bSaved.size}</b>Benchmark</span></div></section>`);
}

document.addEventListener('click',e=>{
 const b=e.target.closest('[data-v2-hot-sort]'); if(!b)return;
 const p=new URLSearchParams(location.hash.split('?')[1]||''); if(b.dataset.v2HotSort==='latest')p.delete('sort');else p.set('sort','heat');
 history.pushState(null,'','#/hot'+(p.size?'?'+p.toString():'')); parseRoute();
});

const v2BaseRenderMain=renderMain;
renderMain=function(){
 v2BaseRenderMain();
 v2Brand();
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