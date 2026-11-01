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

const hfChangeContext={
  HF:{
    web_rank_changes:[
      {id:'org/new-model',rank:20,previous_rank:null,rank_change:null,previous_fetched_at:'2026-11-01T07:21:47Z'},
      {id:'org/moved-model',rank:3,previous_rank:4,rank_change:1,previous_fetched_at:'2026-11-01T07:21:47Z'}
    ],
    web_outgoing:[{id:'org/old-model',previous_rank:19,previous_fetched_at:'2026-11-01T07:21:47Z'}]
  },
  esc:x=>String(x),safeLink:x=>x
};
vm.createContext(hfChangeContext);
vm.runInContext(functionBlock(hf,'hfChangeSummary','hfRows')+'\nthis.result=hfChangeSummary()',hfChangeContext);
assert.match(hfChangeContext.result,/新 #20.*org\/new-model/);
assert.match(hfChangeContext.result,/<b>1<\/b> 位次变化/);
assert.match(hfChangeContext.result,/离 #19.*org\/old-model/);
assert.doesNotMatch(hfChangeContext.result,/<details>/);

const gh=fs.readFileSync(path.join(ROOT,'src/github-hot.js'),'utf8');
const ghContext={Intl,Date,GH:{checked_at:'2026-10-22T00:30:00Z'}};
vm.createContext(ghContext);
vm.runInContext(functionBlock(gh,'ghMoment','ghFreshness')+'\nthis.result=ghWhen()',ghContext);
assert.match(ghContext.result,/10\.22.*08:30.*北京时间/);

console.log('PASS Trending timestamps and one-glance HF change evidence');
