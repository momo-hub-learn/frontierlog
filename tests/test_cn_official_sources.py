"""Deterministic contract checks for official Chinese sources & WeChat link intake."""
import copy
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import cn_official_sources as cn

NOW = datetime(2026, 11, 4, 7, tzinfo=timezone.utc)
CFG = {
    "version": 1,
    "publishers": [
        {"id": "seed", "name": "字节跳动 Seed", "wechat_name": "字节跳动 Seed",
         "feeds": [{"id": "news", "url": "https://seed.bytedance.com/zh/research",
                    "type": "html_links", "allowed_hosts": ["seed.bytedance.com"],
                    "allowed_paths": ["/zh/blog/"], "limit": 30}]},
        {"id": "deepseek", "name": "DeepSeek", "wechat_name": "DeepSeek",
         "feeds": [{"id": "news", "url": "https://deepseek.com/news/",
                    "type": "html_links", "allowed_hosts": ["deepseek.com"],
                    "allowed_paths": ["/news/"], "limit": 30}]},
        {"id": "kimi", "name": "Kimi", "wechat_name": "月之暗面Kimi",
         "feeds": [{"id": "docs", "url": "https://platform.kimi.com/docs/llms.txt",
                    "type": "markdown_links", "allowed_hosts": ["platform.kimi.com"],
                    "allowed_paths": ["/docs/guide/kimi-"], "limit": 30}]},
        {"id": "tencent", "name": "腾讯混元", "wechat_name": "腾讯混元",
         "feeds": [{"id": "home", "url": "https://hunyuan.tencent.com/",
                    "type": "page_watch", "allowed_hosts": ["hunyuan.tencent.com"],
                    "allowed_paths": [], "limit": 0}]},
    ],
}
SAMPLE = {
    "news": '<a href="/zh/blog/seed-model-release">Seed 新模型发布</a>'
            '<a href="https://evil.com/zh/blog/mimic">Fake</a>'
            '<a href="/zh/research">研究</a>',
    "deepseek": '<a href="/news/deepseek-model/">DeepSeek 官方模型动态</a>',
    "docs": '- [Kimi K3](https://platform.kimi.com/docs/guide/kimi-k3-quickstart.md)\n',
}


def fetch(feed):
    if "seed" in feed["url"]:
        return SAMPLE["news"]
    if "deepseek.com" in feed["url"]:
        return SAMPLE["deepseek"]
    if "kimi.com" in feed["url"]:
        return SAMPLE["docs"]
    return "<html><body>Tencent product console v1</body></html>"


