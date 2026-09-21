"""Model/reset UI checks. Memory mode intentionally does not claim origin storage or network integration."""
import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];OUT=R/'screenshots';OUT.mkdir(exist_ok=True)
HTML=(R/'dist/index.html').read_text();checks=[];errors=[]
def ok(s):checks.append(s);print('PASS',s,flush=True)
def route(page,s):page.evaluate('(s)=>location.hash=s',s);page.wait_for_timeout(80)
def shot(page,n,full=False):page.evaluate("scrollTo(0,0);document.querySelector('#toast').classList.remove('active')");page.wait_for_timeout(100);page.screenshot(path=str(OUT/n),full_page=full)
with sync_playwright() as p:
 opts={'headless':True}
 if os.getenv('CHROMIUM_EXECUTABLE'):opts['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
 b=p.chromium.launch(**opts);page=b.new_page(viewport={'width':1512,'height':1050},device_scale_factor=1);page.set_default_timeout(5000)
 page.on('pageerror',lambda e:errors.append(str(e)));page.set_content(HTML)
 route(page,'#/models');expect(page.locator('[data-model-row]')).to_have_count(12)
 assert page.locator('#nav .active').inner_text().startswith('模型榜')
 assert float(page.locator('.m-model-name').first.evaluate('e=>getComputedStyle(e).fontSize').replace('px',''))>=15
 shot(page,'models-first-screen.png');shot(page,'models-full.png',True);ok('new navigation, readable AA sample, preserved theme')
 page.locator('[data-ma="metric"][data-id="speed"]').click()
 assert 'Gemini' in page.locator('[data-model-row]').first.inner_text()
 page.locator('[data-ma="metric"][data-id="cost_task"]').click()
 assert 'DeepSeek' in page.locator('[data-model-row]').first.inner_text()
 page.locator('#m-maker').select_option('OpenAI');expect(page.locator('[data-model-row]')).to_have_count(2)
 page.locator('#m-search').fill('Sol');expect(page.locator('[data-model-row]')).to_have_count(1)
 page.locator('#m-search').fill('no-matching-model');expect(page.locator('.m-empty')).to_have_count(1)
 page.locator('[data-ma="model-clear"]').click();expect(page.locator('[data-model-row]')).to_have_count(12)
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
 page.locator('[data-ma="board"][data-id="arena"]').click();expect(page.locator('[data-model-row]')).to_have_count(8)
 assert '2026-09-13' in page.locator('.m-table').inner_text();assert '± 5' in page.locator('.m-table').inner_text()
 assert '17' in page.locator('[data-model-row]').nth(5).inner_text()
 assert page.locator('.m-comparebar').count()==0
 shot(page,'models-arena.png');ok('independent Arena ranks, error bands, source date and cross-source comparison reset')
 page.locator('[data-ma="model-health"]').click()
 assert '未执行' in page.locator('#modal-body').inner_text()
 with page.expect_download() as dl:page.locator('[data-ma="models-backup"]').click()
 backup=Path(dl.value.path()).read_bytes();assert len(json.loads(backup)['models'])==1
 page.locator('#model-import').set_input_files({'name':'watch.json','mimeType':'application/json','buffer':backup})
 page.wait_for_timeout(100)
 page.locator('[data-ma="model-rss"]').click();assert '/frontierlog/feeds/models.xml' in page.locator('#modal-body').inner_text();page.keyboard.press('Escape')
 ok('model status is honest, local backup import and model RSS entry')
 route(page,'#/tibo');expect(page.locator('.r-day')).to_have_count(42);expect(page.locator('[data-reset-row]')).to_have_count(5)
 assert '尚未接通' in page.locator('.r-smallstats').inner_text();assert '没有已核验时间' in page.locator('.r-smallstats').inner_text()
 shot(page,'tibo-first-screen.png');shot(page,'tibo-full.png',True)
 page.locator('.r-day[data-id="2026-09-07"]').click();assert '全局重置' in page.locator('.r-selected').inner_text()
 page.locator('.r-day[data-id="2026-09-03"]').click();assert '重置卡' in page.locator('.r-selected').inner_text()
 page.locator('.r-day[data-id="2026-09-20"]').click();assert '待核验' in page.locator('.r-selected').inner_text()
 ok('42-cell calendar, separate banked/global/unverified announcements, no fabricated current status')
 page.locator('#r-tz').select_option('America/Los_Angeles');assert page.locator('.r-selected h2').inner_text()=='2026-09-20'
 page.locator('[data-ma="month-prev"]').click();assert '8 月' in page.locator('.r-calendar-head').inner_text()
 page.locator('[data-ma="latest"]').first.click();page.locator('.r-day.selected').focus();page.keyboard.press('ArrowLeft')
 assert page.locator('.r-selected h2').inner_text()=='2026-09-19'
 assert '没有收录记录' in page.locator('.r-selected').inner_text()
 ok('month controls, keyboard calendar, date-only timezone stability and neutral no-record state')
 page.locator('[data-ma="reset-kind"][data-id="banked"]').click();expect(page.locator('[data-reset-row]')).to_have_count(2)
 page.locator('#r-status').select_option('pending');expect(page.locator('[data-reset-row]')).to_have_count(0)
 page.locator('[data-ma="reset-clear"]').click();expect(page.locator('[data-reset-row]')).to_have_count(5)
 page.locator('#r-search').fill('2026-09-07');expect(page.locator('[data-reset-row]')).to_have_count(1)
 page.locator('[data-ma="reset-detail"]').click();assert '无精确' not in page.locator('.dialog-intro').inner_text() # contains source-day, not a made-up time
 assert '来源记日' in page.locator('.dialog-intro').inner_text()
 assert 'help.openai.com' in page.locator('#modal-body').inner_html();shot(page,'reset-detail.png')
 page.keyboard.press('Escape');page.locator('#r-search').fill('');ok('kind/status/search, original-source evidence drawer, URL integrity')
 page.locator('[data-ma="reset-rss"]').click();assert '/frontierlog/feeds/resets.xml' in page.locator('#modal-body').inner_text();page.keyboard.press('Escape')
 page.locator('[data-ma="reset-health"]').click();assert '未执行' in page.locator('#modal-body').inner_text()
 with page.expect_download() as dl:page.locator('[data-ma="reset-export"]').click()
 assert len(json.loads(Path(dl.value.path()).read_text())['events'])==5
 page.locator('[data-ma="refresh-resets"]').click();assert '本地' in page.locator('#toast').inner_text();page.keyboard.press('Escape')
 ok('reset RSS, record export, explicit unconnected status and safe local refresh fallback')
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
