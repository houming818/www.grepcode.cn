#!/bin/sh
set -eu

site_dir="${1:-dist}"

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
grep -q '085-treeheap-fold-energy-and-gradient-pressure.html' "$site_dir/sitemap.xml" ||
  fail "latest SPR article is absent from sitemap.xml"
grep -q '085-treeheap-fold-energy-and-gradient-pressure.html' "$site_dir/llms.txt" ||
  fail "latest SPR article is absent from llms.txt"

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

latest="$site_dir/spr/085-treeheap-fold-energy-and-gradient-pressure.html"
grep -q 'property="og:image"' "$latest" || fail "latest SPR article has no Open Graph image"
grep -q '"@type":"BlogPosting"\|"@type": "BlogPosting"' "$latest" ||
  fail "latest SPR article has no BlogPosting JSON-LD"

printf 'SEO audit passed: language, crawl files, metadata, image and latest SPR discovery are valid.\n'
