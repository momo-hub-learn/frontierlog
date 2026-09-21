"""Hot-list UI regression: editorial signal only, no network scrape or fake traffic numbers."""
import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];OUT=R/'screenshots';OUT.mkdir(exist_ok=True)
HTML=(R/'dist/index.html').read_text();checks=[];errors=[]
def ok(s):checks.append(s);print('PASS',s,flush=True)
def route(p,s):p.evaluate('(s)=>location.hash=s',s);p.wait_for_timeout(100)
def shot(p,n,full=False):p.evaluate("scrollTo(0,0);document.querySelector('#toast').classList.remove('active')");p.wait_for_timeout(70);p.screenshot(path=str(OUT/n),full_page=full)
with sync_playwright() as pw:
 opts={'headless':True};
 if os.getenv('CHROMIUM_EXECUTABLE'):opts['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
 b=pw.chromium.launch(**opts);p=b.new_page(viewport={'width':1512,'height':1050});p.set_default_timeout(5000);p.on('pageerror',lambda e:errors.append(str(e)));p.set_content(HTML)
 route(p,'#/hot');expect(p.locator('.h-row')).to_have_count(5);expect(p.locator('.h-tab')).to_have_count(6)
 assert p.locator('#nav a.active').inner_text().startswith('热点榜');assert '不是全网流量' in p.locator('.h-board-head').inner_text();assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
 shot(p,'hot-first-screen.png');ok('hot ranking, six categories, explicit internal-score boundary, no desktop overflow')
 p.locator('[data-ha="cat"][data-id="model"]').click();assert p.locator('.h-row').count()+p.locator('.h-story').count()==3
 p.locator('#h-search').fill('Gemini');assert p.locator('.h-row').count()+p.locator('.h-story').count()==2
 p.locator('#h-search').fill('not-found-xyz');assert p.locator('.h-empty').count()>=1
 route(p,'#/hot');ok('category and search filters preserve compact ranking')
 p.locator('.h-row .h-title').first.click();assert 'item=' in p.evaluate('location.hash');expect(p.locator('dialog[open]')).to_have_count(1);assert '为什么值得看' in p.locator('#modal-body').inner_text();assert '不要过度解读' in p.locator('#modal-body').inner_text();p.keyboard.press('Escape');ok('deep-linked evidence drawer keeps rationale and boundary separate')
 route(p,'#/hot');p.locator('[data-ha="method"]').click();assert '未开启' in p.locator('#modal-body').inner_text();assert '跨平台统一浏览量' in p.locator('#modal-body').inner_text()
 with p.expect_download() as d:p.locator('[data-ha="export"]').click()
 hot=json.loads(Path(d.value.path()).read_text());assert hot['method']['automatic'] is False and len(hot['items'])==10
 p.locator('[data-ha="rss"]').click();assert '/frontierlog/feeds/hot.xml' in p.locator('#modal-body').inner_text();p.keyboard.press('Escape');ok('data status is honest, JSON export and hot RSS path work')
 route(p,'#/feed');expect(p.locator('.v-hot-mini>a')).to_have_count(5);assert '当前热点' in p.locator('.v-hot-entry').inner_text();ok('curated homepage includes compact five-item hot list')
 route(p,'#/models');expect(p.locator('.m-hubtab')).to_have_count(2);assert p.locator('.m-hubtab.active').inner_text().startswith('模型排行');p.locator('.m-hubtab').nth(1).click();assert p.locator('.m-hubtab.active').inner_text().startswith('Benchmark');assert '模型榜' in p.locator('#nav a.active').inner_text();ok('Benchmark is nested under the model hub and model nav stays active')
 for w in [790,390,360]:
  p.set_viewport_size({'width':w,'height':844});route(p,'#/hot');assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
 shot(p,'hot-mobile.png');ok('hot list is responsive at 790/390/360px')
 assert not errors,errors;ok('zero JavaScript errors')
 b.close()
(R/'docs/hot-ui-tests.json').write_text(json.dumps({'checks':checks,'errors':errors,'mode':'memory','note':'No remote fetches or origin-persistence claims.'},ensure_ascii=False,indent=2))
