"""Test the actual built toolkit; HTTP in CI, memory rendering when network is unavailable."""
import functools
import json
import os
from pathlib import Path
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
TOOLKIT_DATA=json.loads((ROOT/'data/toolkit.json').read_text(encoding='utf-8'))
TOOLKIT_COUNT=len(TOOLKIT_DATA['items'])
OPENAI_COUNT=sum(x.get('publisher')=='OpenAI' for x in TOOLKIT_DATA['items'])
OUT=ROOT/'test-results/toolkit';OUT.mkdir(parents=True,exist_ok=True)
MEMORY=os.environ.get('BROWSER_TEST_MODE')=='memory'
server=None
if not MEMORY:
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'dist')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}/'
else: base=''
checks,errors,layouts=[],[],[]
def passed(name):
    checks.append(name);print('PASS',name,flush=True)
try:
    with sync_playwright() as p:
        opts={'headless':True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):opts['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
        browser=p.chromium.launch(**opts)
        context=browser.new_context(viewport={'width':1440,'height':1000},locale='zh-CN',reduced_motion='reduce')
        page=context.new_page();page.set_default_timeout(8000)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.route('**/*',lambda r:r.continue_() if not MEMORY and r.request.url.startswith(base) else r.abort())
        if MEMORY:page.set_content((ROOT/'dist/index.html').read_text(),wait_until='domcontentloaded')
        def go(route):
            if MEMORY:page.evaluate('(hash)=>{location.hash=hash;lastMain="";parseRoute()}',route)
            else:page.goto(base+route,wait_until='domcontentloaded')
            page.wait_for_timeout(200)
        go('#/toolkit')
        expect(page.locator('.tk-card')).to_have_count(TOOLKIT_COUNT)
        expect(page.locator('.tk-card h2')).to_have_count(10)
        expect(page.locator('.tk-conditions dd')).to_have_count(TOOLKIT_COUNT*2)
        expect(page.locator('[data-tk-id=chatgpt-voice-work] .tk-identity')).to_contain_text('OpenAI')
        assert 'Google DeepMind' not in page.locator('.tk-wrap').inner_text()
        expect(page.locator('.v2-tool')).to_have_count(0)
        passed('Eligible guides match the catalog, with accurate publishers and no duplicate old toolkit')
        page.locator('[data-tk-group=documents]').click();expect(page.locator('.tk-card')).to_have_count(2)
        page.locator('#tk-access').select_option('local');expect(page.locator('.tk-card')).to_have_count(1)
        expect(page.locator('.tk-card')).to_have_attribute('data-tk-id','docling')
        page.locator('#tk-clear').click();expect(page.locator('.tk-card')).to_have_count(10)
        expect(page.locator('#tk-search')).to_be_focused()
        page.locator('#tk-search').fill('OPENAI');expect(page.locator('.tk-card')).to_have_count(OPENAI_COUNT)
        expect(page.locator('#tk-search')).to_be_focused()
        page.locator('#tk-search').fill('<img src=x onerror=alert(1)>');expect(page.locator('.tk-empty')).to_be_visible()
        expect(page.locator('.tk-wrap img[src=x]')).to_have_count(0)
        page.locator('.tk-empty button').click()
        passed('Task, access and publisher filters, empty/reset states, escaped input and retained search focus')
        # Composition must not replace the search node or filter a partially committed IME string.
        page.locator('#tk-search').dispatch_event('compositionstart')
        page.locator('#tk-search').fill('字幕');expect(page.locator('.tk-card')).to_have_count(10)
        page.locator('#tk-search').dispatch_event('compositionend');expect(page.locator('.tk-card')).to_have_count(1)
        expect(page.locator('.tk-card')).to_have_attribute('data-tk-id','whisper')
        page.locator('#tk-clear').click()
        page.locator('[data-tk-group=audio]').click()
        page.evaluate('history.back()');page.wait_for_timeout(300)
        expect(page.locator('[data-tk-group=all]')).to_have_attribute('aria-pressed','true')
        page.locator('.tk-head h1').click();page.keyboard.press('/')
        expect(page.locator('#tk-search')).to_be_focused()
        passed('Chinese IME commit, browser back and toolkit search shortcut')
        summary=page.locator('[data-tk-guide=docling]>summary');summary.focus();page.keyboard.press('Enter')
        expect(page.locator('[data-tk-guide=docling]')).to_have_attribute('open','')
        expect(page.locator('[data-tk-id=docling]')).to_have_class('tk-card is-open')
        command=page.locator('[data-tk-id=docling] .tk-command code').inner_text()
        assert 'docling ./sample.pdf' in command and '\n' in command
        page.evaluate("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async s=>{window.testCopied=s}}})")
        page.locator('[data-tk-id=docling] [data-tk-copy]').click()
        expect(page.locator('[data-tk-id=docling] .tk-copy-status')).to_have_text('已复制这一整段命令。')
        assert page.evaluate('window.testCopied')==command
        expect(page.locator('dialog[open]')).to_have_count(0)
        page.evaluate("() => {navigator.clipboard.writeText=async()=>{throw new Error('denied')}}")
        page.locator('[data-tk-id=docling] [data-tk-copy]').click()
        expect(page.locator('[data-tk-id=docling] .tk-copy-status')).to_contain_text('未能访问剪贴板')
        passed('Native keyboard disclosure and complete clipboard payload; permission failure is explicit')
        check=page.locator('[data-check-task=docling]').first;check.check()
        save=page.locator('[data-tk-save=docling]');save.click()
        expect(save).to_have_attribute('aria-pressed','true');expect(save).to_be_focused()
        expect(page.locator('[data-tk-guide=docling]')).to_have_attribute('open','')
        page.locator('#tk-only').check();expect(page.locator('.tk-card')).to_have_count(1)
        expect(page.locator('[data-check-task=docling]').first).to_be_checked()
        expect(page.locator('.tk-evidence')).to_contain_text('运行未实测')
        if not MEMORY:
            page.reload(wait_until='domcontentloaded')
            expect(page.locator('.tk-card')).to_have_count(1)
            page.locator('[data-tk-guide=docling]>summary').click()
            expect(page.locator('[data-check-task=docling]').first).to_be_checked()
        page.locator('[data-tk-save=docling]').click();expect(page.locator('.tk-empty')).to_be_visible()
        expect(page.locator('#tk-only')).to_be_focused()
        page.locator('.tk-empty button').click()
        passed('Shared bookmarks and personal checklists persist without upgrading runtime evidence')
        go('#/toolkit?task=docling&tab=run')
        expect(page.locator('[data-tk-guide=docling]')).to_have_attribute('open','')
        expect(page.locator('dialog[open]')).to_have_count(0)
        page.locator('[data-tk-guide=docling]>summary').click();page.wait_for_timeout(100)
        page.locator('#tk-search').fill('Docling')
        expect(page.locator('[data-tk-guide=docling]')).not_to_have_attribute('open','')
        page.locator('#tk-clear').click()
        for a in page.locator('.tk-card a').all():
            assert a.get_attribute('href').startswith('https://')
            assert 'noopener' in a.get_attribute('rel')
        passed('Legacy guide links avoid stale modal; closed deep links stay closed; primary links are safe')
        # Export must match the visible selection rather than the legacy unfiltered catalogue.
        page.locator('#tk-search').fill('Whisper')
        if not MEMORY:
            with page.expect_download() as download:
                page.evaluate('exportView()')
            payload=json.loads(Path(download.value.path()).read_text())
            assert [x['id'] for x in payload['items']]==['whisper']
            passed('JSON export contains only currently filtered guides')
        page.locator('#tk-clear').click()
        for width in [1920,1440,1280,1100,1024,820,620,390,360,320]:
            go('#/toolkit');page.set_viewport_size({'width':width,'height':1000 if width>620 else 844})
            page.wait_for_timeout(300)
            if page.locator('[data-tk-guide=docling]').get_attribute('open') is not None:
                page.locator('[data-tk-guide=docling]>summary').click();page.wait_for_timeout(100)
            page.evaluate('scrollTo(0,0)')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,'page overflow')
            assert all(v>=16 for v in page.locator('.tk-identity strong').evaluate_all('(els)=>els.map(e=>parseFloat(getComputedStyle(e).fontSize))'))
            for card in page.locator('.tk-card').all():assert card.evaluate('e=>e.scrollWidth<=e.clientWidth+1'),(width,'card overflow')
            if width in [1440,1280,390,320]:page.screenshot(path=str(OUT/f'toolkit-{width}.png'),full_page=width==1440)
            page.locator('[data-tk-guide=docling]>summary').click()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,'expanded page overflow')
            expect(page.locator('[data-tk-id=docling] .tk-command code')).to_be_visible()
            if width in [1280,390]:page.screenshot(path=str(OUT/f'toolkit-guide-{width}.png'),full_page=width==1280)
            page.locator('[data-tk-guide=docling]>summary').click()
            layouts.append({'width':width,'no_page_overflow':True,'no_card_overflow':True})
        passed('Ten widths, 16px project names and collapsed/expanded layouts without page overflow')
        page.set_viewport_size({'width':1280,'height':1000})
        page.evaluate("document.documentElement.style.fontSize='200%'");page.wait_for_timeout(250)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(OUT/'toolkit-text-200.png'))
        page.evaluate("document.documentElement.style.fontSize='';applyTheme('dark')");page.wait_for_timeout(150)
        expect(page.locator('[data-tk-guide=docling]>summary')).to_be_visible()
        page.screenshot(path=str(OUT/'toolkit-dark.png'))
        page.evaluate("applyTheme('light')")
        passed('200 percent text size and dark mode preserve content and controls')
        for route,selector in [('#/models?board=arena','.ar-table'),('#/hot?cat=product','.pb-wrap'),('#/progress','.p5-progress'),('#/activity','.v2-activity'),('#/toolkit','.tk-wrap')]:
            go(route)
            # These routes evolve separately; require nonempty content and an intact toolkit on return.
            assert len(page.locator('#content').inner_text())+len(page.locator('#vertical-root').inner_text())>80,route
            if route.endswith('toolkit'):expect(page.locator('.tk-card')).to_have_count(10)
        assert not errors,errors
        passed('Navigation to Arena, products, capabilities and activity remains error-free')
        browser.close()
finally:
    if server:server.shutdown()
    (OUT/'report.json').write_text(json.dumps({'mode':'memory' if MEMORY else 'http','checks':checks,'layouts':layouts,'errors':errors},ensure_ascii=False,indent=2))
print(f'{len(checks)} toolkit browser scenarios passed')
