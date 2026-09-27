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
// Rich blocks are semantic HTML: copyable, responsive, and never executed as code.
function dRichCode(b){
 return '<figure class="dv-code"><figcaption><div><span>'+esc(b.language||'python')+'</span><strong>'+esc(b.title)+'</strong></div><button type="button" data-d-copy>复制代码</button></figcaption><pre><code>'+esc(b.code)+'</code></pre>'+(b.caption?'<p class="dv-caption">'+esc(b.caption)+'</p>':'')+'</figure>'
}
function dFlow(b){
 return '<figure class="dv-figure"><figcaption><span class="dv-overline">流程图 / WORKFLOW</span><h3>'+esc(b.title)+'</h3></figcaption><ol class="dv-flow" style="--steps:'+b.nodes.length+'">'+b.nodes.map((n,i)=>'<li><span class="dv-number">'+String(i+1).padStart(2,'0')+'</span><strong>'+esc(n.title)+'</strong><p>'+esc(n.detail||'')+'</p></li>').join('')+'</ol><p class="dv-caption">'+esc(b.caption||'')+'</p></figure>'
}
function dRichCards(b){
 return '<div class="dv-cards-wrap">'+(b.title?'<h3>'+esc(b.title)+'</h3>':'')+'<div class="dv-cards">'+b.items.map(x=>'<div><h4>'+esc(x.title)+'</h4><p>'+esc(x.detail)+'</p></div>').join('')+'</div></div>'
}
function dScene(b){
 return '<figure class="dv-scene"><figcaption><span class="dv-overline">虚构工业案例 / NOT PRODUCTION DATA</span><h3>'+esc(b.question)+'</h3></figcaption><div class="dv-scene-pair"><div><span class="dv-label">你拿到的证据</span><p>'+esc(b.evidence)+'</p><span class="dv-status">已有记录 · 尚无根因报告</span></div><div><span class="dv-label">模型给出的候选结论</span><blockquote>'+esc(b.claim)+'</blockquote><span class="dv-status is-caution">缺少因果证据</span></div></div><div class="dv-scene-verdict">'+esc(b.verdict)+'</div><p class="dv-caption">'+esc(b.caption)+'</p></figure>'
}
function dBars(probabilities,labels){
 return '<div class="dv-bars" aria-label="教学示意概率，非实测">'+Object.entries(probabilities).map(([key,value])=>{const p=Math.max(0,Math.min(1,Number(value)||0));return '<div class="dv-bar"><div><span>'+esc(labels?.[key]||key)+'</span><b>'+p.toFixed(2)+'</b></div><div class="dv-bar-track" aria-hidden="true"><i style="width:'+p*100+'%"></i></div></div>'}).join('')+'</div>'
}
function dDemo(a){
 const d=a.demo;if(!d)return '';
 return '<div class="dv-demo" data-d-tabgroup><div class="dv-demo-head"><span class="dv-status is-caution">'+esc(d.label)+'</span><button type="button" data-d-download>保存请求 JSON</button></div><div class="dv-tabs" role="tablist" aria-label="选择 Jev 原语">'+d.explanations.map((x,i)=>'<button type="button" role="tab" id="dv-tab-'+esc(x.key)+'" data-d-tab="dv-panel-'+esc(x.key)+'" aria-controls="dv-panel-'+esc(x.key)+'" aria-selected="'+(i===0)+'" tabindex="'+(i===0?'0':'-1')+'">'+esc(x.name)+'<small>'+esc(['命题判断','有限单选','等级评分'][i])+'</small></button>').join('')+'</div>'+d.explanations.map((x,i)=>{
 const q=d.request.questions[x.key],out=d.answers[x.key],probs=x.key==='supported'?{'是':out.noul,'否':1-out.noul}:out.probabilities;
 return '<section class="dv-tabpanel" role="tabpanel" id="dv-panel-'+esc(x.key)+'" aria-labelledby="dv-tab-'+esc(x.key)+'"'+(i?' hidden':'')+'><h3>'+esc(x.question)+'</h3><div class="dv-io"><div><span class="dv-overline">INPUT · questions 中的问题</span>'+dRichCode({title:x.key,language:'JSON',code:JSON.stringify({[x.key]:q},null,2)})+'</div><div><span class="dv-overline">OUTPUT · 预设响应摘录</span>'+dRichCode({title:'answers.'+x.key,language:'JSON',code:JSON.stringify(out,null,2)})+dBars(probs)+'</div></div><div class="dv-explain"><strong>怎么读？</strong><p>'+esc(x.meaning)+'</p><strong>下一行代码做什么？</strong><p>'+esc(x.action)+'</p><p class="dv-trap">'+esc(x.trap)+'</p></div></section>'
 }).join('')+'<details class="dv-details"><summary>展开完整 HTTP 请求：model + state + questions</summary>'+dRichCode({title:'POST /v1/systemone',language:'JSON',code:JSON.stringify(d.request,null,2),caption:'服务端调用；Authorization 使用环境变量中的 Bearer 密钥。不要把密钥写入前端或仓库。'})+'</details><p class="dv-caption">输出只保留解释所需字段；未伪造 confidence、legend、usage、延迟或请求 ID。完整响应字段以官方 API 文档为准。</p></div>'
}
function dImplementation(b){
 const stages=[['输入组织','state + question','同一问题共享前缀'],['候选路径','A / B / C','每条拼接候选语义与 EOS'],['共享 Backbone','hidden states','批量前向，取末有效向量'],['决策头','LayerNorm → Scalar','Choice 可加集合注意力'],['输出映射','概率 → 选择 / 评分','没有长文本解码循环']];
 return '<figure class="dv-figure dv-implementation"><figcaption><span class="dv-overline">源码计算图 / THIRD-PARTY REFERENCE</span><h3>'+esc(b.title)+'</h3></figcaption><div class="dv-token-fan"><span>state + question</span><span aria-hidden="true">↘</span><div><b>前缀 + 候选 A</b><b>前缀 + 候选 B</b><b>前缀 + 候选 C</b></div><span aria-hidden="true">↗</span><span>共享参数<br>批量前向</span></div><ol class="dv-flow" style="--steps:5">'+stages.map((s,i)=>'<li><span class="dv-number">'+(i+1)+'</span><strong>'+s[0]+'</strong><code>'+s[1]+'</code><p>'+s[2]+'</p></li>').join('')+'</ol><p class="dv-caption">'+esc(b.caption)+'</p><div class="dv-reference-note">只解释 NanoJev 参考实现，不代表官方 Jev 采用相同网络。</div></figure>'
}
function dRouter(b){
 return '<figure class="dv-figure dv-router"><figcaption><span class="dv-overline">架构图 / CONDITIONAL ROUTING</span><h3>'+esc(b.title)+'</h3></figcaption><div class="dv-router-top"><strong>事件 / 任务 / 当前状态</strong><span aria-hidden="true">↓</span><b>代码策略编排器</b><small>先问：这一步是什么类型的计算？</small></div><div class="dv-branches">'+[
 ['确定规则','Code','算术、权限、状态机','规则可精确表达，直接运行代码。'],
 ['有界语义','Jev','分类、判断、等级评分','答案空间已知，语义规则难写死。'],
 ['开放任务','LLM','生成、解释、开放推理','需要新文本、代码或探索新答案。'],
 ['需要授权 / 超出边界','Human','高风险、冲突、例外','需要责任主体，或自动路径不适用。']
 ].map((s,i)=>'<div class="dv-branch branch-'+i+'"><span>'+s[0]+'</span><strong>'+s[1]+'</strong><b>'+s[2]+'</b><p>'+s[3]+'</p></div>').join('')+'</div><div class="dv-router-bottom"><span aria-hidden="true">↓</span><strong>结果校验 / 权限 / 必要批准</strong><span aria-hidden="true">↓</span><strong>执行器 → 真实结果 → 状态更新</strong></div><div class="dv-feedback">↺ 失败样本 → 调整问题或策略 → 独立回归测试 → 经审核发布</div><p class="dv-caption">'+esc(b.caption)+'</p></figure>'
}
function dApplications(a){
 const rows=a.applications||[];
 return '<div class="dv-applications" data-d-tabgroup><div class="dv-tabs" role="tablist" aria-label="选择产品方向">'+rows.map((x,i)=>'<button type="button" role="tab" id="dv-app-tab-'+esc(x.id)+'" data-d-tab="dv-app-'+esc(x.id)+'" aria-controls="dv-app-'+esc(x.id)+'" aria-selected="'+(i===0)+'" tabindex="'+(i===0?'0':'-1')+'">'+esc(x.tab)+'</button>').join('')+'</div>'+rows.map((x,i)=>'<section class="dv-tabpanel dv-application" id="dv-app-'+esc(x.id)+'" role="tabpanel" aria-labelledby="dv-app-tab-'+esc(x.id)+'"'+(i?' hidden':'')+'><span class="dv-overline">产品方案 / 待验证 MVP</span><h3>'+esc(x.product)+'</h3><p class="dv-goal">'+esc(x.goal)+'</p><div class="dv-app-io"><div><h4>输入是什么</h4><p>'+esc(x.input)+'</p></div><div><h4>输出是什么</h4><p>'+esc(x.output)+'</p></div></div><p class="dv-primitive-use">'+esc(x.primitives)+'</p>'+dFlow({title:'组件怎么接',nodes:x.steps.map(t=>({title:t})),caption:'集成建议；不能跳过权限检查、错误回退和必要的人工审核。'})+'<dl class="dv-spec"><dt>第一版产品</dt><dd>'+esc(x.mvp)+'</dd><dt>数据从哪来</dt><dd>'+esc(x.data)+'</dd><dt>对照怎么做</dt><dd>'+esc(x.experiment)+'</dd></dl><div class="dv-metrics">'+x.metrics.map(m=>'<span>'+esc(m)+'</span>').join('')+'</div><aside class="dv-note"><strong>最容易踩的坑</strong><p>'+esc(x.boundary)+'</p></aside>'+dRefLinks(a,x.refs)+'</section>').join('')+'</div>'
}
function dExperiment(b){
 return '<figure class="dv-figure dv-experiment"><figcaption><span class="dv-overline">评测设计 / NOT MEASURED RESULTS</span><h3>'+esc(b.title)+'</h3></figcaption><div class="dv-dataset">同一份数据 → 按事件 / 实体 / 时间分组 → 校准集与冻结测试集隔离</div><div class="dv-baselines">'+[
 ['A','大 Prompt + LLM','原始端到端基线'],['B','结构化工作流 + 同一个 LLM','B 对 A：看工作流拆分收益'],['C','相同结构化工作流 + Jev','C 对 B：看模型替换收益'],['D','轻量判别器 / 规则基线','检验是否有更简单的可用方案']
 ].map(s=>'<div><b>'+s[0]+'</b><strong>'+s[1]+'</strong><span>'+s[2]+'</span></div>').join('')+'</div><div class="dv-eval-gate"><strong>同一套真实金标 + 冻结阈值</strong><span>错误代价 · 覆盖率 · 校准 · 端到端延迟 · 完整成本</span><em>本页未进行 Jev 真实推理或性能实测</em></div><p class="dv-caption">'+esc(b.caption)+'</p></figure>'
}
// Narrative figures carry selectable text and reflow instead of shrinking a bitmap.
function dInlineRefs(a,ids=[]){
 const sources=dSourceMap(a);
 return ids.map(id=>sources.get(id)).filter(Boolean).map(s=>'<a class="je-inline-ref" href="'+safeLink(s.url)+'" target="_blank" rel="noopener noreferrer" aria-label="来源 '+s.index+'：'+esc(s.title)+'">['+s.index+']</a>').join(' ')
}
function dEssayFigure(b,body,cls=''){
 return '<figure class="je-figure '+cls+'"><figcaption><strong>'+esc(b.title)+'</strong></figcaption>'+body+(b.caption?'<p class="je-caption">'+esc(b.caption)+'</p>':'')+'</figure>'
}
function dTaskAnatomy(b){
 return dEssayFigure(b,'<div class="je-task-origin">工程师的问题：B17 为什么下降？</div><div class="je-fan">'+[
 ['确定规则','核对 B17 / B18','ID、文档状态、权限','代码与系统记录'],
 ['语义判断','材料能支持断言吗？','Noul / Choice / Score','可替换的判断后端'],
 ['开放生成','怎样把证据讲清楚？','有引用的解释','生成模型'],
 ['行动决策','继续、停止还是复核？','代价、预算与批准','代码策略层']
 ].map((x,i)=>'<div class="je-task-item"><span>0'+(i+1)+' · '+x[0]+'</span><strong>'+x[1]+'</strong><p>'+x[2]+'</p><small>'+x[3]+'</small></div>').join('')+'</div><div class="je-flow-footer">同一个目标，不是同一种计算；这些职责不意味着每次都要调用四个组件。</div>','je-anatomy')
}
function dSignal(a,b){
 const q=a.demo.request.questions[b.key],out=a.demo.answers[b.key],ex=a.demo.explanations.find(x=>x.key===b.key);
 const label=q.type==='noul'?'0.08':q.type==='choice'?'observation':'1.8';
 const detail=q.type==='noul'?'P(材料支持断言)':q.type==='choice'?'观测记录 · 最高概率 0.90':'等级期望 · 非正确率';
 const criteria=q.criteria?(Array.isArray(q.criteria)?q.criteria.map((x,i)=>i+'：'+x):Object.entries(q.criteria).map(([k,v])=>k+'：'+v)):[];
 return dEssayFigure({title:ex.name+' · '+b.title,caption:'同一份 B17 state；仅保留关键输出。全部数值为人为示意，不是模型实测。'},'<div class="je-signal-main"><div><span class="je-kicker">输入的问题</span><p>'+esc(q.instructions)+'</p></div><div class="je-signal-value"><strong>'+esc(label)+'</strong><span>'+detail+'</span></div></div>'+(criteria.length?'<div class="je-criteria">'+criteria.map(x=>'<p>'+esc(x)+'</p>').join('')+'</div>':'')+'<pre class="je-output"><code>'+esc(JSON.stringify({[b.key]:out},null,2))+'</code></pre>','je-signal')
}
function dTensor(b){
 const node=(name,shape,detail)=>'<div class="je-tensor-stage"><span>'+name+'</span><code>'+shape+'</code><p>'+detail+'</p></div>';
 return dEssayFigure(b,'<div class="je-paths"><div><strong>Boolean × 1</strong><span>一条命题语义路径</span></div><div><strong>Choice × 3</strong><span>三种材料类别，各一条</span></div><div><strong>Score × 3</strong><span>三个等级，各一条</span></div></div><div class="je-connector" aria-hidden="true">↓ 合并为 7 条路径，补齐到 Lmax</div>'+node('token IDs','[7, Lmax]','每条含状态、问题、候选与决策位置。')+'<div class="je-connector" aria-hidden="true">↓ 共享参数的 Backbone</div>'+node('hidden states','[7, Lmax, D]','每个有效输入位置都有一个 D 维表示。')+'<div class="je-connector" aria-hidden="true">↓ 按每条真实长度取末端</div>'+node('candidate vectors','[7, D]','取 lengths − 1，而不是补齐位置。')+'<div class="je-connector" aria-hidden="true">↓ 按问题分组 → 评分头 → 有效候选掩码</div><div class="je-paths"><div><strong>[0, z]</strong><span>Boolean → 二元概率</span></div><div><strong>[z₀, z₁, z₂]</strong><span>Choice → 类别分布</span></div><div><strong>[z₀, z₁, z₂]</strong><span>Score → 等级分布与期望</span></div></div>','je-tensor')
}
function dDistribution(b){
 return dEssayFigure(b,'<div class="je-distributions">'+b.series.map((s,index)=>'<div><h4>'+esc(s.name)+'</h4><div class="je-distribution-bars">'+s.probabilities.map((v,i)=>'<div><strong>'+Number(v).toFixed(1)+'</strong><div class="je-column-track"><i style="height:'+Number(v)*100+'%"></i></div><span>等级 '+i+'</span></div>').join('')+'</div><p>期望 <b>1.0</b> · 方差 <b>'+index.toFixed(1)+'</b></p></div>').join('')+'</div>','je-distribution')
}
function dCaseUpdate(b){
 return '<aside class="je-case-update"><div><span>案例 '+esc(b.stage)+'</span><strong>'+esc(b.title)+'</strong></div><dl><dt>新材料 / 请求</dt><dd>'+esc(b.evidence)+'</dd><dt>改变了什么</dt><dd>'+esc(b.change)+'</dd><dt>处理边界</dt><dd>'+esc(b.decision)+'</dd></dl><small>虚构情境 · 用于推导，不是实测轨迹</small></aside>'
}
function dKnowledgeFlow(b){
 return dEssayFigure(b,'<ol class="je-swimlane"><li><span class="je-owner">输入</span><div><strong>问题 + 候选断言 + 当前状态</strong><p>B17 / ETCH-03；请求是只读，还是写操作？</p></div></li><li><span class="je-owner">检索器</span><div><strong>取回候选证据及系统元数据</strong><p>正文、批次、有效版本、来源 ID；不让模型编造出处。</p></div></li><li><span class="je-owner">代码</span><div><strong>硬约束先行</strong><p>匹配实体与有效范围；D2 的 B18 ≠ B17，排除。</p></div></li><li><span class="je-owner semantic">判断后端</span><div><strong>Jev / 其他判别模型</strong><p>证据支持、材料形态、语义冲突；只返回信号。</p></div></li><li><span class="je-owner">策略层</span><div><strong>决定状态转移</strong><div class="je-outcomes"><span>证据不足 → 有界补检索 ↺</span><span>有效材料冲突 → 人工复核</span><span>满足只读规则 → 引用式草稿</span><span>写入请求 → 独立审批通道</span></div></div></li><li><span class="je-owner">输出层</span><div><strong>生成解释 → 逐断言检查 → 返回出处</strong><p>超预算或异常就停止；写操作另走授权执行器与结果验收。</p></div></li></ol><div class="je-feedback">日志保留证据版本、判断值、策略版本与真实结果；反馈先进入回归测试，不自动训练模型。</div>','je-knowledge')
}
function dEssayTable(b){
 return dEssayFigure(b,'<table class="je-table"><thead><tr>'+b.headers.map(x=>'<th scope="col">'+esc(x)+'</th>').join('')+'</tr></thead><tbody>'+b.rows.map(row=>'<tr>'+row.map((x,i)=>i===0?'<th scope="row">'+esc(x)+'</th>':'<td data-label="'+esc(b.headers[i])+'">'+esc(x)+'</td>').join('')+'</tr>').join('')+'</tbody></table>')
}
function dEssayResources(b){
 return '<div class="je-resources"><h3>'+esc(b.title)+'</h3><p>正文说明输入、计算与策略。完整协议和四类产品方案可在前文按需展开；下面的脚本均可离线运行，不代表完成真实模型评测。</p>'+[
 ['jev_knowledge_demo.py','接口样例 · 默认离线，显式 --live 才调用付费 API'],
 ['decision_policy.py','策略示例 · 四个虚构阶段与拒绝分支，不执行工具']
 ].map(([file,label])=>'<a href="https://github.com/momo-hub-learn/frontierlog/blob/main/examples/jev/'+file+'" target="_blank" rel="noopener noreferrer"><code>'+file+'</code><span>'+label+'</span><b aria-hidden="true">↗</b></a>').join('')+'</div>'
}

