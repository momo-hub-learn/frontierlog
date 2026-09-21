"""End-to-end UI checks against an actual local HTTP server. No remote account access."""
from __future__ import annotations
import functools
import json
import os
import threading
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results';OUT.mkdir(exist_ok=True)
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/dist/index.html'
checks=[];errors=[]
MEMORY=os.environ.get('BROWSER_TEST_MODE')=='memory'
HTML=(ROOT/'dist/index.html').read_text(encoding='utf-8')
def passed(name):checks.append(name);print('PASS',name,flush=True)
try:
 with sync_playwright() as p:
    options={'headless':True}
    if os.environ.get('CHROMIUM_EXECUTABLE'):options['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
    browser=p.chromium.launch(**options)
    context=browser.new_context(viewport={'width':1512,'height':1100},device_scale_factor=1)
    page=context.new_page();page.set_default_timeout(8000)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content(HTML,wait_until='load') if MEMORY else page.goto(url,wait_until='load')
    page.evaluate("location.hash='#/progress'"); page.wait_for_timeout(100)
    expect(page.locator('.task-card')).to_have_count(8)
    assert page.locator('html').get_attribute('data-theme')=='light'
    assert page.evaluate('getComputedStyle(document.body).backgroundColor')=='rgb(245, 247, 244)'
    assert page.evaluate('getComputedStyle(document.body).color')=='rgb(21, 33, 36)'
    assert page.locator('meta[name="theme-color"]').get_attribute('content')=='#f5f7f4'
    assert page.locator('[data-action="theme"]').get_attribute('aria-label')=='切换为深色'
    passed('reference palette is the default; theme color and control label agree')
    assert page.locator('#nav a.active').inner_text().startswith('AI 又能干什么了')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    passed('desktop initial page and no horizontal overflow')
    page.screenshot(path=str(OUT/'desktop.png'),full_page=True)
    page.locator('[data-category="企业知识"]').click()
    expect(page.locator('.task-card')).to_have_count(1)
    page.locator('[data-category="全部"]').click()
    page.locator('#search').fill('Whisper')
    expect(page.locator('.task-card')).to_have_count(1)
    page.locator('#search').fill('no-such-project-xyz')
    expect(page.locator('.empty')).to_have_count(1)
    page.locator('[data-action="reset"]').click()
    expect(page.locator('.task-card')).to_have_count(8)
    passed('category filters, search, empty state, reset')
    page.locator('[data-layout="matrix"]').click()
    expect(page.locator('.matrix tbody tr')).to_have_count(8)
    page.screenshot(path=str(OUT/'matrix.png'),full_page=True)
    (None if MEMORY else page.reload());expect(page.locator('.matrix tbody tr')).to_have_count(8)
    page.locator('[data-layout="cards"]').click()
    passed('matrix view (persistence only checked in HTTP mode)')
    page.locator('.task-card .save[data-id="graphrag"]').click()
    if not MEMORY: page.reload()
    expect(page.locator('.task-card .save.active')).to_have_count(1)
    page.locator('#nav a[href="#/saved"]').click()
    expect(page.locator('.task-card')).to_have_count(1)
    page.locator('#nav a[href="#/progress"]').click()
    passed('saved collection (reload persistence only checked in HTTP mode)')
    for id in ['graphrag','docling','browser-use']:
        page.locator(f'.task-card [data-action="compare-toggle"][data-id="{id}"]').click()
    assert page.locator('#compare-tray').is_visible()
    page.locator('.task-card [data-action="compare-toggle"][data-id="whisper"]').click()
    expect(page.locator('.compare-toggle.active')).to_have_count(3)
    page.locator('#compare-tray [data-action="compare"]').click()
    expect(page.locator('.compare-table thead td')).to_have_count(3)
    page.wait_for_timeout(2900)
    page.screenshot(path=str(OUT/'compare.png'),full_page=False)
    with page.expect_download() as d:page.locator('[data-action="export-compare"]').click()
    assert d.value.suggested_filename.endswith('.md')
    page.keyboard.press('Escape');page.locator('[data-action="compare-clear"]').click()
    passed('three-project compare limit, table and Markdown export')
    page.locator('.task-card [data-action="task"][data-id="docling"]').first.click()
    assert page.locator('#modal').evaluate('(e)=>e.open')
    assert 'task=docling' in page.url
    expect(page.locator('#modal .source-row')).to_have_count(3)
    page.wait_for_timeout(2900)
    page.screenshot(path=str(OUT/'detail.png'),full_page=False)
    if not MEMORY: page.reload()
    assert page.locator('#modal').evaluate('(e)=>e.open')
    page.locator('[data-task-tab="timeline"]').click()
    expect(page.locator('#modal .event')).to_have_count(2)
    page.locator('[data-task-tab="run"]').click()
    expect(page.locator('#modal .codebox')).to_have_count(1)
    page.locator('[data-check-task="docling"][data-check-index="0"]').check()
    (None if MEMORY else page.reload());assert page.locator('[data-check-task="docling"][data-check-index="0"]').is_checked()
    page.keyboard.press('Escape')
    page.wait_for_function("!location.hash.includes('task=')")
    passed('hash routing, task timeline and checklist (reload tested only in HTTP mode)')
    page.locator('[data-action="command"]').click()
    page.locator('#palette-input').fill('Whisper')
    expect(page.locator('.palette-item')).to_have_count(1)
    page.keyboard.press('Enter')
    assert 'Whisper' in page.locator('#modal-title').inner_text() or '语音' in page.locator('#modal-title').inner_text()
    page.keyboard.press('Escape')
    page.keyboard.press('Control+k')
    assert page.locator('#palette').evaluate('(d)=>d.open')
    page.keyboard.press('Escape')
    passed('command palette search and keyboard navigation')
    page.locator('#nav a[href="#/activity"]').click()
    expect(page.locator('.event')).to_have_count(6)
    page.screenshot(path=str(OUT/'activity.png'),full_page=True)
    page.locator('[data-kind="research"]').click()
    expect(page.locator('.event')).to_have_count(3)
    page.locator('[data-kind="upstream"]').click()
    expect(page.locator('.empty')).to_have_count(1)
    page.locator('#nav a[href="#/toolkit"]').click()
    expect(page.locator('.tool-card')).to_have_count(7)
    page.locator('#nav a[href="#/digest"]').click()
    expect(page.locator('.digest article')).to_have_count(2)
    with page.expect_download() as d:page.locator('[data-action="digest-export"]').click()
    d.value.save_as(str(OUT/'digest.md'))
    passed('activity, evidence filters, toolkit and digest export')
    if not page.locator('.brand-resources').evaluate('e=>e.open'):page.locator('.brand-resources summary').click()
    page.locator('[data-action="contribute"]').first.click()
    page.locator('[name="title"]').fill('Test contribution')
    page.locator('[name="source"]').fill('https://example.org/source')
    page.locator('[name="notes"]').fill('UI test only, not factual evidence')
    page.evaluate("window.__opened=[];window.open=(url)=>{window.__opened.push(url);return null}")
    page.locator('#contribute-form button[type="submit"]').click()
    assert '/momo-hub-learn/frontierlog/issues/new?' in (page.evaluate('window.__opened.at(-1)') or '')
    page.keyboard.press('Escape')
    passed('contribution opens correctly targeted Issue draft; window.open intercepted, no submission')
    page.locator('#nav a[href="#/saved"]').click()
    with page.expect_download() as d:page.locator('[data-action="export-saved"]').click()
    saved_path=OUT/'collection.json';d.value.save_as(str(saved_path))
    page.locator('.task-card .save').first.click()
    expect(page.locator('.empty')).to_have_count(1)
    page.locator('#import-file').set_input_files(str(saved_path))
    expect(page.locator('.task-card')).to_have_count(1)
    bad=OUT/'bad-import.json';bad.write_text('{"version":1,"saved":"bad"}')
    page.locator('#import-file').set_input_files(str(bad))
    expect(page.locator('.task-card')).to_have_count(1)
    passed('collection export, validated import, malformed import rejected')
    page.locator('#nav a[href="#/progress"]').click()
    page.screenshot(path=str(OUT/'light.png'),full_page=True)
    page.locator('[data-action="theme"]').click()
    assert page.locator('html').get_attribute('data-theme')=='dark'
    assert page.locator('meta[name="theme-color"]').get_attribute('content')=='#101819'
    assert page.locator('[data-action="theme"]').get_attribute('aria-label')=='切换为浅色'
    (None if MEMORY else page.reload());assert page.locator('html').get_attribute('data-theme')=='dark'
    page.screenshot(path=str(OUT/'dark.png'),full_page=True)
    page.locator('[data-action="theme"]').click()
    assert page.locator('html').get_attribute('data-theme')=='light'
    assert page.locator('meta[name="theme-color"]').get_attribute('content')=='#f5f7f4'
    passed('optional dark theme and return to light (reload persistence only checked in HTTP mode)')
    if not page.locator('.brand-resources').evaluate('e=>e.open'):page.locator('.brand-resources summary').click()
    with page.expect_download() as d:page.locator('.sidebar [data-action="data"]').click()
    payload=json.loads(Path(d.value.path()).read_text())
    assert len(payload['catalog']['items'])==8
    page.locator('[data-action="repo"]').click()
    assert page.evaluate('window.__opened.at(-1)')=='https://github.com/momo-hub-learn/frontierlog'
    passed('open-data export and correct configured repository link')
    # Actual mobile origin uses a separate context, including independent localStorage.
    mobile_context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=1)
    mobile=mobile_context.new_page();mobile.on('pageerror',lambda e:errors.append(str(e)))
    mobile.set_content(HTML,wait_until='load') if MEMORY else mobile.goto(url)
    assert mobile.evaluate('document.documentElement.scrollWidth<=innerWidth')
    mobile.screenshot(path=str(OUT/'mobile.png'),full_page=True)
    mobile.locator('[data-action="menu"]').click()
    mobile.locator('#nav a[href="#/activity"]').click()
    expect(mobile.locator('body')).not_to_have_class('nav-open')
    expect(mobile.locator('.event')).to_have_count(6)
    assert mobile.evaluate('document.documentElement.scrollWidth<=innerWidth')
    mobile.locator('.event [data-action="task"]').first.click()
    assert mobile.locator('#modal').is_visible()
    assert mobile.locator('#modal').evaluate('(e)=>e.scrollWidth<=e.clientWidth')
    mobile.locator('[data-task-tab="run"]').click()
    assert mobile.locator('#modal').evaluate('(e)=>e.scrollWidth<=e.clientWidth')
    mobile.screenshot(path=str(OUT/'mobile-detail.png'),full_page=False)
    passed('mobile navigation, no overflow, drawer and run view')
    assert not errors,errors
    report={'passed':True,'browser':'Chromium','mode':'in-memory set_content; environment blocks HTTP/file navigation' if MEMORY else 'real localhost HTTP server, nested /dist/ path','checks':checks,'javascript_errors':errors,'not_tested':[*(['Real-origin localStorage persistence','Full navigation/reload deep links'] if MEMORY else []),'Public GitHub Pages deployment','Authenticated target GitHub account','Live GitHub REST collection (not attempted in this palette update)','Third-party AI tools themselves'],'screenshots':['desktop.png','matrix.png','detail.png','compare.png','activity.png','light.png','dark.png','mobile.png','mobile-detail.png']}
    (OUT/'browser-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    browser.close()
finally:
 server.shutdown();server.server_close()
