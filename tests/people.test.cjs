'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const P=require('../src/people.js');
const data=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/people.json'),'utf8'));
const snapshot=JSON.stringify(data),now=Date.parse('2026-10-11T10:00:00Z');
const read=q=>P.read('#/people'+(q?'?'+q:''),data);
let n=0;function test(name,f){f();n++;console.log('PASS',name)}
test('URL normalization and round trip',()=>{
 const s=read('view=bad&area=bad&role=bad');assert.equal(s.view,'directory');assert.equal(s.area,'all');assert.equal(s.role,'all');
 const a=read('view=updates&area=agents&following=1&q=VISTA'),b=P.read(P.href(a,{person:'keya-hu'}),data);
 assert.equal(b.q,'VISTA');assert.equal(b.area,'agents');assert.equal(b.following,true);assert.equal(b.person,'keya-hu');
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
});
test('corrupt/unknown local IDs do not become follows',()=>{
 assert.equal(P.followIds({},data).size,0);assert.equal(P.followIds(['tri-dao','tri-dao',{},'unknown'],data).size,1);
});
test('event time is original publication, not review date',()=>{
 const ev=P.events(data,read(''),new Set(),now);assert.equal(ev[0].id,'vista-paper');assert.equal(ev[0].date,'2026-10-01');
 const page=P.page(data,read('view=updates'),new Set(),now);
 assert(page.includes('历史作品与观点'));assert(page.includes('2023.12.01'));assert(page.includes('近 30 日'));
 const future=JSON.parse(snapshot);future.events.push({...future.events[0],id:'future',date:'2099-01-01'});
 assert(!P.events(future,read(''),new Set(),now).some(x=>x.id==='future'));
});
test('following events use exact author relationships',()=>{
 const ev=P.events(data,read('view=updates&following=1'),new Set(['keya-hu']),now);assert.equal(ev.length,1);assert.equal(ev[0].id,'vista-paper');
});
test('profile coauthor links and empty activity are honest',()=>{
 const profile=P.page(data,read('person=qiushi-han'),new Set(),now);
 assert(profile.includes('person=keya-hu'));assert(profile.includes('不据此推断师生关系'));assert(profile.includes('编辑观察 · 不是本人引语'));
 assert(P.page(data,read('person=bret-taylor'),new Set(),now).includes('暂无已收录动态'));
 assert(P.page(data,read('person=unknown')).includes('未找到这个人物档案'));
});
test('text and URLs are escaped even before validation',()=>{
 assert.equal(P.https('javascript:alert(1)'), '');assert.equal(P.https('https://user:pass@example.org/'),'');
 const unsafe=JSON.parse(snapshot);unsafe.people[0].name='<img src=x onerror=alert(1)>';
 const html=P.page(unsafe,read(''));assert(!html.includes('<img src=x'));assert(html.includes('&lt;img'));
 const q=P.page(data,read('q='+encodeURIComponent('<script>alert(1)</script>')));assert(!q.includes('<script>'));assert(q.includes('&lt;script&gt;'));
});
test('Beijing date and invalid calendar dates',()=>{assert.equal(P.today(Date.parse('2026-10-11T16:30:00Z')),'2026-10-12');assert(!P.day('2026-02-30'));assert(P.day('2024-02-29'))});
test('rendering never mutates source evidence',()=>{assert.equal(JSON.stringify(data),snapshot)});
console.log(`People: ${n} behavioral checks passed.`);
