'use strict';
/* Chronological timeline: keep the verified release date group, but always show a concrete clock when one is known. */
(()=>{
const WEEK=['星期日','星期一','星期二','星期三','星期四','星期五','星期六'];
// Render offset-aware timestamps in Beijing time (+08:00), independent of browser locale.
// Unzoned timestamps remain as written and are explicitly marked as ambiguous.
function stampParts(raw){
  const value=String(raw||'').trim();
  const m=value.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2})(?::\d{2}(?:\.\d+)?)?(Z|[+-]\d{2}:\d{2})?$/i);
  if(!m||Number(m[2])>23||Number(m[3])>59)return null;
  if(m[4]){
    const n=Date.parse(value.replace(' ','T'));
    if(!Number.isFinite(n))return null;
    const local=new Date(n+8*60*60*1000);
    return {date:local.toISOString().slice(0,10),time:local.toISOString().slice(11,16),zone:'北京时间'};
  }
  return {date:m[1],time:m[2]+':'+m[3],zone:'时区未注明'};
}
function shortDate(date){return Number(date.slice(5,7))+'/'+Number(date.slice(8,10))}
function dtInfo(x){
  const date=x.published;
  const source=stampParts(x.published_at);
  if(source)return {date:date||source.date,time:source.time,kind:'source',label:'原始时间 · '+source.zone+(source.date!==date?' · '+shortDate(source.date):'')};
  if(x.published_time&&/^\d{2}:\d{2}$/.test(x.published_time))return {date,time:x.published_time,kind:'source',label:'原始时间 · 时区未注明'};
  const seen=stampParts(x.first_seen_at||x.captured_at);
  if(seen)return {date:date||seen.date,time:seen.time,kind:'seen',label:'首次收录 · '+seen.zone+(seen.date!==date?' · '+shortDate(seen.date):'')};
  return {date,time:null,kind:'date',label:'时间待核验'};
}
function weekday(date){const d=new Date(date+'T12:00:00Z');return WEEK[d.getUTCDay()]||''}
function sortMoment(x){
  const raw=x.published_at||x.first_seen_at||x.captured_at;
  if(raw&&stampParts(raw)?.zone==='北京时间'){const n=Date.parse(raw.replace(' ','T'));if(Number.isFinite(n))return n}
  if(x.published_time&&/^\d{2}:\d{2}$/.test(x.published_time)){
    const n=Date.parse(x.published+'T'+x.published_time+':00+08:00');
    if(Number.isFinite(n))return n
  }
  return 0
}
function sortWithinDay(list){
  return [...list].sort((a,b)=>sortMoment(b)-sortMoment(a)||b.heat-a.heat||a.id.localeCompare(b.id))
}
function dayTitle(date){const m=Number(date.slice(5,7)),d=Number(date.slice(8,10));return m+'月'+d+'日'}
function timelineCard(x){
  const t=dtInfo(x);
  const time=t.time||'--:--';
  return `<article class="intraday-row ${t.kind}">
    <div class="intraday-timecol">
      <time>${esc(time)}</time>
      <small>${esc(t.label)}</small>
      <i class="intraday-node" aria-hidden="true"></i>
    </div>
    <div class="intraday-content">
      <div class="intraday-cardtop">
        <div class="intraday-meta"><span class="h-cat">${icon(H_ICON[x.category]||'sparkles')}${esc(HOT_CATS.get(x.category).title)}</span><span>${esc(x.source)}</span><span>${esc(x.source_kind)}</span></div>
        <div class="intraday-score"><span>AI 评分</span><strong>${x.heat}/100</strong>${hTrend(x)}</div>
      </div>
      <button class="intraday-title" data-ha="detail" data-id="${x.id}">${esc(x.title)}</button>
      <p class="intraday-summary">${esc(x.summary)}</p>
      <div class="intraday-actions"><button data-ha="detail" data-id="${x.id}">为什么值得看 ${icon('arrow')}</button><a href="${safeLink(x.url)}" target="_blank" rel="noopener noreferrer">原始来源 ${icon('external')}</a></div>
    </div>
  </article>`;
}
function chronology(rows,{compact=false}={}){
  const grouped={};
  rows.forEach(x=>{const d=dtInfo(x).date;(grouped[d]??=[]).push(x)});
  const dates=Object.keys(grouped).sort((a,b)=>b.localeCompare(a));
  return `<div class="intraday-timeline ${compact?'compact':''}">${dates.map(date=>{
    const list=sortWithinDay(grouped[date]);
    return `<details class="intraday-day" open>
      <summary>
        <span class="intraday-daymark"><i aria-hidden="true"></i><b>${dayTitle(date)}</b><em>${weekday(date)}</em><small>· ${list.length} 条</small></span>
        ${icon('chevron')}
      </summary>
      <div class="intraday-list">${list.map(timelineCard).join('')}</div>
    </details>`
  }).join('')}</div>`;
}
v10Chronology=function(rows){return chronology(rows)};
v10GeneralTimeline=function(){
  const rows=HOT.items;
  return `<section class="v10-general intraday-general">
    <div class="v10-section-head"><div><p class="eyebrow">DAILY / VERIFIED TIME</p><h2>分时热点</h2><p>优先显示来源发布时间，否则显示首次收录；带时区的时间统一换算为北京时间，未注明时区的原样保留。</p></div>
    <div class="intraday-legend"><span><i class="source"></i>原始时间</span><span><i class="seen"></i>首次收录</span><span><i class="date"></i>待核验</span></div></div>
    ${chronology(v10HotByTime(rows))}
  </section>`;
};
const oldFeed=feedPage;
feedPage=function(){
  const html=oldFeed();
  return html.replace('最后按时间浏览通用 AI 变化。','最后按时间轴浏览全部精选；优先原始时间，没有则显示首次收录时间。').replace('热点时间线','全部热点');
};
if(state.view==='feed'||state.view==='hot'){lastMain='';renderMain()}
})();