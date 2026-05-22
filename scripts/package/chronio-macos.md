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
the bundled `aw-server`, `aw-server-rust`, `aw-watcher-afk`,
`aw-watcher-window`, `aw-watcher-input`, and `aw-notify` helpers remain
discoverable by the existing module manager.

The bundle keeps the current ActivityWatch data, config, watcher bucket, and
helper paths for this slice. Renaming those paths would create a migration
problem without helping macOS distribution.

## Local Build

Run the unsigned package build on macOS with the repository Python packaging
toolchain installed. The V2 handoff artifact was built with Python 3.9:

```sh
poetry install --no-root
make build AW_EXTRAS=true SKIP_SERVER_RUST=true
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
- The signing identity selector in `APPLE_PERSONALID`.
- Notarization credentials in `APPLE_EMAIL`, `APPLE_PASSWORD`, and
  `APPLE_TEAMID` for `xcrun notarytool`.

The current CI script only attempts the signing/notarization branch when Apple
credentials are present. Without them, build output is useful for local
packaging tests but it must not be described as signed or notarized.

Signed/notarized install validation remains blocked until the Apple Developer
inputs above are available. The local unsigned package path is the QA artifact
until that release path can be verified.
