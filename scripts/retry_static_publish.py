"""Safely retry a rejected static-site publish against the newest main commit.

Never rebase old generated HTML across data revisions. Refresh the relevant
source, revalidate, rebuild and create a new commit from latest origin/main.
Called only after an optimistic publisher's non-fast-forward push failed.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED = ["index.html", "404.html", "api/v1", "feeds",
             "feed.xml", "sitemap.xml", "robots.txt"]
DATA_FILES = {
    "hot": ["data/hot.json", "data/hot-policy.json", "data/hot-inbox.json"],
    "activity": ["data/activity-radar.json"],
    "tibo": [],
}


def cmd(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def rebuild(mode: str, output: Path) -> None:
    if mode == "hot":
        cmd(sys.executable, "scripts/hot_sync.py")
    elif mode == "activity":
        cmd(sys.executable, "scripts/collect_activity_radar.py")
    # Tibo UI is a compiled view of already committed reset events; never
    # refetch X posts or synthesize a new social-media event from an old run.
    cmd(sys.executable, "-m", "unittest", "tests.test_build", "tests.test_hot")
    cmd(sys.executable, "scripts/build.py", "--out", str(output),
        "--repo", "momo-hub-learn/frontierlog",
        "--base-url", "https://momo-hub-learn.github.io/frontierlog/")
    for name in PUBLISHED:
        src = output / name
        dest = ROOT / name
        if src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)


def publish(mode: str, attempts: int = 3) -> None:
    if mode not in DATA_FILES:
        raise ValueError("Unsupported publication type")
    if not 1 <= attempts <= 5:
        raise ValueError("Invalid retry count")
    changed = DATA_FILES[mode] + PUBLISHED
    for i in range(1, attempts + 1):
        print(f"Rebuild latest main / {mode} / retry {i} of {attempts}", flush=True)
        cmd("git", "fetch", "origin", "main")
        cmd("git", "reset", "--hard", "origin/main")
        with tempfile.TemporaryDirectory(prefix="frontierlog-static-") as td:
            rebuild(mode, Path(td))
        cmd("git", "add", "--", *changed)
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"],
                              cwd=ROOT, check=False)
        if diff.returncode == 0:
            print("Latest main already contains the verified generated outputs.")
            return
        if diff.returncode != 1:
            raise RuntimeError("Could not inspect staged publication changes")
        cmd("git", "config", "user.name", "github-actions[bot]")
        cmd("git", "config", "user.email",
            "41898282+github-actions[bot]@users.noreply.github.com")
        cmd("git", "commit", "-m", "Rebuild verified site after concurrent update")
        pushed = subprocess.run(["git", "push", "origin", "HEAD:main"],
                                cwd=ROOT, check=False)
        if pushed.returncode == 0:
            print("Published rebuilt snapshot on latest main.")
            return
    raise RuntimeError("Failed to publish verified snapshot after push retries")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=DATA_FILES.keys(), required=True)
    p.add_argument("--attempts", type=int, default=3)
    args = p.parse_args()
    publish(args.mode, args.attempts)


if __name__ == "__main__":
    main()