class CNOfficialIntakeTests(unittest.TestCase):
    def test_configured_accounts_have_nonfabricated_evidence_status(self):
        reg = json.loads((ROOT / "data/cn-official-sources.json").read_text(encoding="utf-8"))
        cn.validate_config(reg)
        self.assertEqual(len(reg["publishers"]), 4)
        ids = {x["id"] for x in reg["publishers"]}
        self.assertEqual(ids, {"bytedance-seed", "tencent-hunyuan", "deepseek", "kimi"})
        bytedance = next(x for x in reg["publishers"] if x["id"] == "bytedance-seed")
        self.assertEqual(bytedance["wechat_identity_status"], "pending_primary_account_verification")
        for pub in reg["publishers"]:
            self.assertTrue(pub["wechat_name"])
            self.assertTrue(pub["feeds"])

    def test_site_links_reject_external_domains_and_navigation(self):
        source = CFG["publishers"][0]["feeds"][0]
        found = cn.parse_links(SAMPLE["news"], source)
        self.assertEqual(found, [{"url": "https://seed.bytedance.com/zh/blog/seed-model-release",
                                  "title": "Seed 新模型发布"}])
        self.assertFalse(cn.allowed("https://seed.bytedance.com.evil.invalid/zh/blog/x", source["allowed_hosts"]))
        self.assertFalse(cn.allowed("http://seed.bytedance.com/zh/blog/x", source["allowed_hosts"]))

    def test_markdown_docs_are_official_site_candidates_not_release_facts(self):
        found = cn.parse_links(SAMPLE["docs"], CFG["publishers"][2]["feeds"][0])
        self.assertEqual(found[0]["title"], "Kimi K3")
        out, summary = cn.update(CFG, {"items": []}, {}, fetch, NOW)
        self.assertEqual(summary["successful"], 4)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(len(out["items"]), 3)
        self.assertTrue(all(x["published_at"] is None for x in out["items"]))
        self.assertTrue(all(x["review_status"] == "unreviewed" for x in out["items"]))

    def test_a_source_failure_is_not_equivalent_to_no_news(self):
        def failing(feed):
            if feed["url"] == "https://deepseek.com/news/":
                raise OSError("HTTP 403")
            return fetch(feed)
        initial, _ = cn.update(CFG, {"items": []}, {}, fetch, NOW)
        prev_time = initial["sources"]["deepseek/news"]["last_success_at"]
        next_time = datetime(2026, 11, 4, 9, tzinfo=timezone.utc)
        after, summary = cn.update(CFG, {"items": []}, initial, failing, next_time)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(after["sources"]["deepseek/news"]["last_success_at"], prev_time)
        self.assertEqual(after["sources"]["deepseek/news"]["status"], "failed")
        self.assertIn("HTTP 403", after["sources"]["deepseek/news"]["last_error"])
        self.assertEqual(len(after["items"]), 3)
        self.assertEqual(after["last_ingested_at"], initial["last_ingested_at"])

    def test_no_new_article_does_not_forge_ingest_date(self):
        first, summary = cn.update(CFG, {"items": []}, {}, fetch, NOW)
        self.assertEqual(summary["new_candidates"], 3)
        again, summary2 = cn.update(CFG, {"items": []}, first, fetch,
                                    datetime(2026, 11, 4, 9, tzinfo=timezone.utc))
        self.assertEqual(summary2["new_candidates"], 0)
        self.assertEqual(first["last_ingested_at"], again["last_ingested_at"])
        self.assertEqual(first["items"], again["items"])

    def test_page_change_without_article_is_only_change_signal(self):
        first, _ = cn.update(CFG, {"items": []}, {}, fetch, NOW)
        def updated(feed):
            if feed["url"] == "https://hunyuan.tencent.com/":
                return "<html><body>Tencent product console v2</body></html>"
            return fetch(feed)
        second, _ = cn.update(CFG, {"items": []}, first, updated,
                              datetime(2026, 11, 4, 9, tzinfo=timezone.utc))
        self.assertEqual(second["sources"]["tencent/home"]["changed_unreviewed_at"], "2026-11-04T09:00:00Z")
        self.assertEqual(len(second["items"]), 3)

    def test_wechat_share_url_not_claimed_as_verified_original(self):
        submitted = {"items": [
            {"publisher_id": "deepseek", "url": "https://mp.weixin.qq.com/s/abc123", "title": "原帖"},
            {"publisher_id": "seed", "url": "https://mp.weixin.qq.com.evil.invalid/s/fake"},
            {"publisher_id": "unknown", "url": "https://mp.weixin.qq.com/s/fake"},
        ]}
        state, summary = cn.update(CFG, submitted, {}, fetch, NOW)
        self.assertEqual(summary["unreviewed_wechat_links"], 1)
        wechat = [x for x in state["items"] if x["source_type"] == "wechat_shared_url"]
        self.assertEqual(len(wechat), 1)
        self.assertEqual(wechat[0]["evidence_level"], "publisher_unverified_share_link")
        self.assertIsNone(wechat[0]["published_at"])

    def test_existing_editorial_decision_never_overwritten(self):
        state, _ = cn.update(CFG, {"items": []}, {}, fetch, NOW)
        state["items"][0]["review_status"] = "approved"
        state["items"][0]["editor_note"] = "human reviewed"
        next_state, _ = cn.update(CFG, {"items": []}, state, fetch,
                                  datetime(2026, 11, 4, 9, tzinfo=timezone.utc))
        self.assertEqual(next_state["items"][0]["review_status"], "approved")
        self.assertEqual(next_state["items"][0]["editor_note"], "human reviewed")

    def test_invalid_or_redirected_origin_rejected(self):
        bad = copy.deepcopy(CFG)
        bad["publishers"][0]["feeds"][0]["url"] = "http://seed.bytedance.com/zh/research"
        with self.assertRaises(ValueError):
            cn.validate_config(bad)
        redirect = cn.PinnedRedirect(["seed.bytedance.com"])
        with self.assertRaises(ValueError):
            redirect.redirect_request(None, None, 302, "Moved", {}, "https://evil.invalid/")

    def test_datetime_is_explicit_utc(self):
        self.assertEqual(cn.stamp(datetime(2026, 11, 4, 15, tzinfo=timezone.utc)),
                         "2026-11-04T15:00:00Z")
        with self.assertRaises(ValueError):
            cn.stamp(datetime(2026, 11, 4, 15))


if __name__ == "__main__":
    unittest.main()
