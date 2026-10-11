#!/usr/bin/env python3
"""Add plainly labelled calendar-art commits on the actual scheduled UTC day."""

import argparse
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request

REPOSITORY = "momo-hub-learn/frontierlog"
LOGIN, USER_ID = "momo-hub-learn", 298967485
SOURCE_SHA = "f03194ff7778c001ef26882036d4259757374346"
ART = Path("contribution-art/2027")
YEAR = 2027


def utcnow():
    return datetime.now(timezone.utc)


def check_day(day):
    current = utcnow()
    if current.year != YEAR or current.date() != day:
        raise RuntimeError("UTC date changed or is outside 2027; no catch-up or backdating is allowed")
    return current


def load_plan(path):
    days = json.loads(Path(path).read_text(encoding="utf-8"))["days"]
    expected = {(date(YEAR, 1, 1) + timedelta(days=i)).isoformat() for i in range(365)}
    if len(days) != 365 or {d["date"] for d in days} != expected:
        raise RuntimeError("Plan must contain each 2027 date exactly once")
    for entry in days:
        amount = entry["extra_commits"]
        if type(entry["lit"]) is not bool or type(amount) is not int:
            raise RuntimeError("Invalid plan value types")
        if not 0 <= amount <= 100 or bool(amount) != entry["lit"]:
            raise RuntimeError("Plan must assign 0 to blank days and 1..100 to lit days")
    return {d["date"]: d for d in days}


class Git:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def call(self, *args, env=None, check=True):
        result = subprocess.run(["git", "-C", str(self.root), *args], env=env,
                                text=True, capture_output=True, timeout=60)
        if check and result.returncode:
            raise RuntimeError(f"git {args[0]} failed: {result.stderr.strip()[:1000]}")
        return result.stdout.strip() if check else result

    def clean(self):
        if self.call("status", "--porcelain", "--untracked-files=all"):
            raise RuntimeError("Worktree/index must be clean; unrelated changes are never staged or discarded")

    def ancestor(self, before, after):
        result = self.call("merge-base", "--is-ancestor", before, after, check=False)
        if result.returncode not in (0, 1):
            raise RuntimeError("Could not verify commit ancestry")
        return result.returncode == 0

    def fetch(self):
        self.call("fetch", "origin", "refs/heads/main:refs/remotes/origin/main")
        return self.call("rev-parse", "origin/main")


def origin_matches(url):
    return url in {f"https://github.com/{REPOSITORY}", f"https://github.com/{REPOSITORY}.git",
                   f"git@github.com:{REPOSITORY}.git", f"ssh://git@github.com/{REPOSITORY}.git"}


def guard_repository(git):
    if Path(git.call("rev-parse", "--show-toplevel")).resolve() != git.root:
        raise RuntimeError("Unexpected repository root")
    if git.call("symbolic-ref", "--short", "HEAD") != "main":
        raise RuntimeError("Apply requires a checked-out main branch")
    if not origin_matches(git.call("remote", "get-url", "origin")):
        raise RuntimeError(f"Origin must be github.com/{REPOSITORY}")
    if git.call("rev-parse", "--is-shallow-repository") != "false":
        raise RuntimeError("Full history is required; use actions/checkout with fetch-depth: 0")
    git.clean()


def verified_author():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        result = subprocess.run(["gh", "auth", "token"], text=True, capture_output=True, timeout=15)
        if result.returncode or not result.stdout.strip():
            raise RuntimeError("GitHub authentication is required to verify the author")
        token = result.stdout.strip()
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/commits/{SOURCE_SHA}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "WELCOME-calendar-art"})
    with urllib.request.urlopen(request, timeout=30) as response:
        commit = json.load(response)
    account = commit.get("author") or {}
    if commit.get("sha") != SOURCE_SHA or account.get("login") != LOGIN or account.get("id") != USER_ID:
        raise RuntimeError("Immutable source commit did not verify the expected GitHub author")
    author = commit["commit"]["author"]
    values = (author.get("name"), author.get("email"))
    if any(not isinstance(v, str) or not v.strip() or any(c in v for c in "\r\n\x00") for v in values):
        raise RuntimeError("Verified source commit has invalid author metadata")
    return values


def receipt_path(day):
    return (ART / "days" / f"{day.isoformat()}.json").as_posix()


def title(day, step, target):
    return f"contribution-art: WELCOME {day.isoformat()} [{step:02d}/{target:02d}]"


def validate_commit(git, sha, day, target, email):
    path = receipt_path(day)
    meta = git.call("show", "-s", "--format=%ae%x00%aI%x00%s", sha).split("\x00")
    if len(meta) != 3 or meta[0] != email or datetime.fromisoformat(meta[1]).astimezone(timezone.utc).date() != day:
        raise RuntimeError("Art commit has an unexpected author or UTC author date")
    if git.call("diff-tree", "--root", "--no-commit-id", "--name-only", "-r", sha).splitlines() != [path]:
        raise RuntimeError("Art commit touches an unexpected path; refusing to rewrite local history")
    receipt = json.loads(git.call("show", f"{sha}:{path}"))
    step = receipt.get("completed")
    if (receipt.get("schema") != 1 or receipt.get("kind") != "contribution-art"
            or receipt.get("account") != LOGIN or receipt.get("date") != day.isoformat()
            or receipt.get("target") != target or type(step) is not int or not 1 <= step <= target
            or meta[2] != title(day, step, target)):
        raise RuntimeError("Art receipt and commit history disagree")
    return step


