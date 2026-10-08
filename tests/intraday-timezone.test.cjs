'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const code = fs.readFileSync(path.join(__dirname, '../src/intraday.js'), 'utf8')
  .replace(/\}\)\(\);\s*$/, 'globalThis.__timeTest = {stampParts, dtInfo, sortMoment};\n})();');
const ctx = {state: {view:'none'}, feedPage: () => ''};
vm.runInNewContext(code, ctx, {filename: 'src/intraday.js'});
const {stampParts, dtInfo, sortMoment} = ctx.__timeTest;

assert.equal(stampParts('2026-10-08T03:30:00Z').time, '11:30');
assert.equal(stampParts('2026-10-07T23:30:00-04:00').date, '2026-10-08');
assert.equal(stampParts('2026-10-08T11:30:00+08:00').time, '11:30');
assert.equal(stampParts('2026-10-08T11:30:00').zone, '时区未注明');
assert.equal(stampParts('2026-10-08T25:30:00Z'), null);
assert.equal(stampParts('not-a-timestamp'), null);

const source = dtInfo({published:'2026-10-08', published_at:'2026-10-07T23:30:00-04:00'});
assert.equal(source.time, '11:30');
assert.match(source.label, /北京时间/);
const seen = dtInfo({published:'2026-10-08', first_seen_at:'2026-10-07T23:30:00Z'});
assert.equal(seen.time, '07:30');
assert.match(seen.label, /首次收录 · 北京时间/);
const unknown = dtInfo({published:'2026-10-08', published_at:'2026-10-08T11:00:00'});
assert.match(unknown.label, /时区未注明/);
assert.equal(sortMoment({published_at:'2026-10-08T03:30:00Z'}),
             sortMoment({published_at:'2026-10-08T11:30:00+08:00'}));
assert.equal(sortMoment({published_at:'2026-10-08T11:30:00'}), 0);
console.log('PASS intraday timezone and provenance regression');
