"""Arena regression against the built site; HTTP in CI, offline memory mode locally."""
import functools
import json
import os
from pathlib import Path
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results/arena'
OUT.mkdir(parents=True,exist_ok=True)
MEMORY=os.environ.get('BROWSER_TEST_MODE')=='memory'
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'dist')))
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}/'
checks,errors,layouts=[],[],[]
def passed(name):
    checks.append(name)
    print('PASS',name,flush=True)
try:
    with sync_playwright() as p:
        options={'headless':True}
        if os.environ.get('CHROMIUM_EXECUTABLE'): options['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
        browser=p.chromium.launch(**options)
        context=browser.new_context(viewport={'width':1440,'height':1000},locale='zh-CN',reduced_motion='reduce')
        page=context.new_page()
        page.set_default_timeout(8000)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.route('**/*',lambda r:r.continue_() if not MEMORY and r.request.url.startswith(base) else r.abort())
        if MEMORY:
            page.set_content((ROOT/'dist/index.html').read_text(),wait_until='domcontentloaded')
        def go(route):
            if MEMORY: page.evaluate('(hash)=>{location.hash=hash;lastMain="";parseRoute()}',route)
            else: page.goto(base+route,wait_until='domcontentloaded')
            page.wait_for_timeout(180)
        go('#/models?board=arena')
        expect(page.locator('.ar-table th')).to_have_count(7)
        assert page.locator('.ar-table th').all_text_contents().count('公司')==1
        expect(page.locator('.ar-table tbody tr')).to_have_count(8)
        for row in page.locator('.ar-table tbody tr').all():
            expect(row.locator('td')).to_have_count(7)
            assert '±' not in row.locator('td').nth(2).inner_text()
            expect(row.locator('td').nth(3)).to_contain_text('±')
            expect(row.locator('td').nth(2).locator('a')).to_have_count(1)
        expect(page.locator('.ar-table td').nth(3)).to_contain_text('1,506')
        assert page.locator('.ar-table td:nth-child(2)').first.bounding_box()['width']>=240
        passed('Exactly one company column/link, inline score uncertainty and readable model width')
        expect(page.locator('.ar-provenance')).to_contain_text('人工摘录 8 条 · 非完整榜')
        assert page.locator('.ar-provenance time').evaluate_all('(els)=>els.map(e=>e.dateTime)')==['2026-09-13','2026-09-22']
        assert not page.locator('.v2-current-first').count()
        assert '速度、成本' not in page.locator('.ar-wrap').inner_text()
        passed('Coverage and two date meanings are explicit; generic/champion clutter is removed')
        page.locator('#m-maker').select_option('OpenAI')
        expect(page.locator('.ar-table tbody tr')).to_have_count(1)
        expect(page.locator('.ar-table .ar-rank')).to_have_text('18')
        expect(page.locator('.ar-table .ar-leading')).to_have_count(0)
        expect(page.locator('.ar-resultline [role=status]')).to_contain_text('1 / 8')
        page.locator('.ar-clear').click()
        expect(page.locator('.ar-table tbody tr')).to_have_count(8)
        page.locator('#m-search').fill('Claude')
        expect(page.locator('.ar-table tbody tr')).to_have_count(4)
        expect(page.locator('#m-search')).to_be_focused()
        page.locator('#m-search').fill('<img src=x onerror=alert(1)>')
        expect(page.locator('.ar-empty')).to_be_visible()
        expect(page.locator('.ar-wrap img[src=x]')).to_have_count(0)
        page.locator('.ar-empty [data-ma=model-clear]').click()
        passed('Company/search/empty/reset interactions keep official ranks and escape user input')
        for key,expected in [('score','不是任务正确率'),('votes','不是胜场数'),('rank','不是历史涨跌')]:
            button=page.locator(f'.ar-table [data-ar-help={key}]')
            button.focus();page.keyboard.press('Enter')
            expect(page.locator('dialog[open]')).to_contain_text(expected)
            page.keyboard.press('Escape')
        page.locator('.ar-table .ar-model-name').first.click()
        expect(page.locator('dialog[open]')).to_contain_text('claude-fable-5-high')
        page.keyboard.press('Escape')
        passed('Keyboard-accessible score/vote/rank explanations and model source drawer')
        for width in [1920,1440,1280,1100,1024,820,620,390,360,320]:
            go('#/models?board=arena')
            page.set_viewport_size({'width':width,'height':1000 if width>620 else 844})
            page.evaluate('scrollTo(0,0)');page.wait_for_timeout(250)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,'page overflow')
            mobile=page.locator('.ar-mobile-list').is_visible()
            models=page.locator('.ar-card .ar-model-name') if mobile else page.locator('.ar-table .ar-model-name')
            assert all(x>=16 for x in models.evaluate_all('(els)=>els.map(e=>parseFloat(getComputedStyle(e).fontSize))'))
            if mobile:
                for card in page.locator('.ar-card').all():
                    assert card.evaluate('e=>e.scrollWidth<=e.clientWidth+1'),(width,'card overflow')
            layouts.append({'width':width,'mode':'cards' if mobile else 'table'})
            if width in [1440,1280,390,320]:
                page.screenshot(path=str(OUT/f'arena-{width}.png'),full_page=width==1440)
            if width==390:
                rect=page.locator('.ar-card').first.bounding_box()
                assert rect['y']+rect['height']<=844,(width,'first model below first screen',rect)
        passed('Ten responsive widths, 16px model names, no page/card overflow, first mobile record in first screen')
        page.set_viewport_size({'width':1280,'height':1000})
        page.evaluate("document.documentElement.style.fontSize='200%'")
        page.wait_for_timeout(250)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        expect(page.locator('.ar-mobile-list')).to_be_visible()
        for card in page.locator('.ar-card').all():
            assert card.evaluate('e=>e.scrollWidth<=e.clientWidth+1'),'zoomed card overflow'
        page.screenshot(path=str(OUT/'arena-text-200.png'))
        page.evaluate("document.documentElement.style.fontSize=''")
        passed('200 percent text size switches to readable cards without horizontal page overflow')
        page.set_viewport_size({'width':390,'height':844});go('#/models?board=arena')
        first=page.locator('[data-ar-model="arena-1"]')
        first.locator('summary').click()
        first.locator('[data-ma=star]').click()
        expect(first.locator('details')).to_have_attribute('open','')
        expect(first.locator('[data-ma=star]')).to_have_attribute('aria-pressed','true')
        expect(first.locator('[data-ma=star]')).to_be_focused()
        first.locator('[data-ma=select]').click()
        second=page.locator('[data-ar-model="arena-2"]')
        second.locator('summary').click();second.locator('[data-ma=select]').click()
        page.locator('.m-comparebar [data-ma=compare]').click()
        expect(page.locator('dialog[open]')).to_contain_text('同源比较')
        expect(page.locator('dialog[open]')).to_contain_text('±5')
        page.keyboard.press('Escape')
        page.locator('.m-comparebar [data-ma=compare-clear]').click()
        page.locator('#m-only').check()
        expect(page.locator('.ar-mobile-list .ar-card')).to_have_count(1)
        if not MEMORY:
            page.reload(wait_until='domcontentloaded')
            expect(page.locator('.ar-mobile-list .ar-card')).to_have_count(1)
        page.locator('.ar-clear').click()
        passed('Mobile source disclosures, bookmarks, focus restoration, same-source comparison and saved filter')
        page.set_viewport_size({'width':1280,'height':1000})
        page.locator('[data-ma=board][data-id=aa]').click()
        expect(page.locator('.v2-model-table table th')).to_have_count(8)
        assert page.locator('.v2-model-table table th').all_text_contents().count('公司')==1
        expect(page.locator('.v2-model-table .m-company-cell').first).not_to_contain_text('±')
        page.wait_for_timeout(200)
        expect(page.locator('.v2-model-table table th')).to_have_count(8)
        page.locator('[data-ma=board][data-id=arena]').click()
        expect(page.locator('.ar-table th')).to_have_count(7)
        page.locator('#m-maker').select_option('OpenAI')
        page.screenshot(path=str(OUT/'arena-openai.png'))
        passed('AA and Arena switch without duplicate company columns or stale compare state')
        if not MEMORY:
            page.go_back(wait_until='domcontentloaded')
            expect(page.locator('.ar-table tbody tr')).to_have_count(8)
            passed('Browser Back restores the previous filter state')
        for route,selector in [('#/models?cap=coding','.v3-ranktable'),('#/models?cap=world','.v3-ranktable'),('#/activity','.ah-hero'),('#/hot?cat=product&pview=map&product=harvey','.pb-history-track')]:
            if MEMORY and 'cap=' in route: continue  # These pages load a relative HTTP JSON endpoint.
            go(route);expect(page.locator(selector)).to_be_visible()
        passed(('Activity header and horizontal product timeline smoke checks; capability HTTP loading deferred to CI' if MEMORY else 'Coding/world models, activity header and horizontal product timeline smoke checks'))
        assert not errors,errors
        passed('No JavaScript runtime errors')
        browser.close()
finally:
    server.shutdown()
(OUT/'report.json').write_text(json.dumps({'status':'passed','mode':'memory' if MEMORY else 'HTTP','checks':checks,'layouts':layouts,'errors':errors,'not_verified':['upstream links and live Pages browser fetch']},ensure_ascii=False,indent=2)+'\n')
