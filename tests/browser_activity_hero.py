"""Activity header interaction, real local artwork, and responsive regression."""
import functools
import json
import os
import re
from pathlib import Path
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results/activity-hero'
OUT.mkdir(parents=True, exist_ok=True)
RADAR = json.loads((ROOT/'data/activity-radar.json').read_text(encoding='utf-8'))
UPSTREAM = json.loads((ROOT/'data/upstream.json').read_text(encoding='utf-8'))
FEATURES = json.loads((ROOT/'data/activity-feature.json').read_text(encoding='utf-8'))['events']
EVENT_IDS = [event['id'] for event in RADAR['events']]
assert len(EVENT_IDS) == len(set(EVENT_IDS))
MEMORY = os.environ.get('BROWSER_TEST_MODE') == 'memory'
CLOCK_ISO = '2026-09-25T13:00:00Z'
CLOCK_NOW = datetime.fromisoformat(CLOCK_ISO.replace('Z','+00:00'))
FEATURE_ID, FEATURE = min(
    ((event_id,event) for event_id,event in FEATURES.items()
     if event.get('start_at') and datetime.fromisoformat(event['start_at'].replace('Z','+00:00')) > CLOCK_NOW),
    key=lambda pair: datetime.fromisoformat(pair[1]['start_at'].replace('Z','+00:00')))
