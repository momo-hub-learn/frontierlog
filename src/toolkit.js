'use strict';
/* Task-first toolkit. Editorial guides are separate from runtime verification. */
const TK = (()=>{
 const TK_SOURCE_MAP=new Map((APP.catalog.sources||[]).map(s=>[s.id,s]));
 const TK_META={
  docling:{publisher:'Docling Project',group:'documents',access:'local',input:'一份获授权的 PDF',output:'结构化文档 / Markdown',cost:'本地计算；预留模型下载与存储空间。'},
  whisper:{publisher:'OpenAI',group:'audio',access:'local',input:'获授权的短音频',output:'转写文本与字幕文件',cost:'本地计算；模型大小影响内存、速度与存储。'},
  graphrag:{publisher:'Microsoft',group:'documents',access:'model',input:'少量获授权文本 + 问题',output:'基于索引的答案与可核对依据',cost:'索引、嵌入与查询可能产生模型费用。'},
  'gemini-38-flash-tts':{publisher:'Google',group:'audio',access:'web',input:'一段自有文稿 + 语气指令',output:'可试听的生成语音',cost:'用量、配额与计费以账号内官方信息为准。',entry_url:'https://aistudio.google.com/'},
  'chatgpt-voice-work':{publisher:'OpenAI',group:'office',access:'web',input:'语音指令 + 授权的工作材料',output:'任务结果，可接续文字对话',cost:'套餐、限额与工作区设置以账号内显示为准。',entry_url:'https://chatgpt.com/'},
  'gemini-connected-apps':{publisher:'Google',group:'office',access:'web',input:'指令 + 已授权应用的测试数据',output:'跨应用查询或操作结果',cost:'账号和接入应用的套餐、额度分别适用。',entry_url:'https://gemini.google.com/'},
  openhands:{publisher:'OpenHands',group:'agents',access:'model',input:'隔离仓库 + 问题描述 + 测试',output:'代码变更与可检查的执行记录',cost:'模型调用与后端运行可能分别产生费用。'},
  'browser-use':{publisher:'Browser Use',group:'agents',access:'model',input:'授权测试网站 + 清晰任务',output:'浏览器操作与可核对结果',cost:'模型调用与可选云端浏览器可能另行计费。'},
  mathlib:{publisher:'Lean Community',group:'research',access:'research',input:'形式化命题 + 证明代码',output:'Lean 检查结果或错误信息',cost:'本地环境与依赖下载；运行条件按选用入口确认。',entry_url:'https://live.lean-lang.org/'},
  'ai-scientist':{publisher:'Sakana AI',group:'research',access:'research',input:'官方实验模板 + 数据 + 模型配置',output:'实验日志、图表和报告草稿',cost:'计算资源、模型调用及依赖安装成本；先限制实验规模。'}
 };
 const data={version:1,
  groups:[{id:'documents',label:'文档与知识'},{id:'audio',label:'语音处理'},{id:'office',label:'办公自动化'},{id:'agents',label:'开发与浏览器'},{id:'research',label:'科研验证'}],
  access_modes:[{id:'local',label:'本地工具'},{id:'model',label:'模型服务 · 需配置'},{id:'web',label:'网页 · 需权限'},{id:'research',label:'科研环境'}],
  items:(APP.catalog.items||[]).filter(t=>t.status==='code'&&TK_META[t.id]).map(t=>{
   const m=TK_META[t.id],srcs=(t.sources||[]).map(id=>TK_SOURCE_MAP.get(id)).filter(Boolean);
   return {id:t.id,publisher:m.publisher,group:m.group,access:m.access,headline:t.title,input:m.input,output:m.output,
    requirements:t.requirements||'按官方资料准备环境。',limitation:t.boundary||t.scope||'需按官方限制使用。',cost:m.cost,
    steps:[{title:'先看官方入口',body:'先阅读一手资料，确认当前版本、账号或环境条件。'},
     {title:'从一个小任务开始',body:t.test||'用可核对的小样本完成第一轮验证。',command:t.command||undefined},
     {title:'按结果验收',body:(t.checks||[]).join('；')||'核对实际输出并记录结果。'}],
    troubleshooting:'先检查版本、权限、输入和运行环境，再缩小到可复现的小样本。',
    sources:srcs.map(s=>({title:s.title,url:s.url,published_at:s.published||null,verified_at:s.checked||t.reviewed||APP.catalog.snapshot})),
    entry_url:m.entry_url||null,evidence_level:'primary-docs',runtime_tested:false};
  })
 };
 const guides=new Map(data.items.map(x=>[x.id,x]));
 const openIds=new Set();
 const groupIds=new Set(data.groups.map(x=>x.id)),modeIds=new Set(data.access_modes.map(x=>x.id));
 const label=(rows,id)=>rows.find(x=>x.id===id)?.label||'';
 function read(hash=location.hash){
  const p=new URLSearchParams(hash.split('?')[1]||'');
  const tool=p.get('tool')||p.get('task')||'';
  return {group:groupIds.has(p.get('group'))?p.get('group'):'all',access:modeIds.has(p.get('access'))?p.get('access'):'all',q:(p.get('q')||'').slice(0,300),only:p.get('saved')==='1',tool:guides.has(tool)?tool:''};
 }
 function href(s,patch={}){
  const next={...s,...patch},p=new URLSearchParams();
  if(groupIds.has(next.group))p.set('group',next.group);
  if(modeIds.has(next.access))p.set('access',next.access);
  if(next.q)p.set('q',next.q.slice(0,300));
  if(next.only)p.set('saved','1');
  if(guides.has(next.tool))p.set('tool',next.tool);
  return '#/toolkit'+(p.size?'?'+p.toString():'');
 }
 function rows(s){
  const q=s.q.trim().toLocaleLowerCase();
  return data.items.filter(g=>{
   const t=tasks.get(g.id);
   return (s.group==='all'||g.group===s.group)&&(s.access==='all'||g.access===s.access)&&(!s.only||saved.has(g.id))&&(!q||[t.name,g.publisher,g.headline,g.input,g.output,label(data.groups,g.group)].join(' ').toLocaleLowerCase().includes(q));
  });
 }
 function route(patch,replace=false,resultsOnly=false){
  const hash=href(read(),patch);
  if(location.hash!==hash)history[replace?'replaceState':'pushState'](null,'',hash);
  if(resultsOnly){state.q=read().q;renderResults()}else{lastMain='';parseRoute()}
 }
 function external(url,text,cls='tk-link'){
  return `<a class="${cls}" href="${safeLink(url)}" target="_blank" rel="noopener noreferrer">${esc(text)} ${icon('external')}</a>`;
 }
 function card(g){
  const t=tasks.get(g.id),opened=openIds.has(g.id)||read().tool===g.id;
  const doc=g.sources[0];
  return `<article class="tk-card ${opened?'is-open':''}" data-tk-id="${g.id}">
   <div class="tk-cardtop"><div class="tk-identity"><span class="tk-mark" aria-hidden="true">${esc(t.mark||t.name.slice(0,2))}</span><div><strong>${esc(t.name)}</strong><span>${esc(g.publisher)}</span></div></div><span class="tk-mode" data-mode="${g.access}">${esc(label(data.access_modes,g.access))}</span></div>
   <h2>${esc(g.headline)}</h2>
   <div class="tk-io"><dl><dt>输入</dt><dd>${esc(g.input)}</dd></dl><span aria-hidden="true">→</span><dl><dt>输出</dt><dd>${esc(g.output)}</dd></dl></div>
   <dl class="tk-conditions"><div><dt>先准备</dt><dd>${esc(g.requirements)}</dd></div><div><dt>最大限制</dt><dd>${esc(g.limitation)}</dd></div></dl>
   <div class="tk-actions">${external(doc.url,'官方上手文档')}${g.entry_url?external(g.entry_url,'打开入口'):''}<button type="button" class="save ${saved.has(g.id)?'active':''}" data-tk-save="${g.id}" aria-label="${saved.has(g.id)?'取消关注':'关注'} ${esc(t.name)}" aria-pressed="${saved.has(g.id)}">${icon('bookmark')}</button></div>
   <details class="tk-guide" data-tk-guide="${g.id}" ${opened?'open':''}>
    <summary><span>${icon('code')} 步骤与验收</span><span class="tk-expand" aria-hidden="true">＋</span></summary>
    <div class="tk-guide-content"><div><h3>从一个小任务开始</h3><ol class="tk-steps">${g.steps.map((step,i)=>`<li><h4>${esc(step.title)}</h4><p>${esc(step.body)}</p>${step.command?`<div class="tk-command"><div><span>示例命令 · 未在本站执行</span><button type="button" data-tk-copy="${i}" data-tk-tool="${g.id}" aria-label="复制 ${esc(t.name)} 第 ${i+1} 步完整命令">${icon('copy')} 复制全部</button></div><pre><code>${esc(step.command)}</code></pre><p class="tk-copy-status" role="status"></p></div>`:''}</li>`).join('')}</ol></div>
     <aside class="tk-validation"><h3>怎样算跑通</h3><p class="tk-note">以下为你的本机验收清单，不是本站测试结果。</p><div class="checklist">${t.checks.map((text,i)=>`<label class="${checks[g.id]?.includes(i)?'done':''}"><input type="checkbox" data-check-task="${g.id}" data-check-index="${i}" ${checks[g.id]?.includes(i)?'checked':''}><span>${esc(text)}</span></label>`).join('')}</div>
     <h4>成本与运行条件</h4><p>${esc(g.cost)}</p><h4>卡住时先检查</h4><p>${esc(g.troubleshooting)}</p></aside>
    </div>
    <section class="tk-evidence" aria-label="${esc(t.name)} 的证据与核验日期"><h3>原始来源 <span>资料已核验 · 运行未实测</span></h3>${g.sources.map(s=>`<div>${external(s.url,s.title)}<span>${s.published_at?'原文发布 <time datetime="'+s.published_at+'">'+s.published_at+'</time> · ':''}资料核验 <time datetime="${s.verified_at}">${s.verified_at}</time></span></div>`).join('')}<p>未提供可复现运行日志，不标记为“本站已实测”；核验日期不是软件发布日期。安装页随版本变化，请记录实际版本与环境。</p></section>
   </details></article>`;
 }
 function renderResults(){
  const s=read(),visible=rows(s),target=document.getElementById('tk-results');
  if(!target)return;
  document.getElementById('tk-count').textContent=`${visible.length} / ${data.items.length} 条上手路径`;
  document.getElementById('tk-clear').hidden=!(s.q||s.group!=='all'||s.access!=='all'||s.only);
  target.innerHTML=visible.length?visible.map(card).join(''):`<div class="tk-empty"><h2>没有匹配的上手路径</h2><p>试试项目名、输入文件或想完成的任务，也可以清除当前筛选。</p><button type="button" class="button" data-tk-clear>清除筛选</button></div>`;
 }
 function page(){
  const s=read();if(s.tool)openIds.add(s.tool);
  renderNav();
  for(const selector of ['#hero','#stats','#vertical-root','.section-head','#toolbar','#layout-buttons','#contextline']){const el=$(selector);if(el)el.hidden=true}
  $('#legacy-saved').innerHTML='';$('.workspace').hidden=false;
  const content=$('#content');content.setAttribute('aria-live','off');
  content.innerHTML=`<div class="tk-wrap"><header class="tk-head"><div><h1>今天能跑<span class="accent">.</span></h1><p>先选任务，再看输入、输出和使用条件。</p></div><span class="tk-boundary"><span class="tk-boundary-wide">官方上手路径 · </span>未实测</span></header>
   <nav class="tk-groups" aria-label="按任务筛选"><button type="button" data-tk-group="all" aria-pressed="${s.group==='all'}">全部 <small>${data.items.length}</small></button>${data.groups.map(g=>`<button type="button" data-tk-group="${g.id}" aria-pressed="${s.group===g.id}">${esc(g.label)} <small>${data.items.filter(x=>x.group===g.id).length}</small></button>`).join('')}</nav>
   <div class="tk-toolbar"><label class="tk-search">${icon('search')}<input id="tk-search" type="search" aria-label="搜索工具、任务、输入或输出" placeholder="搜索工具、任务、输入或输出…" maxlength="300" value="${esc(s.q)}"></label><label class="tk-access"><span class="tk-sr">使用方式</span><select id="tk-access" aria-label="使用方式"><option value="all">全部使用方式</option>${data.access_modes.map(x=>`<option value="${x.id}" ${s.access===x.id?'selected':''}>${esc(x.label)}</option>`).join('')}</select></label><label class="tk-saved"><input id="tk-only" type="checkbox" ${s.only?'checked':''}>只看关注</label></div>
   <div class="tk-resultline"><span id="tk-count" role="status"></span><span class="tk-order">按上手路径编排，非能力排名</span><button type="button" id="tk-clear" data-tk-clear>清除筛选</button></div>
   <div class="tk-grid" id="tk-results"></div><p class="tk-footnote">网页能力以账号内实际开放为准；命令需在自己的环境运行。清单与关注仅保存在当前浏览器，不会改变证据等级。</p></div>`;
  renderResults();document.body.classList.remove('nav-open');renderTray();
 }
 async function copy(button){
  const g=guides.get(button.dataset.tkTool),step=g?.steps[Number(button.dataset.tkCopy)];
  if(!step?.command)return;
  const status=button.closest('.tk-command').querySelector('.tk-copy-status');
  button.disabled=true;
  try{
   if(!navigator.clipboard?.writeText)throw new Error('Clipboard unavailable');
   await navigator.clipboard.writeText(step.command);status.textContent='已复制这一整段命令。';
  }catch{status.textContent='未能访问剪贴板，请手动选择上方完整命令复制。'}
  finally{button.disabled=false;button.focus({preventScroll:true})}
 }
 let composing=false;
 document.addEventListener('compositionstart',e=>{if(e.target.id==='tk-search')composing=true});
 document.addEventListener('compositionend',e=>{if(e.target.id==='tk-search'){composing=false;route({q:e.target.value,tool:''},true,true)}});
 document.addEventListener('input',e=>{if(state.view==='toolkit'&&e.target.id==='tk-search'&&!composing&&!e.isComposing)route({q:e.target.value,tool:''},true,true)});
 document.addEventListener('change',e=>{
  if(state.view!=='toolkit')return;
  if(e.target.id==='tk-access'){route({access:e.target.value,tool:''});$('#tk-access').focus()}
  if(e.target.id==='tk-only'){route({only:e.target.checked,tool:''});$('#tk-only').focus()}
 });
 document.addEventListener('click',e=>{
  if(state.view!=='toolkit')return;
  const b=e.target.closest('button');if(!b)return;
  if(b.hasAttribute('data-tk-group')){route({group:b.dataset.tkGroup,tool:''});$("[data-tk-group='"+read().group+"']").focus()}
  if(b.hasAttribute('data-tk-clear')){route({q:'',group:'all',access:'all',only:false,tool:''});$('#tk-search').focus()}
  if(b.hasAttribute('data-tk-copy'))copy(b);
  if(b.hasAttribute('data-tk-save')){
   const id=b.dataset.tkSave;if(!guides.has(id))return;
   saved.has(id)?saved.delete(id):saved.add(id);
   const ok=store('aip.saved',[...saved]);renderNav();
   if(read().only){renderResults();$('#tk-only').focus({preventScroll:true})}
   else{b.classList.toggle('active',saved.has(id));b.setAttribute('aria-pressed',String(saved.has(id)));b.setAttribute('aria-label',(saved.has(id)?'取消关注':'关注')+' '+tasks.get(id).name)}
   toast(ok?(saved.has(id)?'已加入我的关注':'已取消关注'):'关注仅在本次会话有效');
  }
 });
 document.addEventListener('toggle',e=>{
  const el=e.target;
  if(!el.matches?.('[data-tk-guide]'))return;
  el.open?openIds.add(el.dataset.tkGuide):openIds.delete(el.dataset.tkGuide);
  el.closest('.tk-card').classList.toggle('is-open',el.open);
  if(!el.open&&state.view==='toolkit'&&read().tool===el.dataset.tkGuide){history.replaceState(null,'',href(read(),{tool:''}));state.task=null}
 },true);
 document.addEventListener('keydown',e=>{
  if(state.view==='toolkit'&&e.key==='/'&&!e.ctrlKey&&!e.metaKey&&!e.altKey&&!modal.open&&!palette.open&&!e.target.matches('input,textarea,select,[contenteditable=true]')){
   e.preventDefault();e.stopImmediatePropagation();$('#tk-search')?.focus();
  }
 },true);
 const previous=renderMain;
 let wasToolkit=false;
 renderMain=function(){
  if(state.view==='toolkit'){wasToolkit=true;lastMain='';page();return}
  if(wasToolkit){lastMain='';$('#content').setAttribute('aria-live','polite');wasToolkit=false}
  return previous();
 };
 const previousTask=renderTask;
 renderTask=function(){
  if(state.view==='toolkit'&&guides.has(state.task)){
   const el=$("[data-tk-guide='"+state.task+"']");if(el){el.open=true;openIds.add(state.task)}
   if(modal.open&&modal.dataset.type==='task')hideModal(false);
   return;
  }
  return previousTask();
 };
 const previousExport=exportView;
 exportView=function(){
  if(state.view!=='toolkit')return previousExport();
  download('toolkit-guides.json',JSON.stringify({...data,items:rows(read()),scope:'当前筛选的官方上手指南；运行未实测'},null,2),'application/json;charset=utf-8');
 };
 if(state.view==='toolkit')page();
 return {read,href,rows,card,copy};
})();
