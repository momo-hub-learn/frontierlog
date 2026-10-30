'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname,'../src/v10.js'),'utf8');
const prefix = source.split('hRows=function')[0]+'\nglobalThis.__hotTest={v10Top5Window,v10Top5Rows,v10FeedFreshnessCopy,v10FeedFreshnessTarget,v10HotStatusShort,v10HotResultSummary};';
class FixedDate extends Date{constructor(...args){super(...(args.length?args:['2026-10-08T12:00:00Z']))}static now(){return Date.parse('2026-10-08T12:00:00Z')}}
const make=(items)=>{const ctx={APP:{hot_policy:{}},HOT:{items,checked:'2026-10-08'},Date:FixedDate,Intl};vm.runInNewContext(prefix,ctx);return ctx.__hotTest};
const rows=[
 {id:'new',published:'2026-10-07',heat:90},
 ...Array.from({length:9},(_,i)=>({id:'old'+i,published:'2026-09-'+String(22-i).padStart(2,'0'),heat:99-i}))
];
const got=make(rows);
assert.equal(got.v10Top5Rows().length,5);
assert.equal(got.v10Top5Rows()[0].id,'new');
assert.equal(got.v10Top5Window().recentCount,1);
assert.equal(got.v10Top5Window().archiveCount,4);
assert.match(got.v10FeedFreshnessCopy(),/较早的已核验热点/);
assert.match(got.v10HotStatusShort(),/历史精选/);
const seenToday=make([{id:'late',published:'2026-10-07',first_seen_at:'2026-10-08T00:30:00+08:00',heat:96}]);
assert.match(seenToday.v10FeedFreshnessCopy(),/今天新收录 1 条/);
assert.match(seenToday.v10FeedFreshnessCopy(),/原始发布日期见卡片/);
assert.equal(seenToday.v10FeedFreshnessTarget().id,'late');
const publishedToday=make([
 {id:'seen',published:'2026-10-07',first_seen_at:'2026-10-08T15:30:00+08:00',heat:96},
 {id:'published',published:'2026-10-08',first_seen_at:'2026-10-08T08:30:00+08:00',heat:90}
]);
assert.equal(publishedToday.v10FeedFreshnessTarget().id,'published');
assert.match(source,/class="v10-feed-fresh-link" href="#\/hot\?item=\$\{encodeURIComponent\(fresh\.id\)\}"/);
const seenYesterday=make([{id:'known',published:'2026-10-07',first_seen_at:'2026-10-07T23:30:00+08:00',heat:96}]);
assert.match(seenYesterday.v10FeedFreshnessCopy(),/没有今日发布或新收录/);
assert.equal(seenYesterday.v10FeedFreshnessTarget(),null);
assert.equal(make([]).v10Top5Rows().length,0);
assert.equal(make(rows.slice(0,1)).v10Top5Rows().length,1);
assert.equal(got.v10HotResultSummary({cat:'all',q:''},rows),'10 条已核验');
assert.equal(got.v10HotResultSummary({cat:'model',q:''},rows.slice(0,2)),'2 条匹配 · 10 条已核验');
assert.equal(got.v10HotResultSummary({cat:'all',q:'no-result'},[]),'0 条匹配 · 10 条已核验');
console.log('PASS top5 fresh-first archive backfill');
