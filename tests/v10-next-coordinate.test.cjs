'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../src/v10.js'), 'utf8');
const prefix = source.split('hRows=function')[0] + '\nglobalThis.__nextTest = {v10NextOfficialEvent};';
let clock='2026-10-08T12:00:00Z';
class FixedDate extends Date { constructor(...args){super(...(args.length?args:[clock]))} static now(){return Date.parse(clock)} }
const ctx = {
  APP:{
    hot_policy:null,
    activity_radar:{
      sources:[
        {id:'official',authority:'official'},
        {id:'media',authority:'first-party'}
      ],
      events:[
        {id:'past',source_id:'official',date:'2026-10-07',status:'upcoming',title:'Past',url:'https://example.com/past'},
        {id:'media-soon',source_id:'media',date:'2026-10-09',status:'upcoming',title:'Media',url:'https://example.com/media'},
        {id:'official-later',source_id:'official',date:'2026-12-01',status:'upcoming',title:'Later',url:'https://example.com/later'},
        {id:'official-soon',source_id:'official',date:'2026-10-20',status:'upcoming',title:'Soon',url:'https://example.com/soon'}
      ]
    }
  },
  HOT:{items:[],checked:''},
  Intl,Date:FixedDate,
  safeLink:x=>String(x||'').startsWith('https://')?x:''
};
vm.runInNewContext(prefix, ctx, {filename:'src/v10.js'});
const {v10NextOfficialEvent}=ctx.__nextTest;
assert.equal(v10NextOfficialEvent().id,'official-soon');
clock='2026-10-21T12:00:00Z';
assert.equal(v10NextOfficialEvent().id,'official-later');
assert.ok(source.includes('<h2>下一坐标</h2>'));
console.log('PASS next coordinate selects the nearest future official event');
