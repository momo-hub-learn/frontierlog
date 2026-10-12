'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ROOT=path.resolve(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(ROOT,'data/github-hot.json'),'utf8'));
const gh=fs.readFileSync(path.join(ROOT,'src/github-hot.js'),'utf8');
const cockpit=fs.readFileSync(path.join(ROOT,'src/feed-cockpit.js'),'utf8');

function extract(s,start,end){
 const a=s.indexOf(start),b=s.indexOf(end,a+start.length);
 assert(a>=0&&b>a,{start,end});
 return s.slice(a,b);
}
const watchPart=extract(gh,'function ghWatchPanel(){','function ghActive(){');
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

const panel=extract(cockpit,'function fcGithubPanel(){','function fcCockpit(){');
const view={APP:{github_hot:data},Date,icon:()=>'',safeLink:x=>x,esc:x=>String(x)};
vm.createContext(view);
vm.runInContext(panel+'\nthis.__panel=fcGithubPanel();',view);
assert.match(view.__panel,/当前 Trending 未完成核验/);
assert.match(view.__panel,/morluto\/rea/);
assert.doesNotMatch(view.__panel,/>#01</);
assert.match(view.__panel,/等待首次核验|待核验/);

view.APP.github_hot={
 checked_at:new Date().toISOString(),
 items:[{repo:'example/agent',ai_related:true,stars_today:51,rank:7,url:'https://github.com/example/agent',description:'Agent tools'}],
 watchlist:[{repo:'morluto/rea',url:'https://github.com/morluto/rea',stars:142000,verified_at:new Date().toISOString()}]
};
vm.runInContext('this.__fresh=fcGithubPanel();',view);
assert.match(view.__fresh,/#07/);
assert.match(view.__fresh,/\+51/);
assert.match(view.__fresh,/morluto\/rea/);
assert.match(view.__fresh,/142\.0k/);
assert.match(view.__fresh,/总 Star/);
console.log('PASS GitHub Trending stale guard and independent REA watchlist UI');
