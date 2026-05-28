# -*- mode: python -*-
# vi: set ft=python :

import os
import platform
import re
import shlex
import subprocess
from pathlib import Path

import aw_core
import flask_restx


def build_analysis(name, location, binaries=[], datas=[], hiddenimports=[]):
    name_py = name.replace("-", "_")
    location_candidates = [
        location / f"{name_py}/__main__.py",
        location / f"src/{name_py}/__main__.py",
    ]
    try:
        location = next(p for p in location_candidates if p.exists())
    except StopIteration:
        raise Exception(f"Could not find {name} location from {location_candidates}")

    return Analysis(
        [location],
        pathex=[],
        binaries=binaries,
        datas=datas,
        hiddenimports=hiddenimports,
        hookspath=[],
        runtime_hooks=[],
        excludes=[],
        win_no_prefer_redirects=False,
        win_private_assemblies=False,
    )


def build_collect(analysis, name, console=True):
    """Used to build the COLLECT statements for each module"""
    pyz = PYZ(analysis.pure, analysis.zipped_data)
    exe = EXE(
        pyz,
        analysis.scripts,
        exclude_binaries=True,
        name=name,
        debug=False,
        strip=False,
        upx=True,
        console=console,
        contents_directory=".",
        entitlements_file=entitlements_file,
        codesign_identity=codesign_identity,
    )
    return COLLECT(
        exe,
        analysis.binaries,
        analysis.zipfiles,
        analysis.datas,
        strip=False,
        upx=True,
        name=name,
    )


def detect_bundle_version():
    result = subprocess.run(
        shlex.split("git describe --tags --abbrev=0"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf8",
    )
    if result.returncode == 0:
        tag_version = result.stdout.strip().lstrip("v")
        if tag_version:
            return tag_version

    pyproject = Path("pyproject.toml")
    if pyproject.exists():
        match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject.read_text(), re.MULTILINE)
        if match:
            return match.group(1).lstrip("v")

    return "0.0.0"


current_release = detect_bundle_version()
print("bundling chronio version " + current_release)

# Get entitlements and codesign identity. Release builds must set
# CHRONIO_CODESIGN_IDENTITY to a Developer ID Application identity; local QA
# builds may omit it and will be ad-hoc signed by PyInstaller.
entitlements_file = Path(".") / "scripts" / "package" / "entitlements.plist"
codesign_identity = (
    os.environ.get("CHRONIO_CODESIGN_IDENTITY")
    or os.environ.get("APPLE_PERSONALID")
    or ""
).strip()
if not codesign_identity:
    if os.environ.get("CHRONIO_REQUIRE_DEVELOPER_ID") == "1":
        raise SystemExit(
            "CHRONIO_REQUIRE_DEVELOPER_ID=1 requires CHRONIO_CODESIGN_IDENTITY"
        )
    print("No Chronio codesign identity set. Local builds will not be release-signed.")

aw_core_path = Path(os.path.dirname(aw_core.__file__))
restx_path = Path(os.path.dirname(flask_restx.__file__))

aws_location = Path("aw-server")
aw_server_rust_location = Path("aw-server-rust")
aw_server_rust_bin = aw_server_rust_location / "target/package/aw-server-rust"
aw_sync_bin = aw_server_rust_location / "target/package/aw-sync"
aw_qt_location = Path("aw-qt")
awa_location = Path("aw-watcher-afk")
aww_location = Path("aw-watcher-window")
awss_location = Path("aw-watcher-screenshot")
awi_location = Path("aw-watcher-input")
aw_notify_location = Path("aw-notify")

if platform.system() == "Darwin":
    # Use the custom Chronio clock icon; fall back to the legacy AW icon if
    # the ICNS hasn't been generated yet (run scripts/package/create_icon.py).
    _chronio_icns = aw_qt_location / "media/logo/chronio.icns"
    icon = _chronio_icns if _chronio_icns.exists() else aw_qt_location / "media/logo/logo.icns"
else:
    icon = aw_qt_location / "media/logo/logo.ico"

# Sparkle.framework — optional; bundled when present (run setup_sparkle.sh).
_sparkle_fw = Path("Frameworks") / "Sparkle.framework"
_sparkle_binaries: list = []
if platform.system() == "Darwin" and _sparkle_fw.exists():
    # Copy the entire framework into Contents/Frameworks/
    _sparkle_binaries = [
        (str(_sparkle_fw / "Versions" / "B" / "Sparkle"), "Frameworks/Sparkle.framework/Versions/B"),
        (str(_sparkle_fw / "Versions" / "B" / "Resources"), "Frameworks/Sparkle.framework/Versions/B/Resources"),
    ]
    print(f"Bundling Sparkle.framework from {_sparkle_fw}")
else:
    if platform.system() == "Darwin":
        print("Sparkle.framework not found — run scripts/package/setup_sparkle.sh to enable auto-updates")

skip_rust = False
if not aw_server_rust_bin.exists():
    skip_rust = True
    print("Skipping Rust build because aw-server-rust binary not found.")


