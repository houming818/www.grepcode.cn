#!/bin/sh
set -eu

usage() {
  cat >&2 <<'EOF'
Usage:
  scripts/publish-site.sh "commit message" path [path ...]

Only the explicitly listed paths are staged. The script builds and audits the
site before committing, rejects staged secrets, and pushes the current main
branch to origin.
EOF
  exit 2
}

test "$#" -ge 2 || usage
message=$1
shift

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_dir"

branch=$(git branch --show-current)
test "$branch" = main || {
  printf 'Publishing is allowed only from main; current branch: %s\n' "$branch" >&2
  exit 1
}

git diff --cached --quiet || {
  printf 'Publishing requires an empty staging area; commit or unstage existing entries first.\n' >&2
  exit 1
}

sh scripts/build-site.sh

for path in "$@"; do
  test -e "$path" || {
    printf 'Publish path does not exist: %s\n' "$path" >&2
    exit 1
  }
done

git add -- "$@"
git diff --cached --quiet && {
  printf 'Nothing staged from the requested publish paths.\n' >&2
  exit 1
}

staged_names=$(git diff --cached --name-only)
if printf '%s\n' "$staged_names" | grep -Eiq '(^|/)(\.env($|\.)|id_[er]sa|credentials?|secrets?|.*\.(pem|key|p12|pfx))$'; then
  printf 'Refusing to publish a staged path that looks like a credential.\n' >&2
  git reset -q -- "$@"
  exit 1
fi

if git diff --cached --no-ext-diff --text | grep -Eiq "(AKIA[0-9A-Z]{16}|BEGIN (RSA |OPENSSH )?PRIVATE KEY|(secret[_-]?(key|id)|access[_-]?key)[[:space:]]*[:=][[:space:]]*['\"]?[A-Za-z0-9/+_-]{16,})"; then
  printf 'Refusing to publish: staged content may contain a credential.\n' >&2
  git reset -q -- "$@"
  exit 1
fi

printf 'Files selected for publication:\n%s\n' "$staged_names"
git commit -m "$message"
git push origin main
printf 'Push complete. Gitea CI will build, audit and deploy the site.\n'
