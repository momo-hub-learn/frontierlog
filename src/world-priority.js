'use strict';
/* World Model editorial priorities and durable discovery queue.
 * This is NOT a cross-paradigm capability leaderboard.
 * Loaded after models.js, preserving the AA/Arena official score views. */
const WORLD_CANDIDATES=APP.frontier_candidates||{items:[],checked:null};
const WORLD_DIMENSIONS=[['novelty','方法新意',.30],['evidence','实验证据',.30],['reproducibility','可复验材料',.20],['planning','规划与控制关联',.20]];
function worldResearchScore(item){
 const r=item.research_review;
 if(!r||r.version!=='research-priority-v1'||r.scope!=='research_attention_not_capability')return null;
 let sum=0;
 for(const [key,,weight] of WORLD_DIMENSIONS){const n=r.dimensions?.[key]?.rating;if(!Number.isInteger(n)||n<0||n>4)return null;sum+=weight*n}
 return Math.round(sum*250)/10;
}
function worldResearchEvidence(item){
 const score=worldResearchScore(item),r=item.research_review;
 if(score===null)return '';
 return '<div class="world-research"><div class="world-research-head"><span>编辑研究关注指数 <small>非模型能力排名</small></span><b>'+mNum(score,1)+' <small>/100</small></b></div><details><summary>查看四维评分的证据与限制</summary><dl>'+
 WORLD_DIMENSIONS.map(([k,label,weight])=>'<div><dt>'+esc(label)+' <small>'+Math.round(weight*100)+'%</small></dt><dd><b>'+r.dimensions[k].rating+' / 4</b><p>'+esc(r.dimensions[k].reason)+'</p></dd></div>').join('')+
 '</dl><small>复核：'+esc(r.reviewed_on)+' · '+esc(r.limitation)+'</small></details></div>';
}
const originalWorldCard=mFrontierCard;
mFrontierCard=function(item,track){
 const html=originalWorldCard(item,track);
 if(worldResearchScore(item)===null)return html;
 return html.replace('<div class="m-frontier-tags">',worldResearchEvidence(item)+'<div class="m-frontier-tags">');
};
function worldMethodology(){
 return '<details class="world-method"><summary>评分不是能力排名：查看计算方法与适用边界</summary><p>对有原始证据且完成编辑复核的研究，按 0～4 级评估：方法新意 30%、实验证据 30%、可复验材料 20%、与规划/控制的关联 20%。指数 = 25 × 加权分项之和。每一个维度都附证据理由；未审项目和资料不足的产品一律不赋分。</p><p>此指数只帮助读者确定研究阅读顺序。不同任务、模型范式、数据集、预算和闭环/离线结果不可相加为通用模型能力分；希望比较性能，请以同口径 Benchmark 为依据。</p></details>';
}
function worldCandidateCard(c){
 return '<article class="world-candidate"><div><time>'+esc(c.date)+'</time><span>论文元数据 · 未核验</span></div><a href="'+safeLink(c.url)+'" target="_blank" rel="noopener noreferrer"><strong>'+esc(c.title)+'</strong>'+icon('external')+'</a><p>'+esc((c.authors||[]).slice(0,4).join(' · '))+'</p></article>';
}
function worldPendingSection(compact=false){
 const pending=(WORLD_CANDIDATES.items||[]).filter(c=>c.status==='pending'&&!MODEL_DATA.sources.some(s=>s.url===c.url));
 if(!pending.length)return '';
 if(compact)return '<div class="world-pending-peek"><div><b>待审核论文 '+pending.length+' 篇</b><p>LeHami 等重要研究已进入候选池，但还不是正式能力排名。</p></div><button data-ma="frontier" data-id="world-models">查看论文候选 →</button></div>';
 const important=['2610.15267','2610.18826','2610.18447'];
 const featured=important.map(x=>pending.find(p=>p.arxiv_id===x)).filter(Boolean);
 const rest=pending.filter(c=>!featured.some(x=>x.arxiv_id===c.arxiv_id));
 return '<section class="world-queue"><header><div><p class="eyebrow">DISCOVERY ≠ VERIFIED PROGRESS</p><h3>重要论文，先别急着给名次。</h3><p>持久队列 '+pending.length+' 篇 · 最后新增 '+esc(WORLD_CANDIDATES.checked||'未记录')+' · 摘要/标题仅是发现线索，未完成原文、实验和复现审核。</p></div><span>编辑待审</span></header>'+
 (featured.length?'<div class="world-featured"><b>本期重点核对</b><div class="world-candidate-grid">'+featured.map(worldCandidateCard).join('')+'</div></div>':'')+
 (rest.length?'<details class="world-more"><summary>展开其余 '+rest.length+' 篇待核验候选</summary><div class="world-candidate-grid">'+rest.map(worldCandidateCard).join('')+'</div></details>':'')+
 '<footer>每条论文经过人工审读与证据校验后才能升级正式档案；自动发现不等于研究水平、产品开放或真实世界任务成功。</footer></section>';
}
mFrontierRadar=function(){
 const {tracks,selected}=mFrontierTrackState();if(!tracks.length)return '';
 const visible=selected==='all'?tracks:tracks.filter(t=>t.id===selected);
 const count=tracks.reduce((n,t)=>n+t.items.length,0);
 const order=mParams().get('frontier_order')==='research'?'research':'latest';
 const rows=t=>{const a=mFrontierRows(t,tracks,selected!=='all');if(t.id!=='world-models'||order!=='research')return a;return [...a].sort((x,y)=>(worldResearchScore(y)??-1)-(worldResearchScore(x)??-1)||y.date.localeCompare(x.date))};
 const controls=selected==='world-models'?'<div class="world-sort"><div><strong>World Model / JEPA</strong><p>区分发布日期和研究观察价值，不假装它们是同一种能力分。</p></div><nav aria-label="世界模型研究排序"><a class="'+(order==='latest'?'is-selected':'')+'" href="#/models?frontier=world-models">最新公开</a><a class="'+(order==='research'?'is-selected':'')+'" href="#/models?frontier=world-models&frontier_order=research">研究关注度</a></nav></div>'+worldMethodology():'';
 return '<section class="m-frontier"><div class="m-frontier-head"><div><p class="eyebrow">FRONTIER MODEL RADAR / VERIFIED PUBLIC PROGRESS</p><h2>前沿模型雷达 <small>'+count+' 条</small></h2><p>正式档案保留技术来源与研究边界；已复核的世界模型研究可按“编辑研究关注指数”阅读，未审核论文独立展示，绝不冒充产品能力排名。</p></div><span class="m-frontier-boundary">研究档案 · 不跨范式打分 · 核对 '+esc(MODEL_DATA.frontier_checked||MODEL_DATA.checked)+'</span></div>'+
 '<div class="m-frontier-tabs"><button class="m-segment '+(selected==='all'?'active':'')+'" data-ma="frontier" data-id="all">全部</button>'+tracks.map(t=>'<button class="m-segment '+(selected===t.id?'active':'')+'" data-ma="frontier" data-id="'+esc(t.id)+'">'+esc(t.title)+' <small>'+mFrontierRows(t,tracks).length+'</small></button>').join('')+'</div>'+controls+
 visible.map(t=>'<section class="m-frontier-track"><div class="m-frontier-trackhead"><div><h3>'+esc(t.title)+'</h3><p>'+esc(t.description)+'</p></div><span>'+rows(t).length+' 条正式档案</span></div><div class="m-frontier-grid">'+rows(t).map(x=>mFrontierCard(x,t)).join('')+'</div>'+(t.id==='world-models'?worldPendingSection(selected==='all'):'')+'</section>').join('')+'</section>';
};
