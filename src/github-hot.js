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
  const absRate=Math.abs(t.rate)>=10?Math.round(Math.abs(t.rate)):Math.abs(t.rate).toFixed(1);
  const delta=t.gain>0?('+'+ghFmt(t.gain)):t.gain<0?('−'+ghFmt(Math.abs(t.gain))):'0';
  const rate=t.rate>0?('+'+absRate):t.rate<0?('−'+absRate):'0';
  return '近 '+hours+'h '+delta+' Star · ≈ '+rate+'/h'
}
function ghFmt(n){
  const v=Number(n)||0;
  if(v>=100000)return (v/1000).toFixed(0)+'k';
  if(v>=10000)return (v/1000).toFixed(1)+'k';
  return v.toLocaleString('en-US');
}
function ghApiMetric(symbol,value){
  return Number.isInteger(value)?symbol+' '+ghFmt(value):symbol+' 待核验';
}
function ghMoment(raw){
  if(!raw)return '';
  try{return new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(raw)).replaceAll('/','.')+' 北京时间'}
  catch{return String(raw)}
}
function ghMetadataNote(x){
  if(x.metadata_status==='unavailable')return '<span class="gh-metadata-warning">仓库 API 元数据待核验</span>';
  if(x.metadata_status!=='stale')return '';
  const at=ghMoment(x.metadata_verified_at);
  return '<span class="gh-metadata-warning">仓库 API 旧快照'+(at?' · '+esc(at):'')+'</span>';
}
function ghWhen(){
  const raw=String(GH.checked_at||'');
  if(!raw)return '待核验';
  return ghMoment(raw)
}
function ghMetadataWhen(){
  const verified=(GH.items||[]).map(x=>x.metadata_verified_at).filter(Boolean).sort().at(-1);
  const raw=String(GH.sync?.metadata_checked_at||verified||'');
  return raw?ghMoment(raw):'待核验'
}
function ghFreshness(){
  const t=Date.parse(String(GH.checked_at||''));
  if(!Number.isFinite(t))return {stale:true,ageHours:null};
  const ageHours=Math.max(0,(Date.now()-t)/36e5);
  return {stale:ageHours>6,ageHours}
}
function ghStaleNotice(){
  const f=ghFreshness();
  if(!f.stale&&GH.sync?.status==='error')return '<div class="ranking-stale"><strong>最近一次采集失败，已保留成功快照</strong><span>当前数据仍为 '+esc(ghWhen())+' 的最近成功快照；只有后续采集成功后才会更新榜单。</span></div>';
  if(!f.stale)return '';
  const age=f.ageHours==null?'更新时间不可核验':('已超过 '+Math.floor(f.ageHours)+' 小时未核验');
  const failed=GH.sync?.status==='error'?' · 最近一次同步失败，已进入维护提醒':'';
  return '<div class="ranking-stale"><strong>数据已过期，暂不作为当前榜</strong><span>'+esc(age+failed)+' · 下方仅保留 '+esc(ghWhen())+' 的历史快照，请以 GitHub 官方 Trending 为准。</span></div>'
}
function ghPartialNotice(){
  const sync=GH.sync||{},metadataFailures=Number(sync.metadata_failed_count)||0,watchFailures=Number(sync.watchlist_failed_count)||0;
  if(sync.metadata_status!=='partial'&&!metadataFailures&&!watchFailures)return '';
  const details=[];
  const total=(GH.items||[]).length;
  const allMetadataFailed=total>0&&metadataFailures>=total;
  const stale=(GH.items||[]).filter(x=>x.metadata_status==='stale').length;
  const unavailable=(GH.items||[]).filter(x=>x.metadata_status==='unavailable').length;
  if(stale)details.push(stale+' 个上榜仓库的总 Star / Fork / 推送时间沿用旧快照');
  if(unavailable)details.push(unavailable+' 个新上榜仓库的 API 元数据待首次核验');
  if(metadataFailures&&!stale&&!unavailable)details.push(metadataFailures+' 个上榜仓库的 API 指标未同步');
  if(watchFailures)details.push(watchFailures+' 个长期关注仓库本轮 API 核验失败');
  return '<div class="ranking-partial"><strong>官方榜位与今日 Star 已更新；'+(allMetadataFailed?'全部':'部分')+'仓库 API 指标未同步</strong><span>'+esc(details.join('；')||'部分仓库 API 元数据待核验')+'。下方逐行标出旧快照，不影响 GitHub Trending 官方顺序。</span></div>'
}
function ghWatchPanel(){
 const q=ghQuery().toLowerCase();
 const cat=ghTopic();
 const tracked=(GH.watchlist||[]).filter(x=>(cat==='all'||x.category===cat)&&(!q||[x.repo,x.description,...(x.tags||[])].join(' ').toLowerCase().includes(q)));
 if(!tracked.length)return '';
 return '<section class="gh-watch"><div class="gh-watch-title"><div><h3>长期关注仓库</h3><p>GitHub Repository API 统计，与 Trending 当日名次分开。</p></div><small>'+tracked.length+' 个</small></div>'+
 tracked.map(x=>{
  const rank=(GH.items||[]).find(row=>row.repo.toLowerCase()===x.repo.toLowerCase());
  const verified=Date.parse(x.verified_at||''),age=Number.isFinite(verified)?Math.max(0,(Date.now()-verified)/36e5):Infinity;
  const status=rank&&!ghFreshness().stale?'官方 Trending #'+rank.rank:'独立关注 · 不代表今日上榜';
  const numbers=Number.isInteger(x.stars)&&x.verified_at?'★ '+ghFmt(x.stars)+' 总 Star · ⑂ '+ghFmt(x.forks)+' Forks':'GitHub API 数据待核验';
  const when=Number.isFinite(verified)?(age>24?'旧快照 · ':'API 核验 · ')+esc(x.verified_at.slice(0,10)):'等待首次核验';
  return '<a class="gh-watch-row" href="'+safeLink(x.url)+'" target="_blank" rel="noopener noreferrer"><span class="gh-watch-symbol">'+icon('github')+'</span><span class="gh-watch-copy"><strong>'+esc(x.repo)+'</strong><small>'+esc(x.description||'')+'</small><em>'+esc(status)+'</em></span><span class="gh-watch-stats"><b>'+esc(numbers)+'</b><small>'+when+'</small></span></a>';
 }).join('')+'</section>';
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
  if(ghFreshness().stale)return '<section class="gh-preview"><div class="v10-section-head"><div><p class="eyebrow">GITHUB / DEVELOPER SIGNAL</p><h2>GitHub AI 热仓</h2><p>榜单快照已过期，因此首页不继续展示旧的 Top 项目。</p></div><a href="#/hot?tab=github">查看历史快照 '+icon('arrow')+'</a></div>'+ghStaleNotice()+'</section>';
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
    '<div class="gh-preview-foot"><span>完整榜位不改写 · 来源：GitHub Trending</span><span>榜位 '+esc(ghWhen())+' · 仓库 API '+esc(ghMetadataWhen())+'</span></div>'+
  '</section>';
}

