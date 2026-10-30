'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const P=require('../src/people.js');
const data=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/people.json'),'utf8'));
const snapshot=JSON.stringify(data),now=Date.parse('2026-10-11T10:00:00Z');
const read=q=>P.read('#/people'+(q?'?'+q:''),data);
let n=0;function test(name,f){f();n++;console.log('PASS',name)}
test('URL normalization and round trip',()=>{
 const s=read('view=bad&format=bad&type=bad&area=bad&role=bad');assert.equal(s.view,'updates');assert.equal(s.format,'all');assert.equal(s.type,'all');assert.equal(s.area,'all');assert.equal(s.role,'all');
 const a=read('format=research&area=agents&following=1&q=VISTA'),b=P.read(P.href(a,{person:'keya-hu'}),data);
 assert.equal(b.q,'VISTA');assert.equal(b.area,'agents');assert.equal(b.format,'research');assert.equal(b.following,true);assert.equal(b.person,'keya-hu');
});
test('directory includes all reviewed profiles without expiration',()=>{
 assert.equal(P.rows(data,read('')).length,data.people.length);
 assert(P.rows(data,read('')).some(p=>p.id==='geoffrey-hinton'));
});
test('English aliases, Chinese names and works search',()=>{
 for(const q of ['何恺明','Kaiming','ResNet'])assert(P.rows(data,read('q='+encodeURIComponent(q))).some(p=>p.id==='kaiming-he'));
 assert(P.rows(data,read('q=Mamba')).some(p=>p.id==='tri-dao'));
 assert.equal(P.rows(data,read('q=doesnotexist')).length,0);
});
test('independent role, direction, work-discovery and following filters',()=>{
 const s=read('area=agents&discover=1');assert(P.rows(data,s).every(p=>p.areas.includes('agents')&&p.discovery==='work'));
 const saved=new Set(['tri-dao']);assert.equal(P.rows(data,read('following=1'),saved).length,1);
 assert.equal(P.rows(data,read('following=1&area=product'),saved).length,0);
 assert(P.rows(data,read('role=founder')).every(p=>p.roles.includes('founder')));
 for(const type of data.influence_types){const matches=P.rows(data,read('type='+type.id));assert(matches.length);assert(matches.every(p=>P.influenceTypes(p).includes(type.id)));}
});
test('corrupt/unknown local IDs do not become follows',()=>{
 assert.equal(P.followIds({},data).size,0);assert.equal(P.followIds(['tri-dao','tri-dao',{},'unknown'],data).size,1);
});
test('event time is original publication, not review date',()=>{
 const ev=P.events(data,read(''),new Set(),now);assert.equal(ev[0].id,'bret-poppy-draft-20261009');assert.equal(ev[0].date,'2026-10-09');
 const page=P.page(data,read('view=updates'),new Set(),now);
 assert(page.includes('历史作品与观点'));assert(page.includes('2023.12.01'));assert(page.includes('近 30 日'));
 const future=JSON.parse(snapshot);future.events.push({...future.events[0],id:'future',date:'2099-01-01'});
 assert(!P.events(future,read(''),new Set(),now).some(x=>x.id==='future'));
});
test('following events use exact author relationships',()=>{
 const ev=P.events(data,read('view=updates&following=1'),new Set(['keya-hu']),now);assert.equal(ev.length,1);assert.equal(ev[0].id,'vista-paper');
});
test('activity format filters are transparent kind groups, not depth scores',()=>{
 const opinion=P.events(data,read('format=opinion'),new Set(),now);assert(opinion.length);assert(opinion.every(e=>['article','talk'].includes(e.kind)));
 const research=P.events(data,read('format=research'),new Set(),now);assert(research.length);assert(research.every(e=>e.kind==='paper'));
 const product=P.events(data,read('format=product'),new Set(),now);assert(product.length);assert(product.every(e=>e.kind==='release'));
 const page=P.page(data,read('format=opinion'),new Set(),now);assert(page.includes('阅读价值'));assert(page.includes('不生成主观深度分'));assert(!page.includes('data-depth-score'));
});
test('profile coauthor links and empty activity are honest',()=>{
 const profile=P.page(data,read('person=qiushi-han'),new Set(),now);
 assert(profile.includes('person=keya-hu'));assert(profile.includes('不据此推断师生关系'));assert(profile.includes('编辑观察 · 不是本人引语'));
 assert(P.page(data,read('person=bret-taylor'),new Set(),now).includes('Poppy'));
 assert(P.page(data,read('person=geoffrey-hinton'),new Set(),now).includes('暂无本站已核验的独立动态'));
 assert(P.page(data,read('person=shyam-sankar'),new Set(),now).includes('暂无本站已核验的独立动态'));
 assert(P.page(data,read('person=unknown')).includes('未找到这个人物档案'));
});
test('text and URLs are escaped even before validation',()=>{
 assert.equal(P.https('javascript:alert(1)'), '');assert.equal(P.https('https://user:pass@example.org/'),'');
 const unsafe=JSON.parse(snapshot);unsafe.people[0].name='<img src=x onerror=alert(1)>';
 const html=P.page(unsafe,read(''));assert(!html.includes('<img src=x'));assert(html.includes('&lt;img'));
 const q=P.page(data,read('q='+encodeURIComponent('<script>alert(1)</script>')));assert(!q.includes('<script>'));assert(q.includes('&lt;script&gt;'));
});
test('Beijing date and invalid calendar dates',()=>{assert.equal(P.today(Date.parse('2026-10-11T16:30:00Z')),'2026-10-12');assert(!P.day('2026-02-30'));assert(P.day('2024-02-29'))});
test('latest verified activity covers every profile without inventing updates',()=>{
 const current=Date.parse('2026-10-26T02:30:00Z');
 assert.equal(P.rows(data,read('view=influence&dim=research')).length,data.people.filter(p=>p.impact.dimensions.includes('research')).length);
 const page=P.page(data,read('view=influence'),new Set(),current);
 assert(page.includes('影响力证据'));assert(page.includes('学术与研究'));assert(page.includes('开源与技术生态'));assert(page.includes('产品与产业落地'));
 assert.equal((page.match(/class="pp-latest/g)||[]).length,data.people.length);
 const recent=P.latestSignal(data.people.find(p=>p.id==='harrison-chase'),data,current);assert.equal(recent.date,'2026-10-24');
 const older=P.latestSignal(data.people.find(p=>p.id==='geoffrey-hinton'),data,current);assert.equal(older,null);
 assert(P.page(data,read('person=shreya-shankar'),new Set(),current).includes('Quail'));
 assert(P.page(data,read('person=shreya-shankar'),new Set(),Date.parse('2026-10-28T02:30:00Z')).includes('Evals 汇报不该只给仪表盘'));
 assert(P.page(data,read('person=hamel-husain'),new Set(),Date.parse('2026-10-28T02:30:00Z')).includes('Evals 汇报不该只给仪表盘'));
 const round=P.read(P.href(read('view=influence&dim=research'),{person:'kaiming-he'}),data);assert.equal(round.dim,'research');assert.equal(round.view,'influence');
});
// Synthetic fixtures isolate the ordering contract from changing news and profile counts.
function fixture(){
 const person=(id,checked)=>({...data.people[0],id,name:id,aliases:[],checked,works:[{title:'Work '+id,url:'https://example.org/'+id,relation:'共同作者'},{title:'Second '+id,url:'https://example.org/'+id+'/two',relation:'项目贡献者'}]});
 const event=(id,date,people)=>({...data.events[0],id,title:id,date,people,checked:'2026-10-27'});
 return {...data,people:[person('unknown','2026-10-27'),person('old','2026-10-27'),person('recent-b','2026-10-01'),person('recent-a','2026-10-01')],events:[event('old-event','2026-10-20',['old']),event('recent-event','2026-10-26',['recent-a','recent-b']),event('future-event','2099-01-01',['unknown']),event('invalid-event','2026-02-30',['unknown'])]};
}
test('profile cards sort by newest real event, not profile or source check dates',()=>{
 const f=fixture(),at=Date.parse('2026-10-27T00:00:00Z'),before=JSON.stringify(f);
 assert.deepEqual(P.rows(f,read(''),new Set(),at).map(p=>p.id),['recent-a','recent-b','old','unknown']);
 assert.equal(JSON.stringify(f),before);
 f.people.reverse();assert.deepEqual(P.rows(f,read(''),new Set(),at).map(p=>p.id),['recent-a','recent-b','old','unknown']);
 assert.deepEqual(P.rows(f,read('following=1'),new Set(['old','recent-b']),at).map(p=>p.id),['recent-b','old']);
});
test('compact directory cards preview current evidence while profiles keep complete works',()=>{
 const f=fixture(),at=Date.parse('2026-10-27T00:00:00Z'),state=read('view=directory'),html=P.page(f,state,new Set(),at);
 assert.deepEqual([...html.matchAll(/data-person-card="([^"]+)"/g)].map(m=>m[1]),['recent-a','recent-b','old','unknown']);
 assert(html.includes('最近更新优先'));assert(!html.includes('编辑编选顺序'));
 assert.equal((html.match(/class="pp-card pp-card-compact"/g)||[]).length,f.people.length);
 for(const p of f.people){const card=P.card(p,f,state,new Set(),at);assert(card.includes('接下来验证'));assert(!card.includes('pp-work-preview'));const profile=P.profile(p,f,state,new Set(),at);for(const w of p.works)assert(profile.includes('href="'+w.url+'"'));}
});
test('sort and visible latest event share one clock, including Beijing midnight',()=>{
 const f=fixture();f.events.push({...f.events[0],id:'new-day',title:'MIDNIGHT-EVENT',date:'2026-10-28',people:['unknown']});
 const before=Date.parse('2026-10-27T15:59:00Z'),after=Date.parse('2026-10-27T16:01:00Z');
 assert.notEqual(P.rows(f,read(''),new Set(),before)[0].id,'unknown');assert.equal(P.rows(f,read(''),new Set(),after)[0].id,'unknown');
 assert(!P.page(f,read('view=directory'),new Set(),before).includes('MIDNIGHT-EVENT'));assert(P.page(f,read('view=directory'),new Set(),after).includes('MIDNIGHT-EVENT'));
 assert.equal(P.rows({...f,people:[],events:[]},read(''),new Set(),after).length,0);
});
test('Elon Musk uses first-party role and statement evidence with an explicit boundary',()=>{
 const elon=data.people.find(p=>p.id==='elon-musk');assert(elon);assert(elon.roles.includes('founder'));assert(elon.sources.every(s=>/^https:\/\/(x\.ai|ir\.tesla\.com)\//.test(s.url)));
 const event=data.events.find(e=>e.id==='elon-xai-onegov-20250925');assert(event);assert.equal(event.date,'2025-09-25');assert(event.source.includes('直接引语'));assert(event.boundary.includes('不是独立效果验证'));
 assert(P.page(data,read('person=elon-musk'),new Set(),Date.parse('2026-10-30T03:00:00Z')).includes('OneGov'));
});
test('rendering never mutates source evidence',()=>{assert.equal(JSON.stringify(data),snapshot)});
console.log(`People: ${n} behavioral checks passed.`);
