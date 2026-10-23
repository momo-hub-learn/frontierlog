"""Contracts for the shared browser-check runner setup."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SETUP_SCRIPT = ROOT / "scripts" / "setup_ci_browser.sh"
WORKFLOWS = (
    "activity-hero.yml",
    "arena.yml",
    "deep-guide.yml",
    "jev-narrative.yml",
    "people.yml",
    "product-timeline.yml",
    "toolkit.yml",
)


class ActivityWorkflowContractTests(unittest.TestCase):
    def test_browser_setup_reuses_runner_browser_before_downloading(self):
        text = SETUP_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('command -v "$candidate"', text)
        self.assertIn('echo "CHROMIUM_EXECUTABLE=$browser_bin" >> "$GITHUB_ENV"', text)
        self.assertIn('if [[ -z "$browser_bin" ]]; then', text)
        self.assertNotIn("playwright install --with-deps chromium", text)

    def test_browser_workflows_share_the_bounded_setup(self):
        for name in WORKFLOWS:
            with self.subTest(workflow=name):
                text = (ROOT / ".github" / "workflows" / name).read_text(
                    encoding="utf-8"
                )
                self.assertIn("bash scripts/setup_ci_browser.sh", text)
                self.assertIn("'scripts/setup_ci_browser.sh'", text)
                self.assertNotIn("playwright install --with-deps chromium", text)


if __name__ == "__main__":
    unittest.main()
