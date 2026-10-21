'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../src/v10.js'), 'utf8');
const prefix = source.split('hRows=function')[0] + '\nglobalThis.__timeTest = {v10LocalToday, v10HotCheckedText, v10ShadowCheckedText, AIC_EDITORIAL_TZ};';
const ctx = {APP:{hot_policy:null}, HOT:{items:[
  {verified_at:'2026-10-21T19:40:00+08:00'},
  {verified_at:'2026-10-21T11:00:00Z'},
  {verified_at:'2026-10-22'}
],checked:'2026-10-21',sync:{last_checked_at:'2026-10-21T11:52:59Z'}}, Intl, Date};
vm.runInNewContext(prefix, ctx, {filename:'src/v10.js'});
const {v10LocalToday, AIC_EDITORIAL_TZ} = ctx.__timeTest;

assert.equal(AIC_EDITORIAL_TZ, 'Asia/Shanghai');
assert.equal(v10LocalToday(new Date('2026-10-07T16:30:00Z')), '2026-10-08');
assert.equal(v10LocalToday(new Date('2026-10-08T15:30:00Z')), '2026-10-08');
assert.equal(v10LocalToday(new Date('2026-10-08T16:30:00Z')), '2026-10-09');
assert.equal(ctx.__timeTest.v10HotCheckedText(), '10.21 19:40');
assert.equal(ctx.__timeTest.v10ShadowCheckedText(), '10.21 19:52');
console.log('PASS stable editorial date for freshness windows');
