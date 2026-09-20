#!/bin/sh
set -eu

site_dir="${1:-dist}"
source_dir="${2:-src/spr}"

fail() {
  printf 'SEO audit failed: %s\n' "$1" >&2
  exit 1
}

test -s "$site_dir/sitemap.xml" || fail "missing sitemap.xml"
test -s "$site_dir/robots.txt" || fail "missing robots.txt"
test -s "$site_dir/llms.txt" || fail "missing llms.txt"
test -s "$site_dir/img/treeheap-research-series.png" || fail "missing default research image"

grep -q '^Sitemap: https://www.grepcode.cn/sitemap.xml' "$site_dir/robots.txt" ||
  fail "robots.txt does not advertise sitemap.xml"
latest_slug="${LATEST_SPR_SLUG:-}"
if test -z "$latest_slug"; then
  latest_slug=$(
    for article in "$source_dir"/[0-9][0-9][0-9]-*.md; do
      test -f "$article" && basename "$article"
    done |
      LC_ALL=C sort |
      tail -n 1 |
      sed 's/\.md$//'
  )
fi
test -n "$latest_slug" || fail "cannot determine the latest SPR article"

grep -q "$latest_slug.html" "$site_dir/sitemap.xml" ||
  fail "latest SPR article ($latest_slug) is absent from sitemap.xml"
grep -q "$latest_slug.html" "$site_dir/llms.txt" ||
  fail "latest SPR article ($latest_slug) is absent from llms.txt"
grep -Eq 'treeheap-paper(\.html|/index\.html)' "$site_dir/llms.txt" ||
  fail "TreeHeap paper reading path is absent from llms.txt"
grep -q 'treeheap-paper/001-treeheap-emergent-protocol.html' "$site_dir/llms.txt" ||
  fail "TreeHeap full paper is absent from llms.txt"
grep -q '<title>.*TreeHeap.*</title>' "$site_dir/index.html" ||
  fail "home page title does not describe the TreeHeap research series"

paper_landing="$site_dir/treeheap-paper/index.html"
if ! test -f "$paper_landing"; then
  paper_landing="$site_dir/treeheap-paper.html"
fi
test -f "$paper_landing" || fail "TreeHeap paper landing page was not generated"
grep -q '077-treeheap-paper-origin-and-evolution.html' "$paper_landing" ||
  fail "TreeHeap paper landing page does not link to the first chapter"
grep -q '001-treeheap-emergent-protocol.html' "$paper_landing" ||
  fail "TreeHeap paper landing page does not link to the full paper"

full_paper="$site_dir/treeheap-paper/001-treeheap-emergent-protocol.html"
test -f "$full_paper" || fail "TreeHeap full paper was not generated"
grep -q '<meta name="description"' "$full_paper" ||
  fail "TreeHeap full paper has no meta description"
grep -q 'property="og:image"' "$full_paper" ||
  fail "TreeHeap full paper has no Open Graph image"

pages=$(mktemp)
issues=$(mktemp)
trap 'rm -f "$pages" "$issues"' EXIT
find "$site_dir" -type f -name '*.html' >"$pages"

while IFS= read -r page; do
  # Hugo alias pages are immediate redirect stubs, not indexable content pages.
  if grep -qi 'http-equiv="refresh"' "$page"; then
    continue
  fi

  grep -q '<html lang="zh-cn"' "$page" || printf 'wrong language: %s\n' "$page" >>"$issues"
  if grep -q 'name="robots" content="noindex' "$page"; then
    printf 'unexpected noindex: %s\n' "$page" >>"$issues"
  fi

  case "$page" in
    "$site_dir"/spr/*.html)
      grep -q '<meta name="description"' "$page" || printf 'missing description: %s\n' "$page" >>"$issues"
      grep -q 'rel="canonical"' "$page" || printf 'missing canonical: %s\n' "$page" >>"$issues"
      ;;
  esac
done <"$pages"

if test -s "$issues"; then
  cat "$issues" >&2
  fail "one or more generated HTML pages violate the SEO contract"
fi

latest="$site_dir/spr/$latest_slug.html"
test -f "$latest" || fail "latest SPR article was not generated: $latest"
grep -q 'property="og:image"' "$latest" || fail "latest SPR article has no Open Graph image"
grep -q '"@type":"BlogPosting"\|"@type": "BlogPosting"' "$latest" ||
  fail "latest SPR article has no BlogPosting JSON-LD"

printf 'SEO audit passed: %s and all indexed pages satisfy the publishing contract.\n' "$latest_slug"
