"""Network-free tests for the two-hour no-LLM pipeline."""
import json
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
import ai_coordinate_auto as bot

NOW = datetime(2026, 11, 4, 5, tzinfo=timezone.utc)
OPENAI = b'''<rss version="2.0"><channel>
<item><title> Official AI release </title><link>https://openai.com/news/official-release</link><pubDate>Tue, 03 Nov 2026 20:00:00 GMT</pubDate></item>
<item><title>Malicious redirect</title><link>https://evil.invalid/news</link></item>
</channel></rss>'''
NVIDIA = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>GPU framework update</title>
<link rel="alternate" href="https://developer.nvidia.com/blog/gpu-update/"/>
<updated>2026-11-04T03:00:00+00:00</updated></entry></feed>'''

class LowTokenTests(unittest.TestCase):
    def test_rss_and_atom_only_allow_pinned_original_domains(self):
        a = bot.parse_feed(OPENAI, {**bot.FEEDS["openai-news"], "id": "openai-news"}, NOW)
        b = bot.parse_feed(NVIDIA, {**bot.FEEDS["nvidia-developer"], "id": "nvidia-developer"}, NOW)
        self.assertEqual((len(a), len(b)), (1, 1))
        self.assertEqual(a[0]["published_at"], "2026-11-03T20:00:00Z")
        self.assertEqual(b[0]["published_at"], "2026-11-04T03:00:00Z")
        self.assertEqual(a[0]["status"], "unreviewed")
        self.assertFalse(bot.safe_url("https://openai.com.evil.invalid/x", bot.FEEDS["openai-news"]["hosts"]))
        self.assertFalse(bot.safe_url("http://openai.com/news", bot.FEEDS["openai-news"]["hosts"]))

    def test_missing_timezone_never_fabricates_midnight(self):
        self.assertEqual(bot.publication_time("2026-11-03", NOW), (None, False))
        self.assertEqual(bot.publication_time("2026-11-04T01:00:00", NOW), (None, False))
        self.assertEqual(bot.publication_time("2026-11-04T13:00:00+08:00", NOW), ("2026-11-04T05:00:00Z", False))
        with self.assertRaises(ValueError):
            bot.stamp(datetime(2026, 11, 4))

    def test_future_articles_never_enter_queue(self):
        future = OPENAI.replace(b"03 Nov 2026 20:00:00", b"23 Nov 2026 20:00:00")
        with self.assertRaises(ValueError):
            bot.parse_feed(future, {**bot.FEEDS["openai-news"], "id": "openai-news"}, NOW)

    def test_partial_failure_keeps_old_success_and_first_seen(self):
        previous = {"items": [], "sources": {"nvidia-developer": {"last_success_at": "2026-10-30T12:00:00Z"}}, "last_ingested_at": None}
        def fetch(source):
            if source["id"] == "openai-news":
                return OPENAI
            raise OSError("HTTP 403")
        data, result = bot.update_inbox(previous, fetch, NOW)
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["sources"]["nvidia-developer"]["last_success_at"], "2026-10-30T12:00:00Z")
        self.assertEqual(data["sources"]["nvidia-developer"]["status"], "failed")
        again, summary = bot.update_inbox(data, fetch, NOW)
        self.assertEqual(summary["new_candidates"], 0)
        self.assertEqual(again["items"][0]["first_seen_at"], data["items"][0]["first_seen_at"])
        self.assertEqual(again["last_ingested_at"], data["last_ingested_at"])

    def test_human_review_status_is_not_overwritten(self):
        data, _ = bot.update_inbox({}, lambda s: OPENAI if s["id"] == "openai-news" else NVIDIA, NOW)
        data["items"][0]["status"] = "approved"
        data["items"][0]["reviewed_at"] = "2026-11-04T05:30:00Z"
        again, _ = bot.update_inbox(data, lambda s: OPENAI if s["id"] == "openai-news" else NVIDIA, NOW)
        row = next(x for x in again["items"] if x["status"] == "approved")
        self.assertEqual(row["reviewed_at"], "2026-11-04T05:30:00Z")

    def test_broken_official_source_does_not_block_hf(self):
        called = []
        def executor(args, **kwargs):
            called.append(args[-1])
            return subprocess.CompletedProcess(args, 1, "", "")
        with patch.object(bot, "INBOX", Path("/nonexistent/official-inbox.json")), patch.object(bot, "verify_data", return_value=None):
            with patch.object(bot.Path, "read_text", return_value=json.dumps({"sync": {"web_status": "preserved", "api_status": "preserved"}})):
                result, rc = bot.run_commands(["official", "hf"], executor, NOW)
        self.assertEqual(len(called), 1)
        self.assertEqual(result["sources"]["official"]["status"], "failed")
        self.assertEqual(result["sources"]["hf"]["status"], "failed")
        self.assertEqual(rc, 2)

    def test_each_command_runs_after_preceding_failure(self):
        seen = []
        def executor(args, **kwargs):
            seen.append(args[-1])
            return subprocess.CompletedProcess(args, 2, "", "403")
        with patch.object(bot, "verify_data", return_value=None):
            with patch.object(bot.Path, "read_text", return_value=json.dumps({"sync": {"web_status": "preserved", "api_status": "preserved"}, "repositories_succeeded": 0, "repositories_total": 22, "errors": [1]})):
                result, rc = bot.run_commands(["hf", "upstream"], executor, NOW)
        self.assertEqual(len(seen), 2)
        self.assertEqual(rc, 2)
        self.assertEqual(result["status"], "failed")

if __name__ == "__main__":
    unittest.main()