function dRichBlock(a,b){
 switch(b.type){
 case 'text':return '<p class="dv-text">'+esc(b.text)+' '+dInlineRefs(a,b.refs)+'</p>';
 case 'subheading':return '<h3 class="je-subheading"'+(b.anchor?' id="deep-'+esc(b.anchor)+'"':'')+'>'+esc(b.title)+'</h3>';
 case 'transition':return '<p class="je-transition">'+esc(b.text)+'</p>';
 case 'task_anatomy':return dTaskAnatomy(b);
 case 'signal':return dSignal(a,b);
 case 'tensor':return dTensor(b);
 case 'math':return dEssayFigure(b,'<div class="je-equations">'+b.lines.map(x=>'<code>'+esc(x)+'</code>').join('')+'</div>','je-math');
 case 'distribution':return dDistribution(b);
 case 'case_update':return dCaseUpdate(b);
 case 'knowledge_flow':return dKnowledgeFlow(b);
 case 'table':return dEssayTable(b);
 case 'resources':return dEssayResources(b);
 case 'note':return '<aside class="dv-note"><strong>'+esc(b.title)+'</strong><p>'+esc(b.text)+'</p></aside>';
 case 'scene':return dScene(b);
 case 'flow':return dFlow(b);
 case 'cards':return dRichCards(b);
 case 'code':return dRichCode(b);
 case 'demo':return a.layout==='narrative'?'<details class="je-protocol"><summary>按需查看：完整请求、响应摘录与 JSON 下载</summary>'+dDemo(a)+'</details>':dDemo(a);
 case 'implementation':return dImplementation(b);
 case 'router':return dRouter(b);
 case 'applications':return dApplications(a);
 case 'experiment':return dExperiment(b);
 default:return '';
 }
}

