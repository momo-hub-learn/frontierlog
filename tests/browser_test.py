"""Cross-module browser smoke test against the generated site.

Counts come from source data, so normal editorial additions do not turn this
product contract into a fixed-count news snapshot.
"""
from __future__ import annotations

import functools
import json
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test-results"
OUT.mkdir(exist_ok=True)
CATALOG = json.loads((ROOT / "data/catalog.json").read_text())
TOOLKIT = json.loads((ROOT / "data/toolkit.json").read_text())
RESEARCH = json.loads((ROOT / "data/research-radar.json").read_text())
GITHUB = json.loads((ROOT / "data/github-hot.json").read_text())
HTML = (ROOT / "dist/index.html").read_text()
MEMORY = os.environ.get("BROWSER_TEST_MODE") == "memory"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


server = ThreadingHTTPServer(
    ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT / "dist"))
)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{server.server_port}/"
checks, errors = [], []


def passed(name):
    checks.append(name)
    print("PASS", name, flush=True)


try:
    with sync_playwright() as p:
        options = {"headless": True}
        if os.environ.get("CHROMIUM_EXECUTABLE"):
            options["executable_path"] = os.environ["CHROMIUM_EXECUTABLE"]
        browser = p.chromium.launch(**options)
        page = browser.new_page(viewport={"width": 1512, "height": 1100})
        page.set_default_timeout(45000)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.set_content(HTML, wait_until="domcontentloaded") if MEMORY else page.goto(url, wait_until="domcontentloaded")
        page.set_default_timeout(8000)

        def go(route):
            # Routes are hash-only SPA transitions; keep the loaded document
            # and exercise the same hashchange path as an in-product click.
            page.evaluate("route => location.hash = route", route)
            page.wait_for_timeout(150)

        def active_nav_contrast():
            return page.locator("#nav .active").evaluate(
                """el => {
                  const rgba = value => {
                    const channels = value.match(/[\\d.]+/g).map(Number);
                    return [channels[0], channels[1], channels[2], channels[3] ?? 1];
                  };
                  const composite = (front, back) => {
                    const alpha = front[3] + back[3] * (1 - front[3]);
                    return front.slice(0, 3).map(
                      (channel, index) => (channel * front[3] +
                        back[index] * back[3] * (1 - front[3])) / alpha
                    ).concat(alpha);
                  };
                  const luminance = channels => {
                    channels = channels.map(v => {
                      v /= 255;
                      return v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4;
                    });
                    return .2126 * channels[0] + .7152 * channels[1] + .0722 * channels[2];
                  };
                  const style = getComputedStyle(el);
                  const foreground = luminance(rgba(style.color).slice(0, 3));
                  let backgroundLayer = rgba(style.backgroundColor);
                  let node = el.parentElement;
                  while (backgroundLayer[3] < 1 && node) {
                    backgroundLayer = composite(
                      backgroundLayer,
                      rgba(getComputedStyle(node).backgroundColor)
                    );
                    node = node.parentElement;
                  }
                  const background = luminance(backgroundLayer.slice(0, 3));
                  return (Math.max(foreground, background) + .05) /
                    (Math.min(foreground, background) + .05);
                }"""
            )

        expect(page.locator(".fc-cockpit")).to_have_count(1)
        expect(page.locator(".fc-hf-panel")).to_have_count(1)
        expect(page.locator(".fc-hf-row")).to_have_count(3)
        expect(page.locator(".fc-hf-panel")).to_contain_text("Trending 不等于能力榜")
        github_sync = GITHUB.get("sync", {})
        github_partial = github_sync.get("metadata_status") == "partial" or int(github_sync.get("metadata_failed_count") or 0) > 0
        github_watch_failed = int(github_sync.get("watchlist_failed_count") or 0) > 0
        if github_partial:
            failed = int(github_sync.get("metadata_failed_count") or 0)
            total = len(GITHUB.get("items", []))
            scope = "全部" if total and failed >= total else "部分"
            expected = "仓库资料更新全部失败" if scope == "全部" else "上榜仓库资料更新部分失败"
            expect(page.locator(".fc-gh-panel")).to_contain_text(expected)
            expect(page.locator(".fc-gh-data-state")).not_to_have_count(0)
        elif github_watch_failed:
            expect(page.locator(".fc-gh-panel")).to_contain_text("长期关注仓库资料更新失败")
            expect(page.locator(".fc-gh-panel")).not_to_contain_text("仓库 API")
            expect(page.locator(".fc-gh-data-state")).not_to_have_count(0)
        else:
            expect(page.locator(".fc-gh-panel")).not_to_contain_text("仓库 API")
            expect(page.locator(".fc-gh-data-state")).to_have_count(0)
        assert page.locator("#nav .active").inner_text().startswith("精选")
        assert page.locator("html").get_attribute("data-theme") == "light"
        assert active_nav_contrast() >= 4.5
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        passed("current home cockpit, official HF top three, readable navigation and light theme render without overflow")

        go("#/progress")
        expect(page.locator(".p5-progress")).to_have_count(1)
        expect(page.locator(".p5-change-card")).not_to_have_count(0)
        # This is an in-page hash route. Trigger the real DOM click without
        # asking Playwright to wait for a document navigation that never occurs.
        page.locator('.p5-tabs a[href*="view=map"]').evaluate("el => el.click()")
        expect(page.locator(".p5-map-card")).to_have_count(
            sum(item.get("status") == "code" for item in CATALOG["items"])
        )
        page.locator("#p5-search").fill("no-such-capability-xyz")
        expect(page.locator(".p5-empty")).to_have_count(1)
        page.locator("#p5-search").fill("")
        passed("capability updates, map, source-derived count, search and empty state")

        go("#/progress?view=research")
        expect(page.locator(".p5-research-card")).to_have_count(len(RESEARCH["items"]))
        expect(page.locator(".p5-verification").filter(has_text="外部核验中")).to_have_count(1)
        body = page.locator(".p5-progress").inner_text()
        assert "我们的解读" in body and "现在还不能推出" in body
        assert "世界模型的关键误差不一定出现在最差画面，而在稀有事件" in body
        page.locator("#p5-search").fill("no-such-research-xyz")
        expect(page.locator(".p5-research-empty")).to_contain_text("没有匹配的研究档案")
        expect(page.get_by_role("textbox", name="搜索研究档案")).to_have_value("no-such-research-xyz")
        page.get_by_role("link", name="清除搜索").click()
        expect(page.locator(".p5-research-card")).to_have_count(len(RESEARCH["items"]))
        passed("research radar keeps fact, interpretation and boundary visibly separate")

        go("#/progress?view=research&research=anthropic-agent-judgment-calls")
        focused = page.locator('[data-research-id="anthropic-agent-judgment-calls"]')
        expect(page.locator(".p5-research-card")).to_have_count(1)
        expect(focused).to_contain_text("86%")
        expect(focused).to_contain_text("现在还不能推出")
        expect(page.locator(".p5-research-grid.focused")).to_have_count(1)
        assert focused.bounding_box()["width"] >= 780
        expect(page.get_by_role("link", name="返回全部研究档案")).to_be_visible()
        page.screenshot(path=str(OUT / "research-agent-judgment-desktop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        focused.screenshot(path=str(OUT / "research-agent-judgment-mobile.png"))
        page.get_by_role("link", name="返回全部研究档案").click()
        expect(page.locator(".p5-research-card")).to_have_count(len(RESEARCH["items"]))
        page.set_viewport_size({"width": 1512, "height": 1100})
        passed("exact research deep link, visible return path and 390px reflow")

        go("#/toolkit")
        initial=min(12,len(TOOLKIT["items"]))
        expect(page.locator(".tk-card")).to_have_count(initial)
        while page.locator("#tk-more").is_visible():
            page.locator("#tk-more").click()
        expect(page.locator(".tk-card")).to_have_count(len(TOOLKIT["items"]))
        expect(page.locator(".tk-runtime")).to_have_count(len(TOOLKIT["items"]))
        assert set(page.locator(".tk-runtime").all_inner_texts()) == {"资料核验 · 本站未运行"}
        page.locator("#tk-search").fill("no-such-guide-xyz")
        expect(page.locator(".tk-empty")).to_be_visible()
        page.locator(".tk-empty button").click()
        passed("toolkit progressive disclosure, complete catalog, search, empty state and reset")

        for route, selector in [
            ("#/hot", ".h-wrap"),
            ("#/models", ".m-wrap"),
            ("#/benchmarks", "[data-b-card]"),
            ("#/activity", ".ah-page"),
            ("#/pharma", ".v-sector-hero"),
            ("#/manufacturing", ".v-sector-hero"),
            ("#/people", ".pp-page"),
            ("#/tibo", ".tibo-featured"),
        ]:
            go(route)
            expect(page.locator(selector)).not_to_have_count(0)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), route
        passed("all primary content routes render with no desktop page overflow")

        go("#/hot?tab=hf")
        hf_text = page.locator(".hf-inline").inner_text()
        assert "北京时间" in hf_text and "RecursiveSI/flint" in hf_text
        assert "API Trending（旧）" not in hf_text
        passed("fresh Hugging Face web/API snapshots show explicit Beijing timestamps")

        go("#/feed")
        page.locator('[data-action="theme"]').click()
        assert page.locator("html").get_attribute("data-theme") == "dark"
        assert page.locator('meta[name="theme-color"]').get_attribute("content") == "#101819"
        assert active_nav_contrast() >= 4.5
        if not MEMORY:
            page.set_default_timeout(45000)
            page.reload(wait_until="domcontentloaded")
            page.set_default_timeout(8000)
            assert page.locator("html").get_attribute("data-theme") == "dark"
        page.locator('[data-action="theme"]').click()
        passed("dark theme is reversible and persists on a real origin")

        go("#/saved")
        expect(page.locator("#legacy-saved .v2-saved-head h1")).to_have_text("我的关注")
        expect(page.locator("#section-title")).to_contain_text("已关注项目")
        expect(page.locator("#section-eyebrow")).to_have_text("PROJECT WATCHLIST")
        passed("saved page distinguishes the global personal index from the project watchlist")

        mobile = browser.new_page(
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
        )
        mobile.set_default_timeout(45000)
        mobile.on("pageerror", lambda e: errors.append(str(e)))
        mobile.set_content(HTML, wait_until="domcontentloaded") if MEMORY else mobile.goto(url, wait_until="domcontentloaded")
        mobile.set_default_timeout(8000)
        for selector in (
            '[data-action="menu"]',
            '.top-actions [data-action="command"]',
            '.top-actions a[href="#/saved"]',
            '.top-actions .brand-github',
        ):
            box = mobile.locator(selector).bounding_box()
            assert box and box["width"] >= 44 and box["height"] >= 44, (selector, box)
        expect(
            mobile.get_by_role("button", name="快速跳转", exact=True)
        ).to_be_visible()
        passed("mobile header actions expose 44px touch targets")
        for route in ("#/feed", "#/progress", "#/hot", "#/hot?tab=hf", "#/toolkit", "#/manufacturing"):
            mobile.evaluate("route => location.hash = route", route)
            mobile.wait_for_timeout(120)
            assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth"), route
        mobile.evaluate("location.hash = '#/feed'")
        mobile.wait_for_timeout(120)
        expect(mobile.locator(".fc-hf-panel")).to_have_count(1)
        expect(mobile.locator(".fc-hf-row")).to_have_count(3)
        mobile.locator('[data-action="menu"]').click()
        mobile.locator('#nav a[href="#/models"]').click()
        expect(mobile.locator("body")).not_to_have_class("nav-open")
        expect(mobile.locator(".m-wrap")).to_have_count(1)
        passed("mobile navigation and representative routes avoid horizontal overflow")

        assert not errors, errors
        report = {
            "passed": True,
            "browser": "Chromium",
            "mode": "memory" if MEMORY else "localhost HTTP",
            "checks": checks,
            "javascript_errors": errors,
            "not_tested": [
                "Public GitHub Pages deployment",
                "Authenticated services",
                "Third-party AI tools",
            ],
        }
        (OUT / "browser-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2)
        )
        browser.close()
finally:
    server.shutdown()
    server.server_close()