def reconcile(git, day, target, email):
    path = receipt_path(day)
    commits = git.call("log", "--reverse", "--format=%H", "--", path).splitlines()
    steps = [validate_commit(git, sha, day, target, email) for sha in commits]
    if steps != list(range(1, len(steps) + 1)):
        raise RuntimeError("Duplicate or missing art step in history; refusing additional commits")
    if bool(steps) != (git.root / path).is_file():
        raise RuntimeError("Daily receipt is missing or has no matching committed history")
    return len(steps)


def synchronize(git, day, target, email):
    check_day(day)
    git.clean()
    remote = git.fetch()
    local_only = git.call("rev-list", "origin/main..HEAD").splitlines()
    for sha in local_only:
        validate_commit(git, sha, day, target, email)
    if not git.ancestor("origin/main", "HEAD"):
        check_day(day)
        if local_only:
            # Only verified, unpublished art commits are rebuilt after a race.
            git.call("reset", "--hard", "origin/main")
        else:
            git.call("merge", "--ff-only", "origin/main")
    return remote


def write_remaining(git, day, target, author):
    path = receipt_path(day)
    destination = git.root / path
    completed = reconcile(git, day, target, author[1])
    for step in range(completed + 1, target + 1):
        stamp = check_day(day).isoformat(timespec="seconds")
        git.clean()
        previous = destination.read_text(encoding="utf-8") if destination.exists() else None
        head = git.call("rev-parse", "HEAD")
        receipt = {"schema": 1, "kind": "contribution-art", "account": LOGIN,
                   "date": day.isoformat(), "completed": step, "target": target, "updated_at": stamp}
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        env = os.environ.copy()
        env.update(GIT_AUTHOR_NAME=author[0], GIT_AUTHOR_EMAIL=author[1], GIT_AUTHOR_DATE=stamp,
                   GIT_COMMITTER_NAME="github-actions[bot]",
                   GIT_COMMITTER_EMAIL="41898282+github-actions[bot]@users.noreply.github.com",
                   GIT_COMMITTER_DATE=stamp)
        try:
            git.call("add", "--", path)
            check_day(day)
            git.call("-c", "commit.gpgsign=false", "commit", "--only", "-m", title(day, step, target),
                     "--", path, env=env)
        except Exception:
            if git.call("rev-parse", "HEAD") == head:
                git.call("reset", "-q", "HEAD", "--", path)
                if previous is None:
                    destination.unlink(missing_ok=True)
                else:
                    destination.write_text(previous, encoding="utf-8")
            raise
    git.clean()
    return reconcile(git, day, target, author[1])


def execute(root, plan_path, *, apply=False, push=False, at=None):
    if push and not apply:
        raise RuntimeError("--push requires --apply")
    if at is not None and apply:
        raise RuntimeError("--at is allowed only for a read-only dry-run")
    day = date.fromisoformat(at) if at else utcnow().date()
    if day.year != YEAR:
        return {"status": "no-op", "date": day.isoformat(), "reason": "outside 2027"}
    plan = load_plan(plan_path)
    target = plan[day.isoformat()]["extra_commits"]
    if not target:
        return {"status": "no-op", "date": day.isoformat(), "reason": "blank pixel"}
    if not apply:
        return {"status": "dry-run", "date": day.isoformat(), "planned_extra_commits": target}
    git = Git(root)
    check_day(day)
    guard_repository(git)
    author = verified_author()
    for attempt in range(3):
        remote_before = synchronize(git, day, target, author[1])
        if load_plan(plan_path)[day.isoformat()]["extra_commits"] != target:
            raise RuntimeError("Remote plan changed during this run; rerun with the new plan")
        completed = write_remaining(git, day, target, author)
        if not push:
            return {"status": "committed-locally", "date": day.isoformat(), "completed": completed}
        check_day(day)
        head = git.call("rev-parse", "HEAD")
        result = git.call("push", "origin", "HEAD:refs/heads/main", check=False)
        if result.returncode == 0:
            git.fetch()
            if not git.ancestor(head, "origin/main"):
                raise RuntimeError("Push returned success but remote confirmation failed")
            return {"status": "pushed", "date": day.isoformat(), "completed": completed}
        check_day(day)
        remote_after = git.fetch()
        if attempt == 2 or remote_after == remote_before:
            raise RuntimeError("Non-force push failed; unpublished art commits remain local. "
                               + result.stderr.strip()[:1000])
    raise RuntimeError("Push retries exhausted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write only on the actual scheduled UTC day")
    parser.add_argument("--push", action="store_true", help="Push with normal fast-forward protection; requires --apply")
    parser.add_argument("--at", metavar="YYYY-MM-DD", help="Preview a date; incompatible with --apply")
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent
    try:
        result = execute(directory.parent.parent, directory / "plan.json", **vars(args))
    except (RuntimeError, ValueError, KeyError, OSError, subprocess.SubprocessError, urllib.error.URLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
