#!/usr/bin/env bash

set -euo pipefail

: "${APPLE_EMAIL:?APPLE_EMAIL is required for notarization}"
: "${APPLE_PASSWORD:?APPLE_PASSWORD is required for notarization}"
: "${APPLE_TEAMID:?APPLE_TEAMID is required for notarization}"
: "${APPLE_PERSONALID:?APPLE_PERSONALID is required for notarization}"

applemail=$APPLE_EMAIL
password=$APPLE_PASSWORD
teamid=$APPLE_TEAMID
keychain_profile="${CHRONIO_NOTARY_PROFILE:-chronio-$APPLE_PERSONALID}"
app="${CHRONIO_APP_PATH:-dist/Chronio.app}"
dmg="${CHRONIO_DMG_PATH:-dist/Chronio.dmg}"

notarize() {
    dist=$1
    echo "Notarization: submitting $dist"
    xcrun notarytool submit "$dist" --keychain-profile "$keychain_profile" --wait
}

staple() {
    dist=$1
    xcrun stapler staple "$dist"
}

if ! xcrun notarytool --help >/dev/null 2>&1; then
    echo "xcrun notarytool is required for Chronio notarization" >&2
    exit 1
fi

xcrun notarytool store-credentials "$keychain_profile" \
    --apple-id "$applemail" \
    --team-id "$teamid" \
    --password "$password"

if test -d "$app"; then
    echo "Notarizing: $app"
    zip="$app.zip"
    ditto -c -k --keepParent "$app" "$zip"
    notarize "$zip"
    staple "$app"
else
    echo "Skipping missing app bundle: $app"
fi

if test -f "$dmg"; then
    echo "Notarizing: $dmg"
    notarize "$dmg"
    staple "$dmg"
else
    echo "Skipping missing disk image: $dmg"
fi
