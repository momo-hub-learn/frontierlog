'use strict';
(()=>{
/* 精选头部：全宽热点 + 三张工具卡；关注卡固定在左侧并自适应为方块。 */
function fcHotPanel(){
 const rows=v10Top5Rows();
 return '<section class="fc-panel fc-hot-panel">'+
  '<div class="fc-panel-head"><div class="fc-panel-titleline"><h2>热点</h2><span class="eyebrow">HOT / RECENT</span><span class="fc-hot-sync">'+esc(v10HotStatusShort())+'</span></div><a href="#/hot">全部热点 '+icon('arrow')+'</a></div>'+
  '<div class="fc-hot-list">'+rows.map((x,i)=>
   '<a class="fc-hot-row" href="#/hot?item='+encodeURIComponent(x.id)+'">'+
    '<span class="fc-hot-rank">'+String(i+1).padStart(2,'0')+'</span>'+
    '<span class="fc-hot-main"><span class="fc-hot-meta"><em>'+esc(HOT_CATS.get(x.category)?.title||x.category)+'</em><time>'+esc(x.published.slice(5).replace('-','.'))+'</time><small>'+esc(x.source)+'</small></span><strong>'+esc(x.title)+'</strong></span>'+
    '<span class="fc-hot-score"><b>'+esc(String(x.heat))+'</b>'+hTrend(x)+'</span>'+
   '</a>'
  ).join('')+'</div>'+
 '</section>'
}
function fcPersonalPanel(){
 const p=v10Prefs(),followed=p.topics.size+p.models;
 const latest=v10HotByTime(HOT.items.filter(x=>v10PersonalMatch(x,p)))[0];
 const state=followed?'has-follow':'is-empty';
 const title=followed?'你的关注':'只看与你有关的热点';
 const copy=followed
  ?'已关注 '+followed+' 项；只把匹配主题或模型的高信号变化放进来。'
  :'关注主题或模型后，这里会变成你的本地过滤器，不再占一整条横幅。';
 const latestBlock=latest
  ?'<a class="fc-personal-latest" href="#/hot?item='+encodeURIComponent(latest.id)+'"><span>最新相关</span><b>'+esc(latest.title)+'</b>'+icon('arrow')+'</a>'
  :'<div class="fc-personal-latest empty"><span>开始关注</span><b>先选主题或模型，之后只看相关更新。</b></div>';
 return '<section class="fc-panel fc-personal-panel '+state+'">'+
  '<div class="fc-personal-head"><div><p class="eyebrow">FOR YOU / LOCAL</p><h2>'+esc(title)+'</h2></div><strong class="fc-personal-count">'+esc(String(followed))+'</strong></div>'+
  '<p class="fc-personal-copy">'+esc(copy)+'</p>'+
  '<div class="fc-personal-actions">'+
   '<a href="#/topics"><span>选择主题</span><strong>'+esc(String(p.topics.size))+'</strong><small>医药 / 制造</small></a>'+
   '<a href="#/models"><span>关注模型</span><strong>'+esc(String(p.models))+'</strong><small>模型 / 公司</small></a>'+
  '</div>'+
  latestBlock+
 '</section>'
}
function fcDeepPanel(){
 const a=[...(APP.deep_dives?.articles||[])].sort((x,y)=>String(y.published||'').localeCompare(String(x.published||'')))[0];
 if(!a)return '';
 const flow=(a.mini_flow||[]).slice(0,3);
 const diagram=flow.length===3?'<div class="fc-mini-arch" aria-label="技术链路摘要">'+flow.map((x,i)=>(i?'<i aria-hidden="true">→</i>':'')+'<span class="'+(i===1?'is-accent':'')+'"><b>'+esc(x.label)+'</b><small>'+esc(x.detail)+'</small></span>').join('')+'</div>':'';
 return '<a class="fc-panel fc-deep-panel" href="#/deep?id='+encodeURIComponent(a.id)+'">'+
  '<div class="fc-side-head"><span class="fc-kicker">拆一下</span><small>'+esc(a.published.slice(5).replace('-','.'))+' · '+esc(String(a.read_minutes))+' MIN</small></div>'+
  '<h2>'+esc(a.short_title||a.title)+'</h2>'+
  '<p>'+esc(a.subtitle)+'</p>'+
  diagram+
  '<div class="fc-side-foot"><span>读完整解析</span>'+icon('arrow')+'</div>'+
 '</a>'
}
function fcGithubPanel(){
 const gh=APP.github_hot||{items:[],watchlist:[],checked_at:''};
 const verified=Date.parse(gh.checked_at||'');
 const fresh=Number.isFinite(verified)&&(Date.now()-verified)<=6*36e5&&(Date.now()-verified)>=-36e5;
 const rows=fresh?(gh.items||[]).filter(x=>x.ai_related).sort((a,b)=>(b.stars_today||0)-(a.stars_today||0)||a.rank-b.rank).slice(0,3):[];
 const fmt=n=>{const v=Number(n)||0;return v>=1000?(v/1000).toFixed(v>=10000?0:1)+'k':String(v)};
 const followed=(gh.watchlist||[]).filter(x=>x.ai_related).filter(x=>!rows.some(r=>r.repo.toLowerCase()===x.repo.toLowerCase())).slice(0,1);
 return '<section class="fc-panel fc-gh-panel">'+
  '<div class="fc-panel-head compact"><div><p class="eyebrow">GITHUB / VERIFIED</p><h2>GitHub 热仓</h2></div><a href="#/hot?tab=github">完整榜 '+icon('arrow')+'</a></div>'+
  (fresh?'<div class="fc-gh-list">'+rows.map(x=>
   '<a class="fc-gh-row" href="'+safeLink(x.url)+'" target="_blank" rel="noopener noreferrer">'+
    '<span class="fc-gh-rank">#'+String(x.rank).padStart(2,'0')+'</span>'+
    '<span class="fc-gh-main"><strong>'+esc(x.repo)+'</strong><small>'+esc(x.description||x.language||'')+'</small></span>'+
    '<span class="fc-gh-star"><b>+'+fmt(x.stars_today)+'</b><small>Today</small></span></a>'
  ).join('')+'</div>':
  '<div class="fc-gh-old"><strong>当前 Trending 未完成核验</strong><p>旧榜单已停止作为今日热门展示。可查看独立关注仓库或历史快照。</p></div>')+
  (followed.length?'<div class="fc-gh-watch">'+followed.map(x=>
   '<a class="fc-gh-row" href="'+safeLink(x.url)+'" target="_blank" rel="noopener noreferrer">'+
    '<span class="fc-gh-rank">追踪</span><span class="fc-gh-main"><strong>'+esc(x.repo)+'</strong><small>独立关注 · 不等于今日上榜 · '+esc(x.verified_at?.slice(0,10)||'待核验')+'</small></span>'+
    '<span class="fc-gh-star"><b>'+ (x.verified_at&&Number.isInteger(x.stars)?fmt(x.stars):'—') +'</b><small>总 Star</small></span></a>'
  ).join('')+'</div>':'')+
  '<div class="fc-gh-foot">'+(fresh?'官方 Trending · 当日新增 Star':'历史榜已过期 · 等待新快照')+(gh.sync?.status==='error'?' · 最新同步失败':'')+' · 独立关注不参与排名</div>'+
 '</section>'
}

function fcCockpit(){
 return '<section class="fc-cockpit">'+
  fcHotPanel()+
  '<div class="fc-tool-grid">'+fcPersonalPanel()+fcDeepPanel()+fcGithubPanel()+'</div>'+
 '</section>'
}
function fcStripLegacy(html){
 return html
  .replace(/<section class="top5-editorial">[\s\S]*?<\/section>/,'')
  .replace(/<section class="d-feed">[\s\S]*?<\/section>/,'')
  .replace(/<section class="gh-preview">[\s\S]*?<\/section>/,'')
  .replace(/<section class="v10-personal[\s\S]*?<\/section>/,'')
}
const fcBaseFeedPage=feedPage;
feedPage=function(){
 let html=fcStripLegacy(fcBaseFeedPage());
 const block=fcCockpit();
 const marker='<section class="v10-general',at=html.indexOf(marker);
 return at>=0?html.slice(0,at)+block+html.slice(at):html+block
};
if(state.view==='feed'){lastMain='';renderMain()}
})();