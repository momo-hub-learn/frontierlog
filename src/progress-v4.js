'use strict';
(()=>{
/* Progress v4 — productized capability page: what's new → what works → what is still research. */
function p4SourceRows(t){return (t.sources||[]).map(id=>sources.get(id)).filter(Boolean)}
function p4LatestEvidence(t){
 const rows=p4SourceRows(t);
 const dated=rows.filter(s=>s.published).sort((a,b)=>String(b.published).localeCompare(String(a.published)));
 const s=dated[0]||rows[0]||null;
 return {source:s,date:s?.published||t.reviewed||DATA.snapshot};
}
function p4Days(a,b){try{return Math.round((Date.parse(a+'T00:00:00Z')-Date.parse(b+'T00:00:00Z'))/86400000)}catch{return 999}}
function p4Status(t){
 if(t.status==='research')return {label:'研究阶段',cls:'research',maturity:'公开研究 · 未核验访问'};
 const map={
  'gemini-38-flash-tts':{label:'可直接体验',cls:'direct',maturity:'网页 / API · 未本站实测'},
  'gemini-connected-apps':{label:'限量开放',cls:'limited',maturity:'灰度 rollout · 需账号权限'},
  'chatgpt-voice-work':{label:'可直接用',cls:'direct',maturity:'账号开放 · 受套餐 / 地区限制'}
 };
 if(map[t.id])return map[t.id];
 if(/本地运行|Lean 环境|GPU 环境|沙箱环境/.test(t.effort||''))return {label:'可本地跑',cls:'local',maturity:(t.effort||'本地环境')+' · 未本站实测'};
 if(t.repo)return {label:'可部署',cls:'local',maturity:(t.effort||'开源实现')+' · 未本站实测'};
 return {label:'可使用',cls:'direct',maturity:(t.effort||'公开路径')+' · 未本站实测'};
}
function p4Experience(t){
 const map={
  'gemini-38-flash-tts':['https://aistudio.google.com/','立即体验'],
  'gemini-connected-apps':['https://gemini.google.com/','打开 Gemini'],
  'chatgpt-voice-work':['https://chatgpt.com/','打开 ChatGPT']
 };
 if(map[t.id])return map[t.id];
 if(t.repo)return ['https://github.com/'+t.repo,'打开项目'];
 const s=p4SourceRows(t)[0];return s?[s.url,t.status==='research'?'原始研究':'查看入口']:null
}
function p4Authority(t){
 const {source,date}=p4LatestEvidence(t);
 return {publisher:source?.publisher||t.name,kind:source?.kind||'公开资料',date}
}
function p4Actions(t,compact=false){
 const exp=p4Experience(t),src=p4SourceRows(t)[0];
 return '<div class="p4-actions">'+
  (exp?'<a class="p4-action primary" href="'+safeLink(exp[0])+'" target="_blank" rel="noopener noreferrer">'+esc(exp[1])+' '+icon('external')+'</a>':'')+
  (src&&(!exp||src.url!==exp[0])?'<a class="p4-action" href="'+safeLink(src.url)+'" target="_blank" rel="noopener noreferrer">来源 '+icon('external')+'</a>':'')+
  '<button class="p4-action detail" data-action="task" data-id="'+esc(t.id)+'">详情 '+icon('arrow')+'</button>'+
 '</div>'
}
function p4Fresh(t){
 const e=p4LatestEvidence(t),days=p4Days(DATA.snapshot,e.date);
 return days>=0&&days<=7
}
function p4NewCard(t){
 const st=p4Status(t),ev=p4Authority(t);
 return '<article class="p4-new-card">'+
  '<header><span class="p4-status '+st.cls+'">'+esc(st.label)+'</span><span class="p4-fresh">NEW '+esc(ev.date.slice(5).replace('-','.'))+'</span></header>'+
  '<div class="p4-evidence">'+esc(ev.publisher)+' · '+esc(ev.kind)+'</div>'+
  '<h3>'+esc(t.title)+'</h3>'+
  '<p class="p4-can">'+esc(t.summary)+'</p>'+
  '<div class="p4-limit"><span>限制</span><p>'+esc(t.boundary)+'</p></div>'+
  '<footer><span>'+esc(st.maturity)+'</span>'+p4Actions(t)+'</footer>'+
 '</article>'
}
function p4CapabilityCard(t){
 const st=p4Status(t),ev=p4Authority(t);
 return '<article class="p4-card">'+
  '<div class="p4-card-top"><div><span class="p4-status '+st.cls+'">'+esc(st.label)+'</span><span class="p4-evidence-inline">'+esc(ev.publisher)+' · '+esc(ev.kind)+' · '+esc(ev.date.slice(5).replace('-','.'))+'</span></div><button class="p4-open" data-action="task" data-id="'+esc(t.id)+'" aria-label="打开 '+esc(t.title)+'">'+icon('arrow')+'</button></div>'+
  '<h3>'+esc(t.title)+'</h3><p class="p4-project">'+esc(t.name)+' · '+esc(t.category)+'</p>'+
  '<p class="p4-can">'+esc(t.summary)+'</p>'+
  '<div class="p4-limit compact"><span>还卡在</span><p>'+esc(t.boundary)+'</p></div>'+
  '<footer><span>'+esc(st.maturity)+'</span>'+p4Actions(t,true)+'</footer>'+
 '</article>'
}
function p4ResearchCard(t){
 const ev=p4Authority(t),st=p4Status(t);
 return '<article class="p4-research-card">'+
  '<div class="p4-research-mark">'+icon('flask')+'</div>'+
  '<div class="p4-research-main"><div><span class="p4-status research">'+esc(st.label)+'</span><span class="p4-evidence-inline">'+esc(ev.publisher)+' · '+esc(ev.kind)+' · '+esc(ev.date.slice(5).replace('-','.'))+'</span></div><h3>'+esc(t.title)+'</h3><p>'+esc(t.summary)+'</p><small>'+esc(t.boundary)+'</small></div>'+
  p4Actions(t,true)+
 '</article>'
}
function p4Progress(){
 $('#hero').hidden=true;$('#stats').hidden=true;$('.workspace').hidden=false;$('#vertical-root').hidden=true;$('.section-head').hidden=true;
 $('#layout-buttons').hidden=true;$('#toolbar').hidden=true;$('#contextline').hidden=true;
 const usable=DATA.items.filter(t=>t.status==='code');
 const research=DATA.items.filter(t=>t.status==='research');
 const fresh=usable.filter(p4Fresh).sort((a,b)=>p4LatestEvidence(b).date.localeCompare(p4LatestEvidence(a).date));
 const stable=usable.filter(t=>!p4Fresh(t));
 $('#content').innerHTML='<div class="p4-progress">'+
  '<header class="p4-head"><div><p class="eyebrow">CAPABILITY MAP / VERIFIED SOURCES</p><h1>AI，又能干什么了？</h1><p>先看最近新增 / 明显更新的能力，再看已经有公开路径的能力。每一项都标入口、来源、核验时间和当前限制。</p></div>'+
   '<div class="p4-stats"><span><b>'+fresh.length+'</b>本周新增 / 更新</span><span><b>'+usable.length+'</b>现在能用</span><span><b>'+research.length+'</b>研究阶段</span></div></header>'+
  (fresh.length?'<section class="p4-new"><div class="p4-section-head"><div><p class="eyebrow">NEW THIS WEEK</p><h2>本周新解锁 / 明显更新</h2><span>先看真正改变“现在能做什么”的变化。</span></div><b>'+fresh.length+'</b></div><div class="p4-new-grid">'+fresh.map(p4NewCard).join('')+'</div></section>':'')+
  '<section class="p4-available"><div class="p4-section-head"><div><p class="eyebrow">AVAILABLE NOW</p><h2>持续可用</h2><span>有公开实现、API 或产品入口；不等于已经通过你的业务验收。</span></div><b>'+stable.length+'</b></div><div class="p4-grid">'+stable.map(p4CapabilityCard).join('')+'</div></section>'+
  (research.length?'<section class="p4-research"><div class="p4-section-head"><div><p class="eyebrow">RESEARCH EDGE</p><h2>还在研究</h2><span>有研究证据，但访问、稳定性或复现条件还不够成熟。</span></div><b>'+research.length+'</b></div><div class="p4-research-list">'+research.map(p4ResearchCard).join('')+'</div></section>':'')+
  '</div>';
}
const p4BaseRenderMain=renderMain;
renderMain=function(){
 p4BaseRenderMain();
 if(state.view==='progress')p4Progress();
};
if(state.view==='progress'){lastMain='';renderMain()}
})();