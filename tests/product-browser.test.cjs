'use strict';
// Execute the actual product view, not grep checks for unused code or embedded JSON.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'src/v10.js'),'utf8');
const original=JSON.parse(fs.readFileSync(path.join(root,'data/product-radar.json'),'utf8'));
const clone=x=>JSON.parse(JSON.stringify(x));
const data=clone(original);
const hot={items:[]};
const listeners={};
const ctx={PRODUCT_RADAR:data,HOT:hot,APP:{},URL,URLSearchParams,Date,console,
 location:{hash:'#/hot?cat=product'},history:{pushState(_a,_b,hash){ctx.location.hash=hash}},
 document:{addEventListener(type,fn){(listeners[type]??=[]).push(fn)}},
 esc:x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
 icon:()=>'<svg aria-hidden="true"></svg>',hState:()=>({cat:'product',q:''}),hTabs:()=>'<nav>primary tabs</nav>',
 hCategoryCount:id=>'unchanged-'+id,parseRoute(){ctx.renders=(ctx.renders||0)+1},lastMain:'cached'
};
const start=source.indexOf('/* Product browser:'),end=source.indexOf('/* End product browser. */');
assert(start>=0&&end>start,'Product implementation must be in the compiled source');
vm.createContext(ctx);vm.runInContext(source.slice(start,end)+'\nthis.api=PB;',ctx);
const pb=ctx.api;
const read=q=>pb.read('#/hot?cat=product'+(q?'&'+q:''));
const ids=rows=>Array.from(rows,x=>x.id).sort();
let tests=0;
function check(name,f){f();tests++;console.log('PASS',name)}
check('default view / invalid query values',()=>{
 assert.equal(read('').pview,'updates');assert.equal(read('pview=map').pview,'map');
 const s=read('scene=bad&investor=bad&kind=bad&product=bad&pview=bad');
 assert.equal(s.scene,'all');assert.equal(s.investor,'all');assert.equal(s.kind,'all');assert.equal(s.product,'');assert.equal(s.pview,'updates');
});
check('orthogonal scene and investor filters',()=>{
 assert.deepEqual(ids(pb.products(read('scene=legal&investor=sequoia'))),['harvey']);
 assert.deepEqual(ids(pb.products(read('scene=support&investor=yc'))),['inkeep']);
 assert.equal(pb.products(read('scene=sales&investor=yc')).length,0);
});
check('legacy ptag links retain their exact product set',()=>{
 for(const f of data.filters){assert.deepEqual(ids(pb.products(read('ptag='+f.id))),ids(data.items.filter(x=>x.filter_ids.includes(f.id))),f.id)}
});
check('view switch preserves query + facets, drops platform state',()=>{
 const s=read('ptag=sequoia&scene=legal&q=Word&tab=github');const h=pb.href(s,{pview:'map'});const next=pb.read(h);
 assert.equal(next.scene,'legal');assert.equal(next.investor,'sequoia');assert.equal(next.q,'Word');assert.equal(next.pview,'map');assert(!h.includes('tab='));
 assert.equal(ctx.hCategoryCount('product'),data.items.length);assert.equal(ctx.hCategoryCount('model'),'unchanged-model');
});
check('single event stream / no duplicate legacy news section',()=>{
 const html=pb.page(read(''));assert(html.includes('pb-timeline'));assert(!html.includes('class="pb-grid"'));assert(!html.includes('h-product-moves'));assert(!html.includes('intraday-timeline'));
 assert(source.includes("if(s.cat==='product')return PB.page()"));assert(!source.includes('${hProductRadar(s)}'));
});
check('map is separate and contains every product',()=>{
 const html=pb.page(read('pview=map'));assert.equal((html.match(/data-product-id=/g)||[]).length,data.items.length);assert(!html.includes('data-product-event'));
 assert(html.includes('产品说明'));assert(html.includes('客户采用'));assert(html.includes('投资背景'));assert(html.includes('完整时间线'));
});
check('complete chronological history, not a last-event-only card',()=>{
 const p=data.items.find(x=>x.id==='harvey'),html=pb.page(read('pview=map&product=harvey'));
 for(const e of p.timeline)assert(html.includes(e.title));assert(html.includes('class="pb-card-history" open'));
 const all=pb.events(read(''));assert.equal(all.length,data.items.reduce((n,x)=>n+x.timeline.length,0));
 assert(Array.from(all).every((e,i)=>i===0||all[i-1].date>=e.date));
 assert(pb.updates(all,read(''),new Date('2026-09-25T00:00:00Z')).includes('历史进展'));
});
check('search narrows both cards and event text, not unrelated history',()=>{
 assert.deepEqual(ids(pb.products(read('q=Word'))),['harvey']);assert.equal(pb.events(read('q=Word')).length,1);
 assert(pb.events(read('q=Harvey')).length>=3);assert.equal(pb.events(read('kind=Company')).length,2);
});
check('deduplicate news against recorded product event by date + permalink',()=>{
 const e=data.items.find(x=>x.id==='harvey').timeline[0],before=pb.events(read('')).length;
 hot.items=[{id:'same-event',category:'product',published:e.date,title:e.title,url:e.url+'/?utm_source=test',source:'Harvey'}];
 assert.equal(pb.events(read('')).length,before);
 hot.items.push({id:'outside',category:'product',published:'2026-09-25',title:'Uncatalogued product',url:'https://example.org/releases/new',source:'Example'});
 assert.equal(pb.events(read('')).length,before+1);assert.equal(pb.events(read('scene=legal')).some(x=>x.title==='Uncatalogued product'),false);
 hot.items=[];
});
check('specific sources and broad directory links are not conflated',()=>{
 assert.equal(pb.specific('https://legora.com/newsroom'),false);assert.equal(pb.specific('https://sierra.ai/uk/blog'),false);
 assert.equal(pb.specific('https://sierra.ai/uk/blog/an-announcement'),true);
 assert(pb.page(read('pview=map&product=legora')).includes('栏目页，精确原文待补'));
});
check('no adoption evidence is invented from an investment portfolio',()=>{
 const html=pb.page(read('pview=map&product=harvey'));assert(html.includes('暂无已收录的客户采用公告'));
 assert(pb.page(read('pview=map&product=legora')).includes('公司公告 · 非独立效果评测'));
});
check('empty state resets filters without rendering unrelated stories',()=>{
 const html=pb.page(read('scene=sales&investor=yc'));assert(html.includes('当前筛选下暂无已收录动态'));assert(html.includes('清除筛选'));assert(!html.includes('data-product-event'));
});
check('HTML injection and unsafe URLs are neutralized',()=>{
 const html=pb.page(read('q='+encodeURIComponent('<script>alert(1)</script>')));assert(!html.includes('<script>'));assert(html.includes('&lt;script&gt;'));
 assert.equal(pb.canonical('javascript:alert(1)'),'');assert.equal(pb.canonical('https://user:pass@example.org/'),'');
});
check('invalid calendar dates are not accepted as timeline nodes',()=>{
 assert.equal(pb.chronology({timeline:[{date:'2026-02-30'},{date:'not-a-date'}]}).length,0);
});
check('rendering does not mutate dates, evidence, catalog, or ordering',()=>{assert.deepEqual(data,original)});
check('normal tab click refreshes the route; modified click opens normally',()=>{
 const handler=listeners.click[0];let prevented=0;
 const target={closest:()=>({getAttribute:()=> '#/hot?cat=product&pview=map'})};
 handler({target,button:0,ctrlKey:true,preventDefault(){prevented++}});assert.equal(prevented,0);
 handler({target,button:0,preventDefault(){prevented++}});assert.equal(prevented,1);assert.equal(ctx.location.hash,'#/hot?cat=product&pview=map');assert.equal(ctx.lastMain,'');assert.equal(ctx.renders,1);
});
console.log(`Product browser: ${tests} behavioral checks passed.`);
