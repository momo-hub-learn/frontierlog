"""Responsive Jev guide checks. Run after scripts/build.py --out dist.

HTTP mode also tests actual clipboard access. BROWSER_TEST_MODE=memory renders
an offline HTML document and tests the selection fallback instead.
"""
import functools
import json
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results' / 'jev'
OUT.mkdir(parents=True, exist_ok=True)
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass
server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT / 'dist')))
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}/'
errors = []
checks = []
MEMORY = os.environ.get('BROWSER_TEST_MODE') == 'memory'
HTML = (ROOT / 'dist/index.html').read_text(encoding='utf-8')
CAPTURE_STYLE = '.topbar{visibility:hidden!important}'

def passed(label):
    checks.append(label)
    print('PASS', label, flush=True)

try:
    with sync_playwright() as p:
        options = {'headless': True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            options['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
        browser = p.chromium.launch(**options)
        context = browser.new_context(viewport={'width': 1512, 'height': 1050}, permissions=['clipboard-read','clipboard-write'])
        page = context.new_page()
        page.set_default_timeout(8000)
        page.on('pageerror', lambda error: errors.append(str(error)))
        if MEMORY:
            page.set_content(HTML, wait_until='load')
            page.evaluate("location.hash='#/deep?id=jev-agent-decision-layer'")
        else:
            page.goto(url + '#/deep?id=jev-agent-decision-layer', wait_until='domcontentloaded')
        expect(page.locator('.d-visual')).to_be_visible()
        expect(page.locator('.d-section')).to_have_count(7)
        expect(page.locator('.dv-scene-verdict')).to_contain_text('因果已证明')
        for key in ['supported','next_step','relevance']:
            page.locator('#dv-tab-' + key).click()
            expect(page.locator('#dv-panel-' + key)).to_be_visible()
            assert page.locator('.dv-demo [role="tabpanel"]:visible').count() == 1
        passed('three primitive tabs change content, exactly one visible panel')
        for key in ['theme','model','agent','knowledge']:
            page.locator('#dv-app-tab-' + key).click()
            expect(page.locator('#dv-app-' + key)).to_be_visible()
            assert page.locator('.dv-applications [role="tabpanel"]:visible').count() == 1
        passed('four application tabs switch architecture, MVP, data and metrics')
        page.locator('#dv-tab-supported').click()
        page.locator('#dv-tab-supported').focus()
        page.keyboard.press('ArrowRight')
        expect(page.locator('#dv-tab-next_step')).to_be_focused()
        expect(page.locator('#dv-panel-next_step')).to_be_visible()
        passed('keyboard tab navigation and ARIA state')
        copy = page.locator('#dv-panel-next_step [data-d-copy]').first
        expected = page.locator('#dv-panel-next_step pre code').first.inner_text()
        copy.click()
        if MEMORY:
            assert page.evaluate('window.getSelection().toString()') == expected
            passed('clipboard-unavailable fallback selects the complete code')
        else:
            expect(copy).to_have_text('已复制')
            assert page.evaluate('navigator.clipboard.readText()') == expected
            passed('copy returns code, not markup')
        with page.expect_download() as download_info:
            page.locator('[data-d-download]').click()
        download = download_info.value
        request = json.loads(Path(download.path()).read_text())
        assert request['model'] == 'jev-1.13.0' and len(request['questions']) == 3
        passed('downloaded request JSON is complete and version-pinned')
        page.locator('.dv-details summary').click()
        expect(page.locator('.dv-details pre')).to_be_visible()
        page.locator('.dv-details summary').click()
        passed('full request disclosure opens and closes')
        page.locator('#dv-tab-supported').click()
        page.locator('#dv-app-tab-theme').click()
        for width in [360,390,768,1280,1512]:
            page.set_viewport_size({'width':width,'height':1050})
            page.wait_for_timeout(100)
            size = page.evaluate('({doc:document.documentElement.scrollWidth,win:innerWidth})')
            assert size['doc'] <= size['win'], (width,size)
            overflow = page.locator('.d-visual').evaluate('el=>[...el.querySelectorAll("pre,.dv-figure,.dv-demo,.dv-applications")].filter(x=>x.getBoundingClientRect().width>0 && x.scrollWidth>x.clientWidth+2).map(x=>x.className)')
            assert not overflow, (width,overflow)
            page.evaluate('window.scrollTo(0,0)')
            page.screenshot(path=str(OUT / f'{width}-top.png'))
            if width in [390,1512]:
                for key in ['scene','interface','implementation','stack','applications','evaluation']:
                    page.locator('#deep-' + key).screenshot(path=str(OUT / f'{width}-{key}.png'), style=CAPTURE_STYLE)
            passed(f'{width}px viewport: no document or diagram/code horizontal overflow')
        page.evaluate('document.documentElement.dataset.theme="dark"')
        page.locator('#deep-stack').screenshot(path=str(OUT / 'dark-stack.png'), style=CAPTURE_STYLE)
        passed('dark theme renders the same semantic architecture')
        page.emulate_media(media='print')
        assert page.locator('.dv-demo [role="tabpanel"]:visible').count() == 3
        assert page.locator('.dv-applications [role="tabpanel"]:visible').count() == 4
        page.emulate_media(media='screen')
        passed('printing exposes every primitive and every application')
        page.evaluate('document.documentElement.dataset.theme="light"')
        for route in ['#/feed','#/hot?tab=github','#/hot?tab=hf','#/models','#/activity']:
            if MEMORY:
                page.evaluate('(route)=>location.hash=route', route)
            else:
                page.goto(url + route, wait_until='domcontentloaded')
            page.wait_for_timeout(120)
            assert page.locator('h1,h2').count() > 0
            assert page.locator('.d-visual').count() == 0
        passed('feed, GitHub/HuggingFace hot lists, models and activity route smoke checks')
        assert not errors, errors
        passed('no uncaught JavaScript errors')
        (OUT/'checks.json').write_text(json.dumps({'mode':'memory' if MEMORY else 'http','checks':checks,'errors':errors}, ensure_ascii=False, indent=2))
        browser.close()
finally:
    server.shutdown()
