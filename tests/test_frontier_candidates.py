import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from frontier_candidates import merge_queue, validate_queue
from model_data import validate_models

QUEUE = json.loads((ROOT / "data/frontier-candidates.json").read_text(encoding="utf-8"))
MODELS = json.loads((ROOT / "data/models.json").read_text(encoding="utf-8"))


class FrontierCandidateTests(unittest.TestCase):
    def test_existing_queue_keeps_lehami_and_valid_dates(self):
        validate_queue(QUEUE)
        self.assertIn("2610.15267", {x["arxiv_id"] for x in QUEUE["items"]})

    def test_incremental_merge_no_auto_approval(self):
        report = {
            "checked": QUEUE["checked"], "status": "review_only", "auto_publish": False,
            "source": "arXiv Atom API", "candidates": [
                {"arxiv_id": "2610.29999", "title": "A Synthetic World Model Research Candidate",
                 "date": QUEUE["checked"], "authors": ["Example Researcher"],
                 "url": "https://arxiv.org/abs/2610.29999",
                 "status": "editorial_review_required"}
            ],
        }
        merged, n = merge_queue(copy.deepcopy(QUEUE), report, set())
        self.assertEqual(n, 1)
        new_row = next(x for x in merged["items"] if x["arxiv_id"] == "2610.29999")
        self.assertEqual(new_row["status"], "pending")
        self.assertTrue(any(x["arxiv_id"] == "2610.15267" for x in merged["items"]))
        again, n = merge_queue(merged, report, set())
        self.assertEqual(n, 0)
        self.assertEqual(again, merged)

    def test_already_reviewed_status_survives(self):
        q = copy.deepcopy(QUEUE)
        q["items"][-1]["status"] = "reviewed"
        original = q["items"][-1]
        report = {"checked": QUEUE["checked"], "source": "arXiv Atom API",
                  "status": "review_only", "auto_publish": False, "candidates": []}
        merged, n = merge_queue(q, report, set())
        self.assertEqual(n, 0)
        self.assertEqual(merged["items"][-1], original)

    def test_reject_forged_source_and_approval(self):
        report = {"checked": QUEUE["checked"], "source": "some website",
                  "status": "review_only", "auto_publish": False, "candidates": []}
        with self.assertRaises(ValueError):
            merge_queue(QUEUE, report, set())
        report["source"] = "arXiv Atom API"
        report["auto_publish"] = True
        with self.assertRaises(ValueError):
            merge_queue(QUEUE, report, set())

    def test_research_rubric_is_bounded_and_not_a_model_capability_score(self):
        validate_models(MODELS)
        x = copy.deepcopy(MODELS)
        world = next(t for t in x["frontier_tracks"] if t["id"] == "world-models")
        rated = next(i for i in world["items"] if i.get("research_review"))
        self.assertEqual(rated["research_review"]["scope"], "research_attention_not_capability")
        rated["research_review"]["dimensions"]["novelty"]["rating"] = 5
        with self.assertRaises(ValueError):
            validate_models(x)


if __name__ == "__main__":
    unittest.main()
