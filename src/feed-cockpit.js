'use strict';
(()=>{
/* 精选头部：左侧紧凑热点，右侧「拆一下」+ GitHub 热仓。 */
function fcHotPanel(){
 const rows=v10HotByHeat(HOT.items).slice(0,5);
 return '<section class="fc-panel fc-hot-panel">'+
  '<div class="fc-panel-head"><div><p class="eyebrow">HOT / NOW</p><h2>热点</h2></div><a href="#/hot">全部热点 '+icon('arrow')+'</a></div>'+
  '<div class="fc-hot-list">'+rows.map((x,i)=>
   '<a class="fc-hot-row" href="#/hot?item='+encodeURIComponent(x.id)+'">'+
    '<span class="fc-hot-rank">'+String(i+1).padStart(2,'0')+'</span>'+
    '<span class="fc-hot-main"><span class="fc-hot-meta"><em>'+esc(HOT_CATS.get(x.category)?.title||x.category)+'</em><time>'+esc(x.published.slice(5).replace('-','.'))+'</time><small>'+esc(x.source)+'</small></span><strong>'+esc(x.title)+'</strong></span>'+
    '<span class="fc-hot-score"><b>'+esc(String(x.heat))+'</b>'+hTrend(x)+'</span>'+
   '</a>'
  ).join('')+'</div>'+
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
function fcGithubPanel(){
 const gh=APP.github_hot||{items:[],checked_at:''};
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
  '<div class="fc-gh-foot">GitHub Trending · AI / Agent 相关项目</div>'+
 '</section>'
}
function fcCockpit(){
 return '<section class="fc-cockpit"><div class="fc-left">'+fcHotPanel()+'</div><aside class="fc-right">'+fcDeepPanel()+fcGithubPanel()+'</aside></section>'
}
function fcStripLegacy(html){
 return html
  .replace(/<section class="top5-editorial">[\s\S]*?<\/section>/,'')
  .replace(/<section class="d-feed">[\s\S]*?<\/section>/,'')
  .replace(/<section class="gh-preview">[\s\S]*?<\/section>/,'')
}
const fcBaseFeedPage=feedPage;
feedPage=function(){
 let html=fcStripLegacy(fcBaseFeedPage());
 html=html.replace('先看全站 Top 5，再看你的关注，最后按时间浏览通用 AI 变化。','左边扫热点，右边看「拆一下」和 GitHub 热仓，再往下看你的关注与每日时间线。');
 const block=fcCockpit();
 const marker='<section class="v10-personal',at=html.indexOf(marker);
 return at>=0?html.slice(0,at)+block+html.slice(at):html+block
};
if(state.view==='feed'){lastMain='';renderMain()}
})();