"""Real-browser editorial QA for the REA article, including the broken-workflow regression.

Runs against built dist/index.html. Screenshots are review artifacts, not
substitutes for DOM, CSS and page-overflow assertions.
"""
from pathlib import Path
import functools
import json
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results'/'rea'
OUT.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'dist')))
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/#/deep?id=rea-agent-reverse-engineering'
errors=[]
checks=[]
def passed(label):
    checks.append(label)
    print('PASS',label,flush=True)

def check_no_global_overflow(page,width):
    size=page.evaluate('({document:document.documentElement.scrollWidth,window:innerWidth})')
    if size['document']>size['window']:
        offenders=page.evaluate("""() => [...document.querySelectorAll('body *')].filter(x => {
            const r=x.getBoundingClientRect(),st=getComputedStyle(x);
            return r.width>0&&st.position!=='fixed'&&r.right>innerWidth+0.5;
        }).map(x=>({tag:x.tagName,css:String(x.className).slice(0,80),
            right:Math.round(x.getBoundingClientRect().right)})).slice(0,18)""")
        print('OVERFLOW',width,size,offenders,flush=True)
    assert size['document']<=size['window'],(width,size)

try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,**(
            {'executable_path':os.environ['CHROMIUM_EXECUTABLE']}
            if os.environ.get('CHROMIUM_EXECUTABLE') else {}))
        context=browser.new_context(viewport={'width':1440,'height':950},device_scale_factor=1)
        page=context.new_page()
        page.set_default_timeout(12000)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(url,wait_until='domcontentloaded')
        expect(page.locator('.d-page.d-editorial.d-visual')).to_be_visible()
        expect(page.locator('.d-section')).to_have_count(9)
        expect(page.locator('.d-role-workflow')).to_have_count(1)
        expect(page.locator('.d-role-step')).to_have_count(4)
        expect(page.locator('.d-role-table tbody tr')).to_have_count(4)
        expect(page.locator('.je-table')).to_have_count(4)
        expect(page.locator('.d-sys')).to_have_count(1)
        assert page.locator('.dv-flow[role="list"]').count()==2
        assert page.locator('ol.dv-flow').count()==0
        assert page.locator('.dv-flow-step[role="listitem"]').count()==7
        passed('two genuine workflow layouts, four responsibility cards and four styled evidence tables')
        workflow=page.locator('.d-role-workflow')
        expect(workflow.locator('h3')).to_contain_text('调查链')
        for name in ['Agent','REA','分析引擎','复核与实现']:
            assert workflow.inner_text().count(name)>=1
        assert page.locator('.dv-flow').first.evaluate('(e)=>getComputedStyle(e).display')=='grid'
        assert page.locator('.dv-code pre').first.evaluate('(e)=>getComputedStyle(e).whiteSpace')=='pre-wrap'
        assert page.locator('.je-figure').first.evaluate('(e)=>getComputedStyle(e).borderTopStyle')=='solid'
        assert workflow.evaluate('(e)=>getComputedStyle(e).borderTopStyle')=='solid'
        passed('figure, workflow, code and table have actual computed styles, not UA fallback')
        for width in (320,390,768,1024,1440):
            page.set_viewport_size({'width':width,'height':930})
            page.wait_for_timeout(150)
            check_no_global_overflow(page,width)
            expect(workflow).to_be_visible()
            assert workflow.locator('.d-role-step').count()==4
            assert workflow.locator('tbody tr').count()==4
            role_columns=workflow.locator('.d-role-steps').evaluate('(e)=>getComputedStyle(e).gridTemplateColumns')
            col_count=len(role_columns.split(' '))
            assert col_count==(1 if width<=390 else 2 if width<=1024 else 4),(width,role_columns)
            article_width=page.locator('.d-article').evaluate('(el)=>el.getBoundingClientRect().width')
            role_width=workflow.evaluate('(el)=>el.getBoundingClientRect().width')
            assert role_width<=article_width+1,(width,role_width,article_width)
            workflow.screenshot(path=str(OUT/f'{width}-roles.png'))
            if width in (390,1440):
                page.locator('.dv-flow-figure').first.screenshot(path=str(OUT/f'{width}-workflow.png'))
                page.locator('.je-figure').first.screenshot(path=str(OUT/f'{width}-table.png'))
            passed(f'{width}px: readable figure and role matrix, no double numbers or document overflow')
        page.evaluate("document.documentElement.dataset.theme='dark'")
        assert workflow.locator('tbody tr').count()==4
        workflow.screenshot(path=str(OUT/'dark-roles.png'))
        passed('dark-mode figure and editorial table remain present')
        page.evaluate("document.documentElement.dataset.theme='light'")
        page.emulate_media(media='print')
        assert page.locator('.d-role-step').count()==4
        page.emulate_media(media='screen')
        passed('print media retains diagram and table')
        assert not errors,errors
        passed('no uncaught JavaScript errors')
        (OUT/'checks.json').write_text(json.dumps({'checks':checks,'errors':errors},ensure_ascii=False,indent=2))
        browser.close()
finally:
    server.shutdown()
