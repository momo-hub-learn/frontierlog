'use strict';
/* Activity header: verified event data, honest time states, and local calendar export. */
const ActivityHero = (() => {
 const DAY = 86400000;
 const h = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const https = x => {try {const u = new URL(x); return u.protocol === 'https:' && !u.username && !u.password ? u.href : ''} catch {return ''}};
 const stamp = x => typeof x === 'string' && /T.*(?:Z|[+-]\d\d:\d\d)$/.test(x) && Number.isFinite(Date.parse(x)) ? Date.parse(x) : null;
 const dateOK = x => typeof x === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(x) && Number.isFinite(Date.parse(x)) && new Date(x).toISOString().slice(0,10) === x;
 function dayIn(now, zone = 'Asia/Shanghai') {
  try {return new Intl.DateTimeFormat('en-CA', {timeZone:zone, year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(now))} catch {return new Date(now).toISOString().slice(0,10)}
 }
 function events(radar, config) {
  const sources = new Map((radar.sources || []).map(s => [s.id,s]));
  return (radar.events || []).map(e => {
   const meta = config.events?.[e.id] || {};
   // A newly changed source date invalidates any old reviewed time/artwork override.
   const extra = meta.date === e.date ? meta : {};
   return {...e,...extra,status:e.status,source:sources.get(e.source_id) || {}};
  });
 }
 function phase(e, now = Date.now()) {
  if (['cancelled','canceled','postponed'].includes(e.status)) return 'unavailable';
  if (e.status === 'replay') return 'replay';
  const start = stamp(e.start_at), end = stamp(e.end_at);
  if (start !== null) {
   if (start > now) return 'upcoming';
   // Never infer "live" from a countdown alone, or extend it indefinitely.
   if (e.status === 'live' && end !== null && end > now) return 'live';
   if (end !== null && end <= now) return 'ended';
   return now - start < 6*3600000 ? 'started' : 'ended';
  }
  if (!dateOK(e.date)) return 'unknown';
  const today = dayIn(now, e.time_zone || 'Asia/Shanghai');
  return e.date > today ? 'upcoming' : e.date === today ? 'today' : 'ended';
 }
 function select(radar, config = {}, now = Date.now()) {
  const all = events(radar,config).filter(e => e.source.authority === 'official' && https(e.url));
  const active = all.find(e => ['live','started','today'].includes(phase(e,now)));
  if (active) return {kind:'event',item:active,mode:phase(active,now)};
  const next = all.filter(e => phase(e,now) === 'upcoming').sort((a,b) =>
   (stamp(a.start_at) ?? Date.parse(a.date)) - (stamp(b.start_at) ?? Date.parse(b.date)) || a.id.localeCompare(b.id))[0];
  if (next) return {kind:'event',item:next,mode:'upcoming'};
  const sources = new Map((radar.sources || []).map(s => [s.id,s]));
  const picks = (radar.media_items || []).filter(m => {
   const age = (now - Date.parse(m.published))/DAY, src = sources.get(m.source_id);
   return m.editor_pick === true && dateOK(m.published) && age >= 0 && age <= 30 && https(m.url) &&
    ['official','first-party','creator-page'].includes(src?.authority);
  }).sort((a,b) => b.published.localeCompare(a.published));
  if (picks[0]) return {kind:'media',item:{...picks[0],source:sources.get(picks[0].source_id)},mode:(now-Date.parse(picks[0].published))/DAY <= 7 ? 'week' : 'recent'};
  return {kind:'empty',mode:'empty'};
 }
 function remaining(e, now = Date.now()) {
  const mode = phase(e,now), ms = stamp(e.start_at);
  if (mode === 'live') return '官方已确认直播';
  if (mode === 'started') return '以官方现场为准';
  if (mode === 'today') return '今日 · 时间待公布';
  if (mode !== 'upcoming') return '已过开场时间';
  if (ms === null) return '日期已定';
  const seconds = Math.max(0,Math.ceil((ms-now)/1000));
  if (seconds >= 86400) return '约 '+Math.floor(seconds/86400)+' 天后';
  if (seconds >= 3600) return Math.floor(seconds/3600)+' 小时后';
  return Math.max(1,Math.ceil(seconds/60))+' 分钟后';
 }
 function times(e) {
  if (stamp(e.start_at) === null) return {primary:e.date+' · 时间待公布',secondary:'活动日期以举办地为准'};
  const d = new Date(e.start_at), fmt = zone => new Intl.DateTimeFormat('zh-CN',{timeZone:zone,month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(d).replace(/\//g,'/');
  let local = '';
  try {local = fmt(e.time_zone || 'UTC')} catch {local = fmt('UTC')}
  return {primary:'北京时间 '+fmt('Asia/Shanghai'),secondary:'当地 '+local+' · '+(e.location || e.time_zone || 'UTC')};
 }
 const escapeICS = x => String(x ?? '').replace(/\\/g,'\\\\').replace(/\r\n|\r|\n/g,'\\n').replace(/;/g,'\\;').replace(/,/g,'\\,');
 function fold(line) {
  let out = '', row = '', bytes = 0;
  for (const ch of line) {
   const size = new TextEncoder().encode(ch).length;
   if (bytes+size > 75) {out += row+'\r\n'; row = ' '; bytes = 1}
   row += ch; bytes += size;
  }
  return out+row;
 }
 function calendar(e, now = Date.now()) {
  if (!['upcoming','today'].includes(phase(e,now)) || !dateOK(e.date) || !https(e.url)) return null;
  const start = stamp(e.start_at), dt = n => new Date(n).toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'');
  const lines = ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//AI Coordinates//Event Reminder//ZH','CALSCALE:GREGORIAN','METHOD:PUBLISH','BEGIN:VEVENT',
   'UID:'+String(e.id).replace(/[^a-zA-Z0-9_-]/g,'')+'@frontierlog.github.io','DTSTAMP:'+dt(now),
   start === null ? 'DTSTART;VALUE=DATE:'+e.date.replaceAll('-','') : 'DTSTART:'+dt(start),
   'SUMMARY:'+escapeICS(e.title), 'URL:'+https(e.url),
   'DESCRIPTION:'+escapeICS('AI坐标收录；以官方最新安排为准。日历文件不会自动同步改期。'+(start===null?'仅记录活动日期，具体时刻尚未公布。':'开始前15分钟提醒。')+' 官方来源：'+(https(e.time_source_url)||https(e.url))),
   'LOCATION:'+escapeICS(e.location || '官方线上入口')];
  const end = stamp(e.end_at);
  if (start !== null && end !== null && end > start) lines.push('DTEND:'+dt(end));
  if (start !== null) lines.push('BEGIN:VALARM','TRIGGER:-PT15M','ACTION:DISPLAY','DESCRIPTION:'+escapeICS(e.title+' 即将开始'),'END:VALARM');
  lines.push('END:VEVENT','END:VCALENDAR');
  return lines.map(fold).join('\r\n')+'\r\n';
 }
 function art(e, hero = false) {
  const path = e.artwork?.local;
  const valid = typeof path === 'string' && /^assets\/activity\/[a-z0-9-]+\.webp$/.test(path);
  return '<span class="ah-art '+(hero?'ah-art-hero':'')+'" aria-hidden="true"><span class="ah-art-fallback">'+h(e.short_name || e.source?.publisher || 'AI')+'</span>'+
   (valid?'<img src="'+h(path)+'" alt="" width="640" height="336" '+(hero?'fetchpriority="high"':'loading="lazy"')+' decoding="async">':'')+'</span>';
 }
 function featureHTML(f, now = Date.now()) {
  if (f.kind === 'empty') return '<aside class="ah-feature ah-feature-empty"><span class="ah-eyebrow">等待下一场官宣</span><h2>好内容，不必等发布会</h2><p>先看官方技术文章与深度对谈。</p><a class="ah-secondary" href="#/activity?type=technical">查看技术深读 <span aria-hidden="true">↗</span></a></aside>';
  const e = f.item, event = f.kind === 'event';
  const label = event ? ({upcoming:'下一场重点事件',live:'官方直播中',started:'开场时间已到',today:'今天的重点事件'}[f.mode]) : f.mode === 'week' ? '本周值得看' : '近期值得看';
  const t = event ? times(e) : {primary:e.published.replaceAll('-','.')+' · '+e.source.name,secondary:''};
  return '<aside class="ah-feature" data-ah-feature="'+h(e.id)+'"><div class="ah-feature-top"><span class="ah-eyebrow">'+label+'</span><span class="ah-countdown" data-ah-countdown>'+h(event?remaining(e,now):'编辑精选')+'</span></div><div class="ah-feature-main"><div class="ah-feature-copy"><span class="ah-provider">'+h(e.source.publisher || e.source.name)+'</span><h2><a href="'+h(https(e.url))+'" target="_blank" rel="noopener noreferrer">'+h(e.display_title || e.title)+'</a></h2><time class="ah-start"'+(e.start_at?' datetime="'+h(e.start_at)+'"':'')+'>'+h(t.primary)+'</time>'+(t.secondary?'<small class="ah-local">'+h(t.secondary)+'</small>':'')+'<p class="ah-feature-topics">'+h((e.tags||[]).filter(tag => tag!==e.source.publisher).slice(0,3).join(' · ') || e.value_hint || '查看一手材料')+'</p></div>'+art(e,true)+'</div><div class="ah-feature-actions">'+(event&&['upcoming','today'].includes(f.mode)?'<button type="button" class="ah-calendar" data-ah-calendar="'+h(e.id)+'" title="下载日历文件；导入后提醒生效，不会自动同步改期"><span aria-hidden="true">＋</span> 添加日历</button>':'')+'<a class="ah-secondary" href="'+h(https(e.url))+'" target="_blank" rel="noopener noreferrer">'+(event?'官方详情':'阅读原文')+' <span aria-hidden="true">↗</span></a>'+(event&&e.time_source_url?'<a class="ah-proof" href="'+h(https(e.time_source_url))+'" target="_blank" rel="noopener noreferrer" title="时间核对：'+h(e.checked)+'">官方时间已核对</a>':'')+'</div></aside>';
 }
 function introHTML(radar, config) {
  const sourceCount = new Set((radar.sources||[]).map(s=>s.id)).size;
  const rss = (radar.sources||[]).filter(s=>s.sync==='rss' && s.feed_url).length;
  const hours = Number(radar.sync?.interval_minutes)/60;
  const cadence = rss && hours > 0 ? 'RSS 每 '+hours+' 小时检查' : '按来源核验更新';
  return '<div class="ah-intro"><h1>AI 前沿现场</h1><p class="ah-dek">追踪重要发布、技术深读与一手对谈。</p><div class="ah-metadata"><span><i aria-hidden="true">◈</i> '+sourceCount+' 个精选来源</span><span><i aria-hidden="true">◷</i> '+h(cadence)+'</span><details class="ah-rules"><summary><span aria-hidden="true">ⓘ</span> 收录规则</summary><div class="ah-rules-panel"><strong>来源与更新方式</strong><p>'+h(radar.sync?.note || '官方发布与技术文章按一手来源核验，媒体观点与发布事实分开记录。')+'</p><strong>如何选右侧内容</strong><p>优先展示本站跟踪的官方活动；直播需官方状态确认。没有未来活动时，展示近 7 天编辑精选，再退到近 30 天内容。不把旧消息标成“本周”。</p><strong>论文与日历</strong><p>正式录用或发表后，才标注 CCF 分级或 Nature / Science 等刊物；arXiv 只标预印本。日历提醒须下载导入，不会自动同步改期。</p><small>部分 RSS 源自动检查；不代表全部内容每 2 小时更新。</small></div></details></div></div>';
 }
 function eventHTML(e,now) {
  const mode=phase(e,now), labels={upcoming:'待开始',today:'今日',live:'直播中',started:'已到开场时间',ended:'已结束',replay:'回放',unknown:'时间待核验',unavailable:'安排变更'};
  return '<a class="v2-event-card ah-event '+h(mode)+'" data-ah-date="'+h(e.date)+'" data-ah-id="'+h(e.id)+'" href="'+h(https(e.url))+'" target="_blank" rel="noopener noreferrer">'+art(e)+'<div class="ah-event-copy"><div class="ah-event-meta"><time>'+h(e.date.slice(5).replace('-','月')+'日')+'</time><small>'+h(e.date.slice(0,4))+'</small><span>'+h(labels[mode])+'</span></div><h3>'+h(e.title)+'</h3><p>'+h(e.short_summary || e.summary)+'</p><div class="v2-radar-tags">'+(e.tags||[]).slice(0,3).map(tag=>'<span>'+h(tag)+'</span>').join('')+'</div></div><span class="ah-out" aria-hidden="true">↗</span></a>';
 }
 return {events,phase,select,remaining,times,calendar,fold,featureHTML,introHTML,eventHTML,https};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = ActivityHero;

if (typeof document !== 'undefined' && typeof APP !== 'undefined') (() => {
 const radar=APP.activity_radar||{},config=APP.activity_feature||{};
 let layout='grid',sort='time',currentFeature=null;
 try {layout=localStorage.getItem('aic.activity.layout')==='list'?'list':'grid'} catch {}
 const root=()=>document.getElementById('content');
 function orderCards() {
  const host=root();if(!host?.classList.contains('ah-page'))return;
  host.querySelectorAll('.v2-media-grid,.v2-event-grid').forEach(grid=>{
   const cards=[...grid.children];
   cards.sort((a,b)=>{
    const ea=(radar.events||[]).find(e=>e.id===a.dataset.ahId),eb=(radar.events||[]).find(e=>e.id===b.dataset.ahId);
    if(ea&&eb){const list=ActivityHero.events(radar,config),byid=new Map(list.map(e=>[e.id,e]));const active=e=>['upcoming','today','live','started'].includes(ActivityHero.phase(byid.get(e.id)));const aa=active(ea),bb=active(eb);return Number(bb)-Number(aa)||(aa?ea.date.localeCompare(eb.date):eb.date.localeCompare(ea.date))}
    if(sort==='picks'){const p=Number(b.classList.contains('editor-pick'))-Number(a.classList.contains('editor-pick'));if(p)return p}
    return (b.querySelector('time')?.textContent||'').localeCompare(a.querySelector('time')?.textContent||'');
   });
   cards.forEach(card=>grid.appendChild(card));
  });
 }
 function refreshFeature() {
  if(state.view!=='activity'||document.hidden)return;
  const slot=root()?.querySelector('[data-ah-feature-slot]');if(!slot)return;
  const next=ActivityHero.select(radar,config);
  const same=currentFeature?.item?.id===next.item?.id&&currentFeature?.mode===next.mode;
  if(same&&next.kind==='event'){const count=slot.querySelector('[data-ah-countdown]');if(count)count.textContent=ActivityHero.remaining(next.item)}
  else if(!same)slot.innerHTML=ActivityHero.featureHTML(next);
  currentFeature=next;
 }
 function enhance() {
  const host=root();if(!host)return;
  host.classList.toggle('ah-page',state.view==='activity');
  if(state.view!=='activity'){delete host.dataset.ahLayout;return}
  const intro=host.querySelector('.v2-activity-intro');
  if(intro){
   currentFeature=ActivityHero.select(radar,config);
   intro.outerHTML='<header class="ah-hero">'+ActivityHero.introHTML(radar,config)+'<div data-ah-feature-slot>'+ActivityHero.featureHTML(currentFeature)+'</div></header>';
  }
  host.dataset.ahLayout=layout;
  const byURL=new Map(ActivityHero.events(radar,config).map(e=>[ActivityHero.https(e.url),e]));
  host.querySelectorAll('.v2-event-card:not(.ah-event)').forEach(card=>{const e=byURL.get(ActivityHero.https(card.href));if(e)card.outerHTML=ActivityHero.eventHTML(e,Date.now())});
  const tabs=host.querySelector('.v2-radar-tabs');
  if(tabs&&!tabs.closest('.ah-filterbar')){
   const bar=document.createElement('div');bar.className='ah-filterbar';tabs.before(bar);bar.appendChild(tabs);
   bar.insertAdjacentHTML('beforeend','<div class="ah-display-tools"><label><span class="sr-only">内容排序</span><select data-ah-sort aria-label="内容排序"><option value="time">时间优先</option><option value="picks">编辑精选</option></select></label><div class="ah-view-switch" role="group" aria-label="显示方式"><button type="button" data-ah-view="grid" aria-label="卡片视图" title="卡片视图">'+icon('grid')+'</button><button type="button" data-ah-view="list" aria-label="列表视图" title="列表视图">'+icon('list')+'</button></div></div>');
  }
  host.querySelectorAll('[data-ah-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.ahView===layout)));
  const sorter=host.querySelector('[data-ah-sort]');if(sorter)sorter.value=sort;
  orderCards();
 }
 const baseRender=renderMain;
 renderMain=function(){baseRender();enhance()};
 document.addEventListener('error',e=>{if(e.target.matches?.('.ah-art img')){e.target.hidden=true;e.target.parentElement.classList.add('is-fallback')}},true);
 document.addEventListener('click',e=>{
  const view=e.target.closest('[data-ah-view]');
  if(view){layout=view.dataset.ahView;try{localStorage.setItem('aic.activity.layout',layout)}catch{};enhance();return}
  const btn=e.target.closest('[data-ah-calendar]');
  if(btn){
   const event=ActivityHero.events(radar,config).find(x=>x.id===btn.dataset.ahCalendar);
   const text=event&&ActivityHero.calendar(event);
   if(!text){toast('活动时间或状态已变化，请查看官方安排。');refreshFeature();return}
   const url=URL.createObjectURL(new Blob([text],{type:'text/calendar;charset=utf-8'}));
   const a=document.createElement('a');a.href=url;a.download=event.id+'.ics';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
   toast('日历已生成，导入后提醒生效；改期不会自动同步。');return;
  }
  document.querySelectorAll('.ah-rules[open]').forEach(d=>{if(!d.contains(e.target))d.open=false});
 });
 document.addEventListener('change',e=>{if(e.target.matches('[data-ah-sort]')){sort=e.target.value;orderCards()}});
 document.addEventListener('keydown',e=>{if(e.key==='Escape')document.querySelectorAll('.ah-rules[open]').forEach(d=>{d.open=false;d.querySelector('summary').focus()})});
 document.addEventListener('visibilitychange',refreshFeature);
 window.addEventListener('pageshow',refreshFeature);
 setInterval(refreshFeature,60000);
 enhance();
})();
