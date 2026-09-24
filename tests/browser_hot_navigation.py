"""Regression for grouped hot tabs and readable open-source cards.

Build first with `python scripts/build.py --out dist`. Run with Playwright.
Uses an in-memory page and blocks external requests; no origin/network claims.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('HOT_UI_OUTPUT', str(ROOT / 'screenshots/hot-navigation')))
OUT.mkdir(parents=True, exist_ok=True)
HTML = (ROOT / 'dist/index.html').read_text(encoding='utf-8')
checks, errors = [], []

def ok(message):
    checks.append(message)
    print('PASS', message, flush=True)

def route(page, value):
    page.evaluate('(hash) => { location.hash = hash; parseRoute(); }', value)
    page.wait_for_timeout(240)

with sync_playwright() as pw:
    options = {'headless': True}
    if os.getenv('CHROMIUM_EXECUTABLE'):
        options['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
    browser = pw.chromium.launch(**options)
    page = browser.new_page(viewport={'width': 1440, 'height': 1050})
    page.set_default_timeout(5000)
    page.route('**/*', lambda request: request.abort())
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.set_content(HTML, wait_until='domcontentloaded')

    for platform in ['github', 'hf']:
        for category in ['all', 'model', 'product', 'industry', 'research-eval']:
            route(page, '#/hot?tab=' + platform + '&ghcat=agent-memory&q=not-a-news-query&hftype=text&hfq=not-a-model&ptag=legal&item=old')
            page.locator(f'[data-ha="cat"][data-id="{category}"]').click()
            params = page.evaluate('Object.fromEntries(hParams())')
            assert not set(params).intersection({'tab', 'ghcat', 'q', 'hftype', 'hfq', 'ptag', 'item'}), params
            expect(page.locator('.h-tab.active')).to_have_attribute('data-id', category)
            expect(page.locator('.gh-inline, .hf-inline')).to_have_count(0)
            expect(page.locator('.h-product-radar')).to_have_count(1 if category == 'product' else 0)
            wanted = page.evaluate("(cat) => HOT.items.filter(x => cat === 'all' || x.category === cat || (cat === 'research-eval' && ['research','benchmark'].includes(x.category))).map(x=>x.id).sort()", category)
            actual = page.locator('.intraday-title, .v10-story-title').evaluate_all('(els) => els.map(x=>x.dataset.id).sort()')
            assert actual == wanted, (platform, category, actual, wanted)
            expect(page.locator('.h-tab')).to_have_count(6)
    ok('10 platform-to-category transitions switch real content and clear stale filters')

    for legacy in ['research', 'benchmark', 'research-eval']:
        route(page, '#/hot?cat=' + legacy)
        actual = page.evaluate('hRows().map(x=>x.category)')
        assert actual and set(actual).issubset({'research', 'benchmark'}), actual
        expect(page.locator('.h-tab.active')).to_have_attribute('data-id', 'research-eval')
    ok('Merged Research / Evaluation includes both source categories and supports legacy links')

    route(page, '#/hot?tab=github')
    page.locator('[data-ha="cat"][data-id="product"]').click()
    page.evaluate('history.back()')
    expect(page.locator('.gh-inline')).to_have_count(1)
    page.evaluate('history.forward()')
    expect(page.locator('.h-product-radar')).to_have_count(1)
    ok('Back / Forward restores the platform and product views')

    route(page, '#/hot?cat=product')
    page.locator('.h-product-filter').nth(1).click()
    assert page.evaluate('hParams().get("ptag")')
    expect(page.locator('.h-product-card')).not_to_have_count(0)
    page.locator('[data-ha="cat"][data-id="model"]').click()
    assert page.evaluate('hParams().get("ptag")') is None
    route(page, '#/hot?tab=github')
    page.locator('#gh-search').fill('hindsight')
    expect(page.locator('.gh-row')).to_have_count(1)
    page.locator('[data-ha="cat"][data-id="product"]').click()
    expect(page.locator('.h-product-card')).not_to_have_count(0)
    route(page, '#/hot?tab=hf')
    page.locator('#hf-search').fill('zz-no-such-model-zz')
    expect(page.locator('.hf-row')).to_have_count(0)
    page.locator('[data-ha="cat"][data-id="all"]').click()
    expect(page.locator('.intraday-title, .v10-story-title')).not_to_have_count(0)
    ok('Product tags, repository search and model search do not leak into other categories')

    sizes = {}
    for width in [1440, 1180, 1100, 900, 760, 390, 360]:
        page.set_viewport_size({'width': width, 'height': 1050 if width > 760 else 844})
        for view in ['#/hot', '#/hot?tab=github', '#/hot?tab=hf', '#/hot?cat=product']:
            route(page, view)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, view, 'page overflow')
            if width <= 760:
                assert page.locator('.sidebar').evaluate('(el) => el.getBoundingClientRect().right <= 1'), (width, 'closed drawer obscures content')
            layout = page.evaluate("""() => {
              const nav = document.querySelector('.h-tabs');
              const search = document.querySelector('.h-search');
              const input = search.querySelector('input');
              const n = nav.getBoundingClientRect(), s = search.getBoundingClientRect();
              const tabs = [...nav.querySelectorAll('.h-tab')].map(t=>t.getBoundingClientRect());
              return {hiddenTabs: tabs.some(t=>t.left<n.left-1||t.right>n.right+1),
                overlap: s.left<n.right-1&&s.right>n.left+1&&s.top<n.bottom-1&&s.bottom>n.top+1,
                inputFits: input.getBoundingClientRect().right <= s.right,
                width:s.width};
            }""")
            assert not layout['hiddenTabs'] and not layout['overlap'] and layout['inputFits'], (width, view, layout)
            if width > 500:
                assert layout['width'] <= 231, (width, view, layout)
            if view.endswith('github'):
                font = page.evaluate("Object.fromEntries(['.gh-repo','.gh-main p','.gh-sub','.gh-tags span'].map(s=>[s,parseFloat(getComputedStyle(document.querySelector(s)).fontSize)]))")
                assert font['.gh-repo'] >= 17 and font['.gh-main p'] >= 15 and font['.gh-sub'] >= 13 and font['.gh-tags span'] >= 13, font
                sizes[str(width)] = font
            if view.endswith('hf'):
                font = page.evaluate("Object.fromEntries(['.hf-model','.hf-sub','.hf-tags span'].map(s=>[s,parseFloat(getComputedStyle(document.querySelector(s)).fontSize)]))")
                assert font['.hf-model'] >= 17 and font['.hf-sub'] >= 13 and font['.hf-tags span'] >= 13, font
        ok(f'{width}px: all tabs visible, compact search, no overlap or page overflow; readable cards')

    for width, name in [(1440, 'desktop'), (390, 'mobile')]:
        page.set_viewport_size({'width': width, 'height': 1050 if width > 760 else 1100})
        for platform in ['github', 'hf']:
            route(page, '#/hot?tab=' + platform)
            page.evaluate('scrollTo(0,0)')
            page.wait_for_timeout(300)
            page.screenshot(path=str(OUT / f'{platform}-{name}.png'))
    assert not errors, errors
    ok('Zero JavaScript page errors')
    browser.close()

(OUT / 'results.json').write_text(json.dumps({'checks': checks, 'errors': errors, 'sizes': sizes, 'mode': 'in-memory built site, external requests blocked'}, ensure_ascii=False, indent=2), encoding='utf-8')
