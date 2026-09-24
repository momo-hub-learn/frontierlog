'use strict';
(()=>{
const HF=APP.huggingface_hot||{items:[],checked_at:'',source_url:'https://huggingface.co/models?sort=trending',api_url:'https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=20'};
function hfActive(){
  return state.view==='hot'&&new URLSearchParams(location.hash.split('?')[1]||'').get('tab')==='hf'
}
function hfWhen(){
  const raw=String(HF.checked_at||'');if(!raw)return '待核验';
  try{return new Intl.DateTimeFormat('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(raw))}
  catch{return raw}
}
function hfFmt(n){
  const v=Number(n)||0;
  if(v>=1000000)return (v/1000000).toFixed(v>=10000000?1:2)+'M';
  if(v>=1000)return (v/1000).toFixed(v>=100000?0:1)+'k';
  return v.toLocaleString('en-US')
}
function hfGroup(x){
  const t=String(x.task||'').toLowerCase();
  if(t.includes('speech')||t.includes('audio'))return 'audio';
  if(t.includes('image-to-video')||t.includes('text-to-video')||t.includes('text-to-image')||t.includes('image-to-image'))return 'media';
  if(t.includes('image-text')||t.includes('visual')||t.includes('multimodal'))return 'multimodal';
  if(t.includes('text'))return 'text';
  return 'other'
}
const HF_GROUPS=[['all','全部'],['text','文本'],['multimodal','多模态'],['media','图像 / 视频'],['audio','语音'],['other','其他']];
function hfParams(){return new URLSearchParams(location.hash.split('?')[1]||'')}
function hfQuery(){return (hfParams().get('hfq')||'').slice(0,300).trim()}
function hfType(){const v=hfParams().get('hftype')||'all';return HF_GROUPS.some(x=>x[0]===v)?v:'all'}
function hfHref(type){
  const p=hfParams();p.set('tab','hf');p.delete('cat');p.delete('q');
  if(type==='all')p.delete('hftype');else p.set('hftype',type);
  return '#/hot?'+p.toString()
}
function hfRows(){
  const q=hfQuery().toLowerCase(),type=hfType();
  return (HF.items||[]).filter(x=>(type==='all'||hfGroup(x)===type)&&(!q||[x.id,x.task,x.library,...(x.tags||[])].join(' ').toLowerCase().includes(q))).sort((a,b)=>a.rank-b.rank)
}
function hfTabs(){
  const active=hfType(),items=HF.items||[];
  return '<nav class="hf-types" aria-label="Hugging Face 模型类型">'+HF_GROUPS.map(([id,title])=>{
    const count=id==='all'?items.length:items.filter(x=>hfGroup(x)===id).length;
    if(id!=='all'&&!count)return '';
    return '<a class="hf-type-chip '+(active===id?'active':'')+'" href="'+hfHref(id)+'" '+(active===id?'aria-current="page"':'')+'><span>'+esc(title)+'</span><small>'+count+'</small></a>'
  }).join('')+'</nav>'
}
function hfPreview(){
  const rows=(HF.items||[]).slice(0,5);if(!rows.length)return '';
  const max=Math.max(...rows.map(x=>Number(x.trending_score)||0),1);
  return '<section class="hf-preview">'+
    '<div class="v10-section-head"><div><p class="eyebrow">HUGGING FACE / MODEL SIGNAL</p><h2>HuggingFace 模型热榜</h2><p>直接看 Hugging Face 官方 Models Trending；趋势分是平台热度信号，不是模型能力分。</p></div><a href="#/hot?tab=hf">完整 HuggingFace 热榜 '+icon('arrow')+'</a></div>'+
    '<div class="hf-preview-list">'+rows.map(x=>
      '<a class="hf-preview-row" href="'+safeLink(x.url)+'" target="_blank" rel="noopener noreferrer">'+
        '<span class="hf-preview-rank">HF #'+String(x.rank).padStart(2,'0')+'</span>'+
        '<span class="hf-preview-main"><strong>'+esc(x.id)+'</strong><small>'+esc(x.task||'—')+' · '+esc(x.library||'—')+'</small></span>'+
        '<span class="hf-preview-score"><b>'+hfFmt(x.trending_score)+'</b><small>Trending</small><i style="--hf-w:'+Math.max(4,Math.round((Number(x.trending_score)||0)/max*100))+'%"></i></span>'+
      '</a>'
    ).join('')+'</div>'+
    '<div class="hf-preview-foot"><span>官方 Trending 顺序 · 不等于模型能力榜</span><span>核验 '+esc(hfWhen())+'</span></div>'+
  '</section>'
}
function hfInline(){
  const rows=hfRows(),max=Math.max(...rows.map(x=>Number(x.trending_score)||0),1);
  return '<section class="hf-inline">'+
    '<div class="hf-inline-head"><div><strong>Hugging Face Models · Trending</strong><span>官方 trendingScore + Likes + Downloads，观察模型生态热度。</span></div><div><span>核验 '+esc(hfWhen())+'</span><a href="'+safeLink(HF.source_url)+'" target="_blank" rel="noopener noreferrer">打开 Hugging Face 原榜 '+icon('external')+'</a></div></div>'+
    '<div class="hf-method"><b>怎么看</b><span>左侧 # 保留 Hugging Face 官方 Trending 顺序；右侧 Trending 是官方 API 的 trendingScore。它只反映平台趋势信号，不代表模型质量、Benchmark 成绩或本站实测。Likes / Downloads 也只按 Hugging Face 官方字段展示。</span></div>'+
    hfTabs()+
    (rows.length?'<div class="hf-list">'+rows.map(x=>
      '<a class="hf-row" href="'+safeLink(x.url)+'" target="_blank" rel="noopener noreferrer">'+
        '<div class="hf-rank">#'+String(x.rank).padStart(2,'0')+'</div>'+
        '<div class="hf-main"><div class="hf-model">'+esc(x.id)+'<em>'+esc(x.task||'其他')+'</em></div><div class="hf-sub"><span>'+esc(x.library||'—')+'</span><span>♥ '+hfFmt(x.likes)+'</span><span>↓ '+hfFmt(x.downloads)+'</span><span>创建 '+esc(String(x.created_at||'').slice(0,10))+'</span></div><div class="hf-tags">'+(x.tags||[]).map(t=>'<span>'+esc(t)+'</span>').join('')+'</div></div>'+
        '<div class="hf-score"><strong>'+hfFmt(x.trending_score)+'</strong><span>Trending</span><i style="--hf-w:'+Math.max(4,Math.round((Number(x.trending_score)||0)/max*100))+'%"></i></div>'+
      '</a>'
    ).join('')+'</div>':'<div class="h-empty"><h3>没有匹配模型</h3><p>换个关键词或类型继续看。</p></div>')+
    '<footer class="hf-note">'+esc(HF.note||'')+'</footer>'+
  '</section>'
}

const hfBaseTabs=hTabs;
hTabs=function(s){
  let html=hfBaseTabs(s),active=hfActive();
  if(active)html=html.replace(/class="h-tab active"/g,'class="h-tab"').replace(/ aria-current="page"/g,'');
  const tab='<a class="h-tab hf-hot-tab '+(active?'active':'')+'" href="#/hot?tab=hf" '+(active?'aria-current="page"':'')+'>'+icon('layers')+'HuggingFace 热榜<small>'+String((HF.items||[]).length)+'</small></a>';
  return html.replace('</nav>',tab+'</nav>')
};

const hfBaseHotPage=hotPage;
hotPage=function(){
  if(!hfActive())return hfBaseHotPage();
  const s=hState(),q=hfQuery();
  return '<section class="h-wrap v10-hot hf-embedded">'+
    '<header class="h-head"><div><p class="eyebrow"><span class="accent">●</span> MODEL ECOSYSTEM / TRENDING</p><h1>HuggingFace 热榜<span class="accent">.</span></h1><p>看开源模型生态正在关注什么；平台热度与模型能力严格分开。</p></div><div class="h-meta"><span><i class="state-dot"></i> Hugging Face 官方 Trending</span><span>'+esc(hfWhen())+'</span></div></header>'+
    '<div class="h-filterbar">'+hTabs(s)+'<label class="h-search">'+icon('search')+'<input id="hf-search" type="search" value="'+esc(q)+'" placeholder="搜索模型、任务、标签…" aria-label="搜索 HuggingFace 热榜"><kbd>/</kbd></label></div>'+
    hfInline()+
  '</section>'
};

document.addEventListener('input',e=>{
  if(e.target.id!=='hf-search')return;
  const value=e.target.value,pos=e.target.selectionStart,p=hfParams();
  p.set('tab','hf');if(value)p.set('hfq',value);else p.delete('hfq');
  history.replaceState(null,'','#/hot?'+p.toString());parseRoute();
  const n=document.getElementById('hf-search');if(n){n.focus({preventScroll:true});try{n.setSelectionRange(pos,pos)}catch{}}
});

const hfBaseFeedPage=feedPage;
feedPage=function(){
  const html=hfBaseFeedPage(),block=hfPreview(),marker='<section class="v10-personal',at=html.indexOf(marker);
  return at>=0?html.slice(0,at)+block+html.slice(at):html+block
};

if(state.view==='feed'){lastMain='';renderMain()}
})();
