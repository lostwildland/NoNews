#!/bin/bash
set -euo pipefail

# Explicit preparation for development and release packaging; never run at app launch.
root="$(cd "$(dirname "$0")" && pwd)"
case "$(uname -m)" in
  arm64) arch=aarch64; checksum=8392b6ea51d94391befb2c31ebe75463f045d0b69dfcf5e1bb3234e1f5fa3405; notices_checksum=5706f1fdf82f7ea10b56a9b9cbadfa5f372010568a9794f19e0af4c48d975f34 ;;
  x86_64) arch=x86_64; checksum=7412c19d896c99431b74a18a5643e110449a7f9590fbab179c3e5ab27b9aa9e3; notices_checksum=3b07eb16ae3d4f15e71ba5173f5ebf98156a4fbb1fc62a531b680efadff28feb ;;
  *) printf '%s\n' 'Unsupported architecture' >&2; exit 1 ;;
esac
name="cpython-3.13.18+20261026-${arch}-apple-darwin-install_only_stripped.tar.gz"
url="https://github.com/astral-sh/python-build-standalone/releases/download/20261026/${name/+/%2B}"
destination="${1:-$root/.prepared}"
if [ -e "$destination" ]; then
  printf '%s\n' 'Prepared destination already exists; choose a clean worktree or remove it yourself.' >&2
  exit 1
fi
tmp="$(mktemp -d "${TMPDIR:-/tmp}/nonews-runtime.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
curl --fail --location --silent --show-error --connect-timeout 15 --max-time 180 "$url" -o "$tmp/runtime.tar.gz"
printf '%s  %s\n' "$checksum" "$tmp/runtime.tar.gz" | shasum -a 256 --check --status || { printf '%s\n' 'Runtime checksum mismatch' >&2; exit 1; }
notices="cpython-3.13.18%2B20261026-${arch}-apple-darwin-pgo%2Blto-full.tar.zst"
curl --fail --location --silent --show-error --connect-timeout 15 --max-time 180 "https://github.com/astral-sh/python-build-standalone/releases/download/20261026/$notices" -o "$tmp/notices.tar.zst"
printf '%s  %s\n' "$notices_checksum" "$tmp/notices.tar.zst" | shasum -a 256 --check --status || { printf '%s\n' 'Notices checksum mismatch' >&2; exit 1; }
mkdir "$tmp/payload"
tar -xzf "$tmp/runtime.tar.gz" -C "$tmp/payload"
tar -xf "$tmp/notices.tar.zst" -C "$tmp/payload" python/licenses python/PYTHON.json
test -x "$tmp/payload/python/bin/python3"
env -i PATH=/usr/bin:/bin HOME="$tmp" "$tmp/payload/python/bin/python3" -B -I -m pip --isolated install \
  --disable-pip-version-check --no-cache-dir --only-binary=:all: --require-hashes \
  --index-url https://pypi.org/simple -r "$root/requirements.lock"
"$tmp/payload/python/bin/python3" -B -I "$root/assemble_payload.py" "$tmp/payload"
mv "$tmp/payload" "$destination"
printf '%s\n' "Prepared Python 3.13.18 ($arch) in $destination"
