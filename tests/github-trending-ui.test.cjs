'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ROOT=path.resolve(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(ROOT,'data/github-hot.json'),'utf8'));
const hfData=JSON.parse(fs.readFileSync(path.join(ROOT,'data/huggingface-hot.json'),'utf8'));
const gh=fs.readFileSync(path.join(ROOT,'src/github-hot.js'),'utf8');
const cockpit=fs.readFileSync(path.join(ROOT,'src/feed-cockpit.js'),'utf8');

function extract(s,start,end){
 const a=s.indexOf(start),b=s.indexOf(end,a+start.length);
 assert(a>=0&&b>a,{start,end});
 return s.slice(a,b);
}
const watchPart=extract(gh,'function ghWatchPanel(){','function ghActive(){');
const metadataPart=extract(gh,'function ghFmt(n){','function ghWhen(){');
const partialPart=extract(gh,'function ghPartialNotice(){','function ghWatchPanel(){');
const inlinePart=extract(gh,'function ghInline(){','const ghBaseHotPage=hotPage;');
const pagePart=extract(gh,'const ghBaseHotPage=hotPage;','document.addEventListener(\'input\'');
const app={
 GH:data,ghQuery:()=>'',ghTopic:()=> 'all',
 ghFreshness:()=>({stale:true}),ghFmt:v=>String(v),
 icon:()=>'',safeLink:x=>x,esc:x=>String(x)
};
vm.createContext(app);
vm.runInContext(watchPart+'\nthis.__watch=ghWatchPanel();',app);
assert.match(app.__watch,/长期关注仓库/);
assert.match(app.__watch,/morluto\/rea/);
assert.match(app.__watch,/不代表今日上榜/);
assert.doesNotMatch(app.__watch,/官方 Trending #\d/);

const metadataView={ghFmt:v=>String(v),esc:x=>String(x)};
vm.createContext(metadataView);
vm.runInContext(metadataPart+'\nthis.__unknown=ghApiMetric("★",null)+ghMetadataNote({metadata_status:"unavailable"});this.__stale=ghMetadataNote({metadata_status:"stale",metadata_verified_at:"2026-10-21T08:00:00Z"});',metadataView);
assert.match(metadataView.__unknown,/★ 待核验/);
assert.match(metadataView.__unknown,/API 元数据待核验/);
assert.match(metadataView.__stale,/API 旧快照/);
assert.match(metadataView.__stale,/10\.21 16:00 北京时间/);

const partialView={GH:{items:[
  {metadata_status:'stale'},{metadata_status:'stale'},{metadata_status:'stale'},
  {metadata_status:'unavailable'},{metadata_status:'unavailable'},{metadata_status:'unavailable'},
  {metadata_status:'unavailable'},{metadata_status:'unavailable'}
],sync:{metadata_status:'partial',metadata_failed_count:8,watchlist_failed_count:1}},esc:x=>String(x)};
vm.createContext(partialView);
vm.runInContext(partialPart+'\nthis.__partial=ghPartialNotice();',partialView);
assert.match(partialView.__partial,/官方榜位与今日 Star 已更新/);
assert.match(partialView.__partial,/3 个上榜仓库/);
assert.match(partialView.__partial,/5 个新上榜仓库/);
assert.match(partialView.__partial,/1 个长期关注仓库/);

assert.match(inlinePart,/role="status" aria-live="polite"/);
assert.match(inlinePart,/显示 '\+rows\.length\+' \/ '\+\(GH\.items\|\|\[\]\)\.length\+' 个仓库/);
assert.match(inlinePart,/保留 GitHub 官方榜位/);
assert.match(pagePart,/GitHub 热榜/);
assert.match(pagePart,/DEVELOPER SIGNALS \/ OFFICIAL ORDER/);
assert.match(pagePart,/不和新闻热度混排/);
assert.doesNotMatch(pagePart,/'热点时间线'/);

const panel=extract(cockpit,'function fcGithubPanel(){','function fcCockpit(){');
const historical={...data,checked_at:'2026-09-25T23:16:36Z',sync:{...data.sync,status:'error'}};
const view={APP:{github_hot:historical},Date,icon:()=>'',safeLink:x=>x,esc:x=>String(x)};
vm.createContext(view);
vm.runInContext(panel+'\nthis.__panel=fcGithubPanel();',view);
assert.match(view.__panel,/当前 Trending 未完成核验/);
assert.match(view.__panel,/morluto\/rea/);
assert.doesNotMatch(view.__panel,/>#01</);
assert.match(view.__panel,/独立关注/);
assert.doesNotMatch(view.__panel,/>\+\d+<\/b><small>Today/);

view.APP.github_hot={
 checked_at:new Date().toISOString(),
 items:[{repo:'example/agent',ai_related:true,stars_today:51,rank:7,url:'https://github.com/example/agent',description:'Agent tools'}],
 watchlist:[{repo:'morluto/rea',url:'https://github.com/morluto/rea',ai_related:true,stars:142000,verified_at:new Date().toISOString()}]
};
vm.runInContext('this.__fresh=fcGithubPanel();',view);
assert.match(view.__fresh,/#07/);
assert.match(view.__fresh,/\+51/);
assert.match(view.__fresh,/morluto\/rea/);
assert.match(view.__fresh,/142k/);
assert.match(view.__fresh,/总 Star/);

const hfPanel=extract(cockpit,'function fcHuggingFacePanel(){','function fcCockpit(){');
const hfView={APP:{huggingface_hot:{
 checked_at:new Date().toISOString(),web_fetched_at:new Date().toISOString(),api_fetched_at:new Date().toISOString(),
 web_order:['org/model-a','org/model-b','org/model-c','org/model-d'],
 items:[
  {id:'org/model-a',url:'https://huggingface.co/org/model-a',task:'text-generation',library:'transformers',trending_score:91},
  {id:'org/model-b',url:'https://huggingface.co/org/model-b',task:'image-to-video',library:'diffusers',trending_score:72},
  {id:'org/model-c',url:'https://huggingface.co/org/model-c',task:null,library:null,trending_score:null}
 ]
}},Date,Intl,Map,icon:()=>'',safeLink:x=>x,esc:x=>String(x)};
vm.createContext(hfView);
vm.runInContext(hfPanel+'\nthis.__hf=fcHuggingFacePanel();',hfView);
assert.match(hfView.__hf,/Hugging Face 热榜/);
assert.match(hfView.__hf,/#01/);
assert.match(hfView.__hf,/org\/model-a/);
assert.match(hfView.__hf,/API Trending/);
assert.match(hfView.__hf,/Trending 不等于能力榜/);
assert.doesNotMatch(hfView.__hf,/org\/model-d/);
hfView.APP.huggingface_hot={...hfData,checked_at:'2026-09-25T23:16:36Z',web_fetched_at:'2026-09-25T23:16:36Z'};
vm.runInContext('this.__hfOld=fcHuggingFacePanel();',hfView);
assert.match(hfView.__hfOld,/当前 Models Trending 未完成核验/);
assert.doesNotMatch(hfView.__hfOld,/>#01</);
console.log('PASS GitHub Trending stale guard and independent REA watchlist UI');
