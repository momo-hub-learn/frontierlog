import json
from pathlib import Path
import sys
import unittest
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import huggingface_trending_sync as sync


class HuggingFaceTrendingSyncTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads((ROOT / "data/huggingface-hot.json").read_text(encoding="utf-8"))
        self.now = datetime(2026, 10, 22, 3, 30, tzinfo=timezone.utc)

    def test_web_parser_only_reads_ranked_cards(self):
        page = '<a href="/join/discord"></a>' + ''.join(
            f'<article class="overview-card-wrapper x"><a href="/org/model-{i}"></a></article>'
            for i in range(20)
        )
        self.assertEqual(sync.parse_web_order(page)[0], "org/model-0")
        self.assertEqual(sync.parse_web_order(page)[-1], "org/model-19")

    def test_sources_keep_independent_times(self):
        page = ''.join(
            f'<article class="overview-card-wrapper"><a href="/org/model-{i}"></a></article>'
            for i in range(20)
        )
        old_api_time = self.base["api_fetched_at"]
        out = sync.update_state(self.base, self.now, page, None)
        self.assertEqual(out["web_fetched_at"], "2026-10-22T03:30:00Z")
        self.assertEqual(out["api_fetched_at"], old_api_time)
        self.assertEqual(out["sync"]["api_status"], "preserved")
        self.assertEqual(out["web_verification_method"], "official_web_server_html")

    def test_api_only_refresh_preserves_reviewed_browser_provenance(self):
        payload = [
            {"id": f"api/model-{i}", "trendingScore": 20-i, "tags": []}
            for i in range(20)
        ]
        self.base["web_verification_method"] = "official_web_browser_editorial"
        out = sync.update_state(self.base, self.now, None, payload)
        self.assertEqual(out["web_verification_method"], "official_web_browser_editorial")

    def test_web_rank_changes_only_compare_real_saved_snapshots(self):
        old_order = [f"org/model-{i}" for i in range(20)]
        self.base["web_order"] = old_order
        self.base["web_fetched_at"] = "2026-10-22T01:00:00Z"
        current = [old_order[1], old_order[0], *old_order[2:19], "org/new-model"]
        page = ''.join(
            f'<article class="overview-card-wrapper"><a href="/{model_id}"></a></article>'
            for model_id in current
        )
        out = sync.update_state(self.base, self.now, page, None)
        changes = {row["id"]: row for row in out["web_rank_changes"]}
        self.assertEqual(changes[old_order[1]]["rank_change"], 1)
        self.assertEqual(changes[old_order[0]]["rank_change"], -1)
        self.assertIsNone(changes["org/new-model"]["previous_rank"])
        self.assertIsNone(changes["org/new-model"]["rank_change"])
        self.assertEqual(changes[old_order[1]]["previous_fetched_at"], "2026-10-22T01:00:00Z")
        self.assertEqual(out["web_outgoing"], [{
            "id": old_order[-1],
            "previous_rank": 20,
            "previous_fetched_at": "2026-10-22T01:00:00Z",
        }])

    def test_web_failure_preserves_existing_rank_changes(self):
        before = self.base.get("web_rank_changes")
        outgoing = self.base.get("web_outgoing")
        out = sync.update_state(self.base, self.now, None, [
            {"id": f"api/model-{i}", "trendingScore": 20-i, "tags": []}
            for i in range(20)
        ])
        self.assertEqual(out.get("web_rank_changes"), before)
        self.assertEqual(out.get("web_outgoing"), outgoing)

    def test_partial_source_failure_keeps_machine_readable_reason(self):
        payload = [
            {"id": f"api/model-{i}", "trendingScore": 20-i, "tags": []}
            for i in range(20)
        ]
        out = sync.update_state(
            self.base, self.now, None, payload, {"web": "<urlopen error timed out>"}
        )
        self.assertEqual(out["sync"]["status"], "partial")
        self.assertEqual(out["sync"]["web_status"], "preserved")
        self.assertEqual(out["sync"]["web_error"], "<urlopen error timed out>")
        self.assertNotIn("api_error", out["sync"])

    def test_api_metrics_do_not_rewrite_web_order(self):
        payload = [{"id": f"api/model-{i}", "trendingScore": 20-i, "likes": i,
                    "downloads": i*10, "tags": [], "pipeline_tag": "text-generation"}
                   for i in range(20)]
        web_order = list(self.base["web_order"])
        out = sync.update_state(self.base, self.now, None, payload)
        self.assertEqual(out["web_order"], web_order)
        self.assertEqual(out["items"][0]["id"], "api/model-0")
        self.assertEqual(out["sync"]["web_status"], "preserved")

    def test_api_tags_follow_publish_contract(self):
        payload = [{"id": f"api/model-{i}", "trendingScore": 20-i, "likes": i,
                    "downloads": i*10, "pipeline_tag": "text-generation",
                    "tags": ["ok", "x"*60, "ok", "second"]}
                   for i in range(20)]
        rows = sync.parse_api(payload)
        self.assertEqual(rows[0]["tags"], ["ok", "second"])
        self.assertTrue(all(1 <= len(x["tags"]) <= 4 for x in rows))

    def test_reviewed_snapshot_change_triggers_static_rebuild(self):
        workflow = (ROOT / ".github/workflows/hot-sync.yml").read_text(encoding="utf-8")
        self.assertIn("- 'data/huggingface-hot.json'", workflow)


if __name__ == "__main__":
    unittest.main()
