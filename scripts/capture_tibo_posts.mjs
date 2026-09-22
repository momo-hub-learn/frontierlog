#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import process from 'node:process';
import { chromium } from 'playwright';

const ROOT=path.resolve(path.dirname(new URL(import.meta.url).pathname),'..');
const dataPath=path.join(ROOT,'data','resets.json');
const shotDir=path.join(ROOT,'assets','tibo');
const requireAll=process.argv.includes('--require-all');
const force=process.argv.includes('--force');
const data=JSON.parse(fs.readFileSync(dataPath,'utf8'));
fs.mkdirSync(shotDir,{recursive:true});

const clean=s=>String(s||'').toLowerCase().replace(/@[a-z0-9_]+/g,' ').replace(/[^a-z0-9]+/g,' ').trim();
function expectedTokens(text){
  const stop=new Set(['the','and','but','also','this','that','with','from','have','has','was','are','for','you','your','its','it','all','one','will','who']);
  return clean(text).split(/\s+/).filter(x=>x.length>2&&!stop.has(x)).slice(0,8);
}
function plausible(body,event){
  const low=clean(body);
  const tokens=expectedTokens(event.original_text||event.summary);
  const hits=tokens.filter(t=>low.includes(t)).length;
  return /thsottiaux|tibo/.test(low)&&hits>=Math.min(3,Math.max(1,tokens.length));
}
async function captureOne(browser,event){
  const id=String(event.post_id);
  const postUrl=event.evidence?.post_url||`https://x.com/thsottiaux/status/${id}`;
  const out=path.join(shotDir,`${id}.png`);
  const page=await browser.newPage({viewport:{width:760,height:1100},deviceScaleFactor:1.5,locale:'en-US',colorScheme:'light'});
  const candidates=[
    `https://platform.twitter.com/embed/Tweet.html?id=${encodeURIComponent(id)}&dnt=true&theme=light`,
    postUrl
  ];
  let last='';
  try{
    for(const url of candidates){
      try{
        await page.goto(url,{waitUntil:'domcontentloaded',timeout:45000});
        await page.waitForTimeout(2500);
        const body=await page.locator('body').innerText({timeout:5000}).catch(()=> '');
        last=body.slice(0,500);
        if(!plausible(body,event))continue;
        await page.addStyleTag({content:'html,body{background:#fff!important} body{margin:0!important}'}).catch(()=>{});
        const root=page.locator('article').filter({hasText:(event.original_text||'').replace(/^@[A-Za-z0-9_]+\s*/,'').slice(0,28)}).first();
        if(await root.count()){
          await root.screenshot({path:out,type:'png'});
        }else{
          const bodyLoc=page.locator('body');
          await bodyLoc.screenshot({path:out,type:'png'});
        }
        const bytes=fs.readFileSync(out);
        if(bytes.length<8000)throw new Error('screenshot_too_small');
        const digest=crypto.createHash('sha256').update(bytes).digest('hex');
        event.evidence={
          post_url:postUrl,
          screenshot:`assets/tibo/${id}.png`,
          screenshot_status:'captured',
          captured_at:new Date().toISOString().replace(/\.\d{3}Z$/,'Z'),
          capture_method:'platform_twitter_embed',
          source:'first_party_x_page',
          sha256:digest
        };
        return {id,bytes:bytes.length};
      }catch(err){
        last=String(err?.message||err);
      }
    }
    throw new Error(`no_valid_first_party_render: ${last}`);
  }finally{
    await page.close();
  }
}

const targets=data.events.filter(e=>e.post_id&&e.evidence&&((force)||e.evidence.screenshot_status!=='captured'));
if(!targets.length){
  console.log('No pending Tibo screenshots.');
  process.exit(0);
}
const browser=await chromium.launch({headless:true});
const failures=[];
try{
  for(const event of targets){
    try{
      const r=await captureOne(browser,event);
      console.log(`captured ${r.id} ${r.bytes} bytes`);
    }catch(err){
      failures.push([event.post_id,String(err?.message||err)]);
      event.evidence={
        post_url:`https://x.com/thsottiaux/status/${event.post_id}`,
        screenshot:null,
        screenshot_status:'unavailable',
        captured_at:null,
        capture_method:null,
        source:'first_party_x_page',
        sha256:null,
        capture_error:String(err?.message||err).slice(0,240)
      };
      console.error(`failed ${event.post_id}: ${err?.message||err}`);
    }
  }
}finally{
  await browser.close();
}
fs.writeFileSync(dataPath,JSON.stringify(data,null,2)+'\n');
if(failures.length)console.warn(JSON.stringify({unavailable:failures},null,2));
if(requireAll){
  const terminal=data.events.filter(e=>e.post_id&&e.evidence).every(e=>['captured','unavailable'].includes(e.evidence.screenshot_status));
  if(!terminal)process.exit(2);
}
