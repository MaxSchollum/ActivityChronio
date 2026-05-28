#!/usr/bin/env bash

set -euo pipefail

selector="${CHRONIO_CODESIGN_IDENTITY:-${APPLE_PERSONALID:-}}"
require="${CHRONIO_REQUIRE_DEVELOPER_ID:-0}"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "Chronio macOS signing identity resolution must run on macOS." >&2
  exit 1
fi

identities="$(security find-identity -v -p codesigning || true)"

if [ -n "$selector" ]; then
  match="$(
    printf '%s\n' "$identities" |
      awk -F '"' -v selector="$selector" '
        /Developer ID Application/ && index($0, selector) { print $2; exit }
      '
  )"
  if [ -n "$match" ]; then
    printf '%s\n' "$match"
    exit 0
  fi

  if [ "$require" = "1" ]; then
    echo "No Developer ID Application identity matched selector: $selector" >&2
    echo "$identities" >&2
    exit 1
  fi

  printf '%s\n' "$selector"
  exit 0
fi

match="$(
  printf '%s\n' "$identities" |
    awk -F '"' '/Developer ID Application/ { print $2; exit }'
)"

if [ -n "$match" ]; then
  printf '%s\n' "$match"
  exit 0
fi

if [ "$require" = "1" ]; then
  echo "No Developer ID Application signing identity is available." >&2
  echo "$identities" >&2
  exit 1
fi

exit 0
