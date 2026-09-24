'use strict';
(()=>{
const GH=APP.github_hot||{items:[],checked_at:'',source_url:'https://github.com/trending',source_scope:'GitHub Trending'};
pages.github=['热点榜 · GitHub','github'];
const GH_CATS=new Map((GH.categories||[]).map(c=>[c.id,c]));
function ghCategory(x){return GH_CATS.get(x.category)?.title||'其他'}
function ghTopic(){
  const raw=new URLSearchParams(location.hash.split('?')[1]||'').get('ghcat');
  return raw&&GH_CATS.has(raw)?raw:'all'
}
function ghTopicHref(id){
  const p=new URLSearchParams(location.hash.split('?')[1]||'');
  p.set('tab','github');
  if(id==='all')p.delete('ghcat');else p.set('ghcat',id);
  return '#/hot?'+p.toString()
}
function ghTopicTabs(){
  const active=ghTopic(),items=GH.items||[];
  const cats=(GH.categories||[]).filter(c=>items.some(x=>x.category===c.id));
  const one=(id,title,count)=>'<a class="gh-topic-chip '+(active===id?'active':'')+'" href="'+ghTopicHref(id)+'" '+(active===id?'aria-current="page"':'')+'><span>'+esc(title)+'</span><small>'+count+'</small></a>';
  return '<nav class="gh-topics" aria-label="GitHub 项目主题">'+one('all','全部',items.length)+cats.map(c=>one(c.id,c.title,items.filter(x=>x.category===c.id).length)).join('')+'</nav>'
}

function ghRepoMonth(raw){
  if(!raw)return '—';
  const d=new Date(raw);if(Number.isNaN(d.getTime()))return '—';
  return new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit'}).format(d).replace('/','.');
}
function ghRepoPush(raw){
  if(!raw)return '—';
  const d=new Date(raw);if(Number.isNaN(d.getTime()))return '—';
  return new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(d).replaceAll('/','.');
}
function ghTrend(x){
  const h=(x.star_history||[]).filter(p=>p&&Number.isFinite(Number(p.stars))&&p.at).sort((a,b)=>String(a.at).localeCompare(String(b.at)));
  if(h.length<2)return null;
  const first=h[0],last=h[h.length-1],hours=(Date.parse(last.at)-Date.parse(first.at))/36e5;
  if(!(hours>0))return null;
  const gain=Number(last.stars)-Number(first.stars);
  return {h,first,last,hours,gain,rate:gain/hours}
}
function ghSpark(x){
  const t=ghTrend(x);if(!t)return '';
  const vals=t.h.map(p=>Number(p.stars)),lo=Math.min(...vals),hi=Math.max(...vals),span=Math.max(1,hi-lo);
  const pts=vals.map((v,i)=>{const px=t.h.length===1?50:i/(t.h.length-1)*100,py=22-(v-lo)/span*18;return px.toFixed(1)+','+py.toFixed(1)}).join(' ');
  return '<svg class="gh-spark" viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden="true"><polyline points="'+pts+'"></polyline></svg>'
}
function ghTrendLabel(x){
  const t=ghTrend(x);if(!t)return '';
  const hours=t.hours<10?t.hours.toFixed(1):Math.round(t.hours);
  const rate=t.rate>=10?Math.round(t.rate):t.rate.toFixed(1);
  return '近 '+hours+'h +'+ghFmt(t.gain)+' Star · ≈ '+rate+'/h'
}
function ghFmt(n){
  const v=Number(n)||0;
  if(v>=100000)return (v/1000).toFixed(0)+'k';
  if(v>=10000)return (v/1000).toFixed(1)+'k';
  return v.toLocaleString('en-US');
}
function ghWhen(){
  const raw=String(GH.checked_at||'');
  if(!raw)return '待核验';
  try{return new Intl.DateTimeFormat('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(raw))}
  catch{return raw}
}
function ghActive(){
  if(state.view==='github')return true;
  if(state.view!=='hot')return false;
  return new URLSearchParams(location.hash.split('?')[1]||'').get('tab')==='github';
}
function ghQuery(){
  return (new URLSearchParams(location.hash.split('?')[1]||'').get('q')||'').slice(0,300).trim();
}
function ghRows(){
  const q=ghQuery().toLowerCase(),cat=ghTopic();
  return (GH.items||[]).filter(x=>(cat==='all'||x.category===cat)&&(!q||[x.repo,x.description,x.language,ghCategory(x),...(x.tags||[])].join(' ').toLowerCase().includes(q))).sort((a,b)=>a.rank-b.rank);
}
function ghPreviewRows(){
  return (GH.items||[]).filter(x=>x.ai_related).sort((a,b)=>b.stars_today-a.stars_today||a.rank-b.rank).slice(0,5);
}
function ghBarWidth(value,max){
  if(!max)return 0;
  return Math.max(4,Math.round((Number(value)||0)/max*100));
}
function ghPreview(){
  const rows=ghPreviewRows();
  if(!rows.length)return '';
  const max=Math.max(...rows.map(x=>Number(x.stars_today)||0),1);
  return '<section class="gh-preview">'+
    '<div class="v10-section-head"><div><p class="eyebrow">GITHUB / DEVELOPER SIGNAL</p><h2>GitHub AI 热仓</h2><p>从 GitHub 官方 Trending 中挑出 AI / Agent 相关项目；这里按“今日新增 Star”排，专门看开发者侧热度。</p></div><a href="#/hot?tab=github">完整 GitHub 热榜 '+icon('arrow')+'</a></div>'+
    '<div class="gh-preview-list">'+rows.map(x=>
      '<a class="gh-preview-row" href="'+safeLink(x.url)+'" target="_blank" rel="noopener noreferrer">'+
        '<span class="gh-preview-rank">GitHub #'+String(x.rank).padStart(2,'0')+'</span>'+
        '<span class="gh-preview-main"><strong>'+esc(x.repo)+'</strong><small>'+esc(x.description||'')+'</small></span>'+
        '<span class="gh-preview-heat"><b>+'+ghFmt(x.stars_today)+'</b><small>今日 Star</small><i style="--gh-w:'+ghBarWidth(x.stars_today,max)+'%"></i></span>'+
      '</a>'
    ).join('')+'</div>'+
    '<div class="gh-preview-foot"><span>完整榜位不改写 · 来源：GitHub Trending</span><span>核验 '+esc(ghWhen())+'</span></div>'+
  '</section>';
}

function ghInline(){
  const rows=ghRows();
  const max=Math.max(...rows.map(x=>Number(x.stars_today)||0),1);
  return '<section class="gh-inline">'+
    hOpenTabs('github')+
    '<div class="gh-inline-head"><div><strong>GitHub Trending · Today</strong><span>官方榜位 + 今日新增 Star，作为开发者采用信号。</span></div><div><span>核验 '+esc(ghWhen())+'</span><a href="'+safeLink(GH.source_url)+'" target="_blank" rel="noopener noreferrer">打开 GitHub 原榜 '+icon('external')+'</a></div></div>'+
    '<div class="gh-method"><b>怎么看</b><span>左侧 # 是 GitHub Trending 官方榜位；右侧同时看“今日 Star”和最近几次快照的 Star 斜率；新上榜仓历史不足时不画趋势线。中间补“仓库创建 / 最近推送”，用来区分新仓爆发、老仓翻红和持续活跃。趋势来自连续快照，不是本站估算浏览量。</span></div>'+
    ghTopicTabs()+
    (rows.length?'<div class="gh-list">'+rows.map(x=>
      '<a class="gh-row" href="'+safeLink(x.url)+'" target="_blank" rel="noopener noreferrer">'+
        '<div class="gh-rank">#'+String(x.rank).padStart(2,'0')+'</div>'+
        '<div class="gh-main"><div class="gh-repo">'+esc(x.repo)+'<em class="gh-type">'+esc(ghCategory(x))+'</em></div><p>'+esc(x.description||'')+'</p><div class="gh-sub"><span>'+esc(x.language||'—')+'</span><span>★ '+ghFmt(x.stars)+'</span><span>⑂ '+ghFmt(x.forks)+'</span><span>创建 '+esc(ghRepoMonth(x.repo_created_at))+'</span><span title="北京时间">推送 '+esc(ghRepoPush(x.repo_pushed_at))+'</span></div><div class="gh-tags">'+(x.tags||[]).map(t=>'<span>'+esc(t)+'</span>').join('')+'</div></div>'+
        '<div class="gh-delta"><strong>+'+ghFmt(x.stars_today)+'</strong><span>今日 Star</span><i style="--gh-w:'+ghBarWidth(x.stars_today,max)+'%"></i>'+ghSpark(x)+'<small class="gh-velocity">'+esc(ghTrendLabel(x))+'</small></div>'+
      '</a>'
    ).join('')+'</div>':'<div class="h-empty"><h3>没有匹配的 GitHub 项目</h3><p>换个关键词继续看。</p></div>')+
    '<footer class="gh-note">'+esc(GH.note||'')+'</footer>'+
  '</section>'
}

const ghBaseHotPage=hotPage;
hotPage=function(){
  if(!ghActive())return ghBaseHotPage();
  const s=hState(),q=ghQuery();
  return '<section class="h-wrap v10-hot gh-embedded">'+
    '<header class="h-head"><div><p class="eyebrow"><span class="accent">●</span> HOT SIGNALS / NEWEST FIRST</p><h1>热点时间线<span class="accent">.</span></h1><p>新闻热点看时间，GitHub 热榜看开发者采用信号；两种口径不混排行。</p></div><div class="h-meta"><span><i class="state-dot"></i> GitHub Trending</span><span>'+esc(ghWhen())+'</span></div></header>'+
    '<div class="h-filterbar">'+hTabs(s)+'<label class="h-search">'+icon('search')+'<input id="gh-search" type="search" value="'+esc(q)+'" placeholder="搜索仓库、类型、标签…" aria-label="搜索 GitHub 热榜"><kbd>/</kbd></label></div>'+
    ghInline()+
  '</section>'
};

document.addEventListener('input',e=>{
  if(e.target.id!=='gh-search')return;
  const value=e.target.value,pos=e.target.selectionStart,p=new URLSearchParams(location.hash.split('?')[1]||'');
  p.set('tab','github');
  if(value)p.set('q',value);else p.delete('q');
  history.replaceState(null,'','#/hot?'+p.toString());
  parseRoute();
  const n=document.getElementById('gh-search');if(n){n.focus({preventScroll:true});try{n.setSelectionRange(pos,pos)}catch{}}
});

const ghBaseRenderMain=renderMain;
renderMain=function(){
  if(state.view==='github'){
    history.replaceState(null,'','#/hot?tab=github');
    parseRoute();
    return
  }
  ghBaseRenderMain();
};

const ghBaseFeedPage=feedPage;
feedPage=function(){
  const html=ghBaseFeedPage(),block=ghPreview(),marker='<section class="v10-personal',at=html.indexOf(marker);
  return at>=0?html.slice(0,at)+block+html.slice(at):html+block
};

if(state.view==='feed'){lastMain='';renderMain()}
})();