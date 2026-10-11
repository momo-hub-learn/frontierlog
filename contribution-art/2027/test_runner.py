"""Isolated local-Git tests. No GitHub requests, credentials, or remote mutations."""

from datetime import date, datetime, timedelta, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("welcome_runner", Path(__file__).with_name("runner.py"))
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
DAY = date(2027, 2, 7)
NOW = datetime(2027, 2, 7, 12, 17, tzinfo=timezone.utc)
AUTHOR = ("Verified Test Author", "verified-author@example.test")


def command(root, *args, env=None):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True,
                          text=True, env=env).stdout.strip()


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="welcome-runner-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.remote = self.base / "origin.git"
        self.root = self.base / "work"
        self.remote.mkdir()
        self.root.mkdir()
        command(self.remote, "init", "--bare", "--initial-branch=main")
        command(self.root, "init", "--initial-branch=main")
        command(self.root, "config", "user.name", "Fixture Author")
        command(self.root, "config", "user.email", "fixture@example.test")
        command(self.root, "config", "commit.gpgsign", "false")
        self.plan_path = self.root / runner.ART / "plan.json"
        self.plan_path.parent.mkdir(parents=True)
        self.target = 3
        self.write_plan()
        (self.root / "README.md").write_text("Normal project work.\n", encoding="utf-8")
        command(self.root, "add", ".")
        command(self.root, "commit", "-m", "Initial project and plan")
        command(self.root, "remote", "add", "origin", str(self.remote))
        command(self.root, "push", "-u", "origin", "main")
        self.initial = self.head()
        self.addCleanup(patch.stopall)
        self.clock = patch.object(runner, "utcnow", return_value=NOW).start()
        self.identity = patch.object(runner, "verified_author", return_value=AUTHOR).start()
        patch.object(runner, "origin_matches", side_effect=lambda url: url == str(self.remote)).start()

    def write_plan(self, lit_dates=(DAY,)):
        days = []
        for index in range(365):
            day = date(2027, 1, 1) + timedelta(days=index)
            lit = day in lit_dates
            days.append({"date": day.isoformat(), "lit": lit, "extra_commits": self.target if lit else 0})
        self.plan_path.write_text(json.dumps({"days": days}) + "\n", encoding="utf-8")

    def run_art(self, **kwargs):
        return runner.execute(self.root, self.plan_path, **kwargs)

    def head(self, remote=False):
        return command(self.remote if remote else self.root, "rev-parse", "main")

    def count(self, remote=False):
        return int(command(self.remote if remote else self.root, "rev-list", "--count", "main"))

    def receipt(self, remote=False):
        path = runner.receipt_path(DAY)
        return json.loads(command(self.remote if remote else self.root, "show", f"main:{path}"))

    def assert_clean(self):
        self.assertEqual(command(self.root, "status", "--porcelain"), "")

    def change_target(self, amount):
        self.target = amount
        self.write_plan()
        command(self.root, "add", str(runner.ART / "plan.json"))
        command(self.root, "commit", "-m", "Update plan fixture")
        command(self.root, "push", "origin", "main")

    def test_twenty_real_day_commits_are_idempotent_and_scoped(self):
        self.change_target(20)
        before = self.count(remote=True)
        self.assertEqual(self.run_art(apply=True, push=True)["completed"], 20)
        self.assertEqual(self.count(remote=True) - before, 20)
        head = self.head()
        self.assertEqual(self.run_art(apply=True, push=True)["completed"], 20)
        self.assertEqual(self.head(), head)
        self.assertEqual(self.head(remote=True), head)
        self.assertEqual(self.receipt(remote=True)["completed"], 20)
        self.assertEqual(command(self.root, "diff", "--name-only", f"main~20", "main"), runner.receipt_path(DAY))
        self.assertEqual((self.root / "README.md").read_text(), "Normal project work.\n")
        dates = command(self.root, "log", "-20", "--format=%aI").splitlines()
        self.assertTrue(all(datetime.fromisoformat(value).date() == DAY for value in dates))
        self.assert_clean()

    def test_default_dry_run_does_not_contact_identity_or_write(self):
        self.assertEqual(self.run_art()["status"], "dry-run")
        self.identity.assert_not_called()
        self.assertEqual(self.head(), self.initial)
        self.assert_clean()

    def test_outside_year_and_blank_days_are_noops(self):
        for now in (datetime(2026, 12, 31, tzinfo=timezone.utc),
                    datetime(2028, 1, 1, tzinfo=timezone.utc), NOW + timedelta(days=1)):
            self.clock.return_value = now
            self.assertEqual(self.run_art(apply=True, push=True)["status"], "no-op")
        self.identity.assert_not_called()
        self.assertEqual(self.head(), self.initial)
        self.assertEqual(self.head(remote=True), self.initial)
        self.assertFalse((self.root / runner.ART / "days").exists())
        self.assert_clean()

    def test_simulated_dates_can_only_be_previewed(self):
        self.assertEqual(self.run_art(at=DAY.isoformat())["status"], "dry-run")
        with self.assertRaisesRegex(RuntimeError, "read-only"):
            self.run_art(apply=True, at=DAY.isoformat())
        with self.assertRaisesRegex(RuntimeError, "requires --apply"):
            self.run_art(push=True)
        self.assertEqual(self.head(), self.initial)

    def test_dirty_worktree_and_staging_are_preserved(self):
        readme = self.root / "README.md"
        readme.write_text("Unrelated staged work.\n")
        command(self.root, "add", "README.md")
        (self.root / "untracked.txt").write_text("Unrelated untracked work.\n")
        staged = command(self.root, "diff", "--cached")
        with self.assertRaisesRegex(RuntimeError, "clean"):
            self.run_art(apply=True)
        self.assertEqual(command(self.root, "diff", "--cached"), staged)
        self.assertEqual(readme.read_text(), "Unrelated staged work.\n")
        self.assertEqual((self.root / "untracked.txt").read_text(), "Unrelated untracked work.\n")
        self.assertEqual(self.head(), self.initial)

    def test_unpublished_normal_commits_are_not_discarded(self):
        (self.root / "README.md").write_text("Important unpublished work.\n")
        command(self.root, "add", "README.md")
        command(self.root, "commit", "-m", "Normal unpublished project work")
        head = self.head()
        with self.assertRaises(RuntimeError):
            self.run_art(apply=True, push=True)
        self.assertEqual(self.head(), head)
        self.assertEqual(self.head(remote=True), self.initial)
        self.assertEqual((self.root / "README.md").read_text(), "Important unpublished work.\n")

    def test_nonmain_branch_is_rejected(self):
        command(self.root, "checkout", "-b", "feature")
        with self.assertRaisesRegex(RuntimeError, "main branch"):
            self.run_art(apply=True)
        self.identity.assert_not_called()

    def test_rejected_push_is_an_error_and_rerun_does_not_duplicate(self):
        hook = self.remote / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        for _ in range(2):
            with self.assertRaisesRegex(RuntimeError, "Non-force push failed"):
                self.run_art(apply=True, push=True)
            self.assertEqual(self.count(), 1 + self.target)
            self.assertEqual(self.head(remote=True), self.initial)
            self.assert_clean()
        hook.unlink()
        self.assertEqual(self.run_art(apply=True, push=True)["status"], "pushed")
        self.assertEqual(self.count(remote=True), 1 + self.target)

    def test_remote_project_race_rebuilds_only_art_and_preserves_new_work(self):
        original = runner.Git.call
        raced = []

        def interleave(git, *args, **kwargs):
            if args[0] == "push" and not raced:
                raced.append(True)
                other = self.base / "concurrent"
                command(self.base, "clone", str(self.remote), str(other))
                command(other, "config", "user.name", "Normal Developer")
                command(other, "config", "user.email", "developer@example.test")
                (other / "README.md").write_text("Concurrent normal project improvement.\n")
                command(other, "add", "README.md")
                command(other, "commit", "-m", "Normal concurrent project change")
                command(other, "push", "origin", "main")
            return original(git, *args, **kwargs)

        with patch.object(runner.Git, "call", interleave):
            self.assertEqual(self.run_art(apply=True, push=True)["status"], "pushed")
        self.assertEqual(self.count(remote=True), 2 + self.target)
        self.assertEqual((self.root / "README.md").read_text(), "Concurrent normal project improvement.\n")
        self.assertEqual(self.receipt(remote=True)["completed"], self.target)
        self.assert_clean()

    def test_competing_art_writer_does_not_double_daily_count(self):
        original = runner.Git.call
        raced = []

        def interleave(git, *args, **kwargs):
            if args[0] == "push" and not raced:
                raced.append(True)
                other = self.base / "competing-art"
                command(self.base, "clone", str(self.remote), str(other))
                with patch.object(runner, "utcnow", return_value=NOW + timedelta(minutes=1)):
                    runner.execute(other, other / runner.ART / "plan.json", apply=True, push=True)
            return original(git, *args, **kwargs)

        with patch.object(runner.Git, "call", interleave):
            self.assertEqual(self.run_art(apply=True, push=True)["status"], "pushed")
        self.assertEqual(self.count(remote=True), 1 + self.target)
        self.assertEqual(self.receipt(remote=True)["completed"], self.target)
        self.assert_clean()

    def test_utc_midnight_stops_before_next_day_mutation(self):
        original = runner.Git.call

        def after_first_commit(git, *args, **kwargs):
            result = original(git, *args, **kwargs)
            if "commit" in args and args[0] == "-c":
                self.clock.return_value = NOW + timedelta(days=1)
            return result

        with patch.object(runner.Git, "call", after_first_commit):
            with self.assertRaisesRegex(RuntimeError, "UTC date changed"):
                self.run_art(apply=True, push=True)
        self.assertEqual(self.count(), 2)
        self.assertEqual(self.receipt()["completed"], 1)
        self.assertEqual(self.head(remote=True), self.initial)
        self.assertFalse((self.root / runner.receipt_path(DAY + timedelta(days=1))).exists())
        self.assert_clean()

    def test_duplicate_receipt_history_is_rejected(self):
        self.run_art(apply=True, push=True)
        path = self.root / runner.receipt_path(DAY)
        receipt = json.loads(path.read_text())
        receipt["updated_at"] = (NOW + timedelta(minutes=2)).isoformat()
        path.write_text(json.dumps(receipt))
        env = os.environ.copy()
        env.update(GIT_AUTHOR_NAME=AUTHOR[0], GIT_AUTHOR_EMAIL=AUTHOR[1], GIT_AUTHOR_DATE=NOW.isoformat(),
                   GIT_COMMITTER_DATE=NOW.isoformat())
        command(self.root, "add", str(path))
        command(self.root, "commit", "-m", runner.title(DAY, self.target, self.target), env=env)
        head = self.head()
        with self.assertRaisesRegex(RuntimeError, "Duplicate or missing"):
            self.run_art(apply=True, push=True)
        self.assertEqual(self.head(), head)
        self.assertEqual(self.count(remote=True), 1 + self.target)


