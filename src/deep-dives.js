'use strict';
(()=>{
const DEEP=APP.deep_dives||{articles:[],checked:''};
const DEEP_MAP=new Map((DEEP.articles||[]).map(x=>[x.id,x]));
pages.deep=['拆一下','layers'];

function dParams(){return new URLSearchParams(location.hash.split('?')[1]||'')}
function dCurrent(){return DEEP_MAP.get(dParams().get('id'))||DEEP.articles?.[0]||null}
function dSourceMap(a){return new Map((a.sources||[]).map(s=>[s.id,s]))}
function dRefChips(a,ids=[]){
 const m=dSourceMap(a);
 return ids.map(id=>m.get(id)).filter(Boolean).map(s=>'<a class="d-ref" href="'+safeLink(s.url)+'" target="_blank" rel="noopener noreferrer">'+esc(s.publisher)+' · '+esc(s.kind)+' '+icon('external')+'</a>').join('')
}
function dFeedCard(){
 const a=DEEP.articles?.[0];if(!a)return '';
 return '<section class="d-feed">'+
  '<div class="d-feed-head"><div><p class="eyebrow">本周深读 / 拆一下</p><h2>把热点拆成架构。</h2><p>不是再讲一遍新闻，而是回答：它为什么重要、应该放在系统哪一层、什么还没被证明。</p></div><span>'+esc(String(a.read_minutes))+' MIN READ</span></div>'+
  '<a class="d-feed-card" href="#/deep?id='+encodeURIComponent(a.id)+'">'+
   '<div class="d-feed-no">01</div>'+
   '<div class="d-feed-copy"><div class="d-feed-tags">'+a.tags.slice(0,3).map(t=>'<span>'+esc(t)+'</span>').join('')+'</div><h3>'+esc(a.title)+'</h3><p>'+esc(a.subtitle)+'</p><div class="d-feed-thesis">'+esc(a.thesis)+'</div></div>'+
   '<div class="d-mini-arch" aria-label="架构摘要"><span><b>LLM</b><small>生成 / 推理</small></span><i>+</i><span class="jev"><b>Jev</b><small>路由 / 评分</small></span><i>→</i><span><b>Code</b><small>阈值 / 分支</small></span></div>'+
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
 return '<figure class="d-architecture"><figcaption><span>架构对比</span><p>'+esc(x.note)+'</p></figcaption>'+lane('常见 Agent：一个生成式模型承担多数判断',x.before,'before')+lane('建议分层：生成与决策拆开',x.after,'after')+'</figure>'
}
function dSection(a,s){
 const analysis=s.analysis?'<span class="d-analysis">AI坐标推断</span>':'<span class="d-evidence">公开资料</span>';
 const paragraphs=(s.paragraphs||[]).map(p=>'<p>'+esc(p)+'</p>').join('');
 const bullets=(s.bullets||[]).length?'<div class="d-bullets">'+s.bullets.map(b=>'<article><h4>'+esc(b.title)+'</h4><p>'+esc(b.detail)+'</p></article>').join('')+'</div>':'';
 return '<section class="d-section '+(s.key==='boundary'?'boundary':'')+'">'+
  '<div class="d-section-label"><span>'+esc(s.eyebrow)+'</span>'+analysis+'</div>'+
  '<h2>'+esc(s.title)+'</h2>'+paragraphs+bullets+
  (s.show_architecture?dArchitecture(a):'')+
  '<div class="d-section-refs">'+dRefChips(a,s.source_refs)+'</div>'+
 '</section>'
}
function dSources(a){
 return '<section class="d-sources"><div class="d-sources-head"><div><p class="eyebrow">SOURCES / EVIDENCE</p><h2>这篇文章基于什么</h2></div><span>核对 '+esc(DEEP.checked||a.published)+'</span></div><div class="d-source-grid">'+
 (a.sources||[]).map((s,i)=>'<a href="'+safeLink(s.url)+'" target="_blank" rel="noopener noreferrer"><b>'+String(i+1).padStart(2,'0')+'</b><span><strong>'+esc(s.publisher)+'</strong><em>'+esc(s.kind)+' · '+esc(s.date||'持续更新')+'</em><small>'+esc(s.title)+'</small></span>'+icon('external')+'</a>').join('')+
 '</div></section>'
}
function dPage(a){
 if(!a)return '<div class="d-empty">暂无深度解析。</div>';
 return '<article class="d-page">'+
  '<header class="d-hero">'+
   '<div class="d-hero-top"><span class="d-series">拆一下</span><span>'+esc(a.published.replaceAll('-','.'))+'</span><span>'+esc(String(a.read_minutes))+' min read</span></div>'+
   '<h1>'+esc(a.title)+'</h1><p class="d-dek">'+esc(a.dek)+'</p>'+
   '<div class="d-tagline">'+a.tags.map(t=>'<span>'+esc(t)+'</span>').join('')+'</div>'+
   '<div class="d-thesis"><span>核心判断</span><strong>'+esc(a.thesis)+'</strong></div>'+
  '</header>'+
  '<div class="d-body">'+a.sections.map(s=>dSection(a,s)).join('')+dSources(a)+'</div>'+
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
