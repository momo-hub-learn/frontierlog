'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'src/app.js'),'utf8');
const start=source.indexOf('function renderPalette(){');
const end=source.indexOf('function paletteSelect',start);
assert(start>=0&&end>start,'command palette implementation must remain executable');

const nodes={'#palette-input':{value:''},'#palette-results':{innerHTML:''}};
const pages=Object.fromEntries(Array.from({length:16},(_,i)=>['page-'+i,['页面 '+i,'box']]));
const ctx={
  BENCH:{items:Array.from({length:40},(_,i)=>({id:'bench-'+i,name:'Match Benchmark '+i,subtitle:'任务',group:'agent'}))},
  BGROUPS:new Map([['agent',{title:'Agent'}]]),
  pages,
  DATA:{items:Array.from({length:40},(_,i)=>({id:'task-'+i,name:'Match Tool '+i,title:'可运行',category:'工具'}))},
  VERT:{topics:[],articles:[]},
  VSECTORS:new Map(),
  paletteIndex:0,
  paletteItems:[],
  $:selector=>nodes[selector],
  icon:()=>'<svg aria-hidden="true"></svg>',
  esc:value=>String(value)
};
vm.createContext(ctx);
vm.runInContext(source.slice(start,end)+'\nthis.renderPalette=renderPalette;this.getPaletteItems=()=>paletteItems;',ctx);

ctx.renderPalette();
assert.equal(ctx.getPaletteItems().length,Object.keys(pages).length,'empty query should only expose page destinations');
assert.match(nodes['#palette-results'].innerHTML,/输入关键词可搜索模型/);
assert.doesNotMatch(nodes['#palette-results'].innerHTML,/Match Benchmark/);

nodes['#palette-input'].value='match';
ctx.renderPalette();
assert.equal(ctx.getPaletteItems().length,24,'large searches must stay keyboard-manageable');
assert.match(nodes['#palette-results'].innerHTML,/显示前 24 \/ 80 条/);

nodes['#palette-input'].value='benchmark 39';
ctx.renderPalette();
assert.equal(ctx.getPaletteItems().length,1);
assert.match(nodes['#palette-results'].innerHTML,/Match Benchmark 39/);

nodes['#palette-input'].value='not present';
ctx.renderPalette();
assert.equal(ctx.getPaletteItems().length,0);
assert.match(nodes['#palette-results'].innerHTML,/没有匹配结果/);

console.log('4 command palette scope and empty-state contracts passed');
