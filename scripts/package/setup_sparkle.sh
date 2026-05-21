#!/usr/bin/env bash
# setup_sparkle.sh — download Sparkle.framework into Frameworks/
#
# Usage:
#   ./scripts/package/setup_sparkle.sh [VERSION]
#
# Downloads the specified Sparkle release (default: 2.7.5) from GitHub and
# extracts Sparkle.framework to Frameworks/Sparkle.framework at the repo root.
#
# After running this script:
#   • `make dist/Chronio.app` will pick up the framework via aw.spec and
#     copy it into Chronio.app/Contents/Frameworks/.
#   • The SUPublicEDKey printed below must be pasted into aw.spec's info_plist
#     so the running app can verify update signatures.
#
# Requires: curl, tar, unzip (all pre-installed on macOS).

set -euo pipefail

SPARKLE_VERSION="${1:-2.7.5}"
SPARKLE_URL="https://github.com/sparkle-project/Sparkle/releases/download/${SPARKLE_VERSION}/Sparkle-${SPARKLE_VERSION}.tar.xz"
FRAMEWORKS_DIR="$(cd "$(dirname "$0")/../.." && pwd)/Frameworks"

echo "==> Setting up Sparkle ${SPARKLE_VERSION}"
echo "    Download: ${SPARKLE_URL}"
echo "    Target:   ${FRAMEWORKS_DIR}/Sparkle.framework"
echo

mkdir -p "${FRAMEWORKS_DIR}"

# Download only if not already present at the right version
VERSION_FILE="${FRAMEWORKS_DIR}/.sparkle_version"
if [[ -d "${FRAMEWORKS_DIR}/Sparkle.framework" ]] && [[ -f "${VERSION_FILE}" ]] && [[ "$(cat "${VERSION_FILE}")" == "${SPARKLE_VERSION}" ]]; then
    echo "Sparkle ${SPARKLE_VERSION} already installed. Skipping download."
else
    TMP=$(mktemp -d)
    trap 'rm -rf "${TMP}"' EXIT

    echo "Downloading…"
    curl -L --progress-bar "${SPARKLE_URL}" -o "${TMP}/Sparkle.tar.xz"

    echo "Extracting…"
    tar -xJf "${TMP}/Sparkle.tar.xz" -C "${TMP}"

    # The archive contains Sparkle.framework at its root
    if [[ ! -d "${TMP}/Sparkle.framework" ]]; then
        echo "ERROR: Sparkle.framework not found in archive" >&2
        exit 1
    fi

    rm -rf "${FRAMEWORKS_DIR}/Sparkle.framework"
    cp -R "${TMP}/Sparkle.framework" "${FRAMEWORKS_DIR}/Sparkle.framework"
    echo "${SPARKLE_VERSION}" > "${VERSION_FILE}"
    echo "Sparkle.framework installed."
fi

# ── Generate Ed25519 keypair (if not already present) ─────────────────────
KEYS_DIR="${FRAMEWORKS_DIR}/.sparkle_keys"
PRIV_KEY_FILE="${KEYS_DIR}/sparkle_private_key"
PUB_KEY_FILE="${KEYS_DIR}/sparkle_public_key"
GENERATE_KEYS="${FRAMEWORKS_DIR}/Sparkle.framework/Versions/B/Resources/generate_keys"

if [[ ! -f "${PRIV_KEY_FILE}" ]]; then
    if [[ ! -x "${GENERATE_KEYS}" ]]; then
        echo "WARNING: generate_keys tool not found at ${GENERATE_KEYS}" >&2
        echo "         Manually generate a keypair and set SUPublicEDKey in aw.spec." >&2
    else
        mkdir -p "${KEYS_DIR}"
        chmod 700 "${KEYS_DIR}"
        echo
        echo "==> Generating Sparkle Ed25519 keypair (first-time setup)…"
        "${GENERATE_KEYS}" --account "com.maxschollum.chronio" \
            --private-key-file "${PRIV_KEY_FILE}" \
            --public-key-file "${PUB_KEY_FILE}" 2>/dev/null || true

        if [[ -f "${PUB_KEY_FILE}" ]]; then
            PUB_KEY=$(cat "${PUB_KEY_FILE}")
            echo
            echo "╔══════════════════════════════════════════════════════════════╗"
            echo "║  Add this public key to aw.spec info_plist:                  ║"
            echo "║                                                              ║"
            echo "║  \"SUPublicEDKey\": \"${PUB_KEY}\"  ║"
            echo "╚══════════════════════════════════════════════════════════════╝"
            echo
            echo "  Private key → ${PRIV_KEY_FILE}"
            echo "  Keep the private key secret and back it up safely."
        fi
    fi
else
    echo
    echo "Existing Ed25519 keypair found at ${KEYS_DIR}"
    [[ -f "${PUB_KEY_FILE}" ]] && echo "  Public key: $(cat "${PUB_KEY_FILE}")"
fi

echo
echo "Done.  Run 'make dist/Chronio.app' to build the bundle with Sparkle."