function dSection(a,s){
 const evidence=s.analysis?(a.layout==='narrative'?'':'<span class="d-analysis">含 AI坐标分析</span>'):'';
 const paragraphs=(s.paragraphs||[]).map((p,i)=>'<p'+(i===0?' class="d-section-lead"':'')+'>'+esc(p)+'</p>').join('');
 return '<section class="d-section '+(s.key==='boundary'?'is-ending':'')+'" id="deep-'+esc(s.key)+'">'+
  '<header class="d-section-head"><div><span class="d-section-no">'+esc(s.eyebrow)+'</span>'+(s.kicker?'<span class="d-section-kicker">'+esc(s.kicker)+'</span>':'')+'</div>'+evidence+'</header>'+
  '<h2>'+esc(s.title)+'</h2>'+
  (s.blocks?s.blocks.map(b=>dRichBlock(a,b)+(b.type!=='text'?dRefLinks(a,b.refs):'')).join(''):paragraphs)+
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
 return '<section class="d-sources" id="deep-sources"><div class="d-sources-head"><div><p class="eyebrow">SOURCES / EVIDENCE</p><h2>原始资料与参考代码</h2></div><span>核对 '+esc(a.updated||DEEP.checked||a.published)+'</span></div><div class="d-source-grid">'+
 (a.sources||[]).map((s,i)=>'<a href="'+safeLink(s.url)+'" target="_blank" rel="noopener noreferrer"><b>['+(i+1)+']</b><span><strong>'+esc(s.publisher)+'</strong><em>'+esc(s.kind)+' · '+esc((s.date?'发布 '+s.date+' · ':'')+'核对 '+(s.verified_at||a.updated||DEEP.checked))+'</em><small>'+esc(s.title)+'</small></span>'+icon('external')+'</a>').join('')+
 '</div></section>'
}
function dPage(a){
 if(!a)return '<div class="d-empty">暂无深度解析。</div>';
 return '<article class="d-page'+(a.demo?' d-visual':'')+(a.layout==='narrative'?' d-narrative':'')+'">'+
  '<header class="d-hero">'+
   '<div class="d-hero-top"><span class="d-series">拆一下</span><span>'+esc(a.published.replaceAll('-','.'))+(a.updated?' · 更新 '+esc(a.updated.replaceAll('-','.')):'')+'</span><span>'+esc(String(a.read_minutes))+' min read</span></div>'+
   '<div class="d-hero-grid"><div class="d-hero-copy">'+
    '<h1>'+esc(a.title)+'</h1><p class="d-dek">'+esc(a.dek)+'</p>'+
    '<div class="d-tagline">'+a.tags.map(t=>'<span>'+esc(t)+'</span>').join('')+'</div>'+
   '</div><blockquote class="d-thesis"><span>核心判断</span><strong>'+esc(a.thesis)+'</strong></blockquote></div>'+
  '</header>'+
  (a.layout==='narrative'?'<div class="je-reading-path" aria-label="本文推导路线">问题 <span>→</span> 接口 <span>→</span> 计算 <span>→</span> 概率 <span>→</span> 系统 <span>→</span> 验证</div>':'')+'<div class="d-reading-shell">'+dToc(a)+'<div class="d-article">'+dOpening(a)+a.sections.map(s=>dSection(a,s)).join('')+dSources(a)+'</div></div>'+
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
 e.preventDefault();target.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'})
});

