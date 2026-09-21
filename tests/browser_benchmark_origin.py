"""Same-origin persistence and reload with an intercepted HTTPS test host.
No connection to this host or user services occurs; all responses are local files.
"""
import json,os,mimetypes
from pathlib import Path
from urllib.parse import urlsplit,unquote
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];D=R/'dist';OUT=R/'test-results';OUT.mkdir(exist_ok=True)
base='https://frontierlog.test/frontierlog/';errors=[];checks=[]
with sync_playwright() as p:
 opts={'headless':True}
 if os.environ.get('CHROMIUM_EXECUTABLE'):opts['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
 b=p.chromium.launch(**opts);c=b.new_context()
 def handler(route):
  u=urlsplit(route.request.url)
  if u.hostname!='frontierlog.test' or not u.path.startswith('/frontierlog/'):
   return route.abort()
  rel=unquote(u.path.removeprefix('/frontierlog/')) or 'index.html';file=(D/rel).resolve()
  if D.resolve() not in file.parents or not file.is_file():return route.fulfill(status=404,body='not found')
  route.fulfill(status=200,body=file.read_bytes(),content_type=mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
 c.route('**/*',handler);page=c.new_page();page.set_default_timeout(7000);page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(base+'#/benchmarks');expect(page.locator('[data-b-card]')).to_have_count(20)
 page.locator('[data-ba="save"][data-id="hle"]').click();page.locator('[data-b-pick="hle"]').check()
 page.reload();expect(page.locator('[data-ba="save"][data-id="hle"]')).to_have_attribute('aria-pressed','true')
 assert page.locator('[data-b-pick="hle"]').is_checked();checks.append('favorites and plan survive real reload on isolated test origin')
 page.goto(base+'#/benchmarks?bench=hle');page.locator('[data-b-check="hle"]').first.check();page.reload()
 assert page.locator('[data-b-check="hle"]').first.is_checked();checks.append('deep-linked drawer and checklist survive reload')
 page.keyboard.press('Escape');page.locator('.b-tab[data-id="report"]').click()
 page.locator('#b-note-title').fill('本地持久化测试');page.locator('[data-ba="notes"]').click();page.reload()
 assert page.locator('.b-report-paper h2').inner_text()=='本地持久化测试';checks.append('local report notes survive reload')
 page.locator('[data-action="theme"]').click();page.reload();assert page.locator('html').get_attribute('data-theme')=='dark';checks.append('theme survives reload')
 page.goto(base+'#/benchmarks');expect(page.locator('[data-b-card]')).to_have_count(20)
 data=page.evaluate("fetch('./api/v1/benchmarks.json').then(r=>r.json())")
 assert len(data['items'])==20;checks.append('nested project path resolves local catalog endpoint')
 other=b.new_context();other.route('**/*',handler);q=other.new_page();q.goto(base+'#/benchmarks')
 expect(q.locator('[data-ba="save"][data-id="hle"]')).to_have_attribute('aria-pressed','false');checks.append('separate visitor context does not inherit favorites')
 assert not errors,errors;b.close()
report={'status':'passed','checks':checks,'groups':len(checks),'errors':errors,'mode':'intercepted HTTPS origin; all responses fulfilled from dist/','not_verified':['Public GitHub Pages deployment/network','Browser links to external sites','Live benchmark execution or collection']}
(OUT/'browser-benchmark-origin.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
