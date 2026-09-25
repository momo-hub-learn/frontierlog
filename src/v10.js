'use strict';
/* v1.0: chronological hot stream, Top-5 on the curated landing page, and local personalization. */
const HOT_POLICY=APP.hot_policy||null;
function v10HotByTime(rows){return [...rows].sort((a,b)=>b.published.localeCompare(a.published)||b.heat-a.heat||a.id.localeCompare(b.id))}
function v10HotByHeat(rows){return [...rows].sort((a,b)=>b.heat-a.heat||b.published.localeCompare(a.published)||a.id.localeCompare(b.id))}
hRows=function(){const s=hState(),q=s.q.toLowerCase();return v10HotByTime(HOT.items.filter(x=>hCatMatches(s.cat,x.category)&&(!q||[x.title,x.summary,x.why,x.source,HOT_CATS.get(x.category)?.title].join(' ').toLowerCase().includes(q))))}
function v10Story(x,{rank=null}={}){return `<article class="v10-story">${rank!==null?`<div class="v10-rank">${rank}</div>`:''}<div class="v10-story-main"><div class="h-sub"><span class="h-cat">${icon(H_ICON[x.category]||'sparkles')}${esc(HOT_CATS.get(x.category).title)}</span><span>${esc(x.source)}</span><span class="h-source-kind">${esc(x.source_kind)}</span><time>${esc(x.published)}</time></div><button class="v10-story-title" data-ha="detail" data-id="${x.id}">${esc(x.title)}</button><p>${esc(x.summary)}</p><div class="v10-story-actions"><button data-ha="detail" data-id="${x.id}">为什么值得看 ${icon('arrow')}</button><a href="${safeLink(x.url)}" target="_blank" rel="noopener noreferrer">原始来源 ${icon('external')}</a></div></div><div class="h-heat"><strong>${x.heat}${hTrend(x)}</strong><span>热度</span></div></article>`}
function v10Chronology(rows){const groups={};rows.forEach(x=>(groups[x.published]??=[]).push(x));const entries=Object.entries(groups).sort(([a],[b])=>b.localeCompare(a));return `<div class="v10-chronology">${entries.map(([date,list])=>`<section class="v10-day"><aside><b>${date===HOT.checked?'今天':date.slice(5).replace('-','月')+'日'}</b><span>${date.replaceAll('-','.')}</span></aside><div class="v10-day-items">${list.map(x=>v10Story(x)).join('')}</div></section>`).join('')}</div>`}
hotPage=function(){const s=hState();if(s.cat==='product')return PB.page();const rows=hRows();return `<section class="h-wrap v10-hot"><header class="h-head"><div><p class="eyebrow"><span class="accent">●</span> HOT SIGNALS / NEWEST FIRST</p><h1>热点时间线<span class="accent">.</span></h1><p>按发布时间倒序。热度只表示信号强度，不参与时间线排序。</p></div><div class="h-meta"><span><i class="state-dot"></i> 最新优先</span><span>${esc(HOT.checked)}</span><button class="v10-policy-chip" data-ha="method">${HOT_POLICY?.mode==='shadow'?'策略影子评估':'更新策略'}</button></div></header><div class="h-filterbar">${hTabs(s)}<label class="h-search">${icon('search')}<input id="h-search" type="search" value="${esc(s.q)}" placeholder="搜索标题、来源、摘要…" aria-label="搜索热点"><kbd>/</kbd></label></div>${rows.length?v10Chronology(rows):`<div class="h-empty"><h3>没有匹配热点</h3><p>换个关键词或分类。</p></div>`}</section>`}
function v10Top5(){const rows=v10HotByHeat(HOT.items).slice(0,5);return `<section class="v10-top5"><div class="v10-section-head"><div><p class="eyebrow">TOP 5 / CURRENT SIGNALS</p><h2>当前最热</h2></div><a href="#/hot">全部热点 ${icon('arrow')}</a></div><div class="v10-top5-list">${rows.map((x,i)=>`<a href="#/hot?item=${encodeURIComponent(x.id)}"><b>${String(i+1).padStart(2,'0')}</b><span><em>${esc(HOT_CATS.get(x.category).title)}</em>${esc(x.title)}</span><strong>${x.heat}${hTrend(x)}<small>热度</small></strong></a>`).join('')}</div></section>`}
function v10Prefs(){const topics=[...topicFollows],sectors=new Set(topics.map(id=>VTOPICS.get(id)?.sector).filter(Boolean));return {topics:new Set(topics),sectors,models:msaved.size,articles:articleSaved.size}}
function v10TopicFromLink(link=''){try{const raw=String(link||'');const q=raw.split('?')[1]||'';return new URLSearchParams(q).get('topic')}catch{return null}}
function v10PersonalMatch(x,p){const link=x.link||'';if(link.startsWith('#/pharma')){const t=v10TopicFromLink(link);return t?p.topics.has(t):p.sectors.has('pharma')}if(link.startsWith('#/manufacturing')){const t=v10TopicFromLink(link);return t?p.topics.has(t):p.sectors.has('manufacturing')}if(p.models>0&&(x.category==='model'||x.category==='benchmark'||link.startsWith('#/models')||link.startsWith('#/benchmarks')))return true;return false}
function v10PersonalBlock(){const p=v10Prefs();const followed=p.topics.size+p.models;const rows=v10HotByTime(HOT.items.filter(x=>v10PersonalMatch(x,p))).slice(0,5);if(!followed)return `<section class="v10-personal v10-personal-empty"><div><p class="eyebrow">FOR YOU / LOCAL</p><h2>关注以后，这里只放与你有关的热点。</h2><p>你可以关注医药、晶圆厂、装备制造等业务主题，也可以收藏模型。关注保存在当前浏览器。</p></div><div><a class="button" href="#/topics">选择主题</a><a class="button" href="#/models">关注模型</a></div></section>`;return `<section class="v10-personal"><div class="v10-section-head"><div><p class="eyebrow">FOR YOU / ${followed} FOLLOWING</p><h2>为你关注</h2></div><a href="#/topics">管理关注 ${icon('arrow')}</a></div>${rows.length?`<div class="v10-personal-list">${rows.map(x=>v10Story(x)).join('')}</div>`:`<div class="v10-personal-none">当前关注还没有新的热点；不会为了填满页面塞低信号消息。</div>`}</section>`}
function v10GeneralTimeline(){const rows=HOT.items.filter(x=>!AIC_VERTICAL_ONLY.has(x.id));const grouped={};v10HotByTime(rows).forEach(x=>(grouped[x.published]??=[]).push(x));return `<section class="v10-general"><div class="v10-section-head"><div><p class="eyebrow">DAILY / GENERAL AI</p><h2>每日时间线</h2><p>通用 AI 变化按日期排列；垂类内容只有在你关注后才进入“为你关注”。</p></div></div><div class="aic-timeline">${Object.entries(grouped).sort(([a],[b])=>b.localeCompare(a)).map(([date,list])=>`<section class="aic-day"><div class="aic-day-date"><b>${aicDateLabel(date)}</b><span>${date.replaceAll('-','.')}</span></div><div class="aic-day-list">${list.map((x,i)=>`<article class="aic-story"><div class="aic-story-index">${String(i+1).padStart(2,'0')}</div><div class="aic-story-main"><div class="aic-story-meta"><span class="h-cat">${icon(H_ICON[x.category]||'sparkles')}${esc(HOT_CATS.get(x.category).title)}</span><span>${esc(x.source)}</span><span>${esc(x.source_kind)}</span></div><button class="aic-story-title" data-ha="detail" data-id="${x.id}">${esc(x.title)}</button><p>${esc(x.summary)}</p><div class="aic-story-foot"><button data-ha="detail" data-id="${x.id}">为什么值得看 ${icon('arrow')}</button><a href="${safeLink(x.url)}" target="_blank" rel="noopener noreferrer">原始来源 ${icon('external')}</a></div></div><div class="aic-story-heat"><span class="aic-heat-value">${x.heat}</span><span class="aic-heat-label">热度</span>${hTrend(x)}</div></article>`).join('')}</div></section>`).join('')}</div></section>`}
feedPage=function(){return `<div class="v10-feed"><header class="aic-feed-head"><div><p class="eyebrow"><span class="coordinate-dot"></span> 每日精选 / ${esc(HOT.checked.replaceAll('-','.'))}</p><p>先看全站 Top 5，再看你的关注，最后按时间浏览通用 AI 变化。</p></div><a class="button" href="#/hot">热点时间线 ${icon('arrow')}</a></header>${v10Top5()}${v10PersonalBlock()}${v10GeneralTimeline()}</div>`}
hMethod=function(){const p=HOT_POLICY;showModal('HOT POLICY / UPDATE SCHEDULER',`<h2 id="modal-title">每小时评估，但不是每小时都打扰你。</h2><p class="dialog-intro">${esc(p?.note||'更新策略尚未配置。')}</p><div class="v10-policy-grid"><div><span>决策间隔</span><b>${p?.decision_interval_minutes||'—'} 分钟</b></div><div><span>奖励回看</span><b>${p?.reward_horizon_hours||'—'} 小时</b></div><div><span>当前模式</span><b>${p?.mode==='shadow'?'Shadow / 不自动发布':esc(p?.mode||'—')}</b></div><div><span>学习状态</span><b>${p?.learning?.trained?'已训练':'Bootstrap'}</b></div></div><section class="detail-section"><h3>策略动作</h3><p><strong>Publish</strong>：信号够强，立即更新；<strong>Merge</strong>：中等信号，合并到下一轮；<strong>Hold</strong>：先等热度或证据继续长。</p></section><section class="detail-section"><h3>怎么利用“全天热度”反哺小时决策</h3><p>每个小时只看当时能看到的状态，24 小时后回填最终热度、用户关注匹配、点击/收藏和更新疲劳作为延迟奖励。先用透明权重记录 state → action → reward，积累至少 ${p?.learning?.minimum_feedback_events||'足够多'} 个反馈事件后，再训练 contextual bandit；这样不会一开始就把手写规则冒充成 RL。</p></section><section class="detail-section"><h3>输入特征</h3><div class="v10-feature-list">${(p?.features||[]).map(x=>`<span><b>${esc(x.title)}</b>${esc(x.description)}</span>`).join('')}</div></section><section class="detail-section boundary"><h3>当前边界</h3><p>目前热点内容仍是人工核对快照，策略处于影子模式；它已经定义了每小时是否更新的决策接口，但不会自动把未经核验的候选写成事实。</p></section>`,'hot')}
/* Product browser: two views, one dataset. No publication times or scores are invented. */
const PB=(()=>{
 const SCENES=[['all','全部'],['legal','法律法务'],['support','客服支持'],['knowledge','企业知识'],['sales','销售增长'],['enterprise','企业运营']];
 const INVESTORS=[['all','全部'],['sequoia','Sequoia'],['yc','Y Combinator']];
 const KINDS={all:'全部变化',Product:'产品更新',Adoption:'客户采用',Benchmark:'评测 / 开源',Data:'数据 / 合作',Governance:'治理认证',Company:'融资 / 公司',Market:'行业文章',Research:'观点 / 研究',News:'产品消息'};
 const catalog=()=>PRODUCT_RADAR.items||[];
 const ids=x=>Array.isArray(x.filter_ids)?x.filter_ids:[];
 const scene=x=>x.group==='legal'?'legal':ids(x).some(t=>['customer-experience','support-automation'].includes(t))?'support':ids(x).includes('knowledge-work')?'knowledge':ids(x).includes('gtm')?'sales':'enterprise';
 const sceneName=x=>SCENES.find(([id])=>id===scene(x))?.[1]||'企业运营';
 const plain=x=>String(x??'');
 const text=x=>[x.name,x.company,x.summary,...(x.tags||[])].map(plain).join(' ').toLowerCase();
 const dateOK=d=>/^\d{4}-\d{2}-\d{2}$/.test(plain(d))&&!Number.isNaN(Date.parse(d+'T00:00:00Z'))&&new Date(d+'T00:00:00Z').toISOString().slice(0,10)===d;
 const chronology=x=>[...(x.timeline||[])].filter(e=>dateOK(e.date)).sort((a,b)=>b.date.localeCompare(a.date)||plain(a.title).localeCompare(plain(b.title)));
 function read(hash=location.hash){
  const p=new URLSearchParams(hash.split('?')[1]||''),old=p.get('ptag');
  const s={pview:p.get('pview')==='map'?'map':'updates',scene:p.get('scene')||'all',investor:p.get('investor')||'all',kind:p.get('kind')||'all',product:p.get('product')||'',q:(p.get('q')||'').trim().slice(0,300),legacy:''};
  const oldScene={legal:'legal','customer-experience':'support','support-automation':'support','knowledge-work':'knowledge',gtm:'sales'};
  if(!p.has('scene')&&oldScene[old])s.scene=oldScene[old];
  if(!p.has('investor')&&['sequoia','yc'].includes(old))s.investor=old;
  if(['enterprise-agent','in-house','customer-experience','support-automation'].includes(old))s.legacy=old;
  if(!SCENES.some(([id])=>id===s.scene))s.scene='all';
  if(!INVESTORS.some(([id])=>id===s.investor))s.investor='all';
  if(!Object.hasOwn(KINDS,s.kind))s.kind='all';
  if(!catalog().some(x=>x.id===s.product))s.product='';
  return s;
 }
 function href(s,patch={}){
  const next={...s,...patch},p=new URLSearchParams({cat:'product'});
  for(const key of ['pview','scene','investor','kind','product','q'])if(next[key]&&next[key]!=='all'&&!(key==='pview'&&next[key]==='updates'))p.set(key,next[key]);
  if(next.legacy)p.set('ptag',next.legacy);
  return '#/hot?'+p.toString();
 }
 function facetMatch(x,s){return(s.scene==='all'||scene(x)===s.scene)&&(s.investor==='all'||ids(x).includes(s.investor))&&(!s.legacy||ids(x).includes(s.legacy))&&(!s.product||x.id===s.product)}
 function products(s){
  const q=s.q.toLowerCase();
  return catalog().filter(x=>facetMatch(x,s)&&(!q||text(x).includes(q)||chronology(x).some(e=>plain(e.title).toLowerCase().includes(q))))
   .sort((a,b)=>(chronology(b)[0]?.date||'').localeCompare(chronology(a)[0]?.date||'')||a.name.localeCompare(b.name));
 }
 function canonical(raw){
  try{const u=new URL(raw);if(u.protocol!=='https:'||u.username||u.password)return '';u.hash='';for(const key of [...u.searchParams.keys()])if(/^(utm_|ref$)/i.test(key))u.searchParams.delete(key);return u.href.replace(/\/$/,'')}catch{return ''}
 }
 function specific(raw){try{return !['','blog','news','newsroom','uk/blog'].includes(new URL(raw).pathname.replace(/^\/|\/$/g,''))}catch{return false}}
 function events(s){
  const all=[];
  for(const x of catalog())for(const e of chronology(x))all.push({...e,product_ids:[x.id],names:[x.name],publisher:x.company||x.name});
  // Fold product news into the same stream, instead of rendering a second news list below the map.
  for(const n of HOT.items||[]){
   if(n.category!=='product'||!dateOK(n.published))continue;
   const linked=catalog().find(x=>n.product_id===x.id||((n.product_ids||[]).includes(x.id)));
   all.push({date:n.published,title:n.title,url:n.url,kind:'News',product_ids:linked?[linked.id]:[],names:linked?[linked.name]:[],publisher:n.source||'产品消息'});
  }
  const unique=new Map();
  for(const e of all){
   const url=canonical(e.url),key=specific(e.url)?e.date+'|'+url:e.date+'|'+e.product_ids.join(',')+'|'+plain(e.title).trim();
   const prev=unique.get(key);
   if(prev){prev.product_ids=[...new Set([...prev.product_ids,...e.product_ids])];prev.names=[...new Set([...prev.names,...e.names])];continue}
   unique.set(key,{...e,specific:specific(e.url)});
  }
  const matched=new Set(catalog().filter(x=>facetMatch(x,s)).map(x=>x.id)),q=s.q.toLowerCase();
  return [...unique.values()].filter(e=>{
   const related=e.product_ids.length?e.product_ids.some(id=>matched.has(id)):s.scene==='all'&&s.investor==='all'&&!s.product&&!s.legacy;
   const found=!q||[e.title,e.publisher,...e.names,...e.product_ids.map(id=>text(catalog().find(x=>x.id===id)||{}))].join(' ').toLowerCase().includes(q);
   return related&&found&&(s.kind==='all'||s.kind===e.kind);
  }).sort((a,b)=>b.date.localeCompare(a.date)||a.title.localeCompare(b.title));
 }
 const external=(url,label)=>canonical(url)?'<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">'+esc(label)+' '+icon('external')+'</a>':'<span>来源待补</span>';
 const link=(s,patch,label,cls='')=>'<a data-pb-link class="'+cls+'" href="'+esc(href(s,patch))+'">'+label+'</a>';
 function filters(s){
  const row=(field,label,options)=>'<div class="pb-filter-row"><span>'+label+'</span><nav aria-label="'+label+'">'+options.map(([id,title])=>{
   const next={...s,[field]:id,product:'',legacy:field==='scene'?'':s.legacy};
   const n=products({...next,q:''}).length;
   return '<a data-pb-link href="'+esc(href(s,{[field]:id,product:'',legacy:next.legacy}))+'" class="pb-chip '+(s[field]===id?'active':'')+'" '+(s[field]===id?'aria-current="true"':'')+'>'+esc(title)+'<small>'+n+'</small></a>';
  }).join('')+'</nav></div>';
  const available=SCENES.filter(([id])=>id==='all'||catalog().some(x=>scene(x)===id));
  const activeProduct=catalog().find(x=>x.id===s.product);
  const oldLabel=({'in-house':'企业法务','enterprise-agent':'企业 Agent','customer-experience':'客户体验','support-automation':'支持自动化'})[s.legacy]||'';
  return '<div class="pb-filters">'+row('scene','业务场景',available)+row('investor','投资 / 孵化',INVESTORS)+
   ((activeProduct||oldLabel||s.q)?'<div class="pb-selection">'+(activeProduct?link(s,{product:''},esc(activeProduct.name)+' ×','pb-chip'):'')+(oldLabel?link(s,{legacy:''},'旧标签：'+oldLabel+' ×','pb-chip'):'')+(s.q?link(s,{q:''},'搜索：'+esc(s.q)+' ×','pb-chip'):'')+'</div>':'')+'</div>';
 }
 function eventHTML(e,s){
  const name=e.names.join(' / '),product=e.product_ids[0];
  return '<article class="pb-event" data-product-event><div class="pb-event-meta"><span class="pb-kind">'+esc(KINDS[e.kind]||e.kind)+'</span>'+(name?'<strong>'+esc(name)+'</strong>':'<span>'+esc(e.publisher)+'</span>')+(!e.specific?'<span class="pb-warning">精确原文待补</span>':'')+'</div><h3>'+esc(e.title)+'</h3><div class="pb-event-actions">'+external(e.url,e.specific?'原始来源':'来源栏目')+(product?link(s,{pview:'map',product,kind:'all'},'查看产品 '+icon('arrow')):'<span>尚未加入产品地图</span>')+'</div></article>';
 }
 function timeline(list,s){
  const days=new Map();for(const e of list){if(!days.has(e.date))days.set(e.date,[]);days.get(e.date).push(e)}
  return '<div class="pb-timeline">'+[...days].map(([date,items])=>'<section class="pb-day"><h3><time datetime="'+date+'">'+date.replaceAll('-','.')+'</time><small>'+items.length+' 条</small></h3><div class="pb-day-events">'+items.map(e=>eventHTML(e,s)).join('')+'</div></section>').join('')+'</div>';
 }
 function updates(list,s,now=new Date()){
  if(!list.length)return empty(s,'当前筛选下暂无已收录动态');
  const cut=new Date(now);cut.setUTCDate(cut.getUTCDate()-30);const cutoff=cut.toISOString().slice(0,10),recent=list.filter(e=>e.date>=cutoff),older=list.filter(e=>e.date<cutoff);
  return (recent.length?timeline(recent,s):'<p class="pb-muted pb-no-recent">过去 30 天暂无已收录进展；历史记录保留在下方。</p>')+(older.length?'<details class="pb-archive"'+(!recent.length?' open':'')+'><summary>历史进展 <span>'+older.length+' 条 · '+esc(cutoff)+' 之前</span></summary>'+timeline(older,s)+'</details>':'');
 }
 function empty(s,title){return '<div class="pb-empty"><h3>'+esc(title)+'</h3><p>可以放宽场景、投资背景或搜索条件。</p>'+link(s,{scene:'all',investor:'all',kind:'all',product:'',q:'',legacy:''},'清除筛选','button')+'</div>'}
 // A product history is an ordinal sequence, not a proportional time chart.
 const READING={Product:'关注实际入口、开放范围与人工复核方式。',Company:'区分融资与估值信息，不把资本信号当作产品能力。',Benchmark:'关注任务定义、评分口径与可复现材料。',Adoption:'关注采用范围；客户公告不等于独立效果评测。',Governance:'关注认证范围与适用版本，不外推为全面安全保证。',Data:'关注合作范围、数据权限与可用性。'};
 function historyHTML(x,history){
  const rows=[...history].reverse(),trackId='pb-history-'+x.id;
  const cards=rows.map((e,i)=>{
   const last=i===rows.length-1,valid=canonical(e.url),precise=!!valid&&specific(e.url);
   const source=valid?new URL(valid).hostname.replace(/^www\./,''):'来源待补';
   const rich=precise&&e.evidence_level==='primary_source'&&dateOK(e.verified_at);
   const facts=rich&&Array.isArray(e.facts)?e.facts.filter(f=>f&&typeof f.label==='string'&&typeof f.value==='string').slice(0,3):[];
   const titleId=trackId+'-title-'+i;
   return '<li class="pb-milestone'+(last?' is-latest':'')+'" data-history-node>'+ 
    '<div class="pb-milestone-date"><time datetime="'+e.date+'">'+e.date.replaceAll('-','.')+'</time><span class="pb-milestone-dot" aria-hidden="true"></span></div>'+
    '<article class="pb-milestone-card" aria-labelledby="'+esc(titleId)+'"><div class="pb-milestone-top"><span class="pb-kind" data-kind="'+esc(e.kind)+'">'+esc(KINDS[e.kind]||e.kind)+'</span>'+(last?'<span class="pb-latest-badge">最新记录</span>':'')+'</div>'+
    '<h3 id="'+esc(titleId)+'">'+esc(e.title)+'</h3>'+
    '<p class="pb-milestone-summary">'+(rich&&e.summary?esc(e.summary):'<span class="pb-inline-label">阅读重点</span>'+esc(READING[e.kind]||'回到原始来源，确认发布内容、适用范围与限制。'))+'</p>'+
    (facts.length?'<dl class="pb-milestone-facts">'+facts.map(f=>'<div><dt>'+esc(f.label)+'</dt><dd>'+esc(f.value)+'</dd></div>').join('')+'</dl>':'')+
    (rich&&e.interpretation?'<p class="pb-milestone-insight"><span class="pb-inline-label">我们的解读</span>'+esc(e.interpretation)+'</p>':'')+
    '<div class="pb-milestone-source">'+external(e.url,source)+(rich?'<span>一手原文 · 已核验</span>':'<span class="pb-warning">'+(precise?'沿用收录 · 未重新核验':'栏目页，精确原文待补')+'</span>')+'</div>'+
    '<details class="pb-node-evidence"><summary>证据与边界</summary>'+
    '<p>发布时间：'+e.date.replaceAll('-','.')+(rich?' · 原文日期已核对':' · 沿用已有记录')+'</p>'+
    '<p>核验日期：'+(rich?esc(e.verified_at):'待核验；不沿用名录核对时间')+'</p>'+
    (rich&&e.scope?'<p><b>适用范围：</b>'+esc(e.scope)+'</p>':'')+
    '<p><b>不能推出：</b>'+esc(rich&&e.limitations?e.limitations:'这条记录本身不能证明任务成功率、规模化可用性或本站实测效果。')+'</p></details></article></li>';
  }).join('');
  const path=rows.map(e=>KINDS[e.kind]||e.kind).filter((kind,i,a)=>i===0||kind!==a[i-1]);
  return '<div class="pb-history-shell"><div class="pb-history-toolbar"><span>从早到晚 · 节点间距不代表时长</span><div class="pb-history-controls">'+
   '<button type="button" data-history-action="previous" aria-label="查看更早节点" aria-controls="'+esc(trackId)+'">←</button>'+
   '<button type="button" data-history-action="next" aria-label="查看更晚节点" aria-controls="'+esc(trackId)+'">→</button>'+
   '<button type="button" data-history-action="latest" aria-controls="'+esc(trackId)+'">最新节点</button></div></div>'+
   '<div class="pb-history-track" id="'+esc(trackId)+'" tabindex="0" role="region" aria-label="'+esc(x.name)+' 完整时间线，可左右滑动或使用方向键"><ol class="pb-history-nodes">'+cards+'</ol></div>'+
   (path.length>1&&path.length<=6?'<div class="pb-history-path"><b>节点脉络</b><span>'+path.map(esc).join(' <span aria-hidden="true">→</span> ')+'</span><small>仅表示时间顺序，不代表因果或能力排名。</small></div>':'')+'</div>';
 }
 function card(x,s){
  const history=chronology(x),latest=history[0],adoption=history.find(e=>e.kind==='Adoption'),backers=INVESTORS.filter(([id])=>id!=='all'&&ids(x).includes(id));
  const latestHTML=latest?'<time datetime="'+latest.date+'">'+latest.date.replaceAll('-','.')+'</time><p>'+esc(latest.title)+'</p>':'<p class="pb-muted">暂无带日期的进展</p>';
  return '<article class="pb-card" data-product-id="'+esc(x.id)+'"><header><span class="pb-monogram" aria-hidden="true">'+esc(x.name.slice(0,2).toUpperCase())+'</span><div><h2>'+esc(x.name)+'</h2><span>'+esc(sceneName(x))+(x.company!==x.name?' · '+esc(x.company):'')+'</span></div><div class="pb-backers">'+backers.map(([id,name])=>link(s,{investor:id,product:''},esc(name),'pb-backer')).join('')+'</div></header>'+
   '<div class="pb-capability"><span class="pb-label">现在能做</span><p>'+esc(x.summary)+'</p></div>'+
   '<div class="pb-latest"><span class="pb-label">最新记录</span>'+latestHTML+'</div>'+
   '<dl class="pb-facts"><div><dt>采用信号</dt><dd>'+(adoption?esc(adoption.title)+'<small>公司公告 · 非独立效果评测</small>':'<span class="pb-muted">暂无已收录的客户采用公告</span>')+'</dd></div><div><dt>最大限制</dt><dd>'+esc(x.boundary)+'</dd></div></dl>'+
   '<details class="pb-card-history"'+(s.product===x.id?' open':'')+'><summary>完整时间线 <span>'+history.length+' 个节点</span></summary>'+(history.length?historyHTML(x,history):'<p class="pb-muted">尚无可展示的日期节点，不用首次收录时间冒充发布时间。</p>')+'</details>'+
   '<details class="pb-evidence"><summary>来源与证据</summary><dl><div><dt>产品说明</dt><dd>'+external(x.product_url,'产品官网')+'<small>简介沿用已收录资料，未标记为本站实测。</small></dd></div><div><dt>客户采用</dt><dd>'+(adoption?external(adoption.url,'采用公告'):'<span class="pb-muted">待补客户公告或独立案例</span>')+'</dd></div><div><dt>投资背景</dt><dd>'+external(x.source_url,x.source_label)+'<small>'+esc(x.evidence)+'</small></dd></div></dl></details>'+
   '<footer>'+external(x.product_url,'产品官网')+link(s,{pview:'updates',product:x.id,kind:'all'},'查看动态 '+icon('arrow'))+'</footer></article>';
 }
 function page(s=read()){
  const matches=products(s),stream=events(s),totalEvents=events({...s,kind:'all'});
  const tabs=[['updates','产品动态',totalEvents.length,'条'],['map','产品地图',matches.length,'个']].map(([id,title,n,unit])=>'<a data-pb-link class="pb-view '+(s.pview===id?'active':'')+'" href="'+esc(href(s,{pview:id}))+'" '+(s.pview===id?'aria-current="page"':'')+'>'+title+'<small>'+n+' '+unit+'</small></a>').join('');
  const kindSelect='<label class="pb-kind-select">变化类型<select data-pb-field="kind" aria-label="变化类型">'+Object.entries(KINDS).map(([id,label])=>'<option value="'+id+'"'+(s.kind===id?' selected':'')+'>'+label+'</option>').join('')+'</select></label>';
  const count=s.pview==='map'?matches.length+' 个产品 · 最近有进展的优先':stream.length+' 条记录 · 含历史进展';
  return '<section class="h-wrap pb-page"><header class="pb-page-head"><div><p class="eyebrow">PRODUCT SIGNALS / TRACK & EXPLORE</p><h1>AI 产品雷达</h1><p>动态看最近变化，地图看产品能力与长期进展。</p></div><span>名录核对 '+esc(PRODUCT_RADAR.checked||'待核验')+'</span></header>'+
   '<div class="h-filterbar">'+hTabs({...hState(),cat:'product'})+'<label class="h-search">'+icon('search')+'<input id="h-search" type="search" value="'+esc(s.q)+'" placeholder="搜索产品、能力或进展" aria-label="搜索产品、能力或进展"></label></div>'+
   '<nav class="pb-views" aria-label="产品视图">'+tabs+'</nav>'+filters(s)+'<div class="pb-toolbar"><p aria-live="polite">'+count+'</p>'+(s.pview==='updates'?kindSelect:'')+link(s,{scene:'all',investor:'all',kind:'all',product:'',q:'',legacy:''},'重置筛选','pb-reset')+'</div>'+
   (s.pview==='updates'?updates(stream,s):matches.length?'<div class="pb-grid">'+matches.map(x=>card(x,s)).join('')+'</div>':empty(s,'当前筛选下暂无已建档产品'))+
   '<details class="pb-notes"><summary>收录与证据口径</summary><p>本页沿用已收录资料，不因页面改版刷新发布日期或核对时间。投资 / 孵化关系不代表能力排名；产品说明、客户采用和投资背景分别展示来源。未定位到具体文章的记录标注“精确原文待补”。行业文章不等于产品发布。</p><p>产品动态合并名录时间线与产品热点；未入库产品只在无场景 / 投资筛选时展示。产品地图首批覆盖法律与企业应用，不代表全行业。</p></details></section>';
 }
 return {read,href,products,events,chronology,canonical,specific,page,scene,updates,historyHTML};
})();
// Product tabs count products, not a sum of companies and news events.
const pbPreviousCategoryCount=hCategoryCount;
hCategoryCount=function(id){return id==='product'?(PRODUCT_RADAR.items||[]).length:pbPreviousCategoryCount(id)};
// Force a fresh render for URL-backed product controls; modified clicks retain normal browser behavior.
document.addEventListener('click',e=>{
 const a=e.target.closest('a[data-pb-link]');if(!a||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;
 e.preventDefault();if(a.getAttribute('href')!==location.hash)history.pushState(null,'',a.getAttribute('href'));lastMain='';parseRoute();
});
document.addEventListener('change',e=>{
 if(!e.target.matches('[data-pb-field="kind"]'))return;
 history.pushState(null,'',PB.href(PB.read(),{kind:e.target.value}));lastMain='';parseRoute();
});
// The track owns horizontal scrolling; never scroll the whole page to focus a node.
function pbHistorySync(track){
 const max=track.scrollWidth-track.clientWidth,controls=track.closest('.pb-history-shell').querySelector('.pb-history-controls');
 controls.hidden=max<=2;
 controls.querySelector('[data-history-action="previous"]').disabled=track.scrollLeft<=2;
 for(const action of ['next','latest'])controls.querySelector('[data-history-action="'+action+'"]').disabled=track.scrollLeft>=max-2;
}
function pbHistoryMove(track,action,instant=false){
 const nodes=[...track.querySelectorAll('[data-history-node]')],width=(nodes[0]?.getBoundingClientRect().width||track.clientWidth)+16;
 const left=action==='latest'?track.scrollWidth:action==='first'?0:track.scrollLeft+(action==='previous'?-width:width);
 track.scrollTo({left,behavior:instant||matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
 pbHistorySync(track);
}
document.addEventListener('toggle',e=>{
 if(!e.target.matches('.pb-card-history')||!e.target.open)return;
 requestAnimationFrame(()=>{const track=e.target.querySelector('.pb-history-track');if(!track)return;
  if(!track.dataset.initialized){pbHistoryMove(track,'latest',true);track.dataset.initialized='true'}else pbHistorySync(track);
 });
},true);
document.addEventListener('click',e=>{
 const button=e.target.closest('button[data-history-action]');if(!button)return;
 const track=document.getElementById(button.getAttribute('aria-controls'));if(track)pbHistoryMove(track,button.dataset.historyAction);
});
document.addEventListener('keydown',e=>{
 if(!e.target.matches('.pb-history-track')||e.altKey||e.ctrlKey||e.metaKey||e.shiftKey)return;
 const action={ArrowLeft:'previous',ArrowRight:'next',Home:'first',End:'latest'}[e.key];
 if(action){e.preventDefault();pbHistoryMove(e.target,action)}
});
document.addEventListener('scroll',e=>{if(e.target.matches?.('.pb-history-track'))pbHistorySync(e.target)},true);
window.addEventListener('resize',()=>requestAnimationFrame(()=>document.querySelectorAll('.pb-card-history[open] .pb-history-track').forEach(pbHistorySync)));
/* End product browser. */

// Refresh the landing after late overrides are loaded.
if(state.view==='feed'){lastMain='';renderMain()}
