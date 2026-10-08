'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname,'../src/v10.js'),'utf8');
const prefix = source.split('hRows=function')[0]+'\nglobalThis.__hotTest={v10Top5Window,v10Top5Rows,v10FeedFreshnessCopy,v10HotStatusShort};';
const make=(items)=>{const ctx={APP:{hot_policy:{}},HOT:{items,checked:'2026-10-08'},Date,Intl};vm.runInNewContext(prefix,ctx);return ctx.__hotTest};
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
assert.equal(make([]).v10Top5Rows().length,0);
assert.equal(make(rows.slice(0,1)).v10Top5Rows().length,1);
console.log('PASS top5 fresh-first archive backfill');
