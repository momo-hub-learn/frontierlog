"""Network-free contracts: real publisher RSS ≠ verified primary news.
All data fixtures are synthetic; no published news facts are inferred in tests.
"""
import copy
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import media_sources as m

NOW = datetime(2026, 11, 4, 9, tzinfo=timezone.utc)
BASE = {
    "version": 1,
    "sources": [
        {"id":"qbitai-feed","publisher_id":"qbitai","publisher":"量子位",
         "publisher_kind":"media","source_role":"media_original_publication",
         "mode":"rss","url":"https://www.qbitai.com/feed","hosts":["www.qbitai.com","qbitai.com"],
         "article_hosts":["www.qbitai.com","qbitai.com"],"max_items":40,"enabled":True},
        {"id":"khazix-aihot-changelog","publisher_id":"khazix","publisher":"数字生命卡兹克",
         "publisher_kind":"creator","source_role":"creator_own_project_only",
         "mode":"page_watch","url":"https://aihot.news/changelog","hosts":["aihot.news"],
         "max_items":0,"enabled":True},
    ],
    "manual_sources": [
        {"id":"khazix-wechat","publisher_id":"khazix","publisher":"数字生命卡兹克",
         "publisher_kind":"creator","mode":"wechat_share_link","enabled":True}
    ]
}
CHANGELOG = b'<main><h1>\xe6\x9b\xb4\xe6\x96\xb0\xe6\x97\xa5\xe5\xbf\x97</h1><h2>2026-11-04</h2><h3>AIHOT Model List update</h3></main>'


def feed(count, future=False):
    when = "Wed, 25 Nov 2026 09:00:00 GMT" if future else "Wed, 04 Nov 2026 08:00:00 GMT"
    entries = "".join(
        '<item><title>Agent code model %s</title><link>https://www.qbitai.com/2026/11/post-%s.html</link><pubDate>%s</pubDate></item>' % (i,i,when)
        for i in range(count)
    )
    return ('<rss version="2.0"><channel>%s</channel></rss>' % entries).encode()


def fetcher(src):
    if src["id"] == "qbitai-feed":
        return feed(12)
    return CHANGELOG


