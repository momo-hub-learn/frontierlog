'use strict';
(()=>{
let CAP3=window.APP?.capabilities||null,capLoadStarted=false;
async function ensureCaps(){
 if(CAP3)return CAP3;
 if(capLoadStarted)return null;
 capLoadStarted=true;
 try{
  const r=await fetch('./api/v1/capabilities.json',{cache:'no-store'});
  if(!r.ok)throw new Error('capability data '+r.status);
  CAP3=await r.json();
  if(state.view==='models'||state.view==='benchmarks'){lastMain='';renderMain()}
 }catch(e){console.error(e)}
 return CAP3
}
ensureCaps();
const companyRows=()=>window.MODEL_COMPANIES||[];
function companyFor(maker){return companyRows().find(c=>(c.aliases||[]).includes(maker))||null}
function companyAnchor(maker,label=maker,cls='v3-company-link'){
 const c=companyFor(maker); if(!c)return esc(label);
 return '<a class="'+cls+'" href="'+safeLink(c.url)+'" target="_blank" rel="noopener noreferrer" title="'+esc(c.name)+'">'+esc(label)+' '+icon('external')+'</a>'
}
// Company cells come from structured rows, never from score/error text in the DOM.
function linkedModelCompany(row){
 const company=companyFor(row.maker),logo=mLogoForMaker(row.maker);
 const name=company?'<a class="m-company-name ar-company-link" href="'+safeLink(company.url)+'" target="_blank" rel="noopener noreferrer" title="'+esc(company.name)+' · 官方网站">'+esc(row.maker)+'</a>':'<span class="m-company-name">'+esc(row.maker)+'</span>';
 return '<div class="m-company"><span class="m-company-logo" aria-hidden="true"><span>'+esc(mMakerInitials(row.maker))+'</span>'+(logo?'<img src="'+safeLink(logo)+'" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.hidden=true">':'')+'</span>'+name+'</div>';
}
function decorateBaseModelCompanies(){
 const byId=new Map(mBoardState().b.rows.map(row=>[row.id,row]));
 document.querySelectorAll('.v2-model-table table.m-table').forEach(table=>{
  if(table.dataset.companyColumn==='1')return;
  table.querySelectorAll('tbody tr[data-model-row]').forEach(element=>{
   const row=byId.get(element.dataset.modelRow),cell=element.querySelector('.m-company-cell');
   if(row&&cell)cell.innerHTML=linkedModelCompany(row);
  });
  table.dataset.companyColumn='1';
 });
}
/* Arena view: preserve source semantics; only the presentation changes. */
const arenaExpanded=new Set();
const ARENA_HELP={
 score:['分数与误差怎么读','分数反映该榜单口径下的文本对话偏好。± 后面的数值来自来源方的分数误差字段；缺失时显示“误差未提供”，不补成 0。不能仅凭一两分差距断言显著领先，也不是任务正确率或本站实测。'],
 votes:['票数怎么读','这里保留来源方对该模型记录的票数。票数是评估样本信息，不是胜场数、独立用户数或模型能力分。更多票数本身不等于更强。'],
 rank:['名次范围怎么读','这是来源方给出的名次估计范围，不是历史涨跌，也不是本站重新计算的排名。多个模型的区间可能重叠，单看名次或分数不能确认差异显著。']
};
function arenaHelpButton(key,label){return '<button class="ar-help" data-ar-help="'+key+'" aria-label="'+esc(ARENA_HELP[key][0])+'">'+esc(label)+icon('info')+'</button>'}
function arenaScore(row){
 return '<span class="ar-score"><strong>'+mNum(row.preference,0)+'</strong>'+(Number.isFinite(row.score_error)?'<span>± '+mNum(row.score_error,0)+'</span>':'<span>误差未提供</span>')+'</span>';
}
function arenaRange(row){return Array.isArray(row.rank_spread)&&row.rank_spread.length===2?row.rank_spread.map(x=>mNum(x,0)).join('–'):'—'}
function arenaDate(value){return mValidDate(value)?'<time datetime="'+esc(value)+'">'+esc(value.replaceAll('-','.'))+'</time>':'待核验'}
function arenaName(row){return '<button class="ar-model-name" data-ma="model" data-id="'+esc(row.id)+'">'+esc(row.name)+'</button>'+(row.preliminary?'<span class="ar-preliminary">初步结果 · Preliminary</span>':'')}
function arenaTable(rows,b){
 return '<div class="ar-desktop"><table class="ar-table"><caption class="ar-sr-only">Arena 文本对话偏好榜，官方顺序的站内摘录；筛选不改变来源名次。</caption><colgroup><col class="ar-col-rank"><col class="ar-col-model"><col class="ar-col-company"><col class="ar-col-score"><col class="ar-col-votes"><col class="ar-col-range"><col class="ar-col-actions"></colgroup><thead><tr><th scope="col">官方名次</th><th scope="col">模型 / 配置</th><th scope="col">公司</th><th scope="col">'+arenaHelpButton('score','分数 ± 误差')+'</th><th scope="col">'+arenaHelpButton('votes','票数')+'</th><th scope="col">'+arenaHelpButton('rank','名次范围')+'</th><th scope="col">关注 / 对比</th></tr></thead><tbody>'+rows.map(row=>'<tr data-model-row="'+esc(row.id)+'"'+(row.source_rank===1?' class="ar-leading"':'')+'><td class="ar-rank">'+mNum(row.source_rank,0)+'</td><td>'+arenaName(row)+'</td><td>'+linkedModelCompany(row)+'</td><td class="ar-numeric">'+arenaScore(row)+'</td><td class="ar-numeric">'+mNum(row.votes,0)+'</td><td class="ar-numeric">'+arenaRange(row)+'</td><td><div class="m-table-actions">'+mSavedButton(row)+mCompareButton(row)+'</div></td></tr>').join('')+'</tbody></table></div>';
}
function arenaCards(rows,b){
 return '<div class="ar-mobile-list" role="list" aria-label="Arena 模型记录">'+rows.map(row=>'<article class="ar-card'+(row.source_rank===1?' ar-leading':'')+'" role="listitem" data-ar-model="'+esc(row.id)+'"><div class="ar-card-title"><span class="ar-rank" aria-label="官方名次 '+mNum(row.source_rank,0)+'">#'+mNum(row.source_rank,0)+'</span><div>'+arenaName(row)+'</div></div><div class="ar-card-main">'+linkedModelCompany(row)+'<div class="ar-card-score">'+arenaScore(row)+'<small>分数 ± 误差</small></div></div><dl class="ar-card-facts"><div><dt>'+arenaHelpButton('votes','票数')+'</dt><dd>'+mNum(row.votes,0)+'</dd></div><div><dt>'+arenaHelpButton('rank','名次范围')+'</dt><dd>'+arenaRange(row)+'</dd></div></dl><details class="ar-card-more" data-ar-id="'+esc(row.id)+'"'+(arenaExpanded.has(row.id)?' open':'')+'><summary>来源 · 关注 · 对比</summary><div class="ar-card-actions">'+mSourceLink(row.source||b.source)+'<div class="m-table-actions">'+mSavedButton(row)+mCompareButton(row)+'</div></div></details></article>').join('')+'</div>';
}
function arenaPage(){
 const {b,q,maker,only}=mBoardState();
 if(compareBoard!==b.id){modelCompare.clear();compareBoard=b.id}
 const rows=mRows().slice().sort((a,z)=>a.source_order-z.source_order),providers=[...new Set(b.rows.map(row=>row.maker))].sort(),filtered=!!q||maker!=='all'||only,source=mSource(b.source);
 const sourceTabs='<nav class="ar-source-tabs" aria-label="评测来源">'+MODEL_DATA.boards.map(board=>'<button class="'+(board.id===b.id?'active':'')+'" data-ma="board" data-id="'+esc(board.id)+'" aria-pressed="'+(board.id===b.id)+'">'+esc(board.title)+' <small>· '+esc(board.provider==='Arena'?'Arena':'AA')+'</small></button>').join('')+'</nav>';
 return '<div class="m-wrap ar-wrap">'+modelHubTabs('rankings')+sourceTabs+'<header class="ar-header"><div><h1>Arena 文本对话偏好榜</h1><p>看用户更偏好哪种回答，不代表综合能力或任务正确率。</p></div></header><div class="ar-provenance"><span>来源日期 '+arenaDate(b.as_of)+'</span><span>最近核验 '+arenaDate(b.checked)+'</span><strong>'+esc(b.mode==='manual_excerpt'?'人工摘录':'站内收录')+' '+b.rows.length+' 条 · 非完整榜</strong>'+(source?'<a class="ar-original" href="'+safeLink(source.url)+'" target="_blank" rel="noopener noreferrer">官方原榜 '+icon('external')+'</a>':'')+'</div><div class="ar-toolbar"><label class="m-search">'+icon('search')+'<input id="m-search" type="search" value="'+esc(q)+'" placeholder="搜索模型 / 公司" aria-label="搜索模型或公司"></label><select id="m-maker" class="m-select" aria-label="筛选模型厂商"><option value="all">全部厂商</option>'+providers.map(name=>'<option value="'+esc(name)+'"'+(name===maker?' selected':'')+'>'+esc(name)+'</option>').join('')+'</select><label class="m-check"><input id="m-only" type="checkbox"'+(only?' checked':'')+'>只看关注</label><button class="ar-clear" data-ma="model-clear"'+(!filtered?' disabled':'')+'>清除筛选</button></div><div class="ar-resultline"><span role="status" aria-live="polite">显示 '+rows.length+' / '+b.rows.length+' 条 · 保留官方名次</span><button class="ar-help" data-ar-help="score">如何读分数 '+icon('info')+'</button></div>'+(rows.length?arenaTable(rows,b)+arenaCards(rows,b):'<div class="m-empty ar-empty"><h2>没有匹配的模型</h2><p>可搜索的范围是本站已收录记录，不代表官方完整榜。</p>'+mButton('清除筛选','model-clear')+'</div>')+'<p class="ar-footnote">'+esc(b.methodology)+' · 按来源顺序展示。名次可能不连续；区间重叠时，不作显著领先判断。</p>'+(modelCompare.size?'<div class="m-comparebar"><span>'+modelCompare.size+' / 3 个配置 · 同源对比</span>'+mButton('比较','compare','','primary')+mButton('清空','compare-clear')+'</div>':'')+'</div>';
}
/* End Arena view. */
Object.assign(PATHS,{terminal:'<path d="M4 5h16v14H4z"/><path d="m7 9 3 3-3 3m5 0h5"/>',image:'<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m4 18 5-5 4 4 2-2 5 5"/>',globe:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/>',mic:'<rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6"/>'});
function capParam(){return new URLSearchParams(location.hash.split('?')[1]||'')}
function capGroup(){const id=capParam().get('cap');return CAP3?.groups?.find(g=>g.id===id)||null}
function capRoute(patch={}){const p=capParam();for(const[k,v]of Object.entries(patch)){if(v===null||v===undefined||v==='')p.delete(k);else p.set(k,String(v))}location.hash='#/models'+(p.size?'?'+p.toString():'')}
function fmt(v,col){if(v===null||v===undefined||v==='')return'—';if(typeof v==='number'){const d=Math.abs(v)<1?3:Number.isInteger(v)?0:1,n=v.toLocaleString('en-US',{maximumFractionDigits:d});if(col?.unit==='$')return'$'+n;if(col?.unit==='%')return n+'%';if(col?.unit==='min')return n+'m';if(col?.unit==='s')return n+'s';return n}return esc(v)}
function capNav(active='base',bench=false){const groups=CAP3?.groups||[{id:'coding',title:'Coding Agent',icon:'terminal'},{id:'multimodal',title:'多模态',icon:'image'},{id:'world',title:'世界模型',icon:'globe'},{id:'voice',title:'语音',icon:'mic'}];return '<nav class="v3-capnav" aria-label="模型榜"><a class="'+(active==='base'&&!bench?'active':'')+'" href="#/models">'+icon('cpu')+'<span>基础模型</span></a>'+groups.map(g=>'<a class="'+(active===g.id&&!bench?'active':'')+'" href="#/models?cap='+g.id+'">'+icon(g.icon)+'<span>'+esc(g.title)+'</span></a>').join('')+'<a class="'+(bench?'active':'')+'" href="#/benchmarks">'+icon('gauge')+'<span>Benchmark</span></a></nav>'}
modelHubTabs=function(active='rankings'){return capNav(active==='benchmarks'?'base':(capParam().get('cap')||'base'),active==='benchmarks')};
function capBoardState(g){const p=capParam(),boardId=g.boards.includes(p.get('board'))?p.get('board'):g.boards[0],b=CAP3.boards[boardId],metric=b.columns.some(c=>c.key===p.get('metric'))?p.get('metric'):b.primary,q=(p.get('q')||'').toLowerCase().trim(),maker=p.get('maker')||'all';let rows=b.rows.filter(r=>(maker==='all'||r.maker===maker)&&(!q||[r.name,r.maker,r.detail,...Object.values(r)].join(' ').toLowerCase().includes(q)));rows=[...rows].sort((a,z)=>Number(z[metric]??-Infinity)-Number(a[metric]??-Infinity));return{boardId,b,metric,q,maker,rows}}
function capPodium(rows,b,metric){const col=b.columns.find(c=>c.key===metric)||b.columns[0];return'<section class="v3-podium">'+rows.slice(0,3).map((r,i)=>'<article class="v3-podium-card rank-'+(i+1)+'"><div class="v3-rank">'+String(i+1).padStart(2,'0')+'</div><div class="v3-maker">'+companyAnchor(r.maker,r.maker)+'</div><h3>'+esc(r.name)+'</h3><p>'+esc(r.detail||'')+'</p><div class="v3-score"><strong>'+fmt(r[metric],col)+'</strong><span>'+esc(col.label)+'</span></div>'+b.columns.filter(c=>c.key!==metric).slice(0,2).map(c=>'<small>'+esc(c.label)+' <b>'+fmt(r[c.key],c)+'</b></small>').join('')+'</article>').join('')+'</section>'}
function capTable(rows,b,metric){const cols=b.columns;return'<div class="v3-ranktable" style="--metric-count:'+cols.length+'"><div class="v3-rank-head"><span>#</span><span>模型 / 系统</span><span>公司</span><span>类型 / Harness</span>'+cols.map(c=>'<span class="'+(c.key===metric?'primary':'')+'">'+esc(c.label)+'</span>').join('')+'</div>'+rows.map((r,i)=>'<article class="v3-rank-row"><span class="v3-order">'+String(i+1).padStart(2,'0')+'</span><span class="v3-model"><i>'+esc((r.maker||'--').slice(0,2).toUpperCase())+'</i><span><strong>'+esc(r.name)+'</strong></span></span><span class="v3-company-cell">'+mCompanyCell({maker:r.maker})+'</span><span class="v3-detail">'+esc(r.detail||'—')+'</span>'+cols.map(c=>'<span class="v3-metric '+(c.key===metric?'primary':'')+'"><b>'+fmt(r[c.key],c)+'</b><small>'+(c.key===metric?esc(c.unit||''):'')+'</small></span>').join('')+'</article>').join('')+'</div>'}
function capPage(){if(!CAP3){ensureCaps();return'<div class="m-wrap"><div class="v3-loading">正在加载模型榜数据…</div></div>'}const g=capGroup();if(!g)return null;const{b,metric,q,maker,rows}=capBoardState(g),makers=[...new Set(b.rows.map(r=>r.maker))].sort();return'<div class="m-wrap v3-cap-page">'+capNav(g.id)+'<header class="v3-cap-head"><div><p>模型榜</p><h1>'+esc(g.title)+'</h1><span>'+esc(g.subtitle)+'。先看领先样本，再看完整榜单。</span></div><div class="v3-cap-source"><a href="'+safeLink(b.url)+'" target="_blank" rel="noopener">'+esc(b.source)+' '+icon('external')+'</a><small>核对 '+esc(CAP3.checked)+' · 公开榜单摘录</small></div></header>'+(g.boards.length>1?'<nav class="v3-board-tabs">'+g.boards.map(id=>'<button class="'+(id===b.id?'active':'')+'" data-v3-board="'+id+'">'+esc(CAP3.boards[id].title)+'</button>').join('')+'</nav>':'')+'<div class="v3-boardline"><div><strong>'+esc(b.title)+'</strong><span>'+esc(b.note)+'</span></div><div class="v3-metric-tabs">'+b.columns.filter(c=>b.rows.some(r=>typeof r[c.key]==='number')).map(c=>'<button class="'+(c.key===metric?'active':'')+'" data-v3-metric="'+c.key+'">'+esc(c.label)+'</button>').join('')+'</div></div>'+capPodium(rows,b,metric)+'<div class="v3-rank-tools"><label>'+icon('search')+'<input id="v3-cap-search" value="'+esc(q)+'" placeholder="搜索模型、厂商、Harness"></label><select id="v3-cap-maker"><option value="all">全部厂商</option>'+makers.map(m=>'<option value="'+esc(m)+'" '+(m===maker?'selected':'')+'>'+esc(m)+'</option>').join('')+'</select></div>'+capTable(rows,b,metric)+'<div class="v3-rank-foot"><span>不同榜单不合并总分；外部成绩不能替代你的真实业务验证。</span><a href="'+safeLink(b.url)+'" target="_blank" rel="noopener">查看原始榜单 '+icon('external')+'</a></div></div>'}
const oldModelPage=modelPage;
modelPage=function(){const p=capParam(),wantsCap=p.has('cap');if(wantsCap&&!CAP3){ensureCaps();return'<div class="m-wrap"><div class="v3-loading">正在加载模型榜数据…</div></div>'}const g=capGroup();return g?capPage():mBoardState().b.id==='arena'?arenaPage():oldModelPage()};
document.addEventListener('click',e=>{const board=e.target.closest('[data-v3-board]');if(board){e.preventDefault();capRoute({board:board.dataset.v3Board,metric:null});return}const metric=e.target.closest('[data-v3-metric]');if(metric){e.preventDefault();capRoute({metric:metric.dataset.v3Metric})}});
document.addEventListener('change',e=>{if(e.target.id==='v3-cap-maker')capRoute({maker:e.target.value})});
document.addEventListener('input',e=>{if(e.target.id!=='v3-cap-search')return;const value=e.target.value,pos=e.target.selectionStart,p=capParam();if(value)p.set('q',value);else p.delete('q');history.replaceState(null,'','#/models'+(p.size?'?'+p.toString():''));lastMain='';renderMain();const n=document.getElementById('v3-cap-search');if(n){n.focus({preventScroll:true});try{n.setSelectionRange(pos,pos)}catch{}}});
document.addEventListener('click',e=>{
 const help=e.target.closest('[data-ar-help]');
 if(!help||!ARENA_HELP[help.dataset.arHelp])return;
 const [title,text]=ARENA_HELP[help.dataset.arHelp];
 showModal('ARENA / 评测口径','<h2 id="modal-title">'+esc(title)+'</h2><p class="dialog-intro">'+esc(text)+'</p>'+mSourceRows([mBoardState().b.source]));
});
document.addEventListener('toggle',e=>{
 const element=e.target;
 if(!element.matches?.('.ar-card-more')||!element.isConnected)return;
 if(element.open)arenaExpanded.add(element.dataset.arId);else arenaExpanded.delete(element.dataset.arId);
},true);
// Keep keyboard focus after the shared bookmark/compare handler re-renders the view.
document.addEventListener('click',e=>{
 const button=e.target.closest('.ar-wrap button[data-ma]');
 if(!button||!['star','select'].includes(button.dataset.ma))return;
 const parent=button.closest('.ar-card-more'),selector=parent?'.ar-mobile-list':'.ar-desktop';
 if(parent)arenaExpanded.add(parent.dataset.arId);
 requestAnimationFrame(()=>{
  const buttons=document.querySelectorAll('.ar-wrap '+selector+' button[data-ma]');
  [...buttons].find(b=>b.dataset.ma===button.dataset.ma&&b.dataset.id===button.dataset.id)?.focus({preventScroll:true});
 });
},true);
if(state.view==='models'){lastMain='';renderMain();queueMicrotask(decorateBaseModelCompanies)}
const companyObserver=new MutationObserver(()=>decorateBaseModelCompanies());
companyObserver.observe(document.body,{childList:true,subtree:true});
queueMicrotask(decorateBaseModelCompanies);
})();
