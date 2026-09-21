from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'screenshots-v9'; OUT.mkdir(exist_ok=True)
html=(ROOT/'dist/index.html').read_text(encoding='utf-8')
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content(html,wait_until='load')
    assert page.locator('.brand-copy strong').text_content()=='AI坐标'
    assert 'FrontierLog' not in page.locator('.brand').inner_text()
    assert page.locator('.sector-gateways').count()==0
    assert page.locator('.aic-day').count()>=5
    assert page.locator('.aic-story').count()==5
    page.screenshot(path=str(OUT/'home.png'),full_page=True)
    page.evaluate("location.hash='#/hot'"); page.wait_for_timeout(100)
    page.screenshot(path=str(OUT/'hot.png'),full_page=True)
    for el in page.locator('.h-heat').all():
        box=el.bounding_box()
        assert box and box['height'] < 40, box
        assert el.evaluate('e=>getComputedStyle(e).whiteSpace')=='nowrap'
    page.evaluate("location.hash='#/models'"); page.wait_for_timeout(100)
    page.screenshot(path=str(OUT/'models.png'),full_page=False)
    mobile=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1,is_mobile=True,has_touch=True)
    mobile.on('pageerror',lambda e:errors.append(str(e)))
    mobile.set_content(html,wait_until='load')
    assert mobile.locator('.brand-copy strong').text_content()=='AI坐标'
    assert mobile.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    mobile.screenshot(path=str(OUT/'mobile.png'),full_page=True)
    assert not errors, errors
    browser.close()
print('v0.9 browser checks passed')
