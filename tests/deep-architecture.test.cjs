'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(root,'data/deep-dives.json'),'utf8'));
const js=fs.readFileSync(path.join(root,'src/deep-dives.js'),'utf8');
const start=js.indexOf('function dSystemArchitecture(');
const end=js.indexOf('function dFlow(',start);
assert(start>0&&end>start);
const ctx={esc:x=>String(x).replaceAll('&','&amp;').replaceAll('<','&lt;')};
vm.runInNewContext(js.slice(start,end)+'\nthis.render=dSystemArchitecture;',ctx);
for(const a of data.articles){
 const diagrams=a.sections.flatMap(s=>s.blocks).filter(b=>b.type==='architecture');
 assert(diagrams.length>=1,a.id+' needs a real architecture diagram');
 assert(a.sections.length>=7,a.id+' must provide a deep engineering narrative');
 for(const block of diagrams){
  const g=block.diagram;const ids=new Set(g.nodes.map(n=>n.id));
  assert.equal(ids.size,g.nodes.length);
  for(const e of g.edges){assert(ids.has(e.from)&&ids.has(e.to),'dangling architecture edge');}
  assert(block.refs.length>=2,'architecture must cite primary sources');
  assert(g.boundary.includes('不')||g.boundary.includes('并非'),'editorial reconstruction requires a boundary');
  const html=ctx.render(a,block);
  assert.match(html,/<svg viewBox=/);
  assert.match(html,/TECHNICAL BLUEPRINT/);
  assert.match(html,/证据边界/);
  assert.match(html,/marker-end=/);
  assert.match(html,/aria-label=/);
 }
}
const rea=data.articles.find(a=>a.id==='rea-agent-reverse-engineering');
assert(rea.sections.some(s=>s.key==='ledger'&&s.blocks.some(b=>b.type==='code')));
assert(rea.sections.some(s=>s.key==='failure-modes'&&s.blocks.some(b=>b.type==='table')));
const jev=data.articles.find(a=>a.id==='jev-agent-decision-layer');
assert(jev.sections.some(s=>s.key==='ops'&&s.blocks.some(b=>b.type==='code')));
console.log('PASS cited REA/Jev vector architectures with controls, evidence, and engineering depth');
