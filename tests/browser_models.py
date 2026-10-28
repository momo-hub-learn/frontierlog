"""Model/reset UI checks. Memory mode intentionally does not claim origin storage or network integration."""
import json,os,re
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];OUT=R/'screenshots';OUT.mkdir(exist_ok=True)
HTML=(R/'dist/index.html').read_text();checks=[];errors=[]
MODEL_DATA=json.loads((R/'data/models.json').read_text());RESET_DATA=json.loads((R/'data/resets.json').read_text());CAP_DATA=json.loads((R/'data/capabilities.json').read_text())
BOARD_COUNTS={b['id']:len(b['rows']) for b in MODEL_DATA['boards']};AA=next(b for b in MODEL_DATA['boards'] if b['id']=='aa');ARENA=next(b for b in MODEL_DATA['boards'] if b['id']=='arena')
AA_INDEX=MODEL_DATA['intelligence_index'];AA_EVALUATIONS=[e for category in AA_INDEX['categories'] for e in category['evaluations']]
def ok(s):checks.append(s);print('PASS',s,flush=True)
def route(page,s):page.evaluate('(s)=>location.hash=s',s);page.wait_for_timeout(80)
def shot(page,n,full=False):page.evaluate("scrollTo(0,0);document.querySelector('#toast').classList.remove('active')");page.wait_for_timeout(100);page.screenshot(path=str(OUT/n),full_page=full)
def intercept(route):
 if route.request.url.endswith('/api/v1/capabilities.json'):route.fulfill(status=200,content_type='application/json',body=json.dumps(CAP_DATA))
 else:route.abort()