aw_qt_a = build_analysis(
    "aw-qt",
    aw_qt_location,
    binaries=([(aw_server_rust_bin, "."), (aw_sync_bin, ".")] if not skip_rust else []) + _sparkle_binaries,
    datas=[
        (aw_qt_location / "resources/aw-qt.desktop", "aw_qt/resources"),
        (aw_qt_location / "media", "aw_qt/media"),
    ],
)
aw_server_a = build_analysis(
    "aw-server",
    aws_location,
    datas=[
        (aws_location / "aw_server/static", "aw_server/static"),
        (restx_path / "templates", "flask_restx/templates"),
        (restx_path / "static", "flask_restx/static"),
        (aw_core_path / "schemas", "aw_core/schemas"),
    ],
)
aw_watcher_afk_a = build_analysis(
    "aw_watcher_afk",
    awa_location,
    hiddenimports=[
        "Xlib.keysymdef.miscellany",
        "Xlib.keysymdef.latin1",
        "Xlib.keysymdef.latin2",
        "Xlib.keysymdef.latin3",
        "Xlib.keysymdef.latin4",
        "Xlib.keysymdef.greek",
        "Xlib.support.unix_connect",
        "Xlib.ext.shape",
        "Xlib.ext.xinerama",
        "Xlib.ext.composite",
        "Xlib.ext.randr",
        "Xlib.ext.xfixes",
        "Xlib.ext.security",
        "Xlib.ext.xinput",
        "pynput.keyboard._xorg",
        "pynput.mouse._xorg",
        "pynput.keyboard._win32",
        "pynput.mouse._win32",
        "pynput.keyboard._darwin",
        "pynput.mouse._darwin",
    ],
)
aw_watcher_input_a = build_analysis("aw_watcher_input", awi_location)
aw_watcher_screenshot_a = build_analysis("aw_watcher_screenshot", awss_location)
aw_watcher_window_a = build_analysis(
    "aw_watcher_window",
    aww_location,
    binaries=(
        [
            (
                aww_location / "aw_watcher_window/aw-watcher-window-macos",
                "aw_watcher_window",
            )
        ]
        if platform.system() == "Darwin"
        else []
    ),
    datas=[
        (aww_location / "aw_watcher_window/printAppStatus.jxa", "aw_watcher_window")
    ],
)
aw_notify_a = build_analysis(
    "aw_notify", aw_notify_location, hiddenimports=["desktop_notifier.resources"]
)

# https://pythonhosted.org/PyInstaller/spec-files.html#multipackage-bundles
# MERGE takes a bit weird arguments, it wants tuples which consists of
# the analysis paired with the script name and the bin name
MERGE(
    (aw_server_a, "aw-server", "aw-server"),
    (aw_qt_a, "aw-qt", "aw-qt"),
    (aw_watcher_afk_a, "aw-watcher-afk", "aw-watcher-afk"),
    (aw_watcher_window_a, "aw-watcher-window", "aw-watcher-window"),
    (aw_watcher_screenshot_a, "aw-watcher-screenshot", "aw-watcher-screenshot"),
    (aw_watcher_input_a, "aw-watcher-input", "aw-watcher-input"),
    (aw_notify_a, "aw-notify", "aw-notify"),
)


# aw-server
aws_coll = build_collect(aw_server_a, "aw-server")

# aw-watcher-window
aww_coll = build_collect(aw_watcher_window_a, "aw-watcher-window")

# aw-watcher-afk
awa_coll = build_collect(aw_watcher_afk_a, "aw-watcher-afk")

# aw-watcher-screenshot
awss_coll = build_collect(aw_watcher_screenshot_a, "aw-watcher-screenshot")

# aw-qt
awq_coll = build_collect(
    aw_qt_a,
    "aw-qt",
    console=False if platform.system() == "Windows" else True,
)

# aw-watcher-input
awi_coll = build_collect(aw_watcher_input_a, "aw-watcher-input")

aw_notify_coll = build_collect(aw_notify_a, "aw-notify")

if platform.system() == "Darwin":
    # Read the Sparkle Ed25519 public key if it was generated by setup_sparkle.sh
    _pub_key_file = Path("Frameworks") / ".sparkle_keys" / "sparkle_public_key"
    _su_public_ed_key = _pub_key_file.read_text().strip() if _pub_key_file.exists() else ""
    if not _su_public_ed_key:
        print("WARNING: SUPublicEDKey not set — run scripts/package/setup_sparkle.sh to generate keys")

    app = BUNDLE(
        awq_coll,
        aws_coll,
        aww_coll,
        awa_coll,
        awss_coll,
        awi_coll,
        aw_notify_coll,
        name="Chronio.app",
        icon=str(icon),
        bundle_identifier="com.maxschollum.chronio",
        version=current_release.lstrip("v"),
        info_plist={
            "NSPrincipalClass": "NSApplication",
            "CFBundleExecutable": "MacOS/aw-qt",
            "CFBundleIconFile": "chronio.icns",
            "CFBundleName": "Chronio",
            "CFBundleDisplayName": "Chronio",
            "NSAppleEventsUsageDescription": "Please grant access to use Apple Events",
            "LSUIElement": True,
            "CFBundleVersion": current_release.lstrip("v"),
            # Sparkle auto-update feed
            "SUFeedURL": "https://raw.githubusercontent.com/MaxSchollum/ActivityChronio/master/appcast.xml",
            # Ed25519 public key for update signature verification (from setup_sparkle.sh)
            "SUPublicEDKey": _su_public_ed_key,
            # Hardened runtime: allow JIT (required by some PyInstaller Python runtimes)
            "com.apple.security.cs.allow-jit": True,
        },
    )
