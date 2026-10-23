#!/usr/bin/env bash
set -euo pipefail

python -m pip install playwright==1.55.0

browser_bin=''
for candidate in google-chrome-stable google-chrome chromium chromium-browser; do
  if command -v "$candidate" >/dev/null 2>&1; then
    browser_bin="$(command -v "$candidate")"
    break
  fi
done

if [[ -z "$browser_bin" ]]; then
  python -m playwright install chromium
  browser_bin="$(find "$HOME/.cache/ms-playwright" -type f -path '*/chrome-linux*/chrome' -print -quit)"
fi

test -x "$browser_bin"
echo "CHROMIUM_EXECUTABLE=$browser_bin" >> "$GITHUB_ENV"
"$browser_bin" --version

if ! fc-list :lang=zh | grep -q .; then
  sudo apt-get update
  sudo apt-get install -y --no-install-recommends fonts-noto-cjk
fi
