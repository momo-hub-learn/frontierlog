'use strict';
/* True chronological timeline: date groups + verified clock nodes. Never invent a time. */
(()=>{
const WEEK=['星期日','星期一','星期二','星期三','星期四','星期五','星期六'];
function dtInfo(x){
  const raw=x.published_at||x.first_seen_at||x.captured_at||'';
  if(raw){
    const m=String(raw).match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2})/);
    if(m)return {date:m[1],time:m[2]+':'+m[3],kind:x.published_at?'source':'seen',label:x.published_at?'原始时间':'首次收录'};
  }
  if(x.published_time&&/^\d{2}:\d{2}$/.test(x.published_time))return {date:x.published,time:x.published_time,kind:'source',label:'原始时间'};
  return {date:x.published,time:null,kind:'date',label:'日期已核对'};
}
function weekday(date){const d=new Date(date+'T12:00:00Z');return WEEK[d.getUTCDay()]||''}
function sortWithinDay(list){
  return [...list].sort((a,b)=>{
    const A=dtInfo(a),B=dtInfo(b);
    if(A.time&&B.time)return B.time.localeCompare(A.time)||b.heat-a.heat;
    if(A.time)return -1;
    if(B.time)return 1;
    return b.heat-a.heat||a.id.localeCompare(b.id)
  })
}
function dayTitle(date){const m=Number(date.slice(5,7)),d=Number(date.slice(8,10));return m+'月'+d+'日'}
function timelineCard(x){
  const t=dtInfo(x);
  const time=t.time||'日期';
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
    <div class="v10-section-head"><div><p class="eyebrow">DAILY / VERIFIED TIME</p><h2>分时热点</h2><p>按时间轴看每天发生了什么；有可靠时刻才显示小时，没有就落在“日期已核对”节点。</p></div>
    <div class="intraday-legend"><span><i class="source"></i>原始时间</span><span><i class="seen"></i>首次收录</span><span><i class="date"></i>仅日期</span></div></div>
    ${chronology(v10HotByTime(rows))}
  </section>`;
};
const oldFeed=feedPage;
feedPage=function(){
  const html=oldFeed();
  return html.replace('最后按时间浏览通用 AI 变化。','最后按时间轴浏览全部精选；没有可靠小时的信息只标日期。').replace('热点时间线','全部热点');
};
if(state.view==='feed'||state.view==='hot'){lastMain='';renderMain()}
})();