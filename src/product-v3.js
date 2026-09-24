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
function decorateBaseModelCompanies(){
 const tables=document.querySelectorAll('.v2-model-table table.m-table');
 tables.forEach(table=>{
  if(table.dataset.companyColumn==='1')return;
  const head=table.querySelector('thead tr');
  const ths=head?[...head.children]:[];
  if(!head||ths.length<2)return;
  const companyTh=document.createElement('th');
  companyTh.className='m-company-col';
  companyTh.textContent='公司';
  ths[1].after(companyTh);
  table.querySelectorAll('tbody tr').forEach(row=>{
   const cells=[...row.children],meta=row.querySelector('.m-rowmeta');
   if(cells.length<2||!meta)return;
   const raw=(meta.textContent||'').trim(),maker=raw.split(' · ')[0],c=companyFor(maker);
   const td=document.createElement('td');td.className='m-company-cell';
   td.innerHTML=c?companyAnchor(maker,c.short||maker,'model-maker-link'):esc(maker);
   cells[1].after(td);
   const suffix=raw.slice(maker.length).replace(/^\s*·\s*/,'').trim();
   meta.textContent=suffix;
   if(!suffix)meta.hidden=true;
  });
  table.dataset.companyColumn='1';
 });
}
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
modelPage=function(){const p=capParam(),wantsCap=p.has('cap');if(wantsCap&&!CAP3){ensureCaps();return'<div class="m-wrap"><div class="v3-loading">正在加载模型榜数据…</div></div>'}const g=capGroup();return g?capPage():oldModelPage()};
document.addEventListener('click',e=>{const board=e.target.closest('[data-v3-board]');if(board){e.preventDefault();capRoute({board:board.dataset.v3Board,metric:null});return}const metric=e.target.closest('[data-v3-metric]');if(metric){e.preventDefault();capRoute({metric:metric.dataset.v3Metric})}});
document.addEventListener('change',e=>{if(e.target.id==='v3-cap-maker')capRoute({maker:e.target.value})});
document.addEventListener('input',e=>{if(e.target.id!=='v3-cap-search')return;const value=e.target.value,pos=e.target.selectionStart,p=capParam();if(value)p.set('q',value);else p.delete('q');history.replaceState(null,'','#/models'+(p.size?'?'+p.toString():''));lastMain='';renderMain();const n=document.getElementById('v3-cap-search');if(n){n.focus({preventScroll:true});try{n.setSelectionRange(pos,pos)}catch{}}});
if(state.view==='models'){lastMain='';renderMain();queueMicrotask(decorateBaseModelCompanies)}
const companyObserver=new MutationObserver(()=>decorateBaseModelCompanies());
companyObserver.observe(document.body,{childList:true,subtree:true});
queueMicrotask(decorateBaseModelCompanies);
})();
