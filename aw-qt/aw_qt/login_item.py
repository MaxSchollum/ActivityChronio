"""
login_item.py — manage Chronio as a macOS login item.

Uses a LaunchAgent plist so the app starts on every login.  Works for both
the installed .app bundle and for source-run invocations (though the .app
bundle path is the intended production target).
"""

import plistlib
import subprocess
import sys
from pathlib import Path

BUNDLE_ID = "com.maxschollum.chronio"
_PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{BUNDLE_ID}.plist"


def _app_executable() -> str:
    """
    Return the executable path to register as the login item program.

    When running inside a PyInstaller .app bundle the executable is
    Contents/MacOS/aw-qt.  We register that directly so launchd can
    re-launch the same binary on the next login without needing the
    Finder 'Open at Login' API.
    """
    exe = Path(sys.executable).resolve()
    # Inside Chronio.app: .../Chronio.app/Contents/MacOS/aw-qt
    # Three levels up lands at Chronio.app
    candidate = exe.parent.parent.parent
    if candidate.suffix == ".app":
        return str(exe)
    # Running from source — register the current interpreter + main module
    return f"{exe} -m aw_qt"


def is_login_item() -> bool:
    """Return True if the LaunchAgent plist exists (i.e. login item is enabled)."""
    return _PLIST_PATH.exists()


def enable_login_item() -> None:
    """Create the LaunchAgent plist and load it so it is active immediately."""
    _PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)

    exe = _app_executable()
    # Split composite source-run command string into a list for ProgramArguments
    program_args = exe.split() if " " in exe else [exe]

    plist: dict = {
        "Label": BUNDLE_ID,
        "ProgramArguments": program_args,
        "RunAtLoad": True,
        "KeepAlive": False,
        # Throttle restarts to avoid a crash loop consuming the user's login
        "ThrottleInterval": 10,
    }
    with open(_PLIST_PATH, "wb") as fh:
        plistlib.dump(plist, fh)

    subprocess.run(
        ["launchctl", "load", "-w", str(_PLIST_PATH)],
        check=False,
        capture_output=True,
    )


def disable_login_item() -> None:
    """Unload the LaunchAgent and remove the plist."""
    if _PLIST_PATH.exists():
        subprocess.run(
            ["launchctl", "unload", "-w", str(_PLIST_PATH)],
            check=False,
            capture_output=True,
        )
        _PLIST_PATH.unlink(missing_ok=True)
