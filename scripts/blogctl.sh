#!/bin/sh
set -eu

script_path=$(readlink -f "$0")
repo_dir=$(CDPATH= cd -- "$(dirname -- "$script_path")/.." && pwd)

usage() {
  cat <<'EOF'
Usage: grepcode-blog <command> [arguments]

Commands:
  install                         Install the pinned Hugo Extended release.
  build                           Build and audit the complete site.
  new <slug> <title> [options]    Create the next numbered SPR article.
  preview                         Serve a local preview on port 1313.
  status                          Show branch, remote and concise Git status.
  publish "message" path [...]    Build, audit, commit listed paths and push.
EOF
}

command_name="${1:-help}"
case "$command_name" in
  install)
    exec sh "$repo_dir/scripts/install-hugo-wsl.sh"
    ;;
  build)
    exec sh "$repo_dir/scripts/build-site.sh"
    ;;
  new)
    shift
    exec python3 "$repo_dir/scripts/new-spr.py" "$@"
    ;;
  preview)
    exec sh "$repo_dir/scripts/preview-site.sh"
    ;;
  status)
    printf 'Repository: %s\n' "$repo_dir"
    git -C "$repo_dir" branch --show-current
    git -C "$repo_dir" remote -v
    git -C "$repo_dir" status --short
    ;;
  publish)
    shift
    exec sh "$repo_dir/scripts/publish-site.sh" "$@"
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    printf 'Unknown command: %s\n\n' "$command_name" >&2
    usage >&2
    exit 2
    ;;
esac
