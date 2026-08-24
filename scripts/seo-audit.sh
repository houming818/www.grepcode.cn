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

bad_lang=$(find "$site_dir" -type f -name '*.html' -exec grep -L '<html lang="zh-cn"' {} + || true)
test -z "$bad_lang" || fail "HTML language is not zh-cn:\n$bad_lang"

noindex=$(find "$site_dir" -type f -name '*.html' -exec grep -l 'name="robots" content="noindex' {} + || true)
test -z "$noindex" || fail "production pages contain noindex:\n$noindex"

missing_description=$(find "$site_dir/spr" -type f -name '*.html' -exec grep -L '<meta name="description"' {} + || true)
test -z "$missing_description" || fail "SPR pages missing descriptions:\n$missing_description"

missing_canonical=$(find "$site_dir/spr" -type f -name '*.html' -exec grep -L 'rel="canonical"' {} + || true)
test -z "$missing_canonical" || fail "SPR pages missing canonical URLs:\n$missing_canonical"

latest="$site_dir/spr/085-treeheap-fold-energy-and-gradient-pressure.html"
grep -q 'property="og:image"' "$latest" || fail "latest SPR article has no Open Graph image"
grep -q '"@type":"BlogPosting"\|"@type": "BlogPosting"' "$latest" ||
  fail "latest SPR article has no BlogPosting JSON-LD"

printf 'SEO audit passed: language, crawl files, metadata, image and latest SPR discovery are valid.\n'
