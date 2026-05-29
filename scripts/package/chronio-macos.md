# Chronio macOS Packaging

Issue #16 turns the ActivityWatch bundle into a Chronio macOS product in
scoped slices. The first slice chooses the packaged app identity and keeps the
existing ActivityWatch runtime layout intact so the package can be tested
before identity-sensitive distribution work is added.

## Packaged Identity

| Surface | Value |
| --- | --- |
| App bundle | `Chronio.app` |
| Disk image | `Chronio.dmg` |
| Disk image volume name | `Chronio` |
| Bundle identifier | `com.maxschollum.chronio` |
| Bundle name and display name | `Chronio` |
| Bundle icon asset | Current `aw-qt/media/logo/logo.icns` placeholder |
| Menu bar glyph | Chronio clock mask drawn by `aw_qt.trayicon` on macOS |
| Dock behavior | `LSUIElement = true` |

The executable and helper names inside `Chronio.app` intentionally remain the
ActivityWatch module names. `Contents/MacOS/aw-qt` is the app executable and
the bundled `aw-server`, `aw-watcher-afk`, `aw-watcher-window`,
`aw-watcher-input`, and `aw-notify` helpers remain discoverable by the existing
module manager. Chronio uses the Python/Flask `aw-server` path; `aw-server-rust`
is not part of the active macOS package.

## Server Build Stance

Chronio V2 does not need `aw-server-rust`. The packaged app starts the
Python/Flask `aw-server`, serves the Vue UI from that server, and bundles the
watchers used by the Chronio daily review workflow. `aw-server-rust` remains an
upstream ActivityWatch component only; it is not in Chronio's default
build/test/package surface.

The bundle keeps the current ActivityWatch data, config, watcher bucket, and
helper paths for this slice. Renaming those paths would create a migration
problem without helping macOS distribution.

## Local Build

Run the unsigned package build on macOS with the repository Python packaging
toolchain installed. The V2 handoff artifact was built with Python 3.9:

```sh
poetry install --no-root
make build AW_EXTRAS=true
make dist/Chronio.dmg
```

That target builds `Chronio.app` with PyInstaller and then builds a DMG with a
drag-to-Applications symlink. The produced local app and DMG are unsigned:

| Artifact | Path |
| --- | --- |
| App bundle | `dist/Chronio.app` |
| Disk image | `dist/Chronio.dmg` |

Use `localhost:5600` for daily frontend iteration and normal Chronio UI QA.
Use the packaged app for issue #16 validation, macOS permission prompts,
watcher startup, and install behavior because those flows depend on the app
bundle identity.

The expected V2 packaged UX is the Chronio menu bar app launching the local
Chronio UI/server. It is not a standalone document-style app window. The app
should run as a menu bar utility (`LSUIElement = true`), start the local
server/watchers, and expose Chronio through the local UI.

## Verification Commands

Use the package verifier for the reviewed artifact:

```sh
make verify-macos-package
```

For an unsigned local QA artifact, the same verifier can document the exact
Gatekeeper blocker without treating it as a release pass:

```sh
CHRONIO_ALLOW_GATEKEEPER_REJECT=1 make verify-macos-package
```

The release-acceptance run must not set `CHRONIO_ALLOW_GATEKEEPER_REJECT`.
It is expected to pass `codesign --verify`, `spctl -a -vv -t open`, DMG
verification, stapled notarization validation, DMG mount validation, and
mounted-app `codesign --verify`.

For release builds, import the Developer ID certificate first and resolve the
signing identity before building:

```sh
export CHRONIO_REQUIRE_DEVELOPER_ID=1
export CHRONIO_CODESIGN_IDENTITY="$(./scripts/package/resolve_macos_signing_identity.sh)"
make dist/Chronio.dmg
make dist/notarize
make verify-macos-package
```

## Permission Regrant Test Plan

The bundle identifier and signed app identity change from ActivityWatch to
Chronio. Validate the packaged app as a fresh macOS privacy subject:

1. Install `Chronio.app` from the DMG into `/Applications`.
2. Launch it and confirm the menu bar icon appears without a Dock icon.
3. Grant or regrant Accessibility permission when window tracking needs it.
4. Grant or regrant Screen Recording permission for screenshot capture once
   that watcher is packaged.
5. Quit and relaunch from `/Applications`.
6. Confirm the server, AFK watcher, and window watcher start and append recent
   events while existing historical ActivityWatch data remains readable.

## Distribution Blockers

Gatekeeper-clean distribution cannot be claimed from an unsigned local build.
The signing and notarization CI path needs all of the following external Apple
Developer inputs before the issue acceptance criteria can be verified:

- Active Apple Developer Program membership.
- A Developer ID Application signing identity importable by CI as
  `CERTIFICATE_MACOS_P12_BASE64` and `CERTIFICATE_MACOS_P12_PASSWORD`.
- Optionally, a signing identity selector in `APPLE_PERSONALID`. If it is not
  set, CI resolves the first imported `Developer ID Application` identity.
- Notarization credentials in `APPLE_EMAIL`, `APPLE_PASSWORD`, and
  `APPLE_TEAMID` for `xcrun notarytool`.

The CI script only attempts the signing/notarization branch when Apple
credentials are present. With credentials, the build fails unless it can resolve
a `Developer ID Application` identity, notarize and staple the app/DMG, and pass
`make verify-macos-package`. Without them, build output is useful for local
packaging tests but it must not be described as signed or notarized.

Signed/notarized install validation remains blocked until the Apple Developer
inputs above are available. The local unsigned package path is the QA artifact
until that release path can be verified.
