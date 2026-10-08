'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../src/v10.js'), 'utf8');
const prefix = source.split('hRows=function')[0] + '\nglobalThis.__timeTest = {v10LocalToday, AIC_EDITORIAL_TZ};';
const ctx = {APP:{hot_policy:null}, HOT:{items:[],checked:''}, Intl, Date};
vm.runInNewContext(prefix, ctx, {filename:'src/v10.js'});
const {v10LocalToday, AIC_EDITORIAL_TZ} = ctx.__timeTest;

assert.equal(AIC_EDITORIAL_TZ, 'Asia/Shanghai');
assert.equal(v10LocalToday(new Date('2026-10-07T16:30:00Z')), '2026-10-08');
assert.equal(v10LocalToday(new Date('2026-10-08T15:30:00Z')), '2026-10-08');
assert.equal(v10LocalToday(new Date('2026-10-08T16:30:00Z')), '2026-10-09');
console.log('PASS stable editorial date for freshness windows');
