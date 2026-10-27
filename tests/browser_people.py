"""Exercise the compiled app; CI uses real origin/localStorage, no public network."""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results/people';OUT.mkdir(parents=True,exist_ok=True)
HTML=(ROOT/'dist/index.html').read_text(encoding='utf-8')
DATA=json.loads((ROOT/'data/people.json').read_text(encoding='utf-8'))
OFFLINE=os.getenv('PEOPLE_OFFLINE_TEST')=='1'
checks=[];errors=[]
def ok(text):checks.append(text);print('PASS',text,flush=True)
class App(BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.send_header('Content-type','text/html; charset=utf-8');self.end_headers();self.wfile.write(HTML.encode())
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),App)
threading.Thread(target=server.serve_forever,daemon=True).start()
BASE=f'http://127.0.0.1:{server.server_port}/'
with sync_playwright() as pw:
 options={'headless':True}
 if os.getenv('CHROMIUM_EXECUTABLE'):options['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
 browser=pw.chromium.launch(**options)
 context=browser.new_context(viewport={'width':1440,'height':1080},reduced_motion='reduce')
 # Real first-party storage in CI; an explicit in-memory double only for offline visual review.
 page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.set_default_timeout(45000)
 page.route('**/*',lambda r:r.continue_() if r.request.url.startswith(BASE) else r.abort())
 if OFFLINE:
  page.evaluate("""window.__ppStore={};Object.defineProperty(window,'localStorage',{configurable:true,value:{getItem:k=>window.__ppStore[k]??null,setItem:(k,v)=>window.__ppStore[k]=String(v),removeItem:k=>delete window.__ppStore[k]}})""")
 def load(hash):
  global page
  if OFFLINE:
   stored=page.evaluate('window.__ppStore || {}');page.close();page=context.new_page()
   page.on('pageerror',lambda e:errors.append(str(e)));page.set_default_timeout(45000)
   page.route('**/*',lambda r:r.abort())
   page.evaluate("stored=>{window.__ppStore=stored;Object.defineProperty(window,'localStorage',{configurable:true,value:{getItem:k=>window.__ppStore[k]??null,setItem:(k,v)=>window.__ppStore[k]=String(v),removeItem:k=>delete window.__ppStore[k]}})}",stored)
   page.evaluate('(hash)=>location.hash=hash',hash);page.set_content(HTML,wait_until='domcontentloaded')
  else:
   page.goto(BASE+hash,wait_until='domcontentloaded');page.reload(wait_until='domcontentloaded')
 def route(hash):
  page.evaluate('(hash)=>{location.hash=hash;lastMain="";parseRoute()}',hash)
 def no_overflow():
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'), page.evaluate('({innerWidth,scroll:document.documentElement.scrollWidth})')
 load('#/people')
 expect(page.locator('.pp-head h1')).to_have_text('AI 人物');expect(page.locator('[data-person-card]')).to_have_count(len(DATA['people']))
 expect(page.locator('#nav [data-people-nav]')).to_have_count(1)
 expect(page.locator('#nav [data-people-nav]')).to_have_attribute('aria-current','page')
 expect(page.locator('.pp-latest')).to_have_count(len(DATA['people']))
 ok('Direct people deep link, directory count and sidebar entry')
 expected_order=page.evaluate("PeopleUI.rows(APP.people,PeopleUI.read('#/people',APP.people)).map(p=>p.id)")
 actual_order=page.locator('[data-person-card]').evaluate_all("els=>els.map(e=>e.dataset.personCard)")
 assert actual_order==expected_order
 dated=page.locator('[data-person-card]').evaluate_all("els=>els.map(e=>e.dataset.latestDate)")
 assert dated==sorted(dated,reverse=True)
 expect(page.locator('.pp-achievements')).to_have_count(len(DATA['people']))
 for person in DATA['people']:
  card=page.locator('[data-person-card="'+person['id']+'"]')
  expect(card.locator('.pp-work-preview li')).to_have_count(len(person['works']))
  expect(card.locator('.pp-achievements')).to_contain_text(person['intro'])
 expect(page.locator('.pp-results')).to_contain_text('最近更新优先')
 ok('One complete card per person, newest real activity first, all works and credited achievements visible')
 page.evaluate("localStorage.setItem('aip.saved','[\"docling\"]')")
 page.locator('[data-people-follow="tri-dao"]').click()
 page.locator('#pp-following').check();expect(page.locator('[data-person-card]')).to_have_count(1)
 load('#/people?following=1')
 expect(page.locator('[data-people-follow="tri-dao"]')).to_have_attribute('aria-pressed','true')
 assert page.evaluate("localStorage.getItem('aip.saved')")=='["docling"]'
 ok('Local follows survive document reload and preserve existing project storage')
 page.locator('#pp-following').uncheck()
 page.locator('#pp-search').fill('VISTA');expect(page.locator('[data-person-card]')).to_have_count(5)
 page.locator('[data-person-card="qiushi-han"] .pp-more').click()
 expect(page.locator('[data-profile="qiushi-han"]')).to_be_visible()
 expect(page.locator('.pp-coauthors')).to_contain_text('Keya Hu')
 page.locator('.pp-back').click();expect(page.locator('#pp-search')).to_have_value('VISTA')
 expect(page.locator('[data-person-card]')).to_have_count(5)
 if not OFFLINE:
  page.go_back();expect(page.locator('[data-profile="qiushi-han"]')).to_be_visible()
  page.go_forward();expect(page.locator('[data-person-card]')).to_have_count(5)
 ok('Search by work, contributor profiles, preserved filters and browser history')
 route('#/people?view=influence')
 expect(page.locator('.pp-influence-guide')).to_be_visible()
 expect(page.locator('.pp-latest')).to_have_count(len(DATA['people']))
 expect(page.locator('.pp-impact')).to_have_count(len(DATA['people']))
 page.locator('.pp-influence-guide a').filter(has_text='学术与研究').click()
 assert page.locator('[data-person-card]').count()==sum('research' in p['impact']['dimensions'] for p in DATA['people'])
 route('#/people')
 ok('Influence dimensions are transparent evidence facets; all people show latest or missing-evidence state')
 page.locator('.pp-tabs a').filter(has_text='人物动态').click()
 expect(page.locator('[data-person-event]')).to_have_count(len(DATA['events']))
 expect(page.locator('[data-person-event="vista-paper"]')).to_contain_text('2026.10.01')
 page.locator('.pp-reset').click()
 expect(page.locator('.pp-archive')).to_be_visible()
 expect(page.locator('.pp-archive')).to_contain_text('2023.12.01')
 ok('Original publication dates and separate historical activity')
 route('#/people?area=systems&role=builder')
 expected=[p for p in DATA['people'] if 'systems' in p['areas'] and 'builder' in p['roles']]
 expect(page.locator('[data-person-card]')).to_have_count(len(expected))
 page.locator('#pp-search').fill('<script>bad()</script>');expect(page.locator('.pp-empty')).to_be_visible()
 assert page.locator('.pp-page script').count()==0
 route('#/people?discover=1');expect(page.locator('[data-person-card]')).to_have_count(sum(p['discovery']=='work' for p in DATA['people']))
 ok('Combined facets, work discovery and safely escaped empty search')
 route('#/people')
 page.locator('#main').focus();page.keyboard.press('/');expect(page.locator('#pp-search')).to_be_focused()
 page.keyboard.press('Escape');page.locator('#main').focus();page.keyboard.press('Control+k')
 expect(page.locator('#palette')).to_be_visible();page.locator('#palette-input').fill('AI 人物')
 expect(page.locator('#palette-results')).to_contain_text('AI 人物');page.keyboard.press('Escape')
 ok('Keyboard search and existing global command palette')
 route('#/saved');expect(page.locator('#pp-saved')).to_contain_text('Tri Dao')
 route('#/hot?cat=product&pview=map&product=palantir-aip')
 expect(page.locator('[data-product-id="palantir-aip"]')).to_be_visible()
 expect(page.locator('[data-product-id="palantir-aip"] .pp-reverse')).to_contain_text('Shyam Sankar')
 page.locator('.pp-reverse a').click();expect(page.locator('[data-profile="shyam-sankar"]')).to_be_visible()
 page.locator('.pp-related-link').click();expect(page.locator('[data-product-id="palantir-aip"]')).to_be_visible()
 ok('My Follows aggregation and two-way Palantir/product/person navigation')
 for hash in ['#/feed','#/benchmarks','#/progress?view=research','#/toolkit','#/activity','#/models','#/people']:
  route(hash);assert page.locator('#main').inner_text().strip();expect(page.locator('[data-people-nav]')).to_have_count(1)
 ok('Existing pages remain navigable after people view')
 for width in [1440,1100,768,390,320]:
  page.set_viewport_size({'width':width,'height':1080})
  for hash in ['#/people','#/people?person=shreya-shankar','#/people?person=kaiming-he','#/people?view=influence','#/people?view=updates']:
   route(hash);no_overflow()
  ok(f'{width}px: directory, profiles and activity have no horizontal overflow')
 for width,label,hash in [(1440,'directory-desktop','#/people'),(390,'directory-mobile','#/people'),(1440,'profile-desktop','#/people?person=kaiming-he'),(390,'profile-mobile','#/people?person=shyam-sankar'),(1440,'updates-desktop','#/people?view=updates')]:
  page.set_viewport_size({'width':width,'height':1080});route(hash);page.evaluate('scrollTo(0,0)')
  page.screenshot(path=str(OUT/(label+'.png')))
 page.evaluate("applyTheme('dark',true)");route('#/people');no_overflow()
 page.screenshot(path=str(OUT/'directory-dark.png'))
 ok('Light/dark design and desktop/mobile screenshots')
 page.set_viewport_size({'width':390,'height':1080});route('#/people')
 page.evaluate("""() => {const sizes=[...document.querySelectorAll('.pp-page *')].map(el=>[el,parseFloat(getComputedStyle(el).fontSize)]);for(const [el,size] of sizes)el.style.setProperty('font-size',(size*2)+'px','important')}""")
 no_overflow();ok('People cards remain readable without page overflow at 200 percent text')
 if not OFFLINE:
  denied=browser.new_context();denied.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new DOMException('Storage denied','SecurityError')}})")
  q=denied.new_page();q.on('pageerror',lambda e:errors.append(str(e)));q.route('**/*',lambda r:r.continue_() if r.request.url.startswith(BASE) else r.abort())
  q.goto(BASE+'#/people',wait_until='domcontentloaded');expect(q.locator('[data-person-card]')).to_have_count(len(DATA['people']))
  q.locator('[data-people-follow="tri-dao"]').click();expect(q.locator('#toast')).to_contain_text('不允许持久保存');denied.close()
  corrupt=browser.new_context();corrupt.add_init_script("localStorage.setItem('aic.people.follows.v1','not-json')")
  q=corrupt.new_page();q.on('pageerror',lambda e:errors.append(str(e)));q.route('**/*',lambda r:r.continue_() if r.request.url.startswith(BASE) else r.abort())
  q.goto(BASE+'#/people?following=1',wait_until='domcontentloaded');expect(q.locator('.pp-empty')).to_contain_text('还没有关注人物');corrupt.close()
  ok('Denied and corrupt browser storage degrade safely')
 assert not errors, errors
 (OUT/'report.json').write_text(json.dumps({'checks':checks,'errors':errors,'storage_mode':'explicit offline test double' if OFFLINE else 'real browser localStorage','people':len(DATA['people'])},ensure_ascii=False,indent=2))
 browser.close()
server.shutdown()
print(f'People browser: {len(checks)} checks passed.')
