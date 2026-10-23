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

first_cjk_font="$(fc-list :lang=zh | sed -n '1p')"
if [[ -z "$first_cjk_font" ]]; then
  sudo timeout 120s apt-get update
  sudo timeout 120s apt-get install -y --no-install-recommends fonts-wqy-zenhei
fi
