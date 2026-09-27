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
const tk=ctx.tk;let tests=0;function test(name,fn){fn();tests++;console.log('PASS',name)}
const read=q=>tk.read('#/toolkit'+(q?'?'+q:''));
const ids=r=>Array.from(r,g=>g.id);
test('default and invalid facets',()=>{assert.equal(tk.rows(read('')).length,10);assert.equal(read('group=bad&access=bad').group,'all');assert.equal(read('group=bad&access=bad').access,'all')});
test('all five task categories are effective',()=>{for(const g of data.groups)assert.equal(tk.rows(read('group='+g.id)).length,2)});
test('usage filter is independent of task filter',()=>{assert.deepEqual(ids(tk.rows(read('group=documents&access=local'))),['docling']);assert.deepEqual(ids(tk.rows(read('group=audio&access=web'))),['gemini-38-flash-tts'])});
test('publisher and input/output search',()=>{assert.deepEqual(ids(tk.rows(read('q=PDF'))),['docling']);assert.deepEqual(ids(tk.rows(read('q=OPENAI'))),['whisper','chatgpt-voice-work']);assert.deepEqual(ids(tk.rows(read('q=字幕'))),['whisper'])});
test('whitespace and 300 character query bound',()=>{assert.equal(tk.rows(read('q=%20%20')).length,10);assert.equal(read('q='+'x'.repeat(400)).q.length,300)});
test('bookmarks use shared catalogue IDs',()=>{ctx.saved.add('docling');assert.deepEqual(ids(tk.rows(read('saved=1'))),['docling']);ctx.saved.clear();assert.equal(tk.rows(read('saved=1')).length,0)});
test('route serialization retains independent filters',()=>{const s=read('group=audio&access=local&q=录音&saved=1');const next=tk.read(tk.href(s,{access:'all'}));assert.equal(next.group,'audio');assert.equal(next.access,'all');assert.equal(next.q,'录音');assert.equal(next.only,true)});
test('legacy task route identifies guide not old modal',()=>{assert.equal(read('task=docling&tab=run').tool,'docling');assert.equal(read('tool=not-real').tool,'')});
test('true publisher no arbitrary fallback',()=>{const html=tk.card(data.items.find(x=>x.id==='chatgpt-voice-work'));assert(html.includes('OpenAI'));assert(!html.includes('Google DeepMind'))});
test('complete commands, not fake run/copy buttons',()=>{const html=tk.card(data.items[0]);assert(html.includes('docling ./sample.pdf'));assert(html.includes('data-tk-copy="1"'));assert(!html.includes('data-action="run"'));assert(html.includes('运行未实测'))});
test('cards escape editorial strings and never create fake proof',()=>{const row={...data.items[0],headline:'<img src=x onerror=alert(1)>'};const html=tk.card(row);assert(!html.includes('<img src=x'));assert(html.includes('&lt;img'));assert(html.includes('data-check-task="docling"'));assert(html.includes('资料核验'))});
(async()=>{
 const g=data.items[0],status={textContent:''};let focused=false;
 const b={dataset:{tkTool:g.id,tkCopy:'1'},closest:()=>({querySelector:()=>status}),focus(){focused=true}};
 await tk.copy(b);test('clipboard gets whole multiline command',()=>{assert.equal(ctx.copied,g.steps[1].command);assert.equal(status.textContent,'已复制这一整段命令。');assert.equal(b.disabled,false);assert(focused)});
 ctx.navigator.clipboard.writeText=async()=>{throw new Error('denied')};await tk.copy(b);
 test('denied clipboard never reports success',()=>{assert(status.textContent.includes('未能访问剪贴板'));assert.equal(b.disabled,false)});
 console.log(`${tests} toolkit behavior checks passed`);
})().catch(e=>{console.error(e);process.exitCode=1});
