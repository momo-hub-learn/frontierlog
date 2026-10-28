'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.join(__dirname,'..');
const models = JSON.parse(fs.readFileSync(path.join(root,'data/models.json'),'utf8'));
const candidates = JSON.parse(fs.readFileSync(path.join(root,'data/frontier-candidates.json'),'utf8'));
const code = fs.readFileSync(path.join(root,'src/world-priority.js'),'utf8');
const progressCode = fs.readFileSync(path.join(root,'src/progress-v4.js'),'utf8');
const context = {
 APP:{frontier_candidates:candidates},MODEL_DATA:models,
 mFrontierCard:(item)=>'<article><div class="m-frontier-tags">'+item.name+'</div></article>',
 mFrontierRows:(t)=>t.items, mFrontierTrackState:()=>({tracks:models.frontier_tracks,selected:'world-models'}),
 mParams:()=>new URLSearchParams('frontier=world-models&frontier_order=research'),
 mCompanyCell:x=>x.maker, mSourceLink:()=>'',mNum:x=>String(x),
 esc:x=>String(x).replaceAll('&','&amp;').replaceAll('<','&lt;'),
 icon:()=>'',safeLink:x=>x,URLSearchParams
};
vm.runInNewContext(code+'\nthis.__result={score:worldResearchScore,card:mFrontierCard,queue:worldPendingSection,radar:mFrontierRadar}',context);
const t=context.__result;
const world=models.frontier_tracks.find(x=>x.id==='world-models');
const h=world.items.find(x=>x.id==='hjepa-hierarchical-planning');
assert.equal(t.score(h),82.5);
assert.equal(t.score(world.items.find(x=>x.id==='worldlabs-atlas')),null);
assert.match(t.card(h,world),/研究关注指数/);
assert.match(t.queue(false),/LeHami/);
assert.match(t.queue(false),/未核验/);
assert.match(t.radar(),/研究关注度/);
assert.match(t.radar(),/研究关注指数怎么计算|评分不是能力排名/);
assert(!t.radar().includes('LeHami · 82.5'));
assert.match(progressCode,/research:\(P5_RESEARCH\.items\|\|\[\]\)\.some/);
assert.match(progressCode,/data-research-id=/);
assert.match(progressCode,/p5Href\(\{view:'research',research:x\.id,q:''\}\)/);
assert.match(progressCode,/p\.delete\('research'\)/);
assert.match(progressCode,/返回全部研究档案/);
console.log('PASS research priority is separate from model capability and unreviewed discoveries stay visible');
