"""Hot-list UI regression: editorial signal only, no network scrape or fake traffic numbers."""
import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];OUT=R/'screenshots';OUT.mkdir(exist_ok=True);(R/'docs').mkdir(exist_ok=True)
HOT_DATA=json.loads((R/'data/hot.json').read_text())
HTML=(R/'dist/index.html').read_text();checks=[];errors=[]
def ok(s):checks.append(s);print('PASS',s,flush=True)
def route(p,s):p.evaluate('(s)=>location.hash=s',s);p.wait_for_timeout(100)
def shot(p,n,full=False):p.evaluate("scrollTo(0,0);document.querySelector('#toast').classList.remove('active')");p.wait_for_timeout(70);p.screenshot(path=str(OUT/n),full_page=full)
with sync_playwright() as pw:
 opts={'headless':True};
 if os.getenv('CHROMIUM_EXECUTABLE'):opts['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
 b=pw.chromium.launch(**opts);p=b.new_page(viewport={'width':1512,'height':1050});p.set_default_timeout(45000);p.on('pageerror',lambda e:errors.append(str(e)));p.route('**/*',lambda r:r.abort());p.set_content(HTML,wait_until='domcontentloaded');p.set_default_timeout(5000)
 route(p,'#/hot');expect(p.locator('.intraday-row')).to_have_count(len(HOT_DATA['items']));expect(p.locator('.h-tab')).to_have_count(6)
 assert p.locator('.intraday-score').first.get_attribute('aria-label').startswith('本站编辑热度 ')
 assert any(label in p.locator('.intraday-score').first.inner_text() for label in ('爆热','高热','升温','关注')) and 'AI 评分' not in p.locator('.intraday-score').first.inner_text()
 assert p.locator('.intraday-score.is-extreme,.intraday-score.is-high,.intraday-score.is-rising,.intraday-score.is-watch').count()==len(HOT_DATA['items'])
 assert p.locator('.intraday-day').count()>1 and p.locator('.intraday-day[open]').count()==1
 source_links=p.locator('.intraday-actions a');assert source_links.count()>1
 source_names=source_links.evaluate_all("els=>els.map(x=>x.getAttribute('aria-label'))")
 assert all(source_names) and len(source_names)==len(set(source_names)) and all('新窗口打开' in x for x in source_names)
 assert p.locator('#nav a.active').inner_text().startswith('热点榜');assert '热度只表示信号强度' in p.locator('.h-head').inner_text();assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
 shot(p,'hot-first-screen.png');ok('hot ranking, unique source-link labels, six categories, latest day expanded, older days collapsed, no desktop overflow')
 p.locator('[data-ha="cat"][data-id="model"]').click();assert p.locator('.intraday-row').count()==sum(x['category']=='model' for x in HOT_DATA['items'])
 p.locator('#h-search').fill('Gemini');assert p.locator('.intraday-row').count()==sum('gemini' in ' '.join([x['title'],x['source'],x['summary']]).lower() for x in HOT_DATA['items'] if x['category']=='model')
 p.locator('#h-search').fill('not-found-xyz');expect(p.locator('.h-empty')).to_have_count(1);expect(p.locator('[data-ha="hot-clear-search"]')).to_be_visible();p.locator('[data-ha="hot-clear-search"]').click();expect(p.locator('#h-search')).to_have_value('');expect(p.locator('.intraday-row')).to_have_count(len(HOT_DATA['items']))
 route(p,'#/hot');ok('category and search filters preserve compact ranking')
 route(p,'#/hot?tab=github');expect(p.locator('.h-open-tabs a.active')).to_have_attribute('aria-current','page')
 route(p,'#/hot?tab=hf');expect(p.locator('.h-open-tabs a.active')).to_have_attribute('aria-current','page');ok('platform switch exposes the current page to assistive technology')
 route(p,'#/hot')
 p.locator('.intraday-row [data-ha="detail"]').first.click();assert 'item=' in p.evaluate('location.hash');expect(p.locator('dialog[open]')).to_have_count(1);assert '为什么值得看' in p.locator('#modal-body').inner_text();assert '不要过度解读' in p.locator('#modal-body').inner_text();p.keyboard.press('Escape');p.wait_for_function("!location.hash.includes('item=')");ok('deep-linked evidence drawer keeps rationale and boundary separate and clears its route when closed')
 gated=next(x for x in HOT_DATA['items'] if any(r.get('kind')=='product' for r in x.get('access',[])) and not any(r.get('kind') in {'try','demo','gateway'} for r in x.get('access',[])))
 route(p,'#/hot?item='+gated['id']);expect(p.locator('dialog[open]')).to_have_count(1);status=p.locator('.h-access-status').inner_text();assert '候补或产品资料页' in status and '尚不能直接体验' in status;p.keyboard.press('Escape');ok('gated preview pages are not presented as directly usable experiences')
 route(p,'#/hot');p.locator('[data-ha="method"]').click();status=p.locator('#modal-body').inner_text();assert 'Shadow / 不自动发布' in status;assert '人工核对快照' in status;p.keyboard.press('Escape')
 hot=json.loads((R/'dist/api/v1/hot.json').read_text());assert hot['method']['automatic'] is False and hot['items']==HOT_DATA['items'];assert (R/'dist/feeds/hot.xml').exists();ok('data status is honest, API JSON and hot RSS artifacts match the reviewed input')
 route(p,'#/feed');expect(p.locator('.fc-hot-row')).to_have_count(5);assert 'HOT / RECENT' in p.locator('.fc-hot-panel').inner_text();ok('curated homepage includes compact five-item hot list')
 for w in [790,390,360]:
  p.set_viewport_size({'width':w,'height':844});route(p,'#/hot');assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
 shot(p,'hot-mobile.png');ok('hot list is responsive at 790/390/360px')
 assert not errors,errors;ok('zero JavaScript errors')
 b.close()
(R/'docs/hot-ui-tests.json').write_text(json.dumps({'checks':checks,'errors':errors,'mode':'memory','note':'No remote fetches or origin-persistence claims.'},ensure_ascii=False,indent=2))
