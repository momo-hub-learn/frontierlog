'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const d=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/benchmarks.json'),'utf8'));
const js=fs.readFileSync(path.join(__dirname,'../src/benchmarks.js'),'utf8');
const datasets=new Set(d.evaluation_datasets.map(x=>x.id));
const evaluators=new Set(d.evaluators.map(x=>x.id));
const judge=d.items.filter(x=>x.group==='judge');
assert.equal(judge.length,3);
assert.equal(d.evaluation_datasets.length,3);
assert.ok(judge.every(b=>b.tested===false&&b.result_status==='not_run'));
for(const b of judge){
 assert.ok(b.dataset_ids.length&&b.evaluator_ids.length);
 assert.ok(b.dataset_ids.every(id=>datasets.has(id)));
 assert.ok(b.evaluator_ids.every(id=>evaluators.has(id)));
}
assert.ok(d.evaluation_datasets.every(x=>x.url.startsWith('https://')&&x.gold_label&&x.access==='public'));
assert.ok(js.includes("datasets:'评测集'"));
assert.ok(js.includes("mode==='datasets'?bDatasetRecords()"));
assert.ok(js.includes('${bEvaluationLinks(b)}'));
assert.ok(js.includes('本站未实测；不展示虚构分数或模型排名'));
console.log('PASS Judge benchmark evaluation registry and UI');
