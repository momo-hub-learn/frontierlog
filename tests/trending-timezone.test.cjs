'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ROOT=path.resolve(__dirname,'..');

function functionBlock(source,name,next){
  const start=source.indexOf('function '+name+'(');
  const end=source.indexOf('function '+next+'(',start+1);
  assert(start>=0&&end>start,{name,next});
  return source.slice(start,end);
}

const hf=fs.readFileSync(path.join(ROOT,'src/huggingface-hot.js'),'utf8');
const hfContext={Intl,Date};
vm.createContext(hfContext);
vm.runInContext(functionBlock(hf,'hfWhen','hfAge')+"\nthis.result=hfWhen('2026-10-22T00:30:00Z')",hfContext);
assert.match(hfContext.result,/10\.22.*08:30.*北京时间/);

const gh=fs.readFileSync(path.join(ROOT,'src/github-hot.js'),'utf8');
const ghContext={Intl,Date,GH:{checked_at:'2026-10-22T00:30:00Z'}};
vm.createContext(ghContext);
vm.runInContext(functionBlock(gh,'ghWhen','ghFreshness')+'\nthis.result=ghWhen()',ghContext);
assert.match(ghContext.result,/10\.22.*08:30.*北京时间/);

console.log('PASS Trending timestamps use explicit Asia/Shanghai semantics');
