"""Model/reset UI checks. Memory mode intentionally does not claim origin storage or network integration."""
import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];OUT=R/'screenshots';OUT.mkdir(exist_ok=True)
HTML=(R/'dist/index.html').read_text();checks=[];errors=[]
MODEL_DATA=json.loads((R/'data/models.json').read_text());RESET_DATA=json.loads((R/'data/resets.json').read_text())
BOARD_COUNTS={b['id']:len(b['rows']) for b in MODEL_DATA['boards']};AA=next(b for b in MODEL_DATA['boards'] if b['id']=='aa');ARENA=next(b for b in MODEL_DATA['boards'] if b['id']=='arena')
def ok(s):checks.append(s);print('PASS',s,flush=True)
def route(page,s):page.evaluate('(s)=>location.hash=s',s);page.wait_for_timeout(80)
def shot(page,n,full=False):page.evaluate("scrollTo(0,0);document.querySelector('#toast').classList.remove('active')");page.wait_for_timeout(100);page.screenshot(path=str(OUT/n),full_page=full)
with sync_playwright() as p:
 opts={'headless':True}
 if os.getenv('CHROMIUM_EXECUTABLE'):opts['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
 b=p.chromium.launch(**opts);page=b.new_page(viewport={'width':1512,'height':1050},device_scale_factor=1);page.set_default_timeout(45000)
 page.on('pageerror',lambda e:errors.append(str(e)));page.route('**/*',lambda r:r.abort());page.set_content(HTML,wait_until='domcontentloaded');page.set_default_timeout(5000)
 route(page,'#/models');expect(page.locator('[data-model-row]')).to_have_count(BOARD_COUNTS['aa'])
 assert page.locator('#nav .active').inner_text().startswith('模型榜')
 assert float(page.locator('.m-model-name').first.evaluate('e=>getComputedStyle(e).fontSize').replace('px',''))>=15
 shot(page,'models-first-screen.png');shot(page,'models-full.png',True);ok('new navigation, readable AA sample, preserved theme')
 page.locator('[data-ma="metric"][data-id="speed"]').click()
 assert page.evaluate("(()=>{const r=mRows().map(x=>x.speed).filter(Number.isFinite);return r.every((v,i)=>!i||r[i-1]>=v)})()")
 page.locator('[data-ma="metric"][data-id="cost_task"]').click()
 assert page.evaluate("(()=>{const r=mRows().map(x=>x.cost_task).filter(Number.isFinite);return r.every((v,i)=>!i||r[i-1]<=v)})()")
 page.locator('#m-maker').select_option('OpenAI');expect(page.locator('[data-model-row]')).to_have_count(sum(x['maker']=='OpenAI' for x in AA['rows']))
 page.locator('#m-search').fill('Sol');expect(page.locator('[data-model-row]')).to_have_count(sum(x['maker']=='OpenAI' and 'sol' in x['name'].lower() for x in AA['rows']))
 page.locator('#m-search').fill('no-matching-model');expect(page.locator('.m-empty')).to_have_count(1)
 page.locator('#m-search').fill('');page.locator('#m-maker').select_option('all');expect(page.locator('[data-model-row]')).to_have_count(BOARD_COUNTS['aa'])
 ok('metric numeric sorting, provider filter, incremental search and empty-state reset')
 page.locator('[data-ma="star"]').first.click();page.locator('#m-only').check();expect(page.locator('[data-model-row]')).to_have_count(1)
 page.locator('#m-only').uncheck();page.locator('[data-ma="metric"][data-id="intelligence"]').click()
 for x in range(4):page.locator('[data-ma="select"]').nth(x).click()
 expect(page.locator('[data-ma="select"].active')).to_have_count(3)
 page.locator('[data-ma="compare"]').click();expect(page.locator('.m-comparecol')).to_have_count(3)
 with page.expect_download() as dl:page.locator('[data-ma="compare-export"]').click()
 assert '同源' in Path(dl.value.path()).read_text()
 shot(page,'models-compare.png');page.keyboard.press('Escape');ok('local favorites, maximum three configurations, comparison and Markdown export')
 page.locator('.m-model-name').first.click();expect(page.locator('dialog[open]')).to_have_count(1)
 assert 'model=' in page.evaluate('location.hash');expect(page.locator('#modal-body .source-row')).to_have_count(1)
 shot(page,'model-detail.png');page.keyboard.press('Escape');assert 'model=' not in page.evaluate('location.hash')
 ok('model evidence drawer, deep links, Escape removes detail state')
 page.locator('[data-ma="board"][data-id="arena"]').click();expect(page.locator('[data-model-row]')).to_have_count(BOARD_COUNTS['arena'])
 table=page.locator('#vertical-root').inner_text();assert ARENA['as_of'].replace('-','.',2) in table;assert f"± {ARENA['rows'][0]['score_error']}" in table
 assert page.locator('.m-comparebar').count()==0
 shot(page,'models-arena.png');ok('independent Arena ranks, error bands, source date and cross-source comparison reset')
 assert '不代表综合能力或任务正确率' in page.locator('#vertical-root').inner_text()
 ok('model methodology keeps preference scope separate from general capability')
 page.evaluate("window.twttr={widgets:{createTweet:()=>new Promise(()=>{})}}")
 route(page,'#/tibo');expect(page.locator('.tibo-featured')).to_have_count(1)
 expect(page.locator('.tibo-x-fallback').first).to_be_visible(timeout=7000)
 expect(page.locator('.tibo-x-loading')).to_have_count(0, timeout=7000)
 expect(page.locator('.tibo-evidence-card')).not_to_have_count(0)
 tibo=page.locator('#vertical-root').inner_text()
 assert '待核验' in tibo and 'X 当前无法直连' in tibo and '不模拟 X 界面' in tibo
 assert '已执行表述 · 已确认' in tibo and 'Tibo：reset 已执行' in tibo and '不能证明传播已覆盖每个账户' in tibo
 assert page.locator('.tibo-featured a[href*="x.com"],.tibo-evidence-card a[href*="x.com"]').count()>=1
 assert page.locator('.tibo-x-fallback').count()>=1
 shot(page,'tibo-first-screen.png');shot(page,'tibo-full.png',True)
 ok('Tibo page times out stalled X embeds, then separates original evidence, editorial inference and explicit access limits without fake screenshots')
 route(page,'#/tibo?event=tibo-reset-announced-2026-10-22-day17');expect(page.locator('dialog[open]')).to_have_count(1)
 assert '太平洋时间 10 月 23 日上午 10 点前' in page.locator('dialog[open]').inner_text();page.keyboard.press('Escape')
 ok('Tibo announcement deep link opens the exact reviewed record')
 # Guard invalid runtime data and ensure sources/text cannot become executed markup.
 assert page.evaluate("modulePayloadValid(APP.models,'models')")
 assert not page.evaluate("modulePayloadValid({version:1,checked:'2026-09-21'},'models')")
 assert page.evaluate("(()=>{const e={date:'2026-09-07',precision:'instant',published_at:'2026-09-07T23:30:00Z'};return rDay(e,'Asia/Shanghai')==='2026-09-08'&&rDay(e,'America/Los_Angeles')==='2026-09-07'})()")
 route(page,'#/models?q=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E');expect(page.locator('.m-empty')).to_have_count(1)
 assert page.locator('.m-wrap img').count()==0;ok('runtime validation, exact timestamp conversion and escaped URL inputs')
 for width in [1024,790,390,360]:
  page.set_viewport_size({'width':width,'height':900})
  for path in ['#/models','#/tibo']:
   route(page,path);assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),f'{width}:{path} overflow'
  if width==390:
   shot(page,'tibo-mobile.png',True);route(page,'#/models');shot(page,'models-mobile.png',True)
 route(page,'#/models?model=aa-astra-max');expect(page.locator('dialog[open]')).to_have_count(1)
 assert page.locator('dialog[open]').evaluate('e=>e.scrollWidth<=e.clientWidth+1');page.keyboard.press('Escape')
 ok('1024/790/390/360px layouts, scoped table scrolling and narrow evidence drawer')
 page.set_viewport_size({'width':1512,'height':1050});route(page,'#/models');page.evaluate("applyTheme('dark')")
 shot(page,'models-dark.png');assert not errors,errors
 ok('optional dark theme and no JavaScript errors')
 b.close()
report={'status':'passed','groups':len(checks),'checks':checks,'browser':'Chromium','load_mode':'Playwright set_content / memory','not_verified':['Authenticated AA or X API integration','GitHub Actions deployment','real-origin persistence after reload','live-site HTTP/CORS refresh','upstream links in browser'],'errors':errors}
(R/'test-results').mkdir(exist_ok=True);(R/'test-results/browser-models.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
