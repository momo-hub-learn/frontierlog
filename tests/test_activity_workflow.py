"""Contracts for the activity browser-check runner setup."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "activity-hero.yml"


class ActivityWorkflowContractTests(unittest.TestCase):
    def test_browser_setup_reuses_runner_browser_before_downloading(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('command -v "$candidate"', text)
        self.assertIn('echo "CHROMIUM_EXECUTABLE=$browser_bin" >> "$GITHUB_ENV"', text)
        self.assertIn('if [[ -z "$browser_bin" ]]; then', text)
        self.assertNotIn("playwright install --with-deps chromium", text)


if __name__ == "__main__":
    unittest.main()
