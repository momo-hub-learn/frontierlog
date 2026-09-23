'use strict';
(()=>{
const GH=APP.github_hot||{items:[],checked_at:'',source_url:'https://github.com/trending',source_scope:'GitHub Trending'};
pages.github=['GitHub 热榜','github'];

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
    '<div class="v10-section-head"><div><p class="eyebrow">GITHUB / DEVELOPER SIGNAL</p><h2>GitHub AI 热仓</h2><p>从 GitHub 官方 Trending 中挑出 AI / Agent 相关项目；这里按“今日新增 Star”排，专门看开发者侧热度。</p></div><a href="#/github">完整 GitHub 热榜 '+icon('arrow')+'</a></div>'+
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
function ghPage(){
  const rows=GH.items||[];
  const max=Math.max(...rows.map(x=>Number(x.stars_today)||0),1);
  return '<section class="gh-hot-page">'+
    '<header class="gh-head"><div><p class="eyebrow"><span class="accent">●</span> GITHUB / TRENDING TODAY</p><h1>GitHub 热榜<span class="accent">.</span></h1><p>用 GitHub 官方 Trending 看开发者侧正在升温什么；Star 热度是采用信号，不是模型能力证据。</p></div>'+
    '<div class="gh-head-meta"><span><i class="state-dot"></i> GitHub 官方页面</span><span>'+esc(ghWhen())+'</span><a href="'+safeLink(GH.source_url)+'" target="_blank" rel="noopener noreferrer">原榜 '+icon('external')+'</a></div></header>'+
    '<div class="gh-method"><b>怎么看</b><span>左侧 # 是 GitHub Trending 官方页面顺序；右侧“今日 Star”是 GitHub 页面显示的当日新增值。AI 相关标签只用于本站识别，不改变 GitHub 官方榜位。</span></div>'+
    '<div class="gh-list">'+rows.map(x=>
      '<a class="gh-row" href="'+safeLink(x.url)+'" target="_blank" rel="noopener noreferrer">'+
        '<div class="gh-rank">#'+String(x.rank).padStart(2,'0')+'</div>'+
        '<div class="gh-main"><div class="gh-repo">'+esc(x.repo)+(x.ai_related?'<em>AI 相关</em>':'')+'</div><p>'+esc(x.description||'')+'</p><div class="gh-sub"><span>'+esc(x.language||'—')+'</span><span>★ '+ghFmt(x.stars)+'</span><span>⑂ '+ghFmt(x.forks)+'</span></div></div>'+
        '<div class="gh-delta"><strong>+'+ghFmt(x.stars_today)+'</strong><span>今日 Star</span><i style="--gh-w:'+ghBarWidth(x.stars_today,max)+'%"></i></div>'+
      '</a>'
    ).join('')+'</div>'+
    '<footer class="gh-note">'+esc(GH.note||'')+'</footer>'+
  '</section>';
}
function renderGithubHot(){
  lastMain='';
  $('#hero').hidden=true;
  $('#stats').hidden=true;
  $('.workspace').hidden=true;
  $('#legacy-saved').innerHTML='';
  const root=$('#vertical-root');
  root.hidden=false;
  root.innerHTML=ghPage();
  document.body.classList.remove('nav-open');
  $('#compare-tray').hidden=true;
}

const ghBaseRenderNav=renderNav;
renderNav=function(){
  ghBaseRenderNav();
  const nav=$('#nav');
  if(!nav)return;
  const hot=nav.querySelector('a[href="#/hot"]');
  if(hot&&!nav.querySelector('a[href="#/github"]')){
    hot.insertAdjacentHTML('afterend','<a href="#/github" class="navitem '+(state.view==='github'?'active':'')+'" '+(state.view==='github'?'aria-current="page"':'')+'>'+icon('github')+'<span>GitHub 热榜</span><small>'+String((GH.items||[]).length).padStart(2,'0')+'</small></a>');
  }
  if(state.view==='github')$('#crumb').textContent='GitHub 热榜';
};

const ghBaseRenderMain=renderMain;
renderMain=function(){
  if(state.view==='github'){renderNav();renderGithubHot();return}
  ghBaseRenderMain();
};

const ghBaseFeedPage=feedPage;
feedPage=function(){
  const html=ghBaseFeedPage();
  const block=ghPreview();
  const marker='<section class="v10-personal';
  const at=html.indexOf(marker);
  return at>=0?html.slice(0,at)+block+html.slice(at):html+block;
};

if(location.hash.replace(/^#\/?/,'').split('?')[0]==='github')parseRoute();
else if(state.view==='feed'){lastMain='';renderMain()}
else renderNav();
})();
