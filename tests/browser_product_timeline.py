"""Exercise the built product timeline on desktop/mobile with all external requests blocked."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results/product-timeline'
OUT.mkdir(parents=True, exist_ok=True)
HTML = (ROOT / 'dist/index.html').read_text(encoding='utf-8')
checks, errors = [], []

def ok(message):
    checks.append(message)
    print('PASS', message, flush=True)

with sync_playwright() as pw:
    options = {'headless': True}
    if os.getenv('CHROMIUM_EXECUTABLE'):
        options['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
    browser = pw.chromium.launch(**options)
    page = browser.new_page(viewport={'width': 1440, 'height': 1080}, reduced_motion='reduce')
    page.set_default_timeout(7000)
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('**/*', lambda route: route.abort())
    page.set_content(HTML, wait_until='domcontentloaded')
    page.evaluate("location.hash='#/hot?cat=product&pview=map&product=harvey';lastMain='';parseRoute()")
    track = page.locator('.pb-history-track')
    expect(track).to_be_visible()
    page.wait_for_timeout(200)
    dates = track.locator('.pb-milestone-date time').evaluate_all('(els)=>els.map(e=>e.dateTime)')
    assert dates == ['2026-05-06', '2026-09-09', '2026-09-23'], dates
    expect(track.locator('.is-latest')).to_have_count(1)
    assert 'Microsoft Word' in track.locator('.is-latest h3').inner_text()
    ok('Chronological horizontal history; exactly one highlighted latest node')

    for width in [1920, 1440, 1280, 1100, 1024, 900, 768, 620, 390, 360, 320]:
        page.set_viewport_size({'width': width, 'height': 1080 if width > 620 else 844})
        page.wait_for_timeout(150)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, 'page overflow')
        measures = track.locator('.pb-milestone').evaluate_all('''els => els.map(el => {
          const r=el.getBoundingClientRect(), h=el.querySelector('h3');
          return {x:r.x,y:r.y,width:r.width,titleFont:parseFloat(getComputedStyle(h).fontSize)};
        })''')
        assert measures[0]['x'] < measures[1]['x'] < measures[2]['x'], (width, measures)
        assert max(x['y'] for x in measures)-min(x['y'] for x in measures) < 2
        assert all(x['titleFont'] >= 18 for x in measures)
        assert all(x['width'] >= min(230, width-75) for x in measures), (width, measures)
        # Single-product card must use the entire grid width, not half a grid row.
        assert page.locator('.pb-card').bounding_box()['width'] >= page.locator('.pb-grid').bounding_box()['width']-2
        ok(f'{width}px: horizontal cards, readable titles, no document overflow')

    # Mobile: initialize at the latest node, older/newer buttons and keyboard affect only the track.
    page.set_viewport_size({'width':390, 'height':1000})
    page.evaluate("lastMain='';parseRoute()")
    page.wait_for_timeout(200)
    assert track.evaluate('(e)=>Math.abs(e.scrollWidth-e.clientWidth-e.scrollLeft)<3')
    ok('Fresh mobile render automatically focuses the latest recorded node')
    summary = page.locator('.pb-card-history > summary')
    summary.click(); summary.click()
    page.wait_for_timeout(120)
    page.locator('[data-history-action="previous"]').click()
    page.locator('[data-history-action="latest"]').click()
    assert track.evaluate('(e)=>Math.abs(e.scrollWidth-e.clientWidth-e.scrollLeft)<3')
    page.locator('[data-history-action="previous"]').click()
    assert track.evaluate('(e)=>e.scrollLeft<e.scrollWidth-e.clientWidth-20')
    track.focus()
    y=page.evaluate('scrollY')
    track.press('Home')
    assert track.evaluate('(e)=>e.scrollLeft') < 3
    track.press('End')
    assert track.evaluate('(e)=>Math.abs(e.scrollWidth-e.clientWidth-e.scrollLeft)<3')
    assert abs(page.evaluate('scrollY')-y) < 2
    ok('Buttons and keyboard reach first/latest without moving the whole page')

    details = track.locator('.is-latest .pb-node-evidence')
    details.locator('summary').click()
    expect(details).to_contain_text('Custom Workflows')
    expect(details).to_contain_text('2026-09-25')
    expect(details).to_contain_text('不能推出')
    details.locator('summary').click()
    ok('Source date, verification date, scope and limitations are expandable')

    for width, name in [(1440,'desktop'),(390,'mobile')]:
        # A tall viewport keeps the real sticky header/dock outside the captured module.
        # Capture the document rectangle, not locator.screenshot's auto-scrolled rectangle.
        page.set_viewport_size({'width':width,'height':2800})
        page.evaluate('window.scrollTo(0,0)')
        page.wait_for_timeout(150)
        page.evaluate("pbHistoryMove(document.querySelector('.pb-history-track'),'latest',true)")
        for selector, label in [('.pb-card-history','timeline'),('.pb-card','product')]:
            rect=page.locator(selector).bounding_box()
            assert rect['y']>80 and rect['y']+rect['height']<2750, rect
            page.screenshot(path=str(OUT / f'{label}-{name}.png'),clip=rect)

    # Map view: opening a timeline expands only that product, filters continue to work.
    page.evaluate("location.hash='#/hot?cat=product&pview=map';lastMain='';parseRoute()")
    page.set_viewport_size({'width':1440,'height':1080})
    harvey=page.locator('[data-product-id="harvey"]')
    harvey.locator('.pb-card-history > summary').click()
    page.wait_for_timeout(150)
    assert harvey.bounding_box()['width'] >= page.locator('.pb-grid').bounding_box()['width']-2
    expect(page.locator('.pb-card')).to_have_count(8)
    lightfield=page.locator('[data-product-id="lightfield"]')
    lightfield.locator('.pb-card-history > summary').click()
    expect(lightfield).to_contain_text('尚无可展示的日期节点')
    expect(lightfield.locator('.pb-history-track')).to_have_count(0)
    legora=page.locator('[data-product-id="legora"]')
    legora.locator('.pb-card-history > summary').click()
    expect(legora).to_contain_text('栏目页，精确原文待补')
    ok('Full-width expansion, empty state and incomplete-source warnings are retained')

    # Reuse the real renderer with a many-node fixture; no fixture data is persisted.
    page.evaluate('''()=>{
      const x=JSON.parse(JSON.stringify(PRODUCT_RADAR.items.find(x=>x.id==='harvey')));
      x.timeline=Array.from({length:12},(_,i)=>({...x.timeline[i%3],date:'2026-09-'+String(24-i).padStart(2,'0')}));
      document.querySelector('[data-product-id="harvey"] .pb-card-history').innerHTML=
        '<summary>完整时间线</summary>'+PB.historyHTML(x,PB.chronology(x));
    }''')
    many=harvey.locator('.pb-history-track')
    expect(many.locator('.pb-milestone')).to_have_count(12)
    many.focus();many.press('End');many.press('Home')
    assert many.evaluate('(e)=>e.scrollLeft') < 3
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    ok('Twelve nodes remain reachable without horizontal page overflow')
    assert not errors, errors
    ok('Zero JavaScript page errors')
    browser.close()

(OUT/'results.json').write_text(json.dumps({'checks': checks,'errors':errors,
    'mode':'Built site rendered in memory; external requests blocked'},ensure_ascii=False,indent=2),encoding='utf-8')