class IdentityAndPlanTests(unittest.TestCase):
    def test_author_mapping_requires_exact_account_id_and_source_sha(self):
        fixture = {"sha": runner.SOURCE_SHA, "author": {"login": runner.LOGIN, "id": runner.USER_ID},
                   "commit": {"author": {"name": AUTHOR[0], "email": AUTHOR[1]}}}
        with patch.dict(os.environ, {"GITHUB_TOKEN": "isolated-test-token"}):
            with patch.object(runner.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(fixture).encode())):
                self.assertEqual(runner.verified_author(), AUTHOR)
            fixture["author"]["id"] += 1
            with patch.object(runner.urllib.request, "urlopen", return_value=io.BytesIO(json.dumps(fixture).encode())):
                with self.assertRaisesRegex(RuntimeError, "expected GitHub author"):
                    runner.verified_author()

    def test_origin_guard_rejects_wrong_or_credential_embedded_repository(self):
        self.assertTrue(runner.origin_matches("https://github.com/momo-hub-learn/frontierlog.git"))
        self.assertFalse(runner.origin_matches("https://github.com/momo-hub/frontierlog.git"))
        self.assertFalse(runner.origin_matches("https://token@github.com/momo-hub-learn/frontierlog.git"))
        self.assertFalse(runner.origin_matches("https://example.test/momo-hub-learn/frontierlog.git"))


if __name__ == "__main__":
    unittest.main()
