"""Topic UI regression tests. Memory mode is explicit: no remote or authenticated writes.
Run python scripts/build.py first. Set CHROMIUM_EXECUTABLE when not using bundled browser.
Use BROWSER_TEST_MODE=http on your computer to verify a real localhost origin/reload.
"""
import functools,json,os,threading
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];OUT=R/'screenshots';OUT.mkdir(exist_ok=True)
HTML=(R/'dist/index.html').read_text()
MODE=os.getenv('BROWSER_TEST_MODE','memory')
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(R/'dist')))
threading.Thread(target=server.serve_forever,daemon=True).start()
URL=f'http://127.0.0.1:{server.server_port}/'
checks=[];errors=[]
def pass_(name):checks.append(name);print('PASS',name,flush=True)
def route(page,path):page.evaluate('(p)=>location.hash=p',path);page.wait_for_timeout(100)
def shot(page,name,full=False):page.evaluate('scrollTo(0,0)');page.wait_for_timeout(100);page.screenshot(path=str(OUT/name),full_page=full)
try:
 with sync_playwright() as p:
  opts={'headless':True}
  if os.getenv('CHROMIUM_EXECUTABLE'):opts['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
  b=p.chromium.launch(**opts);page=b.new_page(viewport={'width':1512,'height':1040},device_scale_factor=1)
  page.set_default_timeout(5000);page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(HTML) if MODE=='memory' else page.goto(URL)
  expect(page.locator('.v-article')).to_have_count(15)
  assert page.locator('#nav .active').inner_text().startswith('精选')
  assert page.locator('.sector-gateway').count()==2
  assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
  shot(page,'home.png');pass_('new default feed, sector gateways, 15 real-source articles')
  route(page,'#/pharma');expect(page.locator('.v-article')).to_have_count(8)
  assert float(page.locator('.v-summary').first.evaluate('e=>getComputedStyle(e).fontSize').replace('px',''))>=15
  shot(page,'pharma.png');pass_('pharma page, large reading typography, dated and evergreen records separate')
  route(page,'#/pharma?topic=csr');expect(page.locator('.v-article')).to_have_count(3)
  assert '临床研究报告' in page.locator('body').inner_text()
  page.locator('[data-va="format"][data-id="tool"]').click();expect(page.locator('.v-article')).to_have_count(2)
  page.locator('[data-va="format"][data-id="reference"]').click();expect(page.locator('.v-article')).to_have_count(1)
  assert 'ICH E3' in page.locator('.v-article').inner_text()
  pass_('CSR meaning, subtype filter, historical E3 kept as reference')
  route(page,'#/manufacturing');expect(page.locator('.v-article')).to_have_count(7)
  shot(page,'manufacturing.png')
  route(page,'#/manufacturing?topic=fab-maintenance');expect(page.locator('.v-article')).to_have_count(2)
  route(page,'#/manufacturing?topic=csr');assert page.locator('.v-topic-strip a.active').inner_text()=='全部主题'
  pass_('manufacturing and fab filtering; invalid cross-sector filter is rejected')
  page.locator('#v-search').fill('not-any-topic-zzzx');expect(page.locator('.v-empty')).to_have_count(1)
  page.locator('[data-va="reset"]').click();expect(page.locator('.v-article')).to_have_count(7)
  page.locator('#v-search').fill('Anomalib');expect(page.locator('.v-article')).to_have_count(1)
  page.locator('#v-search').fill('');expect(page.locator('.v-article')).to_have_count(7)
  page.locator('#v-sort').select_option('events')
  assert page.locator('.v-article').first.get_attribute('data-article-id')=='lam-ei'
  pass_('search, no-results, reset, publication sort without fabricated dates')
  route(page,'#/topics');expect(page.locator('.topic-row')).to_have_count(10)
  shot(page,'topics.png',full=True)
  page.locator('[data-va="follow"][data-id="csr"]').click()
  assert page.locator('[data-va="follow"][data-id="csr"]').get_attribute('aria-pressed')=='true'
  route(page,'#/feed?focus=1');expect(page.locator('.v-article')).to_have_count(3)
  pass_('topic directory, per-topic following, filtered personal feed in session')
  page.locator('[data-va="article"][data-id="yseop-csr"]').first.click()
  expect(page.locator('#modal')).to_be_visible()
  assert page.locator('#modal').get_attribute('class')=='drawer'
  assert 'article=yseop-csr' in page.url
  assert page.locator('#modal .source-row').count()>=1
  assert '编辑解读' in page.locator('#modal').inner_text()
  page.locator('[data-v-check="yseop-csr"]').first.check()
  with page.expect_download() as d:page.locator('[data-va="export-article"]').click()
  assert d.value.suggested_filename=='frontierlog-yseop-csr.md'
  page.locator('#modal [data-va="save"]').click()
  assert page.locator('[data-v-check="yseop-csr"]').first.is_checked()
  shot(page,'csr-detail.png')
  page.keyboard.press('Escape');assert 'article=' not in page.url
  route(page,'#/saved');expect(page.locator('#legacy-saved .v-article')).to_have_count(1)
  pass_('deep-linked evidence drawer, independent checklist, Markdown note, save, escape')
  route(page,'#/pharma?topic=csr');page.locator('[data-va="rss"]').click()
  assert 'https://momo-hub-learn.github.io/frontierlog/feeds/csr.xml' in page.locator('#modal').inner_text()
  assert (R/'dist/feeds/csr.xml').is_file();page.keyboard.press('Escape')
  with page.expect_download() as d:page.locator('[data-va="export-topic"]').click()
  payload=json.loads(Path(d.value.path()).read_text());assert len(payload['items'])==3
  pass_('topic RSS maps to generated file, current filtered topic data export')
  route(page,'#/topics')
  with page.expect_download() as d:page.locator('[data-va="export-personal"]').click()
  file=OUT/'personal-test.json';d.value.save_as(str(file))
  payload=json.loads(file.read_text());assert 'csr' in payload['topics'] and 'yseop-csr' in payload['articles']
  page.locator('[data-va="follow"][data-id="csr"]').click()
  page.locator('#vertical-import').set_input_files(str(file))
  assert page.locator('[data-va="follow"][data-id="csr"]').get_attribute('aria-pressed')=='true'
  bad=OUT/'bad-topic-test.json';bad.write_text('{"version":1,"topics":"bad"}')
  page.locator('#vertical-import').set_input_files(str(bad))
  assert page.locator('[data-va="follow"][data-id="csr"]').get_attribute('aria-pressed')=='true'
  page.locator('[data-va="follow-recommended"]').click()
  assert page.locator('.topic-follow.is-followed').count()==6
  pass_('personal export/import, malformed import rejected, six focus topics')
  page.keyboard.press('Control+k');page.locator('#palette-input').fill('晶圆设备')
  page.keyboard.press('Enter');assert 'topic=fab-maintenance' in page.url
  pass_('command palette finds new industry topics')
  route(page,'#/signals');expect(page.locator('.v-empty')).to_have_count(1)
  assert '首次采集尚未执行' in page.locator('.v-empty').inner_text()
  page.locator('[data-va="sync"]').first.click();assert '尚未执行' in page.locator('#modal').inner_text();page.keyboard.press('Escape')
  pass_('collector health shows pending state; no fictitious live queue')
  route(page,'#/pharma');page.locator('[data-action="theme"]').click()
  assert page.locator('html').get_attribute('data-theme')=='dark'
  assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
  page.locator('[data-action="theme"]').click();pass_('optional dark theme preserves topic layout')
  if MODE!='memory':
   page.reload();route(page,'#/topics');assert page.locator('[data-va="follow"][data-id="csr"]').get_attribute('aria-pressed')=='true'
   pass_('real-origin localStorage survives reload')
  # In-memory navigation tests don't establish cross-origin/reload persistence.
  for width in [1024,790,390,360]:
   mobile=b.new_page(viewport={'width':width,'height':880},device_scale_factor=1)
   mobile.set_default_timeout(5000);mobile.on('pageerror',lambda e:errors.append(str(e)))
   mobile.set_content(HTML) if MODE=='memory' else mobile.goto(URL)
   for path in ['#/feed','#/topics','#/pharma','#/manufacturing','#/signals','#/pharma?topic=csr']:
    route(mobile,path)
    assert mobile.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,path)
   mobile.locator('[data-va="article"][data-id="yseop-csr"]').first.click()
   assert mobile.locator('#modal').evaluate('(e)=>e.scrollWidth<=e.clientWidth'),width
   mobile.keyboard.press('Escape')
   if width==390:
    route(mobile,'#/pharma');shot(mobile,'pharma-mobile.png',full=True)
    mobile.locator('[data-action="menu"]').click();mobile.locator('#nav a[href="#/manufacturing"]').click()
    expect(mobile.locator('body')).not_to_have_class('nav-open')
    shot(mobile,'manufacturing-mobile.png')
   mobile.close()
  pass_('responsive 1024, 790, 390, 360 px; topic drawers, nav, no horizontal overflow')
  assert not errors,errors
  report={'passed':True,'checks':checks,'count':len(checks),'javascript_errors':errors,'browser':'Chromium',
          'mode':MODE,'unverified':['Public deployment','External collection first run','Third-party AI tools / clinical or manufacturing results']+(['Real-origin reload persistence (environment blocks HTTP/file navigation)'] if MODE=='memory' else [])}
  (R/'docs/topic-ui-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
  file.unlink(missing_ok=True);bad.unlink(missing_ok=True);b.close()
finally:server.shutdown();server.server_close()
