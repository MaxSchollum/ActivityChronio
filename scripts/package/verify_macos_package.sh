#!/usr/bin/env bash

set -euo pipefail

app="${CHRONIO_APP_PATH:-dist/Chronio.app}"
dmg="${CHRONIO_DMG_PATH:-dist/Chronio.dmg}"
allow_gatekeeper_reject="${CHRONIO_ALLOW_GATEKEEPER_REJECT:-0}"
mount_dir=""

cleanup() {
  if [ -n "$mount_dir" ] && mount | grep -q "$mount_dir"; then
    hdiutil detach "$mount_dir" >/dev/null
  fi
  if [ -n "$mount_dir" ]; then
    rmdir "$mount_dir" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if [ "$(uname -s)" != "Darwin" ]; then
  echo "Chronio macOS package verification must run on macOS." >&2
  exit 1
fi

if [ ! -d "$app" ]; then
  echo "Missing app bundle: $app" >&2
  exit 1
fi

if [ ! -f "$dmg" ]; then
  echo "Missing disk image: $dmg" >&2
  exit 1
fi

echo "== Chronio package identity =="
/usr/libexec/PlistBuddy -c "Print :CFBundleName" "$app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Print :CFBundleIdentifier" "$app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Print :LSUIElement" "$app/Contents/Info.plist"

echo
echo "== Codesign verification =="
codesign --verify --deep --strict --verbose=2 "$app"
sign_details="$(codesign -dv --verbose=4 "$app" 2>&1)"
printf '%s\n' "$sign_details" | grep -E "^(Authority|TeamIdentifier|Signature|Identifier)=" || true
if [ "$allow_gatekeeper_reject" != "1" ]; then
  if printf '%s\n' "$sign_details" | grep -q "^Signature=adhoc$"; then
    echo "Release package is ad-hoc signed." >&2
    exit 1
  fi
  if printf '%s\n' "$sign_details" | grep -q "^TeamIdentifier=not set$"; then
    echo "Release package has no TeamIdentifier." >&2
    exit 1
  fi
  if ! printf '%s\n' "$sign_details" | grep -q "^Authority=Developer ID Application:"; then
    echo "Release package is not signed with a Developer ID Application identity." >&2
    exit 1
  fi
fi

echo
echo "== Gatekeeper assessment =="
if spctl -a -vv -t open "$app"; then
  echo "Gatekeeper assessment passed for $app"
else
  status=$?
  if [ "$allow_gatekeeper_reject" = "1" ]; then
    echo "Gatekeeper assessment failed for $app, continuing because CHRONIO_ALLOW_GATEKEEPER_REJECT=1" >&2
  else
    echo "Gatekeeper assessment failed for $app" >&2
    echo "A Developer ID signed and notarized artifact is required for release acceptance." >&2
    exit "$status"
  fi
fi

echo
echo "== Notarization ticket validation =="
if xcrun stapler validate "$app"; then
  echo "Stapled notarization ticket validated for $app"
else
  status=$?
  if [ "$allow_gatekeeper_reject" = "1" ]; then
    echo "Stapler validation failed for $app, continuing because CHRONIO_ALLOW_GATEKEEPER_REJECT=1" >&2
  else
    echo "Stapler validation failed for $app" >&2
    exit "$status"
  fi
fi

echo
echo "== DMG verification =="
hdiutil verify "$dmg"
if xcrun stapler validate "$dmg"; then
  echo "Stapled notarization ticket validated for $dmg"
else
  status=$?
  if [ "$allow_gatekeeper_reject" = "1" ]; then
    echo "Stapler validation failed for $dmg, continuing because CHRONIO_ALLOW_GATEKEEPER_REJECT=1" >&2
  else
    echo "Stapler validation failed for $dmg" >&2
    exit "$status"
  fi
fi
mount_dir="$(mktemp -d /tmp/chronio-dmg.XXXXXX)"
hdiutil attach "$dmg" -nobrowse -readonly -mountpoint "$mount_dir" >/dev/null
if [ ! -d "$mount_dir/Chronio.app" ]; then
  echo "Mounted DMG does not contain Chronio.app" >&2
  exit 1
fi
test -e "$mount_dir/Applications" || test -L "$mount_dir/Applications"
codesign --verify --deep --strict --verbose=2 "$mount_dir/Chronio.app"

echo
echo "Chronio package verification complete."