const dBaseRelatedCards=hRelatedCards;
hRelatedCards=function(x){
 const base=dBaseRelatedCards(x);
 const a=(DEEP.articles||[]).find(a=>(a.hot_ids||[]).includes(x.id));
 if(!a)return base;
 return base+'<section class="h-detail-panel d-hot-deep"><div class="h-detail-panel-head"><span>进一步理解</span><small>拆一下</small></div><a href="#/deep?id='+encodeURIComponent(a.id)+'" onclick="document.getElementById(\'modal\').close();document.body.style.overflow=\'\'"><span class="d-hot-deep-mark">'+icon('layers')+'</span><span><strong>'+esc(a.short_title||a.title)+'</strong><small>'+esc(String(a.read_minutes))+' min · 架构解析</small></span>'+icon('arrow')+'</a></section>'
};

// Delegation survives route re-renders; no inline code or remote execution.
document.addEventListener('click',async e=>{
 const tab=e.target.closest('[data-d-tab]');
 if(tab){
  const group=tab.closest('[data-d-tabgroup]');
  group.querySelectorAll('[role="tab"]').forEach(x=>{const active=x===tab;x.setAttribute('aria-selected',String(active));x.tabIndex=active?0:-1});
  group.querySelectorAll('[role="tabpanel"]').forEach(x=>{x.hidden=x.id!==tab.dataset.dTab});
  return;
 }
 const copy=e.target.closest('[data-d-copy]');
 if(copy){
  const code=copy.closest('.dv-code').querySelector('code');
  try{await navigator.clipboard.writeText(code.textContent);copy.textContent='已复制'}
  catch(_){const range=document.createRange();range.selectNodeContents(code);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);copy.textContent='已选中，请复制'}
  setTimeout(()=>{if(copy.isConnected)copy.textContent='复制代码'},2000);return;
 }
 const save=e.target.closest('[data-d-download]');
 if(save){
  const request=dCurrent()?.demo?.request;if(!request)return;
  const url=URL.createObjectURL(new Blob([JSON.stringify(request,null,2)+'\n'],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download='jev-request.example.json';document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
});
document.addEventListener('keydown',e=>{
 const tab=e.target.closest('[role="tab"][data-d-tab]');if(!tab)return;
 const keys=['ArrowLeft','ArrowRight','Home','End'];if(!keys.includes(e.key))return;
 const tabs=[...tab.closest('[role="tablist"]').querySelectorAll('[role="tab"]')];let i=tabs.indexOf(tab);
 if(e.key==='Home')i=0;else if(e.key==='End')i=tabs.length-1;else i=(i+(e.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
 e.preventDefault();tabs[i].focus();tabs[i].click();
});

let dPrintDetails=[];
window.addEventListener('beforeprint',()=>{dPrintDetails=[...document.querySelectorAll('.d-narrative details:not([open])')];dPrintDetails.forEach(x=>x.open=true)});
window.addEventListener('afterprint',()=>{dPrintDetails.forEach(x=>{if(x.isConnected)x.open=false});dPrintDetails=[]});
if(location.hash.startsWith('#/deep'))parseRoute();
else if(state.view==='feed'){lastMain='';renderMain()}
})();