import logging
import os
import platform
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

JPEG_MIME_TYPE = "image/jpeg"
JPEG_QUALITY = 60
MAX_WIDTH_PX = 1280


@dataclass
class CapturedScreenshot:
    path: Path
    mime_type: str = JPEG_MIME_TYPE
    width: Optional[int] = None
    height: Optional[int] = None
    byte_size: Optional[int] = None


class MacOSScreenshotCapture:
    def capture(self, output_path: Path) -> CapturedScreenshot:
        if platform.system() != "Darwin":
            raise RuntimeError("aw-watcher-screenshot capture is currently macOS-only")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._temporary_capture_path(output_path.parent)
        try:
            subprocess.run(
                ["/usr/sbin/screencapture", "-x", "-t", "png", str(temporary_path)],
                check=True,
            )
            subprocess.run(
                [
                    "/usr/bin/sips",
                    "-Z",
                    str(MAX_WIDTH_PX),
                    "-s",
                    "format",
                    "jpeg",
                    "-s",
                    "formatOptions",
                    str(JPEG_QUALITY),
                    str(temporary_path),
                    "--out",
                    str(output_path),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
            )
        finally:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass

        dimensions = self._read_dimensions(output_path)
        return CapturedScreenshot(
            path=output_path,
            width=dimensions.get("pixelWidth"),
            height=dimensions.get("pixelHeight"),
            byte_size=output_path.stat().st_size,
        )

    def _temporary_capture_path(self, parent: Path) -> Path:
        fd, path = tempfile.mkstemp(
            prefix=".aw-watcher-screenshot-",
            suffix=".png",
            dir=str(parent),
        )
        os.close(fd)
        return Path(path)

    def _read_dimensions(self, image_path: Path) -> Dict[str, int]:
        try:
            result = subprocess.run(
                [
                    "/usr/bin/sips",
                    "-g",
                    "pixelWidth",
                    "-g",
                    "pixelHeight",
                    str(image_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError):
            logger.warning("Unable to read screenshot dimensions for %s", image_path)
            return {}

        dimensions: Dict[str, int] = {}
        for line in result.stdout.splitlines():
            key, separator, value = line.strip().partition(":")
            if separator and key in ("pixelWidth", "pixelHeight"):
                try:
                    dimensions[key] = int(value.strip())
                except ValueError:
                    logger.warning("Invalid %s value from sips: %s", key, value)
        return dimensions
