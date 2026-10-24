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
        page.set_default_timeout(8000)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.set_content(HTML, wait_until="load") if MEMORY else page.goto(url, wait_until="load")

        def go(route):
            if MEMORY:
                page.evaluate("route => location.hash = route", route)
            else:
                page.goto(url + route, wait_until="domcontentloaded")
            page.wait_for_timeout(150)

        expect(page.locator(".fc-cockpit")).to_have_count(1)
        assert page.locator("#nav .active").inner_text().startswith("精选")
        assert page.locator("html").get_attribute("data-theme") == "light"
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        passed("current home cockpit, navigation and light theme render without overflow")

        go("#/progress")
        expect(page.locator(".p5-progress")).to_have_count(1)
        expect(page.locator(".p5-change-card")).not_to_have_count(0)
        page.locator('.p5-tabs a[href*="view=map"]').click()
        expect(page.locator(".p5-map-card")).to_have_count(
            sum(item.get("status") == "code" for item in CATALOG["items"])
        )
        page.locator("#p5-search").fill("no-such-capability-xyz")
        expect(page.locator(".p5-empty")).to_have_count(1)
        page.locator("#p5-search").fill("")
        passed("capability updates, map, source-derived count, search and empty state")

        go("#/progress?view=research")
        expect(page.locator(".p5-research-card")).to_have_count(len(RESEARCH["items"]))
        body = page.locator(".p5-progress").inner_text()
        assert "我们的解读" in body and "现在还不能推出" in body
        assert "世界模型的关键误差不一定出现在最差画面，而在稀有事件" in body
        page.locator("#p5-search").fill("no-such-research-xyz")
        expect(page.locator(".p5-research-empty")).to_contain_text("没有匹配的研究档案")
        expect(page.get_by_role("textbox", name="搜索研究档案")).to_have_value("no-such-research-xyz")
        page.get_by_role("link", name="清除搜索").click()
        expect(page.locator(".p5-research-card")).to_have_count(len(RESEARCH["items"]))
        passed("research radar keeps fact, interpretation and boundary visibly separate")

        go("#/toolkit")
        expect(page.locator(".tk-card")).to_have_count(len(TOOLKIT["items"]))
        expect(page.locator(".tk-runtime")).to_have_count(len(TOOLKIT["items"]))
        assert set(page.locator(".tk-runtime").all_inner_texts()) == {"资料核验 · 本站未运行"}
        page.locator("#tk-search").fill("no-such-guide-xyz")
        expect(page.locator(".tk-empty")).to_be_visible()
        page.locator(".tk-empty button").click()
        passed("toolkit catalog, search, empty state and reset")

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
        if not MEMORY:
            page.reload(wait_until="domcontentloaded")
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
        mobile.on("pageerror", lambda e: errors.append(str(e)))
        mobile.set_content(HTML, wait_until="load") if MEMORY else mobile.goto(url)
        for selector in (
            '[data-action="menu"]',
            '.top-actions [data-action="command"]',
            '.top-actions a[href="#/saved"]',
            '.top-actions .brand-github',
        ):
            box = mobile.locator(selector).bounding_box()
            assert box and box["width"] >= 44 and box["height"] >= 44, (selector, box)
        passed("mobile header actions expose 44px touch targets")
        for route in ("#/feed", "#/progress", "#/hot", "#/hot?tab=hf", "#/toolkit", "#/manufacturing"):
            mobile.evaluate("route => location.hash = route", route)
            mobile.wait_for_timeout(120)
            assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth"), route
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
