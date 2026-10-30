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
  APP:{
    github_hot:{items:[{repo:'HKUDS/DeepTutor',description:'Personalized tutoring agent',rank:1,stars_today:1930}]},
    huggingface_hot:{web_order:['deepseek-ai/DeepSeek-V4.1-Flash-1017'],items:[{id:'deepseek-ai/DeepSeek-V4.1-Flash-1017',task:'image-text-to-text'}]},
    research_radar:{items:[{id:'world2vec-latent-dynamics-20261029',title:'world2vec：从观测学习可解释动力学',maker:'world2vec authors',tags:['World Models','Control']}]}
  },
  HOT:{items:[{id:'openai-work-codex-allowance-20261029',title:'OpenAI 上调 Pro 的 Work 与 Codex 用量',source:'OpenAI'}]},
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
assert.match(nodes['#palette-results'].innerHTML,/输入关键词可搜索热点、研究、模型/);
assert.doesNotMatch(nodes['#palette-results'].innerHTML,/Match Benchmark/);

nodes['#palette-input'].value='DeepTutor';
ctx.renderPalette();
assert.equal(ctx.getPaletteItems().length,1,'current GitHub Trending entities must be searchable');
assert.match(nodes['#palette-results'].innerHTML,/GitHub Trending #1/);

nodes['#palette-input'].value='DeepSeek-V4.1';
ctx.renderPalette();
assert.equal(ctx.getPaletteItems().length,1,'current Hugging Face Trending entities must be searchable');
assert.match(nodes['#palette-results'].innerHTML,/Hugging Face Trending #1/);

nodes['#palette-input'].value='world2vec';
ctx.renderPalette();
assert.equal(ctx.getPaletteItems().length,1,'research radar entities must be globally searchable');
assert.match(nodes['#palette-results'].innerHTML,/研究雷达/);

nodes['#palette-input'].value='上调 Pro 的 Work 与 Codex 用量';
ctx.renderPalette();
assert.equal(ctx.getPaletteItems().length,1,'curated hot records must be globally searchable');
assert.match(nodes['#palette-results'].innerHTML,/热点 · OpenAI/);
assert.match(source,/r\.type==='hot'[\s\S]*#\/hot\?item=/,'hot search results must deep-link to the exact record');

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
assert.match(nodes['#palette-results'].innerHTML,/换个关键词，或按 Esc 返回/);
assert.match(nodes['#palette-results'].innerHTML,/role="status"/);

const template=fs.readFileSync(path.join(root,'src/index.html'),'utf8');
assert.match(template,/class="palette-foot"[\s\S]*快速跳转/);
assert.doesNotMatch(template,/QUICK NAVIGATION/);

console.log('5 command palette scope, empty-state and readable-footer contracts passed');
