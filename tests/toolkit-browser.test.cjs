'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(root,'data/toolkit.json')));
const catalog=JSON.parse(fs.readFileSync(path.join(root,'data/catalog.json')));
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ctx={APP:{toolkit:data},tasks:new Map(catalog.items.map(t=>[t.id,t])),saved:new Set(),checks:{},URLSearchParams,console,
 location:{hash:'#/toolkit'},document:{addEventListener(){}},state:{view:'feed'},renderMain(){},renderTask(){},exportView(){},
 esc,safeLink:esc,icon:()=>'<svg></svg>',navigator:{clipboard:{async writeText(s){ctx.copied=s}}}};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(root,'src/toolkit.js'),'utf8')+'\nthis.tk=TK;',ctx);
const tk=ctx.tk,total=data.items.length;let tests=0;function test(name,fn){fn();tests++;console.log('PASS',name)}
const read=q=>tk.read('#/toolkit'+(q?'?'+q:''));
const ids=r=>Array.from(r,g=>g.id);
const latest=g=>g.sources.map(x=>x.published_at||x.verified_at||'').filter(Boolean).sort().at(-1)||g.verified_at.slice(0,10);
const recent=rows=>[...rows].sort((a,b)=>latest(b).localeCompare(latest(a))||data.items.indexOf(a)-data.items.indexOf(b));
test('default and invalid facets',()=>{assert.equal(tk.rows(read('')).length,total);assert.equal(read('group=bad&access=bad&sort=bad').group,'all');assert.equal(read('group=bad&access=bad&sort=bad').access,'all');assert.equal(read('group=bad&access=bad&sort=bad').sort,'recent')});
test('recent is the honest default and curated order remains available',()=>{assert.deepEqual(ids(tk.rows(read(''))),ids(recent(data.items)));assert.deepEqual(ids(tk.rows(read('sort=curated'))),ids(data.items))});
test('all five task categories are effective',()=>{for(const g of data.groups)assert.equal(tk.rows(read('group='+g.id)).length,data.items.filter(x=>x.group===g.id).length)});
test('usage filter is independent of task filter',()=>{
 for(const [group,access] of [['documents','local'],['audio','web']]){
  const expected=recent(data.items.filter(x=>x.group===group&&x.access===access)).map(x=>x.id);
  assert.deepEqual(ids(tk.rows(read(`group=${group}&access=${access}`))),expected)
 }
});
test('publisher and input/output search',()=>{
 const pdfExpected=recent(data.items.filter(g=>{const t=ctx.tasks.get(g.id);return [t.name,g.publisher,g.headline,g.input,g.output,data.groups.find(x=>x.id===g.group)?.label].join(' ').toLocaleLowerCase().includes('pdf')})).map(x=>x.id);
 assert.deepEqual(ids(tk.rows(read('q=PDF'))),pdfExpected);
 const expected=recent(data.items.filter(g=>{const t=ctx.tasks.get(g.id);return [t.name,g.publisher,g.headline,g.input,g.output,data.groups.find(x=>x.id===g.group)?.label].join(' ').toLocaleLowerCase().includes('openai')})).map(x=>x.id);
 assert.deepEqual(new Set(ids(tk.rows(read('q=OPENAI')))),new Set(expected));
 assert.deepEqual(ids(tk.rows(read('q=字幕'))),['whisper'])
});
test('whitespace and 300 character query bound',()=>{assert.equal(tk.rows(read('q=%20%20')).length,total);assert.equal(read('q='+'x'.repeat(400)).q.length,300)});
test('bookmarks use shared catalogue IDs',()=>{ctx.saved.add('docling');assert.deepEqual(ids(tk.rows(read('saved=1'))),['docling']);ctx.saved.clear();assert.equal(tk.rows(read('saved=1')).length,0)});
test('route serialization retains independent filters',()=>{const s=read('group=audio&access=local&sort=curated&q=录音&saved=1');const next=tk.read(tk.href(s,{access:'all'}));assert.equal(next.group,'audio');assert.equal(next.access,'all');assert.equal(next.sort,'curated');assert.equal(next.q,'录音');assert.equal(next.only,true)});
test('legacy task route identifies guide not old modal',()=>{assert.equal(read('task=docling&tab=run').tool,'docling');assert.equal(read('tool=not-real').tool,'')});
test('true publisher no arbitrary fallback',()=>{const html=tk.card(data.items.find(x=>x.id==='chatgpt-voice-work'));assert(html.includes('OpenAI'));assert(!html.includes('Google DeepMind'))});
test('duplicate source and entry links collapse to one action',()=>{
 const same=tk.card(data.items.find(x=>x.id==='openai-decisions-api'));
 const actions=same.match(/<div class="tk-actions">([\s\S]*?)<\/div>/)[1];
 assert.equal((actions.match(/openai\.com\/index\/decisions-api\//g)||[]).length,1);
 assert(!actions.includes('打开入口'));
 const distinct=tk.card(data.items.find(x=>x.id==='microsoft-flint-interactive'));
 assert(distinct.includes('官方上手文档'));assert(distinct.includes('打开入口'));
});
test('repeated visible actions have tool-specific accessible names',()=>{
 const html=tk.card(data.items.find(x=>x.id==='microsoft-flint-interactive'));
 assert(html.includes('aria-label="Microsoft Flint · Interactive 官方上手文档（新窗口打开）"'));
 assert(html.includes('aria-label="Microsoft Flint · Interactive 打开入口（新窗口打开）"'));
 assert(html.includes('aria-label="Microsoft Flint · Interactive：'));
});
test('complete commands, not fake run/copy buttons',()=>{const html=tk.card(data.items.find(x=>x.id==='docling'));assert(html.includes('docling ./sample.pdf'));assert(html.includes('data-tk-copy="1"'));assert(!html.includes('data-action="run"'));assert(html.includes('运行未实测'))});
test('cards escape editorial strings and never create fake proof',()=>{const row={...data.items.find(x=>x.id==='docling'),headline:'<img src=x onerror=alert(1)>'};const html=tk.card(row);assert(!html.includes('<img src=x'));assert(html.includes('&lt;img'));assert(html.includes('data-check-task="docling"'));assert(html.includes('资料核验'))});
(async()=>{
 const g=data.items.find(x=>x.id==='docling'),status={textContent:''};let focused=false;
 const b={dataset:{tkTool:g.id,tkCopy:'1'},closest:()=>({querySelector:()=>status}),focus(){focused=true}};
 await tk.copy(b);test('clipboard gets whole multiline command',()=>{assert.equal(ctx.copied,g.steps[1].command);assert.equal(status.textContent,'已复制这一整段命令。');assert.equal(b.disabled,false);assert(focused)});
 ctx.navigator.clipboard.writeText=async()=>{throw new Error('denied')};await tk.copy(b);
 test('denied clipboard never reports success',()=>{assert(status.textContent.includes('未能访问剪贴板'));assert.equal(b.disabled,false)});
 console.log(`${tests} toolkit behavior checks passed`);
})().catch(e=>{console.error(e);process.exitCode=1});
