#!/usr/bin/env python3
"""
create_icon.py — generate aw-qt/media/logo/chronio.icns

Draws the Chronio clock-face icon (dark background, white circle outline,
white hour/minute hands) at every macOS icon resolution and packs them into
an ICNS with macOS-native iconutil.

Usage (macOS only):
    python3 scripts/package/create_icon.py

Output:
    aw-qt/media/logo/chronio.icns
"""

import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_ICNS = REPO_ROOT / "aw-qt" / "media" / "logo" / "chronio.icns"

# iconset sizes required by Apple — name → logical pixel size
# https://developer.apple.com/design/human-interface-guidelines/app-icons#macOS-app-icon-sizes
ICON_SIZES = {
    "icon_16x16.png": 16,
    "icon_16x16@2x.png": 32,
    "icon_32x32.png": 32,
    "icon_32x32@2x.png": 64,
    "icon_128x128.png": 128,
    "icon_128x128@2x.png": 256,
    "icon_256x256.png": 256,
    "icon_256x256@2x.png": 512,
    "icon_512x512.png": 512,
    "icon_512x512@2x.png": 1024,
}

# Brand colours
BG_R, BG_G, BG_B = 13 / 255, 17 / 255, 23 / 255  # #0D1117


def _draw_icon_png(size: int, out_path: Path) -> None:
    """Render one PNG at ``size``×``size`` using AppKit / CoreGraphics."""
    from AppKit import (  # type: ignore[import]
        NSBezierPath,
        NSColor,
        NSGraphicsContext,
        NSBitmapImageRep,
    )
    from Foundation import NSRect, NSPoint  # type: ignore[import]

    rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None,
        size,
        size,
        8,
        4,
        True,
        False,
        "NSCalibratedRGBColorSpace",
        0,
        0,
    )

    ctx = NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(ctx)

    # ── transparent clear ──────────────────────────────────────────────────
    NSColor.clearColor().set()
    NSBezierPath.fillRect_(NSRect((0, 0), (size, size)))

    s = float(size)
    radius_frac = 0.22  # rounded-corner fraction

    # ── dark rounded-rect background ───────────────────────────────────────
    bg = NSColor.colorWithRed_green_blue_alpha_(BG_R, BG_G, BG_B, 1.0)
    bg.set()
    bg_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
        NSRect((0, 0), (size, size)), s * radius_frac, s * radius_frac
    )
    bg_path.fill()

    # ── clock-face circle ──────────────────────────────────────────────────
    pad = s * 0.14
    stroke_w = max(1.5, s * 0.055)
    NSColor.whiteColor().set()

    ring = NSBezierPath.bezierPathWithOvalInRect_(
        NSRect((pad, pad), (s - 2 * pad, s - 2 * pad))
    )
    ring.setLineWidth_(stroke_w)
    ring.stroke()

    # ── clock hands ───────────────────────────────────────────────────────
    # Coordinate system: (0,0) bottom-left, so "up" is +y.
    # 12 o'clock: straight up → angle = 90° from x-axis
    # ~4:30 position for minute hand → angle = -45° (i.e. 315°)
    cx, cy = s / 2, s / 2
    inner_r = s / 2 - pad

    # Hour hand — 2/3 of inner radius, pointing to 12
    r_hour = inner_r * 0.58
    a_hour = math.radians(90)
    hour = NSBezierPath.bezierPath()
    hour.moveToPoint_(NSPoint(cx, cy))
    hour.lineToPoint_(
        NSPoint(cx + r_hour * math.cos(a_hour), cy + r_hour * math.sin(a_hour))
    )
    hour.setLineWidth_(stroke_w)
    hour.setLineCapStyle_(1)  # NSRoundLineCapStyle
    hour.stroke()

    # Minute hand — 3/4 of inner radius, pointing to ~4:30 (−45°)
    r_min = inner_r * 0.72
    a_min = math.radians(-45)
    minute = NSBezierPath.bezierPath()
    minute.moveToPoint_(NSPoint(cx, cy))
    minute.lineToPoint_(
        NSPoint(cx + r_min * math.cos(a_min), cy + r_min * math.sin(a_min))
    )
    minute.setLineWidth_(max(1.0, stroke_w * 0.8))
    minute.setLineCapStyle_(1)
    minute.stroke()

    NSGraphicsContext.restoreGraphicsState()

    # ── write PNG ─────────────────────────────────────────────────────────
    NSPNGFileType = 4
    png_data = rep.representationUsingType_properties_(NSPNGFileType, None)
    out_path.write_bytes(bytes(png_data))


def main() -> None:
    if sys.platform != "darwin":
        print("create_icon.py only runs on macOS (requires AppKit + iconutil)")
        sys.exit(1)

    if not shutil.which("iconutil"):
        print("iconutil not found — install Xcode Command Line Tools")
        sys.exit(1)

    with tempfile.TemporaryDirectory(suffix=".iconset") as tmpdir:
        iconset = Path(tmpdir)

        print(f"Rendering {len(ICON_SIZES)} icon sizes…")
        for filename, size in ICON_SIZES.items():
            out = iconset / filename
            _draw_icon_png(size, out)
            print(f"  {filename} ({size}×{size})")

        OUT_ICNS.parent.mkdir(parents=True, exist_ok=True)
        print(f"Packing → {OUT_ICNS}")
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(OUT_ICNS)],
            check=True,
        )

    print("Done.")


if __name__ == "__main__":
    main()
