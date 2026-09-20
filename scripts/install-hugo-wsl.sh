#!/bin/sh
set -eu

version="${HUGO_VERSION:-0.146.7}"
archive="hugo_extended_${version}_linux-amd64.tar.gz"
base_url="https://github.com/gohugoio/hugo/releases/download/v${version}"
install_root="${XDG_DATA_HOME:-$HOME/.local/share}/grepcode-blog/hugo/$version"
bin_dir="${HOME}/.local/bin"
tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT HUP INT TERM

mkdir -p "$install_root" "$bin_dir"

if test -x "$install_root/hugo" && "$install_root/hugo" version | grep -q "hugo v${version}"; then
  ln -sfn "$install_root/hugo" "$bin_dir/hugo"
  printf 'Already installed: %s\n' "$install_root/hugo"
  "$bin_dir/hugo" version
  exit 0
fi

printf 'Downloading Hugo Extended %s...\n' "$version"
curl -fsSL --retry 3 --retry-delay 2 \
  -o "$tmp_dir/$archive" "$base_url/$archive"
curl -fsSL --retry 3 --retry-delay 2 \
  -o "$tmp_dir/hugo_checksums.txt" "$base_url/hugo_${version}_checksums.txt"

expected=$(awk -v file="$archive" '$2 == file { print $1; exit }' "$tmp_dir/hugo_checksums.txt")
test -n "$expected" || {
  printf 'Checksum entry not found for %s\n' "$archive" >&2
  exit 1
}
actual=$(sha256sum "$tmp_dir/$archive" | awk '{ print $1 }')
test "$actual" = "$expected" || {
  printf 'Checksum mismatch for %s\n' "$archive" >&2
  exit 1
}

tar -xzf "$tmp_dir/$archive" -C "$install_root" hugo LICENSE README.md
ln -sfn "$install_root/hugo" "$bin_dir/hugo"

printf 'Installed: %s\n' "$install_root/hugo"
"$bin_dir/hugo" version
case ":$PATH:" in
  *":$bin_dir:"*) ;;
  *) printf 'Add this line to your shell profile: export PATH="$HOME/.local/bin:$PATH"\n' ;;
esac
