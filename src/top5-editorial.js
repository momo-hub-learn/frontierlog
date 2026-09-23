'use strict';
(()=>{
function top5Meta(x){
  return '<div class="top5-meta"><span class="top5-cat">'+icon(H_ICON[x.category]||'sparkles')+esc(HOT_CATS.get(x.category).title)+'</span><span>'+esc(x.source)+'</span><time>'+esc(x.published)+'</time></div>'
}
function top5Band(score){
  if(score>=98)return {label:'爆热',cls:'is-max'};
  if(score>=95)return {label:'高热',cls:'is-high'};
  if(score>=90)return {label:'升温',cls:'is-warm'};
  return {label:'关注',cls:'is-watch'};
}
function top5Legend(){
  return '<div class="top5-legend" aria-label="热度分层"><span class="is-max">爆热 98+</span><span class="is-high">高热 95–97</span><span class="is-warm">升温 90–94</span></div>';
}
function top5Heat(x,large=false){
  const band=top5Band(Number(x.heat)||0);
  return '<div class="top5-heat '+band.cls+' '+(large?'large':'')+'" title="站内热度 '+esc(String(x.heat))+' · '+band.label+'"><span class="top5-heat-tier">'+band.label+'</span><strong>'+esc(String(x.heat))+'</strong>'+hTrend(x)+'</div>'
}
v10Top5=function(){
  const rows=v10HotByHeat(HOT.items).slice(0,5);
  if(!rows.length)return '';
  const [lead,...rest]=rows;
  return '<section class="top5-editorial">'+
    '<div class="top5-head"><div><p class="eyebrow">TOP 5 / CURRENT SIGNALS</p><h2>当前最热</h2><span>此刻最值得继续追踪的 5 个变化</span></div><div class="top5-head-tools">'+top5Legend()+'<a href="#/hot">查看全部热点 '+icon('arrow')+'</a></div></div>'+
    '<div class="top5-layout">'+
      '<a class="top5-lead '+top5Band(lead.heat).cls+'" href="#/hot?item='+encodeURIComponent(lead.id)+'">'+
        '<div class="top5-lead-top"><span class="top5-rank">01</span>'+top5Heat(lead,true)+'</div>'+
        top5Meta(lead)+
        '<h3>'+esc(lead.title)+'</h3>'+
        '<p>'+esc(lead.summary)+'</p>'+
        '<div class="top5-lead-foot"><span>为什么值得看</span>'+icon('arrow')+'</div>'+
      '</a>'+
      '<div class="top5-grid">'+rest.map((x,i)=>
        '<a class="top5-card '+top5Band(x.heat).cls+'" href="#/hot?item='+encodeURIComponent(x.id)+'">'+
          '<div class="top5-card-top"><span class="top5-rank">0'+(i+2)+'</span>'+top5Heat(x)+'</div>'+
          top5Meta(x)+
          '<h3>'+esc(x.title)+'</h3>'+
          '<div class="top5-card-foot"><span>'+esc(x.source_kind)+'</span>'+icon('arrow')+'</div>'+
        '</a>'
      ).join('')+'</div>'+
    '</div>'+
  '</section>'
};
if(state.view==='feed'){lastMain='';renderMain()}
})();