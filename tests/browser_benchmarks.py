"""Benchmark/UI regression in rendered memory; no account/network writes or evaluation runs."""
import json, os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];OUT=R/'screenshots';OUT.mkdir(exist_ok=True)
HTML=(R/'dist/index.html').read_text();checks=[];errors=[]
def ok(s):checks.append(s);print('PASS',s,flush=True)
def route(p,s):p.evaluate('(s)=>location.hash=s',s);p.wait_for_timeout(100)
def shot(p,n,full=False):
 p.evaluate("scrollTo(0,0);document.querySelector('#toast').classList.remove('active')")
 p.wait_for_timeout(100);p.screenshot(path=str(OUT/n),full_page=full)
with sync_playwright() as pw:
 opts={'headless':True}
 if os.getenv('CHROMIUM_EXECUTABLE'):opts['executable_path']=os.environ['CHROMIUM_EXECUTABLE']
 browser=pw.chromium.launch(**opts);p=browser.new_page(viewport={'width':1512,'height':1050},device_scale_factor=1)
 p.set_default_timeout(5000);p.on('pageerror',lambda e:errors.append(str(e)));p.set_content(HTML)
 assert p.locator('.brand strong').inner_text()=='FrontierLog'
 assert not p.locator('.brand-resources').get_attribute('open')
 assert p.locator('[data-action="repo"]').count()==1
 assert p.locator('html').get_attribute('data-theme')=='light'
 assert p.locator('.b-entry[href="#/benchmarks"]').count()==1
 shot(p,'brand-home.png');ok('unified brand, compact support menu, original homepage and benchmark gateway')
 route(p,'#/benchmarks');expect(p.locator('[data-b-card]')).to_have_count(20)
 assert '模型榜' in p.locator('#nav a.active').inner_text();assert p.locator('.m-hubtab.active').inner_text().startswith('Benchmark')
 assert float(p.locator('.b-body p').first.evaluate('e=>getComputedStyle(e).fontSize').replace('px',''))>=14
 assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
 shot(p,'benchmark-first-screen.png');ok('20 catalog entries nested under model hub, readable protocol cards, no desktop overflow')
 p.locator('[data-ba="group"][data-id="pharma"]').click();expect(p.locator('[data-b-card]')).to_have_count(5)
 shot(p,'benchmark-pharma.png')
 p.locator('[data-ba="group"][data-id="manufacturing"]').click();expect(p.locator('[data-b-card]')).to_have_count(4)
 assert '数据集' in p.locator('[data-b-card="secom"]').inner_text()
 p.locator('[data-ba="group"][data-id="all"]').click()
 p.locator('#b-search').fill('RAGBench');expect(p.locator('[data-b-card]')).to_have_count(1)
 p.locator('#b-search').fill('no-matching-zzz');expect(p.locator('.b-empty')).to_have_count(1)
 p.locator('[data-ba="clear"]').click();expect(p.locator('[data-b-card]')).to_have_count(20)
 p.locator('#b-order').select_option('name');assert 'BioASQ' in p.locator('.b-title').first.inner_text()
 p.locator('[data-ba="layout"][data-id="matrix"]').click();expect(p.locator('[data-b-row]')).to_have_count(20)
 p.locator('[data-ba="layout"][data-id="cards"]').click();p.locator('#b-order').select_option('curated')
 ok('pharma/manufacturing filters, dataset distinction, search/reset, sorting and matrix')
 p.locator('[data-ba="save"][data-id="swe-pro"]').click();p.locator('#b-stars').check();expect(p.locator('[data-b-card]')).to_have_count(1)
 p.locator('#b-stars').uncheck()
 for id in ['swe-pro','terminal3','osworld2','tau3','hle','gpqa','swe-verified']:p.locator('[data-b-pick="'+id+'"]').click()
 expect(p.locator('[data-b-pick]:checked')).to_have_count(6)
 assert p.evaluate('bPicked().size')==6
 assert not p.locator('[data-b-pick="swe-verified"]').is_checked()
 assert p.locator('[data-ba="compare"]').is_disabled()
 p.locator('[data-ba="clear-plan"]').click()
 for id in ['omnidocbench','ragbench','bioasq']:p.locator('[data-b-pick="'+id+'"]').check()
 p.locator('[data-ba="compare"]').click();expect(p.locator('.b-compare-card')).to_have_count(3)
 assert '不拼一个总分' in p.locator('#modal-title').inner_text()
 shot(p,'benchmark-compare.png')
 with p.expect_download() as d:p.locator('[data-ba="export-compare"]').click()
 assert 'OmniDocBench' in Path(d.value.path()).read_text()
 p.keyboard.press('Escape');ok('local favorite filter, six-item limit enforced in state and UI, protocol comparison/export')
 p.locator('[data-ba="detail"][data-id="tau3"]').first.click();assert 'bench=tau3' in p.evaluate('location.hash')
 assert '1.0.1' in p.locator('#modal-body').inner_text()
 assert p.locator('#modal-body .b-source-row').count()>=1
 p.locator('[data-b-check="tau3"]').first.check()
 shot(p,'benchmark-detail.png')
 with p.expect_download() as d:p.locator('[data-ba="export-card"]').click()
 assert '本站未运行' in Path(d.value.path()).read_text()
 p.keyboard.press('Escape');assert 'bench=' not in p.evaluate('location.hash')
 route(p,'#/benchmarks?bench=tau3');assert p.locator('[data-b-check="tau3"]').first.is_checked()
 route(p,'#/models');expect(p.locator('dialog[open]')).to_have_count(0);expect(p.locator('[data-model-row]')).to_have_count(12)
 ok('version-aware source drawer, checklist, exported card, deep link and route exit cleanup')
 route(p,'#/benchmarks?mode=changes');expect(p.locator('.b-event')).to_have_count(4)
 assert '2026-02-23' in p.locator('.b-changes').inner_text()
 with p.expect_download() as d:p.locator('[data-ba="template"]').click()
 data=json.loads(Path(d.value.path()).read_text());assert data['status']=='draft_not_executed'
 assert all(x['score'] is None for x in data['benchmarks'])
 shot(p,'benchmark-changes.png');ok('dated historical events and blank, non-executed evaluation template')
 route(p,'#/benchmarks?mode=suites');expect(p.locator('[data-b-suite]')).to_have_count(5)
 shot(p,'benchmark-suites.png')
 p.locator('[data-ba="use-suite"][data-id="csr"]').click();expect(p.locator('.b-report-item')).to_have_count(3)
 assert 'suite=csr' in p.evaluate('location.hash')
 assert '结构内容参考' in p.locator('.b-report-paper').inner_text()
 p.locator('#b-note-title').fill('CSR 与医学写作 · 评估讨论')
 p.locator('#b-note-question').fill('公开基准能说明什么？哪些交付质量必须用授权样本独立验证？')
 p.locator('[data-ba="notes"]').click()
 assert 'CSR 与医学写作' in p.locator('.b-report-paper h2').inner_text()
 shot(p,'benchmark-csr-brief.png');shot(p,'benchmark-csr-brief-full.png',True)
 with p.expect_download() as d:p.locator('[data-ba="export-report"]').click()
 d.value.save_as(str(R/'docs/csr-benchmark-brief.md'));txt=Path(d.value.path()).read_text();assert 'FDA' in txt or 'fda.gov' in txt
 with p.expect_download() as d:p.locator('[data-ba="export-report-html"]').click()
 text=Path(d.value.path()).read_text();assert '<script' not in text
 (R/'docs/csr-benchmark-brief.html').write_text(text)
 p.evaluate("window.__copied='';copyText=(s)=>{window.__copied=s}")
 p.locator('[data-ba="share-report"]').click();share=p.evaluate('window.__copied')
 assert 'CSR' not in share and '%E5%85%AC' not in share
 assert 'pick=omnidocbench%2Cragbench%2Cbioasq' in share
 ok('five business drafts, CSR sources, editable brief, Markdown/HTML export and private-notes-free share URL')
 p.locator('#b-note-title').fill('<img src=x onerror=alert(1)>')
 p.locator('#b-note-question').fill('</p><script>window.__xss=true</script>')
 p.locator('[data-ba="notes"]').click()
 assert p.locator('.b-report-paper img,.b-report-paper script').count()==0
 assert not p.evaluate('Boolean(window.__xss)')
 with p.expect_download() as d:p.locator('[data-ba="export-report-html"]').click()
 text=Path(d.value.path()).read_text();assert '&lt;script&gt;' in text and '<script>' not in text
 ok('user notes and standalone HTML escaped; no script or image injection')
 p.locator('#b-note-title').fill('AI Benchmark 观察简报');p.locator('#b-note-question').fill('');p.locator('[data-ba="notes"]').click()
 route(p,'#/benchmarks');p.locator('[data-ba="status"]').click()
 assert '未接入' in p.locator('#modal-body').inner_text()
 with p.expect_download() as d:p.locator('[data-ba="data"]').click()
 assert len(json.loads(Path(d.value.path()).read_text())['items'])==20
 with p.expect_download() as d:p.locator('[data-ba="backup"]').click()
 backup=json.loads(Path(d.value.path()).read_text());backup['saved']+=['<script>',None,'unknown'];backup['plan']+=['unknown'];backup['checks']={'tau3':[0,999,'x'],'__proto__':{'bad':True}}
 p.locator('#benchmark-import').set_input_files({'name':'backup.json','mimeType':'application/json','buffer':json.dumps(backup).encode()});p.wait_for_timeout(100)
 assert p.evaluate('bSaved.size')==1 and p.evaluate('bPlan.size')<=6
 assert p.evaluate('JSON.stringify(bCheckStore.tau3)')=='[0]'
 bad={'version':1,'saved':'bad','plan':[]}
 p.locator('#benchmark-import').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':json.dumps(bad).encode()});p.wait_for_timeout(100)
 assert '无效' in p.locator('#toast').inner_text()
 p.locator('[data-ba="status"]').click();p.locator('[data-ba="rss"]').click()
 assert '/frontierlog/feeds/benchmarks.xml' in p.locator('#modal-body').inner_text()
 p.keyboard.press('Escape');ok('honest manual data status, catalog export, bounded backup/import and correct RSS')
 p.keyboard.press('/');assert p.locator('#b-search').evaluate('e=>document.activeElement===e')
 p.locator('#b-search').blur();p.keyboard.press('Control+k');p.locator('#palette-input').fill('BixBench')
 expect(p.locator('.palette-item')).to_have_count(1);p.keyboard.press('Enter')
 assert 'BixBench' in p.locator('#modal-title').inner_text();p.keyboard.press('Escape')
 route(p,'#/saved');assert '我的 Benchmark' in p.locator('#legacy-saved').inner_text()
 route(p,'#/pharma');assert p.locator('a.b-entry[href="#/benchmarks?group=pharma"]').count()==1
 route(p,'#/manufacturing');assert p.locator('a.b-entry[href="#/benchmarks?group=manufacturing"]').count()==1
 ok('slash search, command palette deep link, saved section and sector gateways')
 route(p,'#/benchmarks?q=%3Cimg%20src=x%20onerror=alert(1)%3E');expect(p.locator('.b-empty')).to_have_count(1)
 assert p.locator('.b-wrap img').count()==0
 route(p,'#/benchmarks?mode=unknown&group=unknown&bench=not-there&pick=hle,unknown,hle')
 expect(p.locator('[data-b-card]')).to_have_count(20);assert p.evaluate('bPicked().size')==1
 ok('unknown/hostile URL state safely normalized')
 for width in [1512,1280,1024,790,768,600,390,360]:
  p.set_viewport_size({'width':width,'height':940})
  for path in ['#/benchmarks','#/benchmarks?layout=matrix','#/benchmarks?mode=changes','#/benchmarks?mode=suites','#/benchmarks?mode=report&suite=csr&pick=omnidocbench,ragbench,bioasq']:
   route(p,path)
   assert not p.evaluate('document.documentElement.scrollWidth>innerWidth'),f'{width}:{path} overflow'
  if width==390:
   route(p,'#/benchmarks');shot(p,'benchmark-mobile.png')
   p.locator('[data-action="menu"]').click();p.locator('#nav a[href="#/models"]').click()
   assert not p.locator('body').evaluate('e=>e.classList.contains("nav-open")')
 route(p,'#/benchmarks?bench=secom');assert p.locator('dialog[open]').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
 p.keyboard.press('Escape');ok('responsive 1512–360px, all benchmark modes, scoped table scrolling and mobile drawer/navigation')
 p.set_viewport_size({'width':1512,'height':1050});route(p,'#/benchmarks');p.evaluate("applyTheme('dark')");shot(p,'benchmark-dark.png');p.evaluate("applyTheme('light')")
 assert not errors,errors;ok('optional dark theme and zero JavaScript errors')
 browser.close()
report={'status':'passed','groups':len(checks),'checks':checks,'javascript_errors':errors,'mode':'Chromium memory/set_content','not_verified':['Live GitHub Pages deployment','Real-origin persistence/reload','Live collection or benchmark execution','Third-party linked pages in browser']}
(R/'test-results').mkdir(exist_ok=True);(R/'test-results/browser-benchmarks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
