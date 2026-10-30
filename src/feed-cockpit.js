'use strict';
(()=>{
/* 精选头部：全宽热点 + 三张工具卡；关注卡固定在左侧并自适应为方块。 */
function fcHotPanel(){
 const rows=v10Top5Rows();
 return '<section class="fc-panel fc-hot-panel">'+
  '<div class="fc-panel-head"><div class="fc-panel-titleline"><h2>热点</h2><span class="eyebrow">HOT / RECENT</span><span class="fc-hot-sync">'+esc(v10HotStatusShort())+'</span><span class="fc-hot-order" title="排序分 = 编辑热度 − 2 × 距今天数">新鲜度加权：旧 1 日 −2</span></div><a href="#/hot">全部热点 '+icon('arrow')+'</a></div>'+
  '<div class="fc-hot-list">'+rows.map((x,i)=>
   '<a class="fc-hot-row" href="#/hot?item='+encodeURIComponent(x.id)+'">'+
    '<span class="fc-hot-rank">'+String(i+1).padStart(2,'0')+'</span>'+
    '<span class="fc-hot-main"><span class="fc-hot-meta"><em>'+esc(HOT_CATS.get(x.category)?.title||x.category)+'</em><time>'+esc(x.published.slice(5).replace('-','.'))+'</time><small>'+esc(x.source)+'</small></span><strong>'+esc(x.title)+'</strong></span>'+
    '<span class="fc-hot-score fc-heat-'+hHeatBand(x.heat).key+'" aria-label="编辑热度 '+esc(String(x.heat))+'，'+hHeatBand(x.heat).label+'；新鲜度排序分 '+esc(String(v10Top5Score(x)))+'"><b>'+esc(String(x.heat))+'</b><small>'+hHeatBand(x.heat).label+' · 排序 '+esc(String(v10Top5Score(x)))+'</small>'+hTrend(x)+'</span>'+
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
 const a=[...(APP.deep_dives?.articles||[])].sort((x,y)=>String(y.updated||y.published||'').localeCompare(String(x.updated||x.published||''))||String(y.published||'').localeCompare(String(x.published||'')))[0];
 if(!a)return '';
 const flow=(a.mini_flow||[]).slice(0,3);
 const diagram=flow.length===3?'<div class="fc-mini-arch" aria-label="技术链路摘要">'+flow.map((x,i)=>(i?'<i aria-hidden="true">→</i>':'')+'<span class="'+(i===1?'is-accent':'')+'"><b>'+esc(x.label)+'</b><small>'+esc(x.detail)+'</small></span>').join('')+'</div>':'';
 return '<a class="fc-panel fc-deep-panel" href="#/deep?id='+encodeURIComponent(a.id)+'">'+
  '<div class="fc-side-head"><span class="fc-kicker">拆一下</span><small>'+esc((a.updated||a.published).slice(5).replace('-','.'))+' 更新 · '+esc(String(a.read_minutes))+' MIN</small></div>'+
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
 const metadataFailures=Number(gh.sync?.metadata_failed_count)||0,watchFailures=Number(gh.sync?.watchlist_failed_count)||0;
 const partial=gh.sync?.metadata_status==='partial'||metadataFailures>0||watchFailures>0;
 const trendingPartial=gh.sync?.metadata_status==='partial'||metadataFailures>0;
 const allTrendingMetadataFailed=(gh.items||[]).length>0&&metadataFailures>=(gh.items||[]).length;
 const allRepositoryMetadataFailed=allTrendingMetadataFailed&&(!(gh.watchlist||[]).length||watchFailures>=(gh.watchlist||[]).length);
 const fmt=n=>{const v=Number(n)||0;return v>=1000?(v/1000).toFixed(v>=10000?0:1)+'k':String(v)};
 const followed=(gh.watchlist||[]).filter(x=>x.ai_related).filter(x=>!rows.some(r=>r.repo.toLowerCase()===x.repo.toLowerCase())).slice(0,1);
 return '<section class="fc-panel fc-gh-panel">'+
  '<div class="fc-panel-head compact"><div><p class="eyebrow">GITHUB / VERIFIED</p><h2>GitHub AI 热仓</h2></div><a href="#/hot?tab=github">完整榜 '+icon('arrow')+'</a></div>'+
  (partial?'<div class="fc-gh-data-state" role="status">'+(allRepositoryMetadataFailed?'仓库资料全部沿用旧快照':trendingPartial?('上榜仓库资料'+(allTrendingMetadataFailed?'全部':'部分')+'沿用旧快照'):'长期关注仓库资料沿用旧快照')+(metadataFailures?' · '+metadataFailures+' 个上榜项':'')+(watchFailures?' · '+watchFailures+' 个长期关注项':(gh.watchlist||[]).length?' · 长期关注项已核验':'')+'</div>':'')+
  (fresh?'<div class="fc-gh-list">'+rows.map(x=>
   '<a class="fc-gh-row" href="'+safeLink(x.url)+'" target="_blank" rel="noopener noreferrer">'+
    '<span class="fc-gh-rank">#'+String(x.rank).padStart(2,'0')+'</span>'+
    '<span class="fc-gh-main"><strong>'+esc(x.repo)+'</strong><small>'+esc(x.description||x.language||'')+'</small>'+(x.metadata_status==='stale'?'<em class="fc-gh-data-state">仓库资料旧快照</em>':x.metadata_status==='unavailable'?'<em class="fc-gh-data-state">仓库资料待首次核验</em>':'')+'</span>'+
    '<span class="fc-gh-star"><b>+'+fmt(x.stars_today)+'</b><small>Today</small></span></a>'
  ).join('')+'</div>':
  '<div class="fc-gh-old"><strong>当前 Trending 未完成核验</strong><p>旧榜单已停止作为今日热门展示。可查看独立关注仓库或历史快照。</p></div>')+
  (followed.length?'<div class="fc-gh-watch">'+followed.map(x=>
   '<a class="fc-gh-row" href="'+safeLink(x.url)+'" target="_blank" rel="noopener noreferrer">'+
    '<span class="fc-gh-rank">追踪</span><span class="fc-gh-main"><strong>'+esc(x.repo)+'</strong><small>独立关注 · 不等于今日上榜 · '+esc(x.verified_at?.slice(0,10)||'待核验')+'</small></span>'+
    '<span class="fc-gh-star"><b>'+ (x.verified_at&&Number.isInteger(x.stars)?fmt(x.stars):'—') +'</b><small>总 Star</small></span></a>'
  ).join('')+'</div>':'')+
  '<div class="fc-gh-foot">'+(fresh?'从官方 Today 筛选 AI / Agent · 按当日新增 Star 排序':'历史榜已过期 · 等待新快照')+(gh.sync?.status==='error'?' · 最新同步失败':'')+(partial?' · '+(allRepositoryMetadataFailed?'仓库资料更新全部失败':trendingPartial?('上榜仓库资料更新'+(allTrendingMetadataFailed?'全部':'部分')+'失败'):'长期关注仓库资料更新失败')+'：'+(metadataFailures?metadataFailures+' 个上榜项':'')+(metadataFailures&&watchFailures?'、':'')+(watchFailures?watchFailures+' 个长期关注项':'')+'沿用旧值'+(!watchFailures&&(gh.watchlist||[]).length?'；长期关注项已核验':''):'')+' · 独立关注不参与排名</div>'+
 '</section>'
}

function fcHuggingFacePanel(){
 const hf=APP.huggingface_hot||{items:[],web_order:[],checked_at:''};
 const now=Date.now(),webAt=Date.parse(hf.web_fetched_at||hf.checked_at||''),apiAt=Date.parse(hf.api_fetched_at||'');
 const webFresh=Number.isFinite(webAt)&&(now-webAt)<=6*36e5&&(now-webAt)>=-36e5;
 const apiFresh=Number.isFinite(apiAt)&&(now-apiAt)<=6*36e5&&(now-apiAt)>=-36e5;
 const byId=new Map((hf.items||[]).map(x=>[x.id,x]));
 const order=Array.isArray(hf.web_order)&&hf.web_order.length?hf.web_order:[...(hf.items||[])].sort((a,b)=>(a.rank||999)-(b.rank||999)).map(x=>x.id);
 const rows=webFresh?order.slice(0,3).map((id,index)=>({...byId.get(id),id,rank:index+1})):[];
 const changes=Array.isArray(hf.web_rank_changes)?hf.web_rank_changes:[];
 const entrants=changes.filter(x=>x.previous_rank==null).length;
 const moved=changes.filter(x=>Number.isInteger(x.previous_rank)&&x.rank_change!==0).length;
 const outgoing=Array.isArray(hf.web_outgoing)?hf.web_outgoing.length:0;
 const hasChanges=webFresh&&(entrants||moved||outgoing);
 const fmt=n=>{const v=Number(n);if(!Number.isFinite(v))return '—';if(v>=1000000)return (v/1000000).toFixed(v>=10000000?1:2)+'M';if(v>=1000)return (v/1000).toFixed(v>=100000?0:1)+'k';return v.toLocaleString('en-US')};
 const when=raw=>{try{return new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(raw)).replaceAll('/','.')+' 北京时间'}catch{return '待核验'}};
 const previous=changes.find(x=>x&&x.previous_fetched_at)?.previous_fetched_at||(hf.web_outgoing||[]).find(x=>x&&x.previous_fetched_at)?.previous_fetched_at||'';
 const comparison=previous?'较 '+when(previous).replace(' 北京时间','')+' 快照':'';
 return '<section class="fc-panel fc-hf-panel">'+
  '<div class="fc-panel-head compact"><div><p class="eyebrow">HUGGING FACE / WEB ORDER</p><h2>Hugging Face 热榜</h2></div><a href="#/hot?tab=hf">完整榜 '+icon('arrow')+'</a></div>'+
  (hasChanges?'<div class="fc-hf-change" role="status"><a href="#/hot?tab=hf"><b>本轮变化</b>'+(comparison?'<small>'+esc(comparison)+'</small>':'')+'<span>'+entrants+' 新上榜 · '+moved+' 位次变化 · '+outgoing+' 离榜</span>'+icon('arrow')+'</a></div>':'')+
  (webFresh?'<div class="fc-hf-list">'+rows.map(x=>
   '<a class="fc-hf-row" href="'+safeLink(x.url||('https://huggingface.co/'+x.id))+'" target="_blank" rel="noopener noreferrer">'+
    '<span class="fc-hf-rank">#'+String(x.rank).padStart(2,'0')+'</span>'+
    '<span class="fc-hf-main"><strong>'+esc(x.id)+'</strong><small>'+esc((x.task||'任务未标注')+' · '+(x.library||'库未标注'))+'</small></span>'+
    '<span class="fc-hf-score"><b>'+fmt(x.trending_score)+'</b><small>API Trending'+(apiFresh?'':'（旧）')+'</small></span></a>'
  ).join('')+'</div>':'<div class="fc-gh-old"><strong>当前 Models Trending 未完成核验</strong><p>旧榜位已停止作为首页前列展示；仍可查看可追溯的历史快照。</p></div>')+
  '<div class="fc-hf-foot">'+(webFresh?'官方网页顺序 · '+esc(when(hf.web_fetched_at||hf.checked_at)):'历史榜已过期 · 等待新快照')+(webFresh&&!apiFresh?' · API 指标沿用旧快照':'')+' · Trending 不等于能力榜</div>'+
 '</section>'
}

function fcCockpit(){
 return '<section class="fc-cockpit">'+
  fcHotPanel()+
  '<div class="fc-tool-grid">'+fcPersonalPanel()+fcDeepPanel()+fcGithubPanel()+fcHuggingFacePanel()+'</div>'+
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
