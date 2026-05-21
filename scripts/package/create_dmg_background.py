#!/usr/bin/env python3
"""
create_dmg_background.py — generate scripts/package/dmg-background.png

Renders a 640×280 @2x (1280×560 pixel) PNG for the Chronio DMG window.
The image shows a subtle dark-gradient background with the Chronio wordmark
and an arrow pointing from the app icon position to the Applications folder.

Usage (macOS only):
    python3 scripts/package/create_dmg_background.py

Output:
    scripts/package/dmg-background.png  (1280×560 px, logical 640×280 @2x)
"""

import sys
from pathlib import Path

# Logical window dimensions (from dmgbuild-settings.py window_rect)
W_LOGICAL, H_LOGICAL = 640, 280
# Render at 2× for retina
SCALE = 2
W, H = W_LOGICAL * SCALE, H_LOGICAL * SCALE

# Icon centre positions (from icon_locations in dmgbuild-settings.py, scaled)
# appname at (140, 120), Applications at (500, 120) — logical coords, origin TL
APP_X = 140 * SCALE
APP_Y = (H_LOGICAL - 120) * SCALE  # flip y (AppKit origin is bottom-left)
APPS_X = 500 * SCALE
APPS_Y = (H_LOGICAL - 120) * SCALE

OUT = Path(__file__).resolve().parent / "dmg-background.png"


def main() -> None:
    if sys.platform != "darwin":
        print("create_dmg_background.py only runs on macOS (requires AppKit)")
        sys.exit(1)

    from AppKit import (  # type: ignore[import]
        NSBezierPath,
        NSColor,
        NSFont,
        NSFontManager,
        NSGradient,
        NSGraphicsContext,
        NSBitmapImageRep,
        NSString,
        NSMutableParagraphStyle,
        NSAttributedString,
    )
    from Foundation import NSRect, NSPoint, NSMakeRect  # type: ignore[import]

    rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, W, H, 8, 4, True, False, "NSCalibratedRGBColorSpace", 0, 0
    )
    ctx = NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(ctx)

    # ── background gradient ───────────────────────────────────────────────
    top_color = NSColor.colorWithRed_green_blue_alpha_(13 / 255, 17 / 255, 23 / 255, 1.0)
    bot_color = NSColor.colorWithRed_green_blue_alpha_(20 / 255, 26 / 255, 35 / 255, 1.0)
    grad = NSGradient.alloc().initWithStartingColor_endingColor_(top_color, bot_color)
    full_rect = NSRect((0, 0), (W, H))
    grad.drawInRect_angle_(full_rect, 90)

    # ── subtle grid dots ──────────────────────────────────────────────────
    dot_color = NSColor.colorWithRed_green_blue_alpha_(1.0, 1.0, 1.0, 0.04)
    dot_color.set()
    spacing = 40 * SCALE
    dot_r = 1.0
    x = spacing
    while x < W:
        y = spacing
        while y < H:
            dot = NSBezierPath.bezierPathWithOvalInRect_(
                NSRect((x - dot_r, y - dot_r), (dot_r * 2, dot_r * 2))
            )
            dot.fill()
            y += spacing
        x += spacing

    # ── arrow from app to Applications ───────────────────────────────────
    arrow_color = NSColor.colorWithRed_green_blue_alpha_(1.0, 1.0, 1.0, 0.35)
    arrow_color.set()
    arrow = NSBezierPath.bezierPath()
    arrow.setLineWidth_(2.0 * SCALE)
    arrow.setLineCapStyle_(1)
    # Horizontal line between the two icons
    mid_y = APP_Y  # same y for both icons
    start_x = APP_X + 68 * SCALE   # just outside the app icon
    end_x = APPS_X - 68 * SCALE    # just before the folder icon
    arrow.moveToPoint_(NSPoint(start_x, mid_y))
    arrow.lineToPoint_(NSPoint(end_x, mid_y))
    arrow.stroke()

    # Arrowhead
    head_size = 12 * SCALE
    head = NSBezierPath.bezierPath()
    head.moveToPoint_(NSPoint(end_x, mid_y))
    head.lineToPoint_(NSPoint(end_x - head_size, mid_y + head_size * 0.5))
    head.moveToPoint_(NSPoint(end_x, mid_y))
    head.lineToPoint_(NSPoint(end_x - head_size, mid_y - head_size * 0.5))
    head.setLineWidth_(2.0 * SCALE)
    head.setLineCapStyle_(1)
    head.stroke()

    # ── "Drag to install" label ───────────────────────────────────────────
    label_color = NSColor.colorWithRed_green_blue_alpha_(1.0, 1.0, 1.0, 0.45)
    label_font = NSFont.systemFontOfSize_(13 * SCALE)
    attrs = {
        "NSColor": label_color,
        "NSFont": label_font,
    }
    label = NSAttributedString.alloc().initWithString_attributes_(
        "Drag Chronio to Applications to install", attrs
    )
    label_w = label.size().width
    label_x = (W - label_w) / 2
    label_y = mid_y - 52 * SCALE
    label.drawAtPoint_(NSPoint(label_x, label_y))

    NSGraphicsContext.restoreGraphicsState()

    # ── write PNG ─────────────────────────────────────────────────────────
    OUT.parent.mkdir(parents=True, exist_ok=True)
    NSPNGFileType = 4
    png_data = rep.representationUsingType_properties_(NSPNGFileType, None)
    OUT.write_bytes(bytes(png_data))
    print(f"Wrote {OUT}  ({W}×{H} px, logical {W_LOGICAL}×{H_LOGICAL} @2x)")


if __name__ == "__main__":
    main()
