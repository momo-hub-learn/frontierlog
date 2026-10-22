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


if __name__ == "__main__":
    unittest.main()
