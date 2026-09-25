'use strict';
(()=>{
/* 精选头部：全宽热点 + 三张工具卡；关注卡固定在左侧并自适应为方块。 */
function fcHotPanel(){
 const rows=v10HotByHeat(HOT.items).slice(0,5);
 return '<section class="fc-panel fc-hot-panel">'+
  '<div class="fc-panel-head"><div class="fc-panel-titleline"><h2>热点</h2><span class="eyebrow">HOT / NOW</span></div><a href="#/hot">全部热点 '+icon('arrow')+'</a></div>'+
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
 const a=APP.deep_dives?.articles?.[0];
 if(!a)return '';
 return '<a class="fc-panel fc-deep-panel" href="#/deep?id='+encodeURIComponent(a.id)+'">'+
  '<div class="fc-side-head"><span class="fc-kicker">拆一下</span><small>'+esc(String(a.read_minutes))+' MIN</small></div>'+
  '<h2>'+esc(a.short_title||a.title)+'</h2>'+
  '<p>'+esc(a.subtitle)+'</p>'+
  '<div class="fc-mini-arch" aria-label="架构摘要"><span><b>LLM</b><small>生成 / 推理</small></span><i>+</i><span class="is-accent"><b>Jev</b><small>路由 / 评分</small></span><i>→</i><span><b>Code</b><small>阈值 / 分支</small></span></div>'+
  '<div class="fc-side-foot"><span>读完整架构解析</span>'+icon('arrow')+'</div>'+
 '</a>'
}
function fcTrendAgeHours(raw){
 const t=Date.parse(raw||'');return Number.isFinite(t)?Math.max(0,(Date.now()-t)/36e5):Infinity
}
function fcTrendStale(data){return fcTrendAgeHours(data?.checked_at)>6}
function fcTrendStamp(data){
 const raw=String(data?.checked_at||'');if(!raw)return '待核验';
 try{return new Intl.DateTimeFormat('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(raw))}catch{return raw}
}
function fcGithubPanel(){
 const gh=APP.github_hot||{items:[],checked_at:''};
 if(fcTrendStale(gh))return '<section class="fc-panel fc-gh-panel">'+
  '<div class="fc-panel-head compact"><div><p class="eyebrow">GITHUB / SNAPSHOT</p><h2>GitHub 热仓</h2></div><a href="#/hot?tab=github">上次快照 '+icon('arrow')+'</a></div>'+
  '<div class="fc-personal-latest empty"><span>过期快照 · '+esc(fcTrendStamp(gh))+'</span><b>超过 6 小时未完成官方核验，暂不展示“今日 Top”。</b></div>'+
  '<div class="fc-gh-foot">旧榜仅作历史参考 · 等下一次 GitHub Trending 官方核验后恢复</div>'+
 '</section>';
 const rows=(gh.items||[]).filter(x=>x.ai_related).sort((a,b)=>(b.stars_today||0)-(a.stars_today||0)||a.rank-b.rank).slice(0,3);
 const fmt=n=>{const v=Number(n)||0;return v>=1000?(v/1000).toFixed(v>=10000?0:1)+'k':String(v)};
 return '<section class="fc-panel fc-gh-panel">'+
  '<div class="fc-panel-head compact"><div><p class="eyebrow">GITHUB / TODAY</p><h2>GitHub 热仓</h2></div><a href="#/hot?tab=github">完整榜 '+icon('arrow')+'</a></div>'+
  '<div class="fc-gh-list">'+rows.map(x=>
   '<a class="fc-gh-row" href="'+safeLink(x.url)+'" target="_blank" rel="noopener noreferrer">'+
    '<span class="fc-gh-rank">#'+String(x.rank).padStart(2,'0')+'</span>'+
    '<span class="fc-gh-main"><strong>'+esc(x.repo)+'</strong><small>'+esc(x.description||x.language||'')+'</small></span>'+
    '<span class="fc-gh-star"><b>+'+fmt(x.stars_today)+'</b><small>today</small></span>'+
   '</a>'
  ).join('')+'</div>'+
  '<div class="fc-gh-foot">GitHub Trending · Runtime / Harness / Memory / Coding Agent 等细分</div>'+
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
 html=html.replace('先看全站 Top 5，再看你的关注，最后按时间浏览通用 AI 变化。','先扫热点，再看你的关注、「拆一下」和 GitHub 热仓，最后进入分时热点。');
 const block=fcCockpit();
 const marker='<section class="v10-general',at=html.indexOf(marker);
 return at>=0?html.slice(0,at)+block+html.slice(at):html+block
};

function fcTrendFreshnessGuard(){
 const pairs=[
  ['.gh-embedded .gh-inline',APP.github_hot,'GitHub Trending'],
  ['.hf-embedded .hf-inline',APP.huggingface_hot,'Hugging Face Trending']
 ];
 pairs.forEach(([selector,data,label])=>{
  if(!fcTrendStale(data))return;
  const host=document.querySelector(selector);if(!host||host.querySelector('.fc-trend-stale'))return;
  const note=document.createElement('div');note.className='gh-method fc-trend-stale';
  const b=document.createElement('b');b.textContent='过期快照';
  const span=document.createElement('span');span.textContent='最后核验 '+fcTrendStamp(data)+'，已超过 6 小时；以下只保留为历史快照，不代表当前 '+label+'。';
  note.append(b,span);host.prepend(note)
 });
 const ghMeta=document.querySelector('.gh-embedded .h-meta span:last-child');
 if(ghMeta&&fcTrendStale(APP.github_hot))ghMeta.textContent='过期快照 · '+fcTrendStamp(APP.github_hot);
 const hfMeta=document.querySelector('.hf-embedded .h-meta span:last-child');
 if(hfMeta&&fcTrendStale(APP.huggingface_hot))hfMeta.textContent='过期快照 · '+fcTrendStamp(APP.huggingface_hot)
}
const fcFreshBaseRenderMain=renderMain;
renderMain=function(){fcFreshBaseRenderMain();fcTrendFreshnessGuard()};

if(state.view==='feed'){lastMain='';renderMain()}
})();
