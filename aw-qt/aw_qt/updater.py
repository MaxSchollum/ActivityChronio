"""
updater.py — background update checker for Chronio.

Polls the GitHub Releases API once per session and calls back with the
latest tag when a newer version is available.  This module is intentionally
standalone and has zero non-stdlib dependencies so it works both from source
and inside the PyInstaller bundle.

Sparkle integration (see sparkle.py) uses the same release feed via the
appcast.xml mechanism.  This module acts as the Python-side fallback for
showing an "update available" menu item.
"""

import json
import threading
from typing import Callable, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

RELEASES_API = (
    "https://api.github.com/repos/MaxSchollum/ActivityChronio/releases/latest"
)
RELEASES_URL = "https://github.com/MaxSchollum/ActivityChronio/releases/latest"


def _version_tuple(tag: str) -> tuple:
    """Convert a semver-ish tag like 'v1.2.3' to (1, 2, 3) for comparison."""
    parts = tag.lstrip("v").split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return (0,)


def check_for_update(
    current_version: str,
    callback: Callable[[Optional[str]], None],
) -> None:
    """
    Fetch the latest release in a daemon thread.

    Calls ``callback(latest_tag)`` when a newer version exists,
    or ``callback(None)`` when already up-to-date or on any error.
    Never raises — all exceptions are swallowed so a network failure
    never crashes the tray application.
    """

    def _worker() -> None:
        try:
            req = Request(
                RELEASES_API,
                headers={"User-Agent": "chronio-update-checker/1"},
            )
            with urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            latest_tag: str = data.get("tag_name", "")
            if latest_tag and _version_tuple(latest_tag) > _version_tuple(
                current_version
            ):
                callback(latest_tag)
            else:
                callback(None)
        except Exception:
            callback(None)

    t = threading.Thread(target=_worker, daemon=True, name="chronio-update-check")
    t.start()
