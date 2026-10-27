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
    # The production document is intentionally self-contained and now exceeds 1.5 MB;
    # leave enough time for Chromium to parse it before applying interaction assertions.
    page.set_default_timeout(15000)
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
            expect(page.locator('.pb-page')).to_have_count(1 if category == 'product' else 0)
            if category == 'product':
                expect(page.locator('.pb-view')).to_have_count(2)
                expect(page.locator('[data-product-event]')).not_to_have_count(0)
            else:
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
    expect(page.locator('.pb-page')).to_have_count(1)
    ok('Back / Forward restores the platform and product views')

    route(page, '#/hot?cat=product')
    page.locator('.pb-view').nth(1).click()
    page.locator('.pb-filter-row').first.locator('.pb-chip').nth(1).click()
    assert page.evaluate('hParams().get("scene")')
    expect(page.locator('.pb-card')).not_to_have_count(0)
    page.locator('[data-ha="cat"][data-id="model"]').click()
    assert page.evaluate('Object.keys(Object.fromEntries(hParams())).every(k => !["pview","scene","investor","kind","product","legacy","q"].includes(k))')
    route(page, '#/hot?tab=github')
    repo = page.evaluate('APP.github_hot.items[0].repo')
    page.locator('#gh-search').fill(repo)
    expect(page.locator('.gh-row')).to_have_count(1)
    page.locator('#gh-search').fill('zz-no-such-repo-zz')
    expect(page.locator('[data-gh-clear]')).to_be_visible()
    page.locator('[data-gh-clear]').click()
    expect(page.locator('#gh-search')).to_have_value('')
    expect(page.locator('.gh-row')).to_have_count(page.evaluate('APP.github_hot.items.length'))
    page.locator('[data-ha="cat"][data-id="product"]').click()
    expect(page.locator('[data-product-event]')).not_to_have_count(0)
    route(page, '#/hot?tab=hf')
    expect(page.locator('.hf-resultline')).to_have_attribute('role', 'status')
    expect(page.locator('.hf-resultline')).to_have_text(f"显示 {page.evaluate('APP.huggingface_hot.items.length')} / {page.evaluate('APP.huggingface_hot.items.length')} 个模型 · 保留官方网页名次")
    page.locator('#hf-search').fill('zz-no-such-model-zz')
    expect(page.locator('.hf-row')).to_have_count(0)
    expect(page.locator('.hf-resultline')).to_have_text(f"显示 0 / {page.evaluate('APP.huggingface_hot.items.length')} 个模型 · 保留官方网页名次")
    expect(page.locator('[data-hf-clear]')).to_be_visible()
    page.locator('[data-hf-clear]').click()
    expect(page.locator('#hf-search')).to_have_value('')
    expect(page.locator('.hf-row')).to_have_count(page.evaluate('APP.huggingface_hot.items.length'))
    page.locator('[data-ha="cat"][data-id="all"]').click()
    expect(page.locator('.intraday-title, .v10-story-title')).not_to_have_count(0)
    ok('Product tags, repository search and model search do not leak into other categories')

    original_changes = page.evaluate('structuredClone(APP.huggingface_hot.web_rank_changes || [])')
    page.evaluate("""() => {
      const first = APP.huggingface_hot.web_order[0];
      APP.huggingface_hot.web_rank_changes = [{id:first,rank:1,previous_rank:3,rank_change:2,previous_fetched_at:'2026-10-23T01:00:00Z'}];
    }""")
    route(page, '#/hot?tab=hf')
    expect(page.locator('.hf-row').first.locator('.hf-delta')).to_have_text('↑2')
    expect(page.locator('.hf-row').first.locator('.hf-delta')).to_have_attribute('aria-label', '较上次官方网页快照上升 2 位')
    expect(page.locator('.hf-method')).to_contain_text('只比较')
    expect(page.locator('.hf-method')).to_contain_text('官方网页快照')
    page.evaluate('(value) => { APP.huggingface_hot.web_rank_changes = value; }', original_changes)
    route(page, '#/hot?tab=hf')
    ok('HF rank movement uses a truthful previous-snapshot label and non-color arrow')

    original_changes = page.evaluate('structuredClone(APP.huggingface_hot.web_rank_changes || [])')
    page.evaluate("""() => {
      const first = APP.huggingface_hot.web_order[0];
      APP.huggingface_hot.web_rank_changes = [{id:first,rank:1,previous_rank:null,rank_change:null,previous_fetched_at:'2026-10-24T01:16:11Z'}];
    }""")
    route(page, '#/hot?tab=hf')
    expect(page.locator('.hf-row').first.locator('.hf-delta')).to_have_text('新上榜')
    expect(page.locator('.hf-row').first.locator('.hf-delta')).to_have_attribute('aria-label', '较上次官方网页快照新入榜')
    page.evaluate('(value) => { APP.huggingface_hot.web_rank_changes = value; }', original_changes)
    route(page, '#/hot?tab=hf')
    current_new_ids = page.evaluate('(APP.huggingface_hot.web_rank_changes || []).filter(x => !Number.isInteger(x.previous_rank)).map(x => x.id)')
    for model_id in current_new_ids:
        expect(page.locator('.hf-row', has_text=model_id).locator('.hf-delta')).to_have_text('新上榜')
    ok('HF first-time entrants use an explicit new-entry label instead of an ambiguous single character')

    original_outgoing = page.evaluate('structuredClone(APP.huggingface_hot.web_outgoing || [])')
    page.evaluate("""() => {
      APP.huggingface_hot.web_outgoing = [{id:'org/previous-model',previous_rank:20,previous_fetched_at:'2026-10-24T01:16:11Z'}];
    }""")
    route(page, '#/hot?tab=hf')
    expect(page.locator('.hf-change-summary')).to_contain_text('1 新上榜')
    expect(page.locator('.hf-change-summary')).to_contain_text('1 离榜')
    page.locator('.hf-change-summary summary').click()
    expect(page.locator('.hf-change-summary details a')).to_have_text('#20 org/previous-model')
    page.evaluate('(value) => { APP.huggingface_hot.web_outgoing = value; }', original_outgoing)
    route(page, '#/hot?tab=hf')
    ok('HF change summary exposes entrants, rank moves and outgoing models without manual snapshot comparison')

    original_hf_state = page.evaluate('structuredClone(APP.huggingface_hot)')
    page.evaluate("""() => {
      APP.huggingface_hot.web_fetched_at = new Date().toISOString();
      APP.huggingface_hot.api_fetched_at = new Date(Date.now() - 7 * 3600 * 1000).toISOString();
      APP.huggingface_hot.web_order = [...APP.huggingface_hot.web_order];
      APP.huggingface_hot.web_order[10] = 'example/web-only-model';
    }""")
    route(page, '#/hot?tab=hf')
    rendered = page.locator('.hf-model').evaluate_all("els => els.map(x => x.firstChild.nodeValue.trim())")
    expected = page.evaluate('APP.huggingface_hot.web_order')
    assert rendered == expected, (rendered, expected)
    expect(page.locator('.h-head h1')).to_contain_text('Hugging Face 热榜')
    expect(page.locator('.h-head')).to_contain_text('看模型社区正在关注什么')
    expect(page.locator('#hf-search')).to_have_attribute('aria-label', '搜索 Hugging Face 热榜')
    expect(page.locator('.h-head .h-meta')).not_to_contain_text('待核验')
    expect(page.locator('.ranking-stale strong')).to_have_text('网页榜位已核验；API 指标沿用旧快照')
    expect(page.locator('.hf-score span', has_text='API Trending（旧）')).not_to_have_count(0)
    expect(page.locator('.hf-row', has_text='example/web-only-model').locator('.hf-score span')).to_have_text('API 未收录')
    ok('HF web order stays current while older API metrics remain visibly time-separated')
    page.evaluate('(value) => { Object.keys(APP.huggingface_hot).forEach(k => delete APP.huggingface_hot[k]); Object.assign(APP.huggingface_hot,value); }', original_hf_state)
    route(page, '#/hot?tab=hf')

    sizes = {}
    for width in [1440, 1180, 1100, 900, 760, 390, 360]:
        page.set_viewport_size({'width': width, 'height': 1050 if width > 760 else 844})
        for view in ['#/hot', '#/hot?tab=github', '#/hot?tab=hf', '#/hot?cat=product']:
            route(page, view)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, view, 'page overflow')
            if width <= 760:
                assert page.locator('.sidebar').evaluate('(el) => el.getBoundingClientRect().right <= 1'), (width, 'closed drawer obscures content')
                expect(page.locator('#v2-tool-dock')).to_be_hidden()
            else:
                expect(page.locator('#v2-tool-dock')).to_be_visible()
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
            if platform == 'hf' and name == 'mobile' and current_new_ids:
                page.locator('.hf-row', has_text=current_new_ids[0]).screenshot(path=str(OUT / 'hf-new-entry-mobile.png'))
    assert not errors, errors
    ok('Zero JavaScript page errors')
    browser.close()

(OUT / 'results.json').write_text(json.dumps({'checks': checks, 'errors': errors, 'sizes': sizes, 'mode': 'in-memory built site, external requests blocked'}, ensure_ascii=False, indent=2), encoding='utf-8')