class TestMediaAuto(unittest.TestCase):
    def test_registry_is_genuine_public_publisher_and_creator_project(self):
        reg = json.loads((ROOT / "data/media-sources.json").read_text(encoding="utf-8"))
        m.validate_sources(reg)
        self.assertEqual({s["id"] for s in reg["sources"]}, {"qbitai-feed","khazix-aihot-changelog"})
        self.assertTrue(all("aihot.news/api" not in str(s) for s in reg["sources"]))
        self.assertEqual(reg["sources"][0]["url"], "https://www.qbitai.com/feed")

    def test_1_10_12_17_input_sizes_without_hard_coding_counts(self):
        src=BASE["sources"][0]
        for count in (1,10,12,17):
            rows=m.parse_feed(feed(count),src,NOW)
            self.assertEqual(len(rows),count)
            self.assertEqual(len({x["source_url"] for x in rows}),count)
            self.assertEqual(rows[0]["published_at"], "2026-11-04T08:00:00Z")
            self.assertIn("agent",rows[0]["labels"])
            self.assertIn("model",rows[0]["labels"])

    def test_offhost_http_and_tracking_links_not_mirrored(self):
        src=BASE["sources"][0]
        self.assertFalse(m.safe_https("https://www.qbitai.com.evil.invalid/2026/1",src["article_hosts"]))
        self.assertFalse(m.safe_https("http://www.qbitai.com/2026/1",src["article_hosts"]))
        self.assertEqual(m.canonical_article("https://www.qbitai.com/2026/11/post-1.html?utm_source=x#share",src["article_hosts"]),
                         "https://www.qbitai.com/2026/11/post-1.html")
        raw=b'<rss><channel><item><title>hijacked headline</title><link>https://evil.invalid/fake</link></item></channel></rss>'
        with self.assertRaises(ValueError):
            m.parse_feed(raw,src,NOW)
        with self.assertRaises(ValueError):
            m.SameHostRedirect(["www.qbitai.com"]).redirect_request(None,None,302,"Moved",{},"https://evil.invalid/")

    def test_rss_future_rejected_and_unzoned_time_not_invented(self):
        src=BASE["sources"][0]
        with self.assertRaises(ValueError):
            m.parse_feed(feed(1,True),src,NOW)
        self.assertEqual(m.source_instant("2026-11-04",NOW),(None,False))
        self.assertEqual(m.source_instant("2026-11-04T08:00:00",NOW),(None,False))
        self.assertEqual(m.source_instant("2026-11-04T16:00:00+08:00",NOW),("2026-11-04T08:00:00Z",False))
        with self.assertRaises(ValueError):
            m.utc_stamp(datetime(2026,11,4,8))

    def test_atom_supported_as_secondary_discovery(self):
        atom=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>AI medical paper</title><link rel="alternate" href="https://qbitai.com/2026/11/paper.html"/><updated>2026-11-04T08:30:00Z</updated></entry></feed>'
        rows=m.parse_feed(atom,BASE["sources"][0],NOW)
        self.assertEqual(len(rows),1)
        self.assertIn("biomedical",rows[0]["labels"])

    def test_creator_changelog_is_only_a_change_signal(self):
        out,report=m.update(BASE,{"items":[]},{},fetcher,NOW)
        self.assertEqual(report["sources_succeeded"],2)
        self.assertEqual(report["new_candidates"],12)
        self.assertEqual(len(out["items"]),12)
        self.assertTrue(all(row["evidence_level"]=="secondary_media_lead" and row["review_status"]=="unreviewed" for row in out["items"]))
        self.assertIn("last_digest",out["sources"]["khazix-aihot-changelog"])
        before=out["last_ingested_at"]
        def changed(src):
            if src["mode"]=="page_watch":
                return CHANGELOG.replace(b"Model List",b"New report")
            return fetcher(src)
        later=datetime(2026,11,4,11,tzinfo=timezone.utc)
        nxt,summary=m.update(BASE,{"items":[]},out,changed,later)
        self.assertEqual(summary["new_candidates"],0)
        self.assertEqual(nxt["last_ingested_at"],before)
        self.assertEqual(nxt["sources"]["khazix-aihot-changelog"]["changed_unreviewed_at"],"2026-11-04T11:00:00Z")

    def test_independent_failure_keeps_previous_success_and_inbox(self):
        original,_=m.update(BASE,{"items":[]},{},fetcher,NOW)
        previous=original["sources"]["qbitai-feed"]["last_success_at"]
        def denied(src):
            if src["id"]=="qbitai-feed":
                raise OSError("HTTP 403")
            return CHANGELOG
        new,summary=m.update(BASE,{"items":[]},original,denied,datetime(2026,11,4,10,tzinfo=timezone.utc))
        self.assertEqual(summary["sources_failed"],1)
        self.assertEqual(summary["sources_succeeded"],1)
        self.assertEqual(new["sources"]["qbitai-feed"]["last_success_at"],previous)
        self.assertEqual(new["sources"]["qbitai-feed"]["status"],"failed")
        self.assertEqual(new["items"],original["items"])
        self.assertEqual(new["last_ingested_at"],original["last_ingested_at"])

    def test_repeat_new_deleted_and_merge_source_cases(self):
        original,_=m.update(BASE,{"items":[]},{},fetcher,NOW)
        repeat,summary=m.update(BASE,{"items":[]},original,fetcher,NOW)
        self.assertEqual(summary["new_candidates"],0)
        self.assertEqual(original["items"],repeat["items"])
        old_id=original["items"][0]["id"]
        repeat["items"][0]["review_status"]="approved"
        repeat["items"][0]["editor_note"]="reviewed"
        def changed(src):
            if src["mode"]=="rss":
                return feed(17)
            return CHANGELOG
        new,summary=m.update(BASE,{"items":[]},repeat,changed,datetime(2026,11,4,11,tzinfo=timezone.utc))
        self.assertEqual(summary["new_candidates"],5)
        retained=next(x for x in new["items"] if x["id"]==old_id)
        self.assertEqual(retained["review_status"],"approved")
        self.assertEqual(retained["editor_note"],"reviewed")
        self.assertEqual(retained["first_seen_at"],repeat["items"][0]["first_seen_at"])

    def test_explicit_wechat_share_keeps_attribution_pending_and_no_fake_date(self):
        submitted={"items":[
          {"source_id":"khazix-wechat","url":"https://mp.weixin.qq.com/s/actual-share-id?utm_source=a","title":"自主分享的文章标题"},
          {"source_id":"khazix-wechat","url":"https://mp.weixin.qq.com.evil.invalid/s/fake","title":"fake"},
          {"source_id":"unknown","url":"https://mp.weixin.qq.com/s/foo","title":"unknown"}
        ]}
        state, report=m.update(BASE,submitted,{},fetcher,NOW)
        self.assertEqual(report["manual_links_added"],1)
        wx=[x for x in state["items"] if x["source_role"]=="wechat_unverified_share_link"]
        self.assertEqual(len(wx),1)
        self.assertIsNone(wx[0]["published_at"])
        self.assertEqual(wx[0]["evidence_level"],"link_only_publisher_unverified")
        self.assertIn("utm_source=a",wx[0]["source_url"])
        m.validate_inbox(state)

    def test_dynamic_or_unreadable_changelog_does_not_count_as_success(self):
        def fails(src):
            return feed(10) if src["mode"]=="rss" else b'<html><div id="root"></div></html>'
        state,report=m.update(BASE,{"items":[]},{},fails,NOW)
        self.assertEqual(report["sources_succeeded"],1)
        self.assertEqual(report["sources_failed"],1)
        self.assertEqual(state["sources"]["khazix-aihot-changelog"]["status"],"failed")
        self.assertNotIn("last_success_at",state["sources"]["khazix-aihot-changelog"])

    def test_invalid_registry_and_inbox_evidence_rejected(self):
        cfg=copy.deepcopy(BASE)
        cfg["sources"][0]["url"]="https://www.qbitai.com.evil.invalid/feed"
        with self.assertRaises(ValueError):
            m.validate_sources(cfg)
        data,_=m.update(BASE,{"items":[]},{},fetcher,NOW)
        data["items"][0]["evidence_level"]="official_confirmed"
        with self.assertRaises(ValueError):
            m.validate_inbox(data)

if __name__=="__main__":
    unittest.main()
