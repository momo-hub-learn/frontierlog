'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ROOT=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(ROOT,'src/hot.js'),'utf8');
const hot=JSON.parse(fs.readFileSync(path.join(ROOT,'data/hot.json'),'utf8'));

function extract(start,end){
 const a=source.indexOf(start),b=source.indexOf(end,a+start.length);
 assert(a>=0&&b>a,{start,end});
 return source.slice(a,b);
}
const part=extract('function hAccessRows(x){','function hPrimaryCta(r){');
const ctx={
 esc:s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])),
 safeLink:s=>String(s),
 icon:()=>'<svg></svg>'
};
vm.createContext(ctx);
vm.runInContext(part+'\nthis.renderAccess=hAccessCards;',ctx);

const transcribe=hot.items.find(x=>x.id==='nvidia-nemotron-3-5-transcribe-20261028');
assert(transcribe);
const internal=ctx.renderAccess(transcribe);
assert.match(internal,/打开站内分项验收指南/);
assert.match(internal,/当前提供站内核验路径与官方资料/);
assert.doesNotMatch(internal,/当前没有独立可体验入口/);

const docsOnly=ctx.renderAccess({source:'Official',source_kind:'官方材料',url:'https://example.com'});
assert.match(docsOnly,/当前没有独立可体验入口/);

const runnable=ctx.renderAccess({source:'Official',source_kind:'官方入口',url:'https://example.com',access:[{label:'立即试用',note:'公开入口',url:'https://example.com/try',kind:'try'}]});
assert.doesNotMatch(runnable,/h-access-status/);

console.log('3 hot access-state contracts passed');
