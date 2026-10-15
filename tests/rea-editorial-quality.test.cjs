'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'), path=require('node:path'), vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const article=JSON.parse(fs.readFileSync(path.join(root,'data/deep-dives.json'),'utf8'))
 .articles.find(a=>a.id==='rea-agent-reverse-engineering');
const source=fs.readFileSync(path.join(root,'src/deep-dives.js'),'utf8');
const css=fs.readFileSync(path.join(root,'src/deep-dives.css'),'utf8');
assert(article&&article.sections.length>=8);
assert(source.includes('d-page d-visual')&&source.includes('d-editorial'),
 'every rich article needs the rich-component styling scope');
const start=source.indexOf('function dFlow('),end=source.indexOf('function dRichCards(',start);
assert(start>0&&end>start);
const ctx={esc:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;')};
vm.runInNewContext(source.slice(start,end)+
 '\nthis.unit={flow:dFlow,role:dRoleWorkflow,rea:dReaRolePayload}',ctx);
const {flow,role,rea}=ctx.unit;
const intro=article.sections.find(x=>x.key==='question').blocks.find(b=>b.type==='flow');
const basic=flow(intro);
assert.match(basic,/role="list"/);
assert.match(basic,/role="listitem"/);
assert(!basic.includes('<ol'),'native ordered markers must not double the authored number');
assert.match(basic,/class="dv-number">01/);
const input=article.sections.find(x=>x.key==='stack').blocks.find(b=>b.title==='一次任务中谁负责什么？');
assert(input&&input.nodes.length===4);
const html=role(rea(input));
assert.match(html,/class="d-role-workflow"/);
assert.match(html,/class="d-role-table"/);
assert.equal((html.match(/class="d-role-step"/g)||[]).length,4);
assert.equal((html.match(/<tr><th scope="row">/g)||[]).length,4);
for(const word of ['Agent','REA','分析引擎','复核与实现','典型输入','可检查的产出','风险 / 复核','图示边界','返回调查']){
 assert(html.includes(word),word+' missing from architecture/table');
}
assert(!/1\. 01Agent|<ol class="dv-flow"/.test(html));
assert(css.includes('.d-editorial .dv-code')&&css.includes('.d-editorial .je-figure')&&css.includes('.d-role-step'),
 'unstyled rich blocks are a fatal editorial quality regression');
assert(css.includes('@container (max-width:475px)'), 'mobile responsibility diagram must reflow');
console.log('PASS REA: rich CSS contract, duplicate-number prevention, evidence matrix, mobile responsibility layout');
