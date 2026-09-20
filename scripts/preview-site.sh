#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
host="${HUGO_BIND:-0.0.0.0}"
port="${HUGO_PORT:-1313}"

if command -v hugo >/dev/null 2>&1; then
  hugo_bin=$(command -v hugo)
elif test -x "$HOME/.local/bin/hugo"; then
  hugo_bin="$HOME/.local/bin/hugo"
else
  printf 'Hugo is not installed. Run scripts/install-hugo-wsl.sh first.\n' >&2
  exit 1
fi

cd "$repo_dir"
printf 'Preview: http://localhost:%s/\n' "$port"
exec "$hugo_bin" server --buildFuture --disableFastRender --bind "$host" --port "$port"
