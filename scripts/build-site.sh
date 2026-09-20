#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
site_dir="${1:-dist}"

if command -v hugo >/dev/null 2>&1; then
  hugo_bin=$(command -v hugo)
elif test -x "$HOME/.local/bin/hugo"; then
  hugo_bin="$HOME/.local/bin/hugo"
else
  printf 'Hugo is not installed. Run scripts/install-hugo-wsl.sh first.\n' >&2
  exit 1
fi

cd "$repo_dir"
python3 scripts/validate-content.py --repo "$repo_dir"
rm -rf -- "$site_dir"
"$hugo_bin" --buildFuture --destination "$site_dir"
sh scripts/seo-audit.sh "$site_dir" src/spr

page_count=$(find "$site_dir" -type f -name '*.html' | wc -l | tr -d ' ')
printf 'Build passed: %s HTML pages in %s/%s\n' "$page_count" "$repo_dir" "$site_dir"
