'use strict';
(()=>{
const MAX_AGE_HOURS=6;
function stale(raw){
  const t=Date.parse(String(raw||''));
  return !Number.isFinite(t)||(Date.now()-t)/36e5>MAX_AGE_HOURS;
}
function note(section,text,cls){
  if(!section||section.querySelector('.'+cls))return;
  const n=document.createElement('div');
  n.className=cls;
  n.textContent=text;
  section.prepend(n);
}
function apply(){
  if(stale(APP.github_hot&&APP.github_hot.checked_at)){
    document.querySelectorAll('.gh-preview').forEach(section=>{
      const list=section.querySelector('.gh-preview-list');
      if(list)list.hidden=true;
      note(section,'GitHub 热榜快照已超过 6 小时：旧排名已隐藏，请以官方 Today 榜为准。','trend-stale-card');
    });
    document.querySelectorAll('.gh-inline').forEach(section=>{
      note(section,'快照已过期：以下仅保留上次核验结果，不代表当前 GitHub Trending。','trend-stale-banner');
      const title=section.querySelector('.gh-inline-head strong');
      if(title)title.textContent='GitHub Trending · 上次核验快照';
      section.querySelectorAll('.gh-delta span').forEach(x=>x.textContent='核验时 Today Star');
    });
  }
  const hf=APP.huggingface_hot||{};
  if(stale(hf.web_fetched_at||hf.checked_at)){
    document.querySelectorAll('.hf-inline').forEach(section=>{
      note(section,'快照已过期：以下仅保留上次核验结果，不代表当前 Hugging Face Trending。','trend-stale-banner');
      const title=section.querySelector('.hf-inline-head strong');
      if(title)title.textContent='Hugging Face Models · 上次核验快照';
      section.querySelectorAll('.hf-score span').forEach(x=>{if(x.textContent.startsWith('API Trending'))x.textContent='核验时 API Trending'});
    });
  }else if(stale(hf.api_fetched_at||hf.checked_at)){
    document.querySelectorAll('.hf-inline .hf-score span').forEach(x=>{if(x.textContent==='API Trending')x.textContent='API Trending（旧）'});
  }
}
const baseRenderMain=renderMain;
renderMain=function(){baseRenderMain();queueMicrotask(apply)};
apply();
})();
