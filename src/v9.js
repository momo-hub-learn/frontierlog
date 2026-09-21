'use strict';
/* v0.9 editorial landing: one brand, one daily timeline. Industry gateways stay in /topics. */
const AIC_BRAND='AI坐标';
const AIC_VERTICAL_ONLY=new Set(['anthropic-biomolecular-20260917','anthropic-lsvp-20260917','quotient-formulation-20260917','asml-tsmc-mask-20260908','taiwan-packaging-park-20260921']);
function aicCuratedRows(){return HOT.items.filter(x=>!AIC_VERTICAL_ONLY.has(x.id)).sort((a,b)=>b.published.localeCompare(a.published)||b.heat-a.heat)}
function aicDateLabel(date){
  const latest=aicCuratedRows()[0]?.published;
  if(date===HOT.checked)return '今天';
  if(date===latest)return '最新';
  return date.slice(5).replace('-','月')+'日';
}
function aicTimeline(){
  const rows=aicCuratedRows();
  const grouped={}; rows.forEach(x=>(grouped[x.published]??=[]).push(x));
  return `<div class="aic-feed-head"><div><p class="eyebrow"><span class="coordinate-dot"></span> 每日精选 / ${esc(HOT.checked.replaceAll('-','.'))}</p><h1>今天，AI 走到哪了？</h1><p>按时间看每天热点。垂类行业内容单独放在「主题」，精选只保留通用 AI 变化。</p></div><a class="button" href="#/hot">查看热点榜 ${icon('arrow')}</a></div>
  <div class="aic-feed-tools"><div class="aic-feed-note">${icon('clock')} ${rows.length} 条已核对热点 · 保留原始发布日期</div><div class="aic-feed-links"><a href="#/models">模型榜</a><a href="#/benchmarks">Benchmark</a><a href="#/topics">垂类主题</a></div></div>
  <div class="aic-timeline">${Object.entries(grouped).map(([date,list],gi)=>`<section class="aic-day"><div class="aic-day-date"><b>${aicDateLabel(date)}</b><span>${date.replaceAll('-','.')}</span></div><div class="aic-day-list">${list.map((x,i)=>`<article class="aic-story"><div class="aic-story-index">${String(i+1).padStart(2,'0')}</div><div class="aic-story-main"><div class="aic-story-meta"><span class="h-cat">${icon(H_ICON[x.category]||'sparkles')}${esc(HOT_CATS.get(x.category).title)}</span><span>${esc(x.source)}</span><span>${esc(x.source_kind)}</span></div><button class="aic-story-title" data-ha="detail" data-id="${x.id}">${esc(x.title)}</button><p>${esc(x.summary)}</p><div class="aic-story-foot"><button data-ha="detail" data-id="${x.id}">为什么值得看 ${icon('arrow')}</button><a href="${safeLink(x.url)}" target="_blank" rel="noopener noreferrer">原始来源 ${icon('external')}</a></div></div><div class="aic-story-heat"><span class="aic-heat-value">${x.heat}</span><span class="aic-heat-label">热度</span>${hTrend(x)}</div></article>`).join('')}</div></section>`).join('')}</div>`;
}
feedPage=function(){return aicTimeline()};
// Keep the landing count aligned with the new source instead of the vertical article count.
const aicRenderNav=renderNav;
renderNav=function(){aicRenderNav();const feed=$('.navitem[href="#/feed"] small');if(feed)feed.textContent=String(aicCuratedRows().length).padStart(2,'0')};
// Bootstrap runs before this late visual/editorial override, so refresh the landing once.
if(state.view==='feed'){lastMain='';renderMain()}
