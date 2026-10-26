'use strict';
// Exercise actual render functions and shared filtering; do not change source data.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..'),read=name=>fs.readFileSync(path.join(root,name),'utf8');
const models=JSON.parse(read('data/models.json')),original=JSON.stringify(models),arena=models.boards.find(board=>board.id==='arena');
const ctx={APP:{models,resets:{}},window:{},URLSearchParams,URL,Date,console,readStore:()=>[],
 location:{hash:'#/models?board=arena'},modelHubTabs:()=>'<nav>Capabilities</nav>',
 esc:v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
 safeLink:v=>{try{const u=new URL(v);return u.protocol==='https:'&&!u.username&&!u.password?u.href:'#'}catch{return'#'}},
 icon:()=>'<svg aria-hidden="true"></svg>'};
vm.createContext(ctx);
const shared=read('src/models.js'),companies=read('src/v2.js'),source=read('src/product-v3.js');
vm.runInContext(shared.slice(0,shared.indexOf('function mFrontierTrackState')),ctx);
vm.runInContext(companies.slice(companies.indexOf('const MODEL_COMPANIES='),companies.indexOf('const ACTIVITY_RADAR=')),ctx);
vm.runInContext(source.slice(source.indexOf('const companyRows='),source.indexOf('Object.assign(PATHS,'))+'\nthis.api={page:arenaPage,score:arenaScore,range:arenaRange,date:arenaDate,name:arenaName,company:linkedModelCompany,decorate:decorateBaseModelCompanies,saved:msaved,compare:modelCompare};',ctx);
const api=ctx.api,render=query=>{ctx.location.hash='#/models?board=arena'+query;return api.page()};
let count=0;
function check(name,fn){fn();count++;console.log('PASS',name)}
check('single company column and seven semantic table headers',()=>{
 const html=render('');assert.equal((html.match(/<th scope=/g)||[]).length,7);assert.equal((html.match(/>公司<\/th>/g)||[]).length,1);
 assert.equal((html.match(/data-model-row=/g)||[]).length,arena.rows.length);assert(!html.includes('来源日期</th>'));
});
check('official ranks are preserved, including gaps and equal scores',()=>{
 const html=render(''),ranks=Array.from(html.matchAll(/<td class="ar-rank">(.*?)<\/td>/g),x=>Number(x[1]));
 assert.deepEqual(ranks,arena.rows.map(row=>row.source_rank));assert(!html.includes('#1 当前样本'));
});
check('maker filtering retains source ranks rather than manufacturing #1',()=>{
 const maker=arena.rows.some(row=>row.maker==='OpenAI')?'OpenAI':arena.rows.at(-1).maker;
 const selected=arena.rows.filter(row=>row.maker===maker),html=render('&maker='+encodeURIComponent(maker));
 assert.equal((html.match(/data-model-row=/g)||[]).length,selected.length);assert(html.includes('<td class="ar-rank">'+selected[0].source_rank+'</td>'));
 assert.equal(html.includes('class="ar-leading"'),selected.some(row=>row.source_rank===1));assert(html.includes('显示 '+selected.length+' / '+arena.rows.length+' 条'));assert(html.includes('非完整榜'));
});
check('search and saved-only filtering share the real model state',()=>{
 api.saved.add(arena.rows[0].id);assert(render('&stars=1').includes('显示 1 / '+arena.rows.length+' 条'));api.saved.clear();
 assert(render('&q=not-a-model').includes('没有匹配的模型'));
 const claude=arena.rows.filter(row=>(row.name+' '+row.maker).toLowerCase().includes('claude')).length;
 assert(render('&q=Claude').includes('显示 '+claude+' / '+arena.rows.length+' 条'));
});
check('provenance has separate original/verified dates and honest coverage',()=>{
 const html=render('');assert(html.includes('最近核验 <time datetime="'+arena.checked+'"'));assert(html.includes('来源日期 <time datetime="'+arena.as_of+'"'));
 assert(html.includes('人工摘录 '+arena.rows.length+' 条 · 非完整榜'));assert(!html.includes('实时全量'));
});
check('missing uncertainty and dates are not manufactured',()=>{
 assert(api.score({preference:0,score_error:0}).includes('± 0'));assert(api.score({preference:null}).includes('误差未提供'));assert(!api.score({}).includes('± 0'));
 assert.equal(api.range({}),'—');assert.equal(api.date(null),'待核验');assert.equal(api.date('2026-02-30'),'待核验');
});
check('company metadata links use the official registry and preserve maker names',()=>{
 const html=api.company({maker:'OpenAI'});assert(html.includes('https://openai.com/'));assert(html.includes('m-company-logo'));assert(html.includes('OpenAI'));
 assert(api.company({maker:'Moonshot'}).includes('https://www.kimi.com/'));assert(!api.company({maker:'unknown'}).includes('<a'));
});
check('HTML inputs, model names and company names are escaped',()=>{
 assert(render('&q='+encodeURIComponent('<img onerror=alert(1)>')).includes('&lt;img'));assert(!api.name({id:'x',name:'<script>x</script>'}).includes('<script>'));
 assert(!api.company({maker:'<img src=x>'}).includes('<img src=x>'));
});
check('preliminary source flag and source score precision survive rendering',()=>{
 assert(api.name({id:'x',name:'candidate',preliminary:true}).includes('初步结果'));assert(!api.name({id:'x',name:'candidate'}).includes('Preliminary'));
 assert(api.score({preference:1506,score_error:5}).includes('<strong>1,506</strong>'));
});
check('table and mobile view expose the same records and unique search controls',()=>{
 const html=render('');assert.equal((html.match(/data-ar-model=/g)||[]).length,8);assert.equal((html.match(/id="m-search"/g)||[]).length,1);
 assert(!html.includes('输出 tok/s'));assert(!html.includes('USD / task'));assert(!html.includes('BASE MODELS'));
});
check('source switch names two independent boards without inventing a combined score',()=>{
 const html=render('');assert(html.includes('综合能力主榜'));assert(html.includes('人类偏好榜'));
 assert(html.includes('两张独立榜单 · 不合成本站总分'));assert(html.includes('aria-label="选择独立榜单"'));
});
check('company decorator is idempotent and never reads score metadata',()=>{
 render('');let writes=0;const cell={set innerHTML(s){writes++;assert(s.includes('Anthropic'));assert(!s.includes('±'))}};
 const row={dataset:{modelRow:'arena-1'},querySelector:selector=>{assert.equal(selector,'.m-company-cell');return cell}};
 const table={dataset:{},querySelectorAll:selector=>{assert.equal(selector,'tbody tr[data-model-row]');return[row]}};
 ctx.document={querySelectorAll:()=>[table]};api.decorate();api.decorate();assert.equal(writes,1);assert.equal(table.dataset.companyColumn,'1');
});
check('all model data remain unchanged after filtering and rendering',()=>assert.equal(JSON.stringify(models),original));
console.log(`Arena browser: ${count} behavioral checks passed.`);
