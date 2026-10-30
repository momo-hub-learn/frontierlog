import unittest

from scripts.collect_activity_radar import clip_text, editorial_title_key, keyword_match, merge_media_items, tags


def item(item_id, published, source="feed", title=None, url=None, origin="rss"):
    return {
        "id": item_id,
        "source_id": source,
        "published": published,
        "title": title or item_id,
        "summary": "",
        "url": url or f"https://example.com/{item_id}",
        "tags": [],
        "origin": origin,
    }


class ActivityRadarCollectorTests(unittest.TestCase):
    def test_chinese_ai_safety_conversation_gets_scannable_topics(self):
        self.assertEqual(tags('对话 AI安全 与有效利他主义如何影响硅谷'), ['AI Safety', 'Society'])

    def test_latin_topic_keywords_do_not_match_inside_unrelated_words(self):
        self.assertFalse(keyword_match('the master biographer reflects at 91', 'bio'))
        self.assertEqual(tags('the master biographer reflects at 91'), [])

    def test_latin_topic_keywords_still_match_terms_and_compounds(self):
        self.assertTrue(keyword_match('bio-ai systems and robot learning', 'bio'))
        self.assertEqual(tags('bio-ai systems and robot learning'), ['Robotics', 'BioAI'])
    def test_clip_text_prefers_a_complete_sentence(self):
        text = "A complete sentence with enough context. A second sentence that should not be cut in the middle of a word."
        self.assertEqual(clip_text(text, 70), "A complete sentence with enough context.")

    def test_clip_text_uses_a_word_boundary_when_no_sentence_fits(self):
        clipped = clip_text("one two three four five six seven", 18)
        self.assertEqual(clipped, "one two three four…")

    def test_keeps_existing_rss_when_feed_yields_no_match(self):
        previous = [item("old", "2026-10-23")]
        self.assertEqual(merge_media_items(previous, []), previous)

    def test_adds_new_items_without_dropping_existing_history(self):
        previous = [item("old", "2026-10-22")]
        new = [item("new", "2026-10-24")]
        self.assertEqual([x["id"] for x in merge_media_items(previous, new)], ["new", "old"])

    def test_deduplicates_feed_rows_by_url_and_title(self):
        previous = [item("old", "2026-10-22", title="Same", url="https://example.com/same")]
        new = [item("new", "2026-10-24", title="Same", url="https://example.com/same")]
        merged = merge_media_items(previous, new)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["id"], "new")

    def test_deduplicates_same_day_episode_aliases_by_long_shared_subtitle(self):
        post = item(
            "post",
            "2026-10-27",
            source="show",
            title="How Anthropic ships Claude with Claude: Separating the Brain from the Hands",
            url="https://example.com/p/opus55/",
        )
        podcast = item(
            "podcast",
            "2026-10-27",
            source="show",
            title="How Anthropic ships the #1 LLM safely: Separating the Brain from the Hands",
            url="https://example.com/p/podcast-episode/",
        )
        self.assertEqual(editorial_title_key(post), editorial_title_key(podcast))
        self.assertEqual([x["id"] for x in merge_media_items([], [podcast, post])], ["post"])

    def test_shared_short_or_cross_day_suffix_does_not_merge(self):
        first = item("first", "2026-10-27", source="show", title="News: Model update")
        second = item("second", "2026-10-27", source="show", title="Interview: Model update")
        next_day = item(
            "next-day",
            "2026-10-28",
            source="show",
            title="Follow-up interview: Separating the Brain from the Hands",
        )
        previous_day = item(
            "previous-day",
            "2026-10-27",
            source="show",
            title="Launch interview: Separating the Brain from the Hands",
        )
        self.assertEqual(editorial_title_key(first), "")
        self.assertEqual(len(merge_media_items([], [first, second, previous_day, next_day])), 4)

    def test_applies_global_recency_limit(self):
        rows = [item(f"item-{n}", f"2026-10-{n:02d}") for n in range(1, 18)]
        self.assertEqual(len(merge_media_items(rows, [], limit=10)), 10)
        self.assertEqual(merge_media_items(rows, [], limit=10)[0]["id"], "item-17")

    def test_never_evicts_editorially_verified_manual_items(self):
        manual = item("manual", "2026-01-01", origin="verified-manual")
        feed = [item(f"feed-{n}", f"2026-10-{n:02d}") for n in range(1, 18)]
        merged = merge_media_items([manual, *feed], [], limit=10)
        self.assertEqual(len(merged), 10)
        self.assertIn("manual", {x["id"] for x in merged})

    def test_manual_record_wins_over_duplicate_rss_discovery(self):
        manual = item("manual", "2026-10-23", source="show", title="Same", url="https://example.com/same", origin="verified-manual")
        rss = item("rss", "2026-10-24", source="show", title="Same", url="https://example.com/same")
        merged = merge_media_items([manual], [rss])
        self.assertEqual([x["id"] for x in merged], ["manual"])


if __name__ == "__main__":
    unittest.main()