function ghInline(){
  const rows=ghRows();
  const max=Math.max(...rows.map(x=>Number(x.stars_today)||0),1);
  return '<section class="gh-inline">'+
    hOpenTabs('github')+
    '<div class="gh-inline-head"><div><strong>'+(ghFreshness().stale?'GitHub Trending · 历史快照':'GitHub Trending · Today')+'</strong><span>'+(ghFreshness().stale?'该快照已过期，不代表当前榜位。':'官方榜位 + 今日新增 Star，作为开发者采用信号。')+'</span></div><div><span>榜位 '+esc(ghWhen())+'</span><span>'+(GH.sync?.metadata_status==='success'?'仓库 API ':'仓库 API 最近成功 ')+esc(ghMetadataWhen())+'</span><a href="'+safeLink(GH.source_url)+'" target="_blank" rel="noopener noreferrer">打开 GitHub 原榜 '+icon('external')+'</a></div></div>'+
    ghStaleNotice()+
    ghPartialNotice()+
    '<div class="gh-method"><b>怎么看</b><span>左侧 # 是 GitHub Trending 官方榜位；右侧同时看“今日 Star”和最近几次快照的 Star 斜率；新上榜仓历史不足时不画趋势线。中间补“仓库创建 / 最近推送”，用来区分新仓爆发、老仓翻红和持续活跃。趋势来自连续快照，不是本站估算浏览量。</span></div>'+
    ghTopicTabs()+
    '<p class="gh-resultline" role="status" aria-live="polite">显示 '+rows.length+' / '+(GH.items||[]).length+' 个仓库 · 保留 GitHub 官方榜位</p>'+
    (rows.length?'<div class="gh-list">'+rows.map(x=>
      '<a class="gh-row" href="'+safeLink(x.url)+'" target="_blank" rel="noopener noreferrer">'+
        '<div class="gh-rank">#'+String(x.rank).padStart(2,'0')+'</div>'+
        '<div class="gh-main"><div class="gh-repo">'+esc(x.repo)+'<em class="gh-type">'+esc(ghCategory(x))+'</em></div><p>'+esc(x.description||'')+'</p><div class="gh-sub"><span>'+esc(x.language||'—')+'</span><span>'+esc(ghApiMetric('★',x.stars))+'</span><span>'+esc(ghApiMetric('⑂',x.forks))+'</span><span>创建 '+esc(ghRepoMonth(x.repo_created_at))+'</span><span title="北京时间">推送 '+esc(ghRepoPush(x.repo_pushed_at))+'</span>'+ghMetadataNote(x)+'</div><div class="gh-tags">'+(x.tags||[]).map(t=>'<span>'+esc(t)+'</span>').join('')+'</div></div>'+
        '<div class="gh-delta"><strong>+'+ghFmt(x.stars_today)+'</strong><span>今日 Star</span><i style="--gh-w:'+ghBarWidth(x.stars_today,max)+'%"></i>'+ghSpark(x)+'<small class="gh-velocity">'+esc(ghTrendLabel(x))+'</small></div>'+
      '</a>'
    ).join('')+'</div>':'<div class="h-empty"><h3>没有匹配的 GitHub 项目</h3><p>换个关键词或主题继续看。</p><button class="button" data-gh-clear>清除搜索与筛选</button></div>')+
    '<footer class="gh-note">'+esc(GH.note||'')+'</footer>'+
    ghWatchPanel()+
  '</section>'
}

const ghBaseHotPage=hotPage;
hotPage=function(){
  if(!ghActive())return ghBaseHotPage();
  const s=hState(),q=ghQuery(),stale=ghFreshness().stale;
  return '<section class="h-wrap v10-hot gh-embedded">'+
    '<header class="h-head"><div><p class="eyebrow"><span class="accent">●</span> '+(stale?'HISTORICAL SNAPSHOT / STALE':'DEVELOPER SIGNALS / OFFICIAL ORDER')+'</p><h1>'+(stale?'GitHub 历史快照':'GitHub 热榜')+'<span class="accent">.</span></h1><p>'+(stale?'旧数据不再占据“当前”位置；先保留可追溯快照，并引导回官方原榜。':'看官方 Trending Today 的榜位与今日 Star；它们是开发者关注信号，不和新闻热度混排。')+'</p></div><div class="h-meta"><span><i class="state-dot"></i> '+(stale?'非当前榜':'GitHub Trending')+'</span><span>'+esc(ghWhen())+'</span></div></header>'+
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
document.addEventListener('click',e=>{if(!e.target.closest('[data-gh-clear]'))return;e.preventDefault();history.replaceState(null,'','#/hot?tab=github');parseRoute()});

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