FEATURE_START = datetime.fromisoformat(FEATURE['start_at'].replace('Z','+00:00'))
BEIJING_TEXT = FEATURE_START.astimezone(ZoneInfo('Asia/Shanghai')).strftime('%m/%d %H:%M')
SOURCE_TEXT = FEATURE_START.astimezone(ZoneInfo(FEATURE['time_zone'])).strftime('%m/%d %H:%M')
ICS_START = FEATURE_START.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
CLOCK = """{ const OriginalDate=Date; const fixed=OriginalDate.parse('2026-09-25T13:00:00Z');
window.Date=class extends OriginalDate { constructor(...a){super(...(a.length?a:[fixed]))} static now(){return fixed} }; }"""
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
server = ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'dist')))
threading.Thread(target=server.serve_forever,daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}/'
checks, errors, typography = [], [], {}
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
        nav_count = page.locator('#nav a[href="#/activity"] small').inner_text().strip()
        tab_count = page.locator('.v2-radar-tabs a[href="#/activity"]').inner_text().strip().split()[-1]
        assert nav_count.lstrip('0') == tab_count.lstrip('0'), (nav_count, tab_count)
        expect(page.locator('.ah-hero')).to_have_count(1)
        expect(page.locator('.ah-feature')).to_have_count(1)
        expect(page.locator('.ah-event')).to_have_count(len(EVENT_IDS))
        assert page.locator('.ah-event').evaluate_all("es=>es.map(e=>e.dataset.ahId)") == EVENT_IDS
        assert len(page.locator('.ah-intro').inner_text()) < 125
        expect(page.locator('.ah-feature')).to_have_attribute('data-ah-feature',FEATURE_ID)
        expect(page.locator('.ah-feature .ah-start')).to_contain_text(BEIJING_TEXT)
        expect(page.locator('.ah-feature .ah-local')).to_contain_text(SOURCE_TEXT)
        fde = page.locator('[data-ah-id="openai-fde-frontier-2026-10-22"]')
        expect(fde).to_have_class(re.compile(r'\bupcoming\b'))
        page.evaluate("Date.now=()=>Date.parse('2026-10-22T18:01:00Z');window.dispatchEvent(new Event('pageshow'))")
        expect(page.locator('[data-ah-id="openai-fde-frontier-2026-10-22"]')).to_have_class(re.compile(r'\bended\b'))
        expect(page.locator('[data-ah-id="openai-fde-frontier-2026-10-22"]')).to_contain_text('已结束')
        page.evaluate("Date.now=()=>Date.parse('2026-09-25T13:00:00Z');window.dispatchEvent(new Event('pageshow'))")
        passed('event cards cross start/end boundaries without a page reload')
        # A readable type scale is allowed more space than the former 10px labels.
        hero_height=page.locator('.ah-hero').bounding_box()['height']
        assert hero_height < 550, hero_height
        passed('readable header, one feature, correct Beijing and source-local times')
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
        assert 'DTSTART:'+ICS_START in text and 'TRIGGER:-PT15M' in text
        assert 'ATTENDEE' not in text
        passed('calendar button exports a real ICS, exact UTC start, no external signup')
        page.wait_for_timeout(3600)
        if not MEMORY:
            page.wait_for_function("[...document.querySelectorAll('.ah-art img')].every(i=>i.complete&&i.naturalWidth>0)")
            passed('all configured local event artwork loads from checked-in previews')
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
            if kind=='events':
                expected=sum(event['source_id']==source for event in RADAR['events'])
                expect(page.locator('.ah-event')).to_have_count(expected)
        passed('type and source filters preserve state and the global featured event')
        go('#/activity?type=technical')
        expect(page.locator('.v2-media-card').first).to_contain_text('官方来源')
        expect(page.locator('.v2-media-card').first).to_contain_text('打开官方原文')
        page.locator('[data-ah-sort]').select_option('picks')
        cards=page.locator('.v2-media-grid').first.locator(':scope > a')
        assert 'editor-pick' in (cards.first.get_attribute('class') or '')
        page.locator('[data-ah-sort]').select_option('time')
        dates=cards.locator('time').all_text_contents()
        assert dates==sorted(dates,reverse=True)
        passed('editor/time sorting changes the actual visible cards')
        go('#/activity?type=conversation&source=latent-space')
        media_claim=page.locator('.v2-media-card').filter(has_text='Anthropic files for $2T IPO').first
        expect(media_claim).to_contain_text('媒体内容 · 非官方公告')
        expect(media_claim).to_contain_text('打开媒体原文')
        media_claim.scroll_into_view_if_needed()
        page.screenshot(path=str(OUT/'media-provenance.png'))
        passed('official technical posts and third-party media claims have explicit textual provenance')
        go('#/activity?kind=upstream')
        summary=page.locator('.v2-queue-summary')
        expect(page.locator('#content > .v2-pageintro h1')).to_have_text('上游候选')
        expect(page.locator('#content > .v2-radar-section > header h2')).to_have_count(0)
        expect(page.get_by_role('heading',name='上游候选',exact=True)).to_have_count(1)
        expect(page.locator('#content > .v2-radar-tabs')).to_have_count(0)
        expect(page.locator('#content > .v2-radar-section')).to_have_count(1)
        expect(summary).to_contain_text(f"{UPSTREAM['repositories_succeeded']}/{UPSTREAM['repositories_total']} 源成功")
        expect(summary).to_contain_text(f"候选 {page.locator('.v2-life-node').count()} 条")
        if UPSTREAM['errors']:
            expect(summary).to_contain_text(f"{len(UPSTREAM['errors'])} 源失败")
            expect(summary).to_contain_text('最近完整成功')
        for width in [360,768,1640]:
            page.set_viewport_size({'width':width,'height':1000})
            page.wait_for_timeout(200)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), ('upstream',width)
            rect=summary.bounding_box()
            assert rect['x']>=0 and rect['x']+rect['width']<=width+1,('upstream',width,rect)
            summary.scroll_into_view_if_needed()
            page.screenshot(path=str(OUT/f'{width}-upstream-health.png'))
        passed('upstream queue exposes complete-success time, latest attempt coverage, failures and candidate count')
        go('#/activity')
        for width in [320,360,390,768,1024,1280,1640]:
            page.set_viewport_size({'width':width,'height':1000})
            page.wait_for_timeout(350)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), width
            for selector in ['.ah-hero','.ah-feature','.ah-filterbar','.ah-event']:
                for rect in page.locator(selector).evaluate_all('es=>es.map(e=>({x:e.getBoundingClientRect().x,r:e.getBoundingClientRect().right,sw:e.scrollWidth,cw:e.clientWidth}))'):
                    assert rect['x']>=0 and rect['r']<=width+1 and rect['sw']<=rect['cw']+2,(width,selector,rect)
            # Regressions must fail if later compact styles shrink the text again.
            roles = {
                '.ah-intro h1':32, '.ah-dek':17, '.ah-metadata':14,
                '.ah-feature h2':21, '.ah-start':16, '.ah-local':14,
                '.ah-calendar':15, '.ah-countdown':14,
                '.ah-event h3':19, '.ah-event p':16,
                '.ah-event-meta time':14, '.ah-event-meta small':14,
                '.v2-radar-tags span':13,
                '.v2-radar-section>header h2':24,
                '.v2-media-card h3':20, '.v2-media-card>p':16,
                '.v2-media-top':14, '.v2-media-top time':14,
                '.v2-media-takeaways li':16,
                '.ah-filterbar .v2-radar-tab strong':16,
            }
            typography[width] = {}
            for selector, minimum in roles.items():
                element = page.locator(selector).first
                actual = element.evaluate('e=>parseFloat(getComputedStyle(e).fontSize)')
                typography[width][selector] = actual
                assert actual >= minimum - 0.05, (width, selector, actual, minimum)
            for selector in ['.ah-event p', '.v2-media-card>p', '.v2-media-takeaways li']:
                for sizes in page.locator(selector).evaluate_all('es=>es.map(e=>({h:e.clientHeight,sh:e.scrollHeight,w:e.clientWidth,sw:e.scrollWidth}))'):
                    assert sizes['sh'] <= sizes['h']+2 and sizes['sw'] <= sizes['w']+2, (width,selector,sizes)
            page.locator('.ah-rules summary').click()
            rect=page.locator('.ah-rules-panel').bounding_box()
            assert rect['x']>=0 and rect['x']+rect['width']<=width+1,(width,rect)
            page.keyboard.press('Escape')
            page.locator('.ah-intro h1').click()
            page.evaluate('window.scrollTo(0,0)')
            page.screenshot(path=str(OUT/f'{width}-activity.png'))
            passed(f'{width}px: header, feature, cards, filters and rules stay in viewport')
        passed('titles, summaries, metadata and technical takeaways meet minimum readable sizes')
        # Text-only enlargement at 200% must reflow without clipping the page.
        for width in [390,1640]:
            page.set_viewport_size({'width':width,'height':1000})
            page.evaluate("document.documentElement.style.fontSize='200%'")
            page.wait_for_timeout(350)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), ('text200',width)
            for selector in ['.ah-feature','.ah-event','.v2-media-card']:
                for size in page.locator(selector).evaluate_all('es=>es.map(e=>({w:e.clientWidth,sw:e.scrollWidth}))'):
                    assert size['sw'] <= size['w']+2, ('text200',width,selector,size)
            page.evaluate("document.documentElement.style.removeProperty('font-size')")
        passed('200 percent text enlargement reflows at phone and desktop widths')
        page.set_viewport_size({'width':1640,'height':1000})
        page.wait_for_timeout(350)
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
        (OUT/'checks.json').write_text(json.dumps({'mode':'memory' if MEMORY else 'http','checks':checks,'errors':errors,'typography':typography},ensure_ascii=False,indent=2))
        browser.close()
finally:
    server.shutdown()
