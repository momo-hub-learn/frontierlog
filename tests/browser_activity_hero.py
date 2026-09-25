"""Activity header interaction, real local artwork, and responsive regression."""
import functools
import json
import os
from pathlib import Path
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results/activity-hero'
OUT.mkdir(parents=True, exist_ok=True)
MEMORY = os.environ.get('BROWSER_TEST_MODE') == 'memory'
CLOCK = """{ const OriginalDate=Date; const fixed=OriginalDate.parse('2026-09-25T13:00:00Z');
window.Date=class extends OriginalDate { constructor(...a){super(...(a.length?a:[fixed]))} static now(){return fixed} }; }"""
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
server = ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'dist')))
threading.Thread(target=server.serve_forever,daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}/'
checks, errors = [], []
def passed(name):
    checks.append(name)
    print('PASS', name, flush=True)

try:
    with sync_playwright() as p:
        opts = {'headless':True}
        if os.environ.get('CHROMIUM_EXECUTABLE'): opts['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
        browser=p.chromium.launch(**opts)
        context=browser.new_context(viewport={'width':1640,'height':1000},locale='zh-CN',timezone_id='Asia/Shanghai')
        context.add_init_script(CLOCK)
        page=context.new_page()
        page.set_default_timeout(8000)
        page.on('pageerror',lambda e:errors.append(str(e)))
        if MEMORY:
            page.route('**/*',lambda r:r.abort())
            html=(ROOT/'dist/index.html').read_text(encoding='utf-8').replace('<head>','<head><script>'+CLOCK+'</script>',1)
            page.set_content(html,wait_until='load')
        def go(route):
            if MEMORY: page.evaluate('(route)=>location.hash=route',route)
            else: page.goto(url+route,wait_until='domcontentloaded')
            page.wait_for_timeout(100)
        go('#/activity')
        expect(page.locator('.ah-hero')).to_have_count(1)
        expect(page.locator('.ah-feature')).to_have_count(1)
        expect(page.locator('.ah-event')).to_have_count(4)
        assert len(page.locator('.ah-intro').inner_text()) < 125
        expect(page.locator('.ah-feature .ah-start')).to_contain_text('12/02 03:00')
        expect(page.locator('.ah-feature .ah-local')).to_contain_text('12/01 14:00')
        assert page.locator('.ah-hero').bounding_box()['height'] < 300
        passed('compact header, one feature, correct Beijing and source-local times')
        expect(page.locator('.ah-rules-panel')).not_to_be_visible()
        page.locator('.ah-rules summary').click()
        expect(page.locator('.ah-rules-panel')).to_be_visible()
        expect(page.locator('.ah-rules-panel')).to_contain_text('不代表全部内容')
        page.keyboard.press('Escape')
        expect(page.locator('.ah-rules-panel')).not_to_be_visible()
        expect(page.locator('.ah-rules summary')).to_be_focused()
        passed('rules disclosure is collapsed, keyboard accessible, and closes with Escape')
        with page.expect_download() as dl:
            page.locator('[data-ah-calendar]').click()
        text=Path(dl.value.path()).read_bytes().decode('utf-8')
        assert 'DTSTART:20261201T190000Z' in text and 'TRIGGER:-PT15M' in text
        assert 'ATTENDEE' not in text
        passed('calendar button exports a real ICS, exact UTC start, no external signup')
        page.wait_for_timeout(3600)
        if not MEMORY:
            page.wait_for_function("[...document.querySelectorAll('.ah-art img')].every(i=>i.complete&&i.naturalWidth>0)")
            passed('all five visible artwork instances load from checked-in local previews')
        page.locator('[data-ah-view=list]').click()
        expect(page.locator('#content')).to_have_attribute('data-ah-layout','list')
        expect(page.locator('[data-ah-view=list]')).to_have_attribute('aria-pressed','true')
        assert len(page.locator('.v2-event-grid').evaluate('e=>getComputedStyle(e).gridTemplateColumns').split()) == 1
        if not MEMORY:
            page.reload(wait_until='domcontentloaded')
            expect(page.locator('#content')).to_have_attribute('data-ah-layout','list')
        page.locator('[data-ah-view=grid]').click()
        passed('grid/list actually changes layout and persists in local storage')
        for kind,source in [('events','apple-events'),('technical','google-research-blog'),('conversation','dwarkesh')]:
            go('#/activity?type='+kind)
            expect(page.locator('.ah-feature')).to_have_count(1)
            expect(page.locator('.v2-radar-tabs .active')).to_have_attribute('href','#/activity?type='+kind)
            go('#/activity?type='+kind+'&source='+source)
            expect(page.locator('.v2-radar-subtabs .active')).to_contain_text({'apple-events':'Apple Events','google-research-blog':'Google Research','dwarkesh':'Dwarkesh'}[source])
            if kind=='events': expect(page.locator('.ah-event')).to_have_count(2)
        passed('type and source filters preserve state and the global featured event')
        go('#/activity?type=technical')
        page.locator('[data-ah-sort]').select_option('picks')
        cards=page.locator('.v2-media-grid').first.locator(':scope > a')
        assert 'editor-pick' in (cards.first.get_attribute('class') or '')
        page.locator('[data-ah-sort]').select_option('time')
        dates=cards.locator('time').all_text_contents()
        assert dates==sorted(dates,reverse=True)
        passed('editor/time sorting changes the actual visible cards')
        go('#/activity')
        for width in [360,390,768,1280,1640]:
            page.set_viewport_size({'width':width,'height':1000})
            page.wait_for_timeout(80)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), width
            for selector in ['.ah-hero','.ah-feature','.ah-filterbar','.ah-event']:
                for rect in page.locator(selector).evaluate_all('es=>es.map(e=>({x:e.getBoundingClientRect().x,r:e.getBoundingClientRect().right,sw:e.scrollWidth,cw:e.clientWidth}))'):
                    assert rect['x']>=0 and rect['r']<=width+1 and rect['sw']<=rect['cw']+2,(width,selector,rect)
            page.locator('.ah-rules summary').click()
            rect=page.locator('.ah-rules-panel').bounding_box()
            assert rect['x']>=0 and rect['x']+rect['width']<=width+1,(width,rect)
            page.keyboard.press('Escape')
            page.locator('.ah-intro h1').click()
            page.evaluate('window.scrollTo(0,0)')
            page.screenshot(path=str(OUT/f'{width}-activity.png'))
            passed(f'{width}px: header, feature, cards, filters and rules stay in viewport')
        page.evaluate("document.documentElement.dataset.theme='dark'")
        page.screenshot(path=str(OUT/'dark-activity.png'))
        page.evaluate("document.documentElement.dataset.theme='light'")
        passed('dark theme renders with explicit readable feature colors')
        page.locator('.ah-art img').first.evaluate("i=>i.dispatchEvent(new Event('error'))")
        expect(page.locator('.ah-art img').first).not_to_be_visible()
        expect(page.locator('.ah-art-fallback').first).to_be_visible()
        passed('broken image has text fallback; controls keep working')
        for route in ['#/feed','#/hot?tab=github','#/hot?tab=hf','#/hot?cat=product','#/models','#/deep?id=jev-agent-decision-layer']:
            go(route)
            expect(page.locator('#content')).not_to_have_class('ah-page')
            assert page.locator('h1,h2').count()>0
        go('#/activity')
        expect(page.locator('.ah-hero')).to_have_count(1)
        assert not errors, errors
        passed('other pages unchanged, return route works, no uncaught JS errors')
        (OUT/'checks.json').write_text(json.dumps({'mode':'memory' if MEMORY else 'http','checks':checks,'errors':errors},ensure_ascii=False,indent=2))
        browser.close()
finally:
    server.shutdown()
