'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'src/deep-dives.js'),'utf8');
const cockpit=fs.readFileSync(path.join(root,'src/feed-cockpit.js'),'utf8');
const a={id:'new-paper',published:'2026-10-13',updated:'2026-10-15',
  title:'New paper',short_title:'New paper',subtitle:'Current headline',read_minutes:9,
  tags:['Research'],thesis:'Evidence',mini_flow:[],sections:[],sources:[]};
const b={id:'old-paper-revised',published:'2026-09-24',updated:'2026-10-19',
  title:'Revised technical paper',short_title:'Updated deep dive',subtitle:'New evidence',read_minutes:15,
  tags:['Research'],thesis:'Measured tradeoff',mini_flow:[],sections:[],sources:[]};
const deep={articles:[a,b],checked:'2026-10-19'};
const ctx={APP:{deep_dives:deep},pages:{},location:{hash:'#/deep'},URLSearchParams,esc:String,icon:()=>''};
const p=source.slice(source.indexOf('const DEEP='),source.indexOf('function dFeedCard(){'));
vm.runInNewContext(p+'\nthis.result={first:DEEP_LATEST[0].id,current:dCurrent().id};',ctx);
assert.equal(ctx.result.first,'old-paper-revised');
assert.equal(ctx.result.current,'old-paper-revised');
assert.deepEqual([a.published,b.published],['2026-10-13','2026-09-24'],
  'revisions never change original release dates');
const c=cockpit.slice(cockpit.indexOf('function fcDeepPanel(){'),cockpit.indexOf('\nfunction fcGithubPanel()',cockpit.indexOf('function fcDeepPanel(){')));
const panelCtx={APP:{deep_dives:deep},esc:String,icon:()=>'',encodeURIComponent};
vm.runInNewContext(c+'\nthis.html=fcDeepPanel();',panelCtx);
assert.match(panelCtx.html,/old-paper-revised/);
assert.match(panelCtx.html,/10.19 更新/);
assert(!panelCtx.html.includes('#/deep?id=new-paper'));
assert(source.includes('编辑目标 · 每 3 天实质更新'));
assert(fs.readFileSync(path.join(root,'src/deep-dives.css'),'utf8').includes('.d-update-cadence'));
console.log('PASS every-3-day editorial UI: revised article promoted without changing published day');
