'use strict';
(()=>{
const HF=APP.huggingface_hot||{items:[],checked_at:'',source_url:'https://huggingface.co/models?sort=trending',api_url:'https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=20'};
function hfActive(){
  return state.view==='hot'&&new URLSearchParams(location.hash.split('?')[1]||'').get('tab')==='hf'
}
function hfWhen(value){
  const raw=String(value||'');if(!raw)return '待核验';
  try{return new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(raw)).replaceAll('/','.')+' 北京时间'}
  catch{return raw}
}
function hfAge(raw){
  const t=Date.parse(String(raw||''));
  if(!Number.isFinite(t))return {stale:true,ageHours:null};
  const ageHours=Math.max(0,(Date.now()-t)/36e5);
  return {stale:ageHours>6,ageHours}
}
function hfFreshness(){
  return {
    web:hfAge(HF.web_fetched_at||HF.checked_at),
    api:hfAge(HF.api_fetched_at||HF.checked_at)
  }
}
function hfStaleNotice(){
  const f=hfFreshness();
  if(f.web.stale){
    const age=f.web.ageHours==null?'更新时间不可核验':('已超过 '+Math.floor(f.web.ageHours)+' 小时未核验');
    return '<div class="ranking-stale"><strong>网页榜位已过期，暂不作为当前榜</strong><span>'+esc(age)+' · 下方仅保留 '+esc(hfWhen(HF.web_fetched_at||HF.checked_at))+' 的历史快照，请以 Hugging Face 官方 Trending 为准。</span></div>'
  }
  if(f.api.stale)return '<div class="ranking-stale"><strong>网页榜位已核验；API 指标沿用旧快照</strong><span># 顺序来自 '+esc(hfWhen(HF.web_fetched_at||HF.checked_at))+' 的官方网页；trendingScore、Likes 与 Downloads 来自 '+esc(hfWhen(HF.api_fetched_at||HF.checked_at))+' 的官方 API，不拼成伪精确同步榜。</span></div>';
  return ''
}
function hfFmt(n){
  if(n===null||n===undefined||n==='')return '—';
  const v=Number(n);if(!Number.isFinite(v))return '—';
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
function hfSourceRows(){
  const api=new Map((HF.items||[]).map(x=>[x.id,x]));
  const changes=new Map((HF.web_rank_changes||[]).map(x=>[x.id,x]));
  const ids=Array.isArray(HF.web_order)&&HF.web_order.length?HF.web_order:[...(HF.items||[])].sort((a,b)=>a.rank-b.rank).map(x=>x.id);
  return ids.map((id,index)=>{
    const item=api.get(id),change=changes.get(id)||{};
    if(item)return {...item,...change,rank:index+1,web_rank:index+1,api_rank:item.rank,api_available:true};
    return {id,url:'https://huggingface.co/'+id,...change,rank:index+1,web_rank:index+1,api_rank:null,api_available:false,trending_score:null,likes:null,downloads:null,task:'未标注',library:'未标注',created_at:null,tags:[]}
  })
}
function hfDelta(x){
  if(!Number.isInteger(x.previous_rank))return '<span class="hf-delta is-new" aria-label="较上次官方网页快照新入榜">新上榜</span>';
  const d=Number(x.rank_change)||0;if(!d)return '';
  const up=d>0,label=up?'上升':'下降';
  return '<span class="hf-delta '+(up?'is-up':'is-down')+'" aria-label="较上次官方网页快照'+label+' '+Math.abs(d)+' 位">'+(up?'↑':'↓')+Math.abs(d)+'</span>'
}
function hfChangeSummary(){
  const changes=HF.web_rank_changes||[],previous=changes.find(x=>x&&x.previous_fetched_at)?.previous_fetched_at;
  if(!previous)return '';
  const entrants=changes.filter(x=>!Number.isInteger(x.previous_rank));
  const moved=changes.filter(x=>Number.isInteger(x.previous_rank)&&Number(x.rank_change)!==0);
  const outgoing=Array.isArray(HF.web_outgoing)?HF.web_outgoing:[];
  if(!entrants.length&&!moved.length&&!outgoing.length)return '<p class="hf-change-summary is-steady">与上次官方网页快照一致</p>';
  return '<div class="hf-change-summary" aria-label="Hugging Face 官方网页榜位变化摘要">'+
    '<span><b>'+entrants.length+'</b> 新上榜</span><span><b>'+moved.length+'</b> 位次变化</span>'+
    (outgoing.length?'<details><summary><b>'+outgoing.length+'</b> 离榜</summary><div>'+outgoing.map(x=>'<a href="'+safeLink('https://huggingface.co/'+x.id)+'" target="_blank" rel="noopener noreferrer">#'+esc(x.previous_rank)+' '+esc(x.id)+'</a>').join('')+'</div></details>':'<span><b>0</b> 离榜</span>')+
  '</div>'
}
function hfRows(){
  const q=hfQuery().toLowerCase(),type=hfType();
  return hfSourceRows().filter(x=>(type==='all'||hfGroup(x)===type)&&(!q||[x.id,x.task,x.library,...(x.tags||[])].join(' ').toLowerCase().includes(q))).sort((a,b)=>a.web_rank-b.web_rank)
}
function hfTabs(){
  const active=hfType(),items=hfSourceRows();
  return '<nav class="hf-types" aria-label="Hugging Face 模型类型">'+HF_GROUPS.map(([id,title])=>{
    const count=id==='all'?items.length:items.filter(x=>hfGroup(x)===id).length;
    if(id!=='all'&&!count)return '';
    return '<a class="hf-type-chip '+(active===id?'active':'')+'" href="'+hfHref(id)+'" '+(active===id?'aria-current="page"':'')+'><span>'+esc(title)+'</span><small>'+count+'</small></a>'
  }).join('')+'</nav>'
}
function hfInline(){
  const rows=hfRows(),all=hfSourceRows(),fresh=hfFreshness(),max=Math.max(...rows.map(x=>Number(x.trending_score)||0),1);
  const previous=(HF.web_rank_changes||[]).find(x=>x&&x.previous_fetched_at)?.previous_fetched_at;
  return '<section class="hf-inline">'+
    hOpenTabs('hf')+
    '<div class="hf-inline-head"><div><strong>'+(fresh.web.stale?'Hugging Face · 历史快照':'Hugging Face Models · Trending')+'</strong><span>'+(fresh.web.stale?'该网页榜位快照已过期，不代表当前官方榜位。':'网页榜位与 API 指标分别保留来源时间；热度不等于模型能力。')+'</span></div><div><span>网页榜位 '+esc(hfWhen(HF.web_fetched_at||HF.checked_at))+'</span><span>API 指标 '+esc(hfWhen(HF.api_fetched_at||HF.checked_at))+'</span><a href="'+safeLink(HF.source_url)+'" target="_blank" rel="noopener noreferrer">打开 Hugging Face 原榜 '+icon('external')+'</a></div></div>'+
    hfStaleNotice()+
    '<div class="hf-method"><b>怎么看</b><span>左侧 # 严格保留官方 Models Trending 网页顺序；升降箭头只比较'+(previous?' '+esc(hfWhen(previous))+' ':'本站上一次成功保存的')+'官方网页快照。右侧 API Trending 是官方 API 的 trendingScore；不同来源时间单独标注，不拼成伪精确榜。这些只是平台关注/使用信号，不是 Benchmark 或本站实测。</span></div>'+
    hfTabs()+
    hfChangeSummary()+
    '<p class="hf-resultline" role="status" aria-live="polite">显示 '+rows.length+' / '+all.length+' 个模型 · 保留官方网页名次</p>'+
    (rows.length?'<div class="hf-list">'+rows.map(x=>
      '<a class="hf-row" href="'+safeLink(x.url)+'" target="_blank" rel="noopener noreferrer">'+
        '<div class="hf-rank"><span>#'+String(x.rank).padStart(2,'0')+'</span>'+hfDelta(x)+'</div>'+
        '<div class="hf-main"><div class="hf-model">'+esc(x.id)+'<em>'+esc(x.task||'其他')+'</em></div><div class="hf-sub"><span>'+esc(x.library||'—')+'</span><span>赞 '+hfFmt(x.likes)+'</span><span>下载 '+hfFmt(x.downloads)+'</span><span>创建 '+esc(x.created_at?String(x.created_at).slice(0,10):'未标注')+'</span></div><div class="hf-tags">'+(x.tags||[]).map(t=>'<span>'+esc(t)+'</span>').join('')+'</div></div>'+
        '<div class="hf-score"><strong>'+hfFmt(x.trending_score)+'</strong><span>'+(x.api_available?('API Trending'+(fresh.api.stale?'（旧）':'')):'API 未收录')+'</span><i style="--hf-w:'+(x.api_available?Math.max(4,Math.round((Number(x.trending_score)||0)/max*100)):0)+'%"></i></div>'+
      '</a>'
    ).join('')+'</div>':'<div class="h-empty"><h3>没有匹配模型</h3><p>换个关键词或类型继续看。</p><button class="button" data-hf-clear>清除搜索与筛选</button></div>')+
    '<footer class="hf-note">'+esc(HF.note||'')+'</footer>'+
  '</section>'
}

const hfBaseHotPage=hotPage;
hotPage=function(){
  if(!hfActive())return hfBaseHotPage();
  const s=hState(),q=hfQuery(),fresh=hfFreshness(),stale=fresh.web.stale;
  return '<section class="h-wrap v10-hot hf-embedded">'+
    '<header class="h-head"><div><p class="eyebrow"><span class="accent">●</span> '+(stale?'HISTORICAL SNAPSHOT / STALE':'MODEL ECOSYSTEM / TRENDING')+'</p><h1>'+(stale?'Hugging Face 历史快照':'Hugging Face 热榜')+'<span class="accent">.</span></h1><p>'+(stale?'旧数据不再冒充当前 Trending；保留历史快照供追溯，并直接回到官方原榜。':'看模型社区正在关注什么；平台热度与模型能力严格分开。')+'</p></div><div class="h-meta"><span><i class="state-dot"></i> '+(stale?'非当前榜':'Hugging Face 官方 Trending')+'</span><span>'+esc(hfWhen(HF.web_fetched_at||HF.checked_at))+'</span></div></header>'+
    '<div class="h-filterbar">'+hTabs(s)+'<label class="h-search">'+icon('search')+'<input id="hf-search" type="search" value="'+esc(q)+'" placeholder="搜索模型、任务、标签…" aria-label="搜索 Hugging Face 热榜"><kbd>/</kbd></label></div>'+
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
document.addEventListener('click',e=>{if(!e.target.closest('[data-hf-clear]'))return;e.preventDefault();history.replaceState(null,'','#/hot?tab=hf');parseRoute()});

if(state.view==='feed'){lastMain='';renderMain()}
})();
