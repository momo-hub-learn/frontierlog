'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const deep=JSON.parse(fs.readFileSync(path.join(root,'data/deep-dives.json'),'utf8'));
const hot=JSON.parse(fs.readFileSync(path.join(root,'data/hot.json'),'utf8'));
const rea=deep.articles.find(x=>x.id==='rea-agent-reverse-engineering');
const decisions=deep.articles.find(x=>x.id==='decisions-api-bounded-decision-layer');
const containment=deep.articles.find(x=>x.id==='frontier-training-containment');
const credits=deep.articles.find(x=>x.id==='openai-api-credits-ledger');
assert(rea&&rea.sections.length>=6&&rea.sources.length>=5);
assert(decisions&&decisions.sections.length>=6&&decisions.sources.length>=3);
assert(containment&&containment.sections.length>=7&&containment.sources.length>=3);
assert(credits&&credits.sections.length>=7&&credits.sources.length>=2);
assert(hot.items.some(x=>x.id==='rea-ai-reverse-engineering-20261012'&&x.link==='#/deep?id='+rea.id));
assert(hot.items.some(x=>x.id==='openai-frontier-training-containment-20261023'&&x.link==='#/deep?id='+containment.id));
const source=fs.readFileSync(path.join(root,'src/deep-dives.js'),'utf8');
const prefix=source.slice(source.indexOf('const DEEP='),source.indexOf('function dFeedCard(){'));
const ctx={APP:{deep_dives:deep},pages:{},location:{hash:'#/deep'},URLSearchParams,esc:x=>String(x)};
vm.runInNewContext(prefix+'\nthis.__select={dCurrent,dMiniFlow,DEEP_LATEST};',ctx);
assert.equal(ctx.__select.dCurrent().id,credits.id);
ctx.location.hash='#/deep?id=jev-agent-decision-layer';
assert.equal(ctx.__select.dCurrent().id,'jev-agent-decision-layer');
const diagram=ctx.__select.dMiniFlow(rea);
assert.match(diagram,/REA \+ MCP/);
assert(!diagram.includes('Jev'));
// Background references are curated for each article and appear immediately after the opening context.
for(const article of deep.articles){
 assert(article.background_refs?.length,article.id+' needs a background source link');
 assert(article.background_refs.every(id=>article.sources.some(s=>s.id===id)),article.id+' has an unknown background ref');
}
const bgStart=source.indexOf('function dBackgroundSources(a){');
const bgEnd=source.indexOf('function dToc(a){',bgStart);
assert(bgStart>=0&&bgEnd>bgStart);
const bgCtx={
 esc:x=>String(x).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;'),
 safeLink:x=>String(x),
 dSourceMap:a=>new Map(a.sources.map((s,i)=>[s.id,{...s,index:i+1}]))
};
vm.runInNewContext(source.slice(bgStart,bgEnd)+'\nthis.__opening=dOpening;',bgCtx);
for(const article of deep.articles){
 const html=bgCtx.__opening(article);
 const firstParagraphEnd=html.indexOf('</p>');
 const backgroundStart=html.indexOf('class="d-background-sources"');
 assert(backgroundStart>firstParagraphEnd,article.id+' background link must follow the opening context');
 assert(backgroundStart<html.indexOf('<p',firstParagraphEnd+4),article.id+' background link should precede the second paragraph');
 for(const id of article.background_refs){
  const src=article.sources.find(s=>s.id===id);
  assert(html.includes('href="'+src.url+'"'),article.id+' missing original source '+id);
 }
 assert(html.includes('rel="noopener noreferrer"'),article.id+' missing safe new-tab link rel');
}
assert(!bgCtx.__opening({...rea,background_refs:[]}).includes('d-background-sources'));
assert(source.includes('dOtherReads(a)'));
const cockpit=fs.readFileSync(path.join(root,'src/feed-cockpit.js'),'utf8');
const start=cockpit.indexOf('function fcDeepPanel(){');
const end=cockpit.indexOf('\nfunction fcGithubPanel()',start);
assert(start>=0&&end>start);
const runCtx={APP:{deep_dives:deep},esc:x=>String(x),icon:()=>'',encodeURIComponent};
vm.runInNewContext(cockpit.slice(start,end)+'\nthis.__panel=fcDeepPanel();',runCtx);
assert.match(runCtx.__panel,/openai-api-credits-ledger/);
assert.match(runCtx.__panel,/套餐 \/ 7 天 \/ cohort/);
assert(!runCtx.__panel.includes('生成 \/ 推理'));
console.log('PASS latest deep dive, homepage spotlight, and historical deep links');
