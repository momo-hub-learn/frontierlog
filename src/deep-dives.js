'use strict';
(()=>{
const DEEP=APP.deep_dives||{articles:[],checked:''};
const DEEP_MAP=new Map((DEEP.articles||[]).map(x=>[x.id,x]));
pages.deep=['拆一下','layers'];

function dParams(){return new URLSearchParams(location.hash.split('?')[1]||'')}
function dCurrent(){return DEEP_MAP.get(dParams().get('id'))||DEEP.articles?.[0]||null}
function dSourceMap(a){return new Map((a.sources||[]).map((s,i)=>[s.id,{...s,index:i+1}]))}
function dRefLinks(a,ids=[]){
 const m=dSourceMap(a),rows=ids.map(id=>m.get(id)).filter(Boolean);
 if(!rows.length)return '';
 return '<div class="d-section-refs"><span>参考</span>'+rows.map(s=>'<a class="d-ref" href="'+safeLink(s.url)+'" target="_blank" rel="noopener noreferrer" title="'+esc(s.title)+'">['+s.index+'] '+esc(s.publisher)+'</a>').join('')+'</div>'
}
function dFeedCard(){
 const a=DEEP.articles?.[0];if(!a)return '';
 return '<section class="d-feed">'+
  '<div class="d-feed-head"><div><p class="eyebrow">本周深读 / 拆一下</p><h2>把热点拆成架构。</h2><p>不复述新闻，追问它改变了什么系统边界。</p></div><span>'+esc(String(a.read_minutes))+' MIN READ</span></div>'+
  '<a class="d-feed-card" href="#/deep?id='+encodeURIComponent(a.id)+'">'+
   '<div class="d-feed-no">01</div>'+
   '<div class="d-feed-copy"><div class="d-feed-tags">'+a.tags.slice(0,3).map(t=>'<span>'+esc(t)+'</span>').join('')+'</div><h3>'+esc(a.title)+'</h3><p>'+esc(a.subtitle)+'</p><div class="d-feed-thesis">'+esc(a.thesis)+'</div></div>'+
   '<div class="d-mini-arch" aria-label="架构摘要"><span><b>Code</b><small>确定规则</small></span><i>+</i><span class="jev"><b>Jev</b><small>结构判断</small></span><i>+</i><span><b>LLM</b><small>开放推理</small></span></div>'+
   '<div class="d-feed-open"><span>读完整解析</span>'+icon('arrow')+'</div>'+
  '</a>'+
 '</section>'
}

const dBaseFeedPage=feedPage;
feedPage=function(){
 const html=dBaseFeedPage(),block=dFeedCard();
 if(!block)return html;
 const gh='<section class="gh-preview', personal='<section class="v10-personal';
 let at=html.indexOf(gh);
 if(at<0)at=html.indexOf(personal);
 return at>=0?html.slice(0,at)+block+html.slice(at):html+block
};

function dArchitecture(a){
 const x=a.architecture;if(!x)return '';
 const lane=(title,rows,cls)=>'<div class="d-arch-lane '+cls+'"><div class="d-arch-title">'+title+'</div><div class="d-arch-flow">'+rows.map((n,i)=>'<div class="d-arch-node '+esc(n.kind||'')+'"><strong>'+esc(n.label)+'</strong>'+(n.detail?'<small>'+esc(n.detail)+'</small>':'')+'</div>'+(i<rows.length-1?'<span class="d-arch-arrow">'+icon('arrow')+'</span>':'')).join('')+'</div></div>';
 return '<figure class="d-architecture d-breakout"><figcaption><span>把 Agent 的智能重新分层</span><p>'+esc(x.note)+'</p></figcaption>'+lane('常见做法：大部分“智能”都回到 LLM',x.before,'before')+lane('一种更可控的分层方式',x.after,'after')+'</figure>'
}
function dPrimitives(rows=[]){
 if(!rows.length)return '';
 return '<div class="d-primitives d-breakout">'+rows.map((r,i)=>'<article><span>0'+(i+1)+'</span><div><strong>'+esc(r.name)+'</strong><em>'+esc(r.label)+'</em><p>'+esc(r.detail)+'</p></div></article>').join('')+'</div>'
}
function dCaseStudy(x){
 if(!x)return '';
 return '<figure class="d-case d-breakout"><figcaption><span>具体一点</span><strong>'+esc(x.title)+'</strong><small>'+esc(x.label||'')+'</small></figcaption><div class="d-case-flow">'+
  x.steps.map((s,i)=>'<div class="d-case-step"><b>'+esc(s.who)+'</b><p>'+esc(s.text)+'</p>'+(i<x.steps.length-1?'<span>'+icon('arrow')+'</span>':'')+'</div>').join('')+
  '</div>'+(x.note?'<p class="d-case-note">'+esc(x.note)+'</p>':'')+'</figure>'
}
function dEquation(x){
 if(!x)return '';
 return '<div class="d-equation"><code>'+esc(x.left)+'</code><strong>'+esc(x.center)+'</strong><span>'+esc(x.right)+'</span></div>'
}
function dComparison(rows=[]){
 if(!rows.length)return '';
 return '<div class="d-comparison d-breakout"><div class="d-comparison-head"><span>把哪种计算放在哪一层？</span><small>AI坐标架构框架</small></div><div class="d-comparison-grid">'+rows.map(r=>'<article><h4>'+esc(r.layer)+'</h4><dl><dt>最适合</dt><dd>'+esc(r.best)+'</dd><dt>优势</dt><dd>'+esc(r.strength)+'</dd><dt>主要风险</dt><dd>'+esc(r.risk)+'</dd></dl></article>').join('')+'</div></div>'
}
function dPoints(rows=[]){
 if(!rows.length)return '';
 return '<div class="d-points">'+rows.map((b,i)=>'<div class="d-point"><span>'+String(i+1).padStart(2,'0')+'</span><div><h4>'+esc(b.title)+'</h4><p>'+esc(b.detail)+'</p></div></div>').join('')+'</div>'
}
function dSection(a,s){
 const evidence=s.analysis?'<span class="d-analysis">含 AI坐标分析</span>':'';
 const paragraphs=(s.paragraphs||[]).map((p,i)=>'<p'+(i===0?' class="d-section-lead"':'')+'>'+esc(p)+'</p>').join('');
 return '<section class="d-section '+(s.key==='boundary'?'is-ending':'')+'" id="deep-'+esc(s.key)+'">'+
  '<header class="d-section-head"><div><span class="d-section-no">'+esc(s.eyebrow)+'</span>'+(s.kicker?'<span class="d-section-kicker">'+esc(s.kicker)+'</span>':'')+'</div>'+evidence+'</header>'+
  '<h2>'+esc(s.title)+'</h2>'+
  paragraphs+
  dPrimitives(s.primitives||[])+
  dCaseStudy(s.case_study)+
  dEquation(s.equation)+
  (s.show_architecture?dArchitecture(a):'')+
  dComparison(s.comparison||[])+
  dPoints(s.bullets||[])+
  (s.pullquote?'<blockquote class="d-pullquote">'+esc(s.pullquote)+'</blockquote>':'')+
  dRefLinks(a,s.source_refs)+
 '</section>'
}
function dOpening(a){
 const rows=a.opening||[];if(!rows.length)return '';
 return '<section class="d-opening">'+rows.map((p,i)=>'<p'+(i===0?' class="d-opening-lead"':'')+'>'+esc(p)+'</p>').join('')+'</section>'
}
function dToc(a){
 return '<aside class="d-toc"><div class="d-toc-inner"><span>阅读地图</span>'+a.sections.map(s=>'<button data-d-jump="'+esc(s.key)+'"><b>'+esc(s.eyebrow)+'</b><small>'+esc(s.kicker||s.title)+'</small></button>').join('')+'<div class="d-toc-time">'+esc(String(a.read_minutes))+' MIN READ</div></div></aside>'
}
function dSources(a){
 return '<section class="d-sources" id="deep-sources"><div class="d-sources-head"><div><p class="eyebrow">SOURCES / EVIDENCE</p><h2>原始资料与独立报道</h2></div><span>核对 '+esc(DEEP.checked||a.published)+'</span></div><div class="d-source-grid">'+
 (a.sources||[]).map((s,i)=>'<a href="'+safeLink(s.url)+'" target="_blank" rel="noopener noreferrer"><b>['+(i+1)+']</b><span><strong>'+esc(s.publisher)+'</strong><em>'+esc(s.kind)+' · '+esc(s.date||'持续更新')+'</em><small>'+esc(s.title)+'</small></span>'+icon('external')+'</a>').join('')+
 '</div></section>'
}
function dPage(a){
 if(!a)return '<div class="d-empty">暂无深度解析。</div>';
 return '<article class="d-page">'+
  '<header class="d-hero">'+
   '<div class="d-hero-top"><span class="d-series">拆一下</span><span>'+esc(a.published.replaceAll('-','.'))+'</span><span>'+esc(String(a.read_minutes))+' min read</span></div>'+
   '<h1>'+esc(a.title)+'</h1><p class="d-dek">'+esc(a.dek)+'</p>'+
   '<div class="d-tagline">'+a.tags.map(t=>'<span>'+esc(t)+'</span>').join('')+'</div>'+
   '<blockquote class="d-thesis"><span>核心判断</span><strong>'+esc(a.thesis)+'</strong></blockquote>'+
  '</header>'+
  '<div class="d-reading-shell">'+dToc(a)+'<main class="d-article">'+dOpening(a)+a.sections.map(s=>dSection(a,s)).join('')+dSources(a)+'</main></div>'+
 '</article>'
}
function renderDeep(){
 lastMain='';
 $('#hero').hidden=true;$('#stats').hidden=true;$('.workspace').hidden=true;$('#legacy-saved').innerHTML='';
 const root=$('#vertical-root');root.hidden=false;root.innerHTML=dPage(dCurrent());
 document.body.classList.remove('nav-open');$('#compare-tray').hidden=true;
 const feedNav=document.querySelector('.navitem[href="#/feed"]');
 if(feedNav){feedNav.classList.add('active');feedNav.setAttribute('aria-current','page')}
}
const dBaseRenderMain=renderMain;
renderMain=function(){
 if(state.view==='deep'){renderNav();renderDeep();return}
 dBaseRenderMain()
};

document.addEventListener('click',e=>{
 const b=e.target.closest('[data-d-jump]');if(!b)return;
 const target=document.getElementById('deep-'+b.dataset.dJump);if(!target)return;
 e.preventDefault();target.scrollIntoView({behavior:'smooth',block:'start'})
});

const dBaseRelatedCards=hRelatedCards;
hRelatedCards=function(x){
 const base=dBaseRelatedCards(x);
 const a=(DEEP.articles||[]).find(a=>(a.hot_ids||[]).includes(x.id));
 if(!a)return base;
 return base+'<section class="h-detail-panel d-hot-deep"><div class="h-detail-panel-head"><span>进一步理解</span><small>拆一下</small></div><a href="#/deep?id='+encodeURIComponent(a.id)+'" onclick="document.getElementById(\'modal\').close();document.body.style.overflow=\'\'"><span class="d-hot-deep-mark">'+icon('layers')+'</span><span><strong>'+esc(a.short_title||a.title)+'</strong><small>'+esc(String(a.read_minutes))+' min · 架构解析</small></span>'+icon('arrow')+'</a></section>'
};

if(location.hash.startsWith('#/deep'))parseRoute();
else if(state.view==='feed'){lastMain='';renderMain()}
})();