with sync_playwright() as p:
 opts={'headless':True}
 if os.getenv('CHROMIUM_EXECUTABLE'):opts['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
 b=p.chromium.launch(**opts);page=b.new_page(viewport={'width':1512,'height':1050},device_scale_factor=1);page.set_default_timeout(45000)
 page.on('pageerror',lambda e:errors.append(str(e)));page.route('**/*',intercept)
 test_html=HTML.replace("fetch('./api/v1/capabilities.json'","fetch('https://frontierlog.test/api/v1/capabilities.json'")
 page.set_content(test_html,wait_until='domcontentloaded');page.set_default_timeout(5000)
 route(page,'#/models');expect(page.locator('[data-model-row]')).to_have_count(BOARD_COUNTS['aa'])
 aa_headers=page.locator('.v2-model-table table th').all_text_contents()
 expected_aa_headers=5+int(any(isinstance(x.get('speed'),(int,float)) for x in AA['rows']))+int(any(isinstance(x.get('cost_task'),(int,float)) for x in AA['rows']))+int(any(isinstance(x.get('context'),str) and x['context'].strip() for x in AA['rows']))
 assert len(aa_headers)==expected_aa_headers
 if expected_aa_headers==5:
  assert not {'输出 tok/s','USD / task','上下文'} & set(aa_headers)
  expect(page.locator('.m-mobile-hint')).to_have_text('仅展示当前可核验字段；缺失指标不占空列。')
 expect(page.locator('.v2-model-head h1')).to_have_text('模型综合能力榜')
 expect(page.locator('.v2-source-tabs')).to_have_attribute('aria-label','选择独立榜单')
 expect(page.locator('.v2-aa-method')).to_have_count(1)
 expect(page.locator('.v2-aa-method')).to_contain_text('这张总榜实际考什么？')
 expect(page.locator('.v2-aa-method')).to_contain_text(f"Intelligence Index v{AA_INDEX['version']} · {len(AA_EVALUATIONS)} 项评测")
 weights=page.locator('.v2-aa-weights').inner_text()
 for category in AA_INDEX['categories']:
  label=f"{category['weight']}%\n{category['label']}"
  assert label in weights
 assert '多模态、语音与多语言能力不计入这张总榜' in page.locator('.v2-aa-method').inner_text()
 expect(page.locator('.v2-aa-method a')).to_have_attribute('href','https://artificialanalysis.ai/methodology/intelligence-benchmarking')
 details=page.locator('.v2-aa-suite');expect(details).to_have_count(1);assert details.get_attribute('open') is None
 expect(details.locator('summary')).to_contain_text(f'查看 {len(AA_EVALUATIONS)} 项评测与各自权重')
 page.locator('.v2-aa-suite summary').click();expect(details).to_have_attribute('open','')
 suite=details.inner_text()
 for evaluation in AA_EVALUATIONS:
  assert evaluation['name'] in suite
 assert '单项强弱可能被总分掩盖' in suite
 assert details.evaluate('e=>e.scrollWidth<=e.clientWidth+1')
 assert '综合能力主榜' in page.locator('.v2-source-tabs').inner_text()
 assert '人类偏好榜' in page.locator('.v2-source-tabs').inner_text()
 assert '两张独立榜单 · 不合成本站总分' in page.locator('.v2-source-tabs').inner_text()
 expect(page.locator('.m-segments')).to_have_attribute('aria-label','查看与排序指标')
 assert '已收录模型 #1' in page.locator('.v2-current-first').inner_text()
 expect(page.locator('[data-model-row]').first.locator('.m-access-limited')).to_have_text('小范围 Fairwind')
 expect(page.locator('[data-model-row]').first.locator('.m-access-limited')).to_have_attribute('title',re.compile('coming soon'))
 assert '#1 当前样本' not in page.locator('#vertical-root').inner_text()
 expect(page.locator('#m-search')).to_have_attribute('aria-label','搜索基础模型或厂商')
 expect(page.locator('#m-maker')).to_have_attribute('aria-label','筛选基础模型厂商')
 assert page.locator('#nav .active').inner_text().startswith('模型榜')
 meta=page.locator('.v2-model-meta').inner_text()
 assert f"来源 {AA['as_of'].replace('-', '.')}" in meta
 if AA['checked']!=AA['as_of']:assert f"核验 {AA['checked'].replace('-', '.')}" in meta
 else:assert '核验' not in meta
 assert float(page.locator('.m-model-name').first.evaluate('e=>getComputedStyle(e).fontSize').replace('px',''))>=15
 shot(page,'models-first-screen.png');shot(page,'models-full.png',True);ok('new navigation, readable AA sample, unavailable metric columns removed, preserved theme')
 if any(isinstance(x.get('speed'),(int,float)) for x in AA['rows']):
  page.locator('[data-ma="metric"][data-id="speed"]').click()
  assert '当前查看首位' in page.locator('.v2-current-first').inner_text()
  assert page.evaluate("(()=>{const r=mRows().map(x=>x.speed).filter(Number.isFinite);return r.every((v,i)=>!i||r[i-1]>=v)})()")
 if any(isinstance(x.get('cost_task'),(int,float)) for x in AA['rows']):
  page.locator('[data-ma="metric"][data-id="cost_task"]').click()
  assert page.evaluate("(()=>{const r=mRows().map(x=>x.cost_task).filter(Number.isFinite);return r.every((v,i)=>!i||r[i-1]<=v)})()")
 page.locator('#m-maker').select_option('OpenAI');expect(page.locator('[data-model-row]')).to_have_count(sum(x['maker']=='OpenAI' for x in AA['rows']))
 page.locator('#m-search').fill('Sol');expect(page.locator('[data-model-row]')).to_have_count(sum(x['maker']=='OpenAI' and 'sol' in x['name'].lower() for x in AA['rows']))
 page.locator('#m-search').fill('no-matching-model');expect(page.locator('.m-empty')).to_have_count(1)
 page.locator('#m-search').fill('');page.locator('#m-maker').select_option('all');expect(page.locator('[data-model-row]')).to_have_count(BOARD_COUNTS['aa'])
 ok('named search and provider controls, numeric sorting, incremental search and empty-state reset')
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
 expect(page.locator('.v2-aa-method')).to_have_count(0)
 assert '人类偏好榜' in page.locator('.ar-source-tabs').inner_text()
 assert '综合能力主榜' in page.locator('.ar-source-tabs').inner_text()
 assert '两张独立榜单 · 不合成本站总分' in page.locator('.ar-source-tabs').inner_text()
 table=page.locator('#vertical-root').inner_text();assert ARENA['as_of'].replace('-','.',2) in table;assert f"± {ARENA['rows'][0]['score_error']}" in table
 assert page.locator('.m-comparebar').count()==0
 shot(page,'models-arena.png');ok('independent Arena ranks, error bands, source date and cross-source comparison reset')
 assert '不代表综合能力或任务正确率' in page.locator('#vertical-root').inner_text()
 ok('model methodology keeps preference scope separate from general capability')
 route(page,'#/models?cap=coding')
 expect(page.locator('.v3-capnav a.active')).to_have_attribute('aria-current','page')
 expect(page.locator('.v3-version-notice')).to_have_count(1)
 notice=page.locator('.v3-version-notice').inner_text()
 for label in ['当前官方口径','Coding Agent Index v2.0','FrontierCode v1.1 · 100 tasks','Terminal-Bench 4.0 · 66 tasks','SWE-Atlas-QnA-AA · 124 tasks','本页分数是 v1.5 历史快照','不能与当前 v2.0 分数混排']:
  assert label in notice
 expect(page.locator('.v3-version-warning a')).to_have_attribute('href','https://artificialanalysis.ai/methodology/coding-agents-benchmarking')
 assert 'Coding Agent Index v1.5 · 历史快照' in page.locator('.v3-boardline').inner_text()
 assert 'DeepSWE' in page.locator('.v3-metric-tabs').inner_text()
 shot(page,'models-coding-version.png',True)
 ok('superseded Coding Agent v1.5 scores stay historical while the current v2.0 method is explicit')
 expect(page.locator('.v3-metric-tabs button.active')).to_have_attribute('aria-pressed','true')
 for button in page.locator('.v3-metric-tabs button').all():
  expect(button).to_have_attribute('aria-pressed','true' if 'active' in (button.get_attribute('class') or '') else 'false')
 assert page.locator('.v3-metric-tabs').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
 ok('desktop capability metrics stay fully visible and expose their selected state without relying on color')
 page.evaluate("window.twttr={widgets:{createTweet:()=>new Promise(()=>{})}}")
 route(page,'#/tibo');expect(page.locator('.tibo-featured')).to_have_count(1)
 expect(page.locator('.tibo-x-fallback').first).to_be_visible(timeout=7000)
 expect(page.locator('.tibo-x-loading')).to_have_count(0, timeout=7000)
 expect(page.locator('.tibo-evidence-card')).not_to_have_count(0)
 tibo=page.locator('#vertical-root').inner_text()
 assert '待核验' in tibo and 'X 当前无法直连' in tibo and '不模拟 X 界面' in tibo
 assert '已确认' in tibo and 'Tibo：reset' in tibo
 assert '不能证明' in tibo and '每个账户' in tibo
 assert page.locator('.tibo-featured a[href*="x.com"],.tibo-evidence-card a[href*="x.com"]').count()>=1
 assert page.locator('.tibo-x-fallback').count()>=1
 expect(page.locator('.r-guidance')).to_have_count(1)
 expect(page.locator('[data-reset-guidance]')).to_have_count(3)
 guidance=page.locator('.r-guidance').inner_text()
 for label in ['先判断是哪一种 reset','Banked reset','Automatic / global reset','Purchased reset','不足 80%','不高于 10%','近 30 天','第一次 Work / Codex 请求','七天后']:
  assert label in guidance
 paid=page.locator('[data-reset-row="openai-paid-weekly-reset-2026-10-26"]')
 expect(paid).to_contain_text('使用说明')
 expect(paid).to_contain_text('来源已确认')
 assert '已核验预告' not in paid.inner_text()
 shot(page,'tibo-first-screen.png');shot(page,'tibo-full.png',True)
 ok('Tibo page separates original evidence, three official reset types, editorial inference and explicit access limits without fake screenshots')
 route(page,'#/tibo?event=tibo-reset-announced-2026-10-22-day17');expect(page.locator('dialog[open]')).to_have_count(1)
 assert '太平洋时间 10 月 23 日上午 10 点前' in page.locator('dialog[open]').inner_text();page.keyboard.press('Escape')
 ok('Tibo announcement deep link opens the exact reviewed record')
 # Guard invalid runtime data and ensure sources/text cannot become executed markup.
 assert page.evaluate("modulePayloadValid(APP.models,'models')")
 assert not page.evaluate("modulePayloadValid({version:1,checked:'2026-09-21'},'models')")
 assert not page.evaluate("(()=>{const x=structuredClone(APP.models);delete x.intelligence_index;return modulePayloadValid(x,'models')})()")
 assert page.evaluate("(()=>{const e={date:'2026-09-07',precision:'instant',published_at:'2026-09-07T23:30:00Z'};return rDay(e,'Asia/Shanghai')==='2026-09-08'&&rDay(e,'America/Los_Angeles')==='2026-09-07'})()")
 route(page,'#/models?q=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E');expect(page.locator('.m-empty')).to_have_count(1)
 assert page.locator('.m-wrap img').count()==0;ok('runtime validation, exact timestamp conversion and escaped URL inputs')
 for width in [1024,790,390,360]:
  page.set_viewport_size({'width':width,'height':900})
  for path in ['#/models','#/tibo']:
   route(page,path);assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),f'{width}:{path} overflow'
  route(page,'#/models?cap=coding')
  metrics=page.locator('.v3-metric-tabs')
  if width<=760:assert metrics.evaluate("e=>getComputedStyle(e).overflowX==='auto'")
  if width==390:
   shot(page,'models-coding-version-mobile.png',True);route(page,'#/tibo');shot(page,'tibo-mobile.png',True);route(page,'#/models');page.locator('.v2-aa-suite summary').click();assert page.locator('.v2-aa-suite').evaluate('e=>e.scrollWidth<=e.clientWidth+1');shot(page,'models-mobile.png',True)
 route(page,'#/models?model=aa-astra-max');expect(page.locator('dialog[open]')).to_have_count(1)
 assert page.locator('dialog[open]').evaluate('e=>e.scrollWidth<=e.clientWidth+1');page.keyboard.press('Escape')
 ok('1024/790/390/360px layouts, scoped table scrolling and narrow evidence drawer')
 page.set_viewport_size({'width':1512,'height':1050});route(page,'#/models');page.evaluate("applyTheme('dark')")
 shot(page,'models-dark.png');assert not errors,errors
 ok('optional dark theme and no JavaScript errors')
 b.close()
report={'status':'passed','groups':len(checks),'checks':checks,'browser':'Chromium','load_mode':'Playwright set_content / memory','not_verified':['Authenticated AA or X API integration','GitHub Actions deployment','real-origin persistence after reload','live-site HTTP/CORS refresh','upstream links in browser'],'errors':errors}
(R/'test-results').mkdir(exist_ok=True);(R/'test-results/browser-models.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
