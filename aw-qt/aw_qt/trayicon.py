import logging
import os
import json
import signal
import subprocess
import sys
import webbrowser
from datetime import datetime, timezone
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen
from pathlib import Path
from typing import Any, Dict, Optional

import aw_core
import iso8601
from PyQt6 import QtCore
from PyQt6.QtGui import QIcon, QPainter, QPen, QBrush, QColor, QCursor
from PyQt6.QtWidgets import (
    QApplication,
    QMenu,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QWidget,
)

from .manager import Manager, Module

logger = logging.getLogger(__name__)


def get_env() -> Dict[str, str]:
    """
    Necessary for xdg-open to work properly when PyInstaller overrides LD_LIBRARY_PATH

    https://github.com/ActivityWatch/activitywatch/issues/208#issuecomment-417346407
    """
    env = dict(os.environ)  # make a copy of the environment
    lp_key = "LD_LIBRARY_PATH"  # for GNU/Linux and *BSD.
    lp_orig = env.get(lp_key + "_ORIG")
    if lp_orig is not None:
        env[lp_key] = lp_orig  # restore the original, unmodified value
    else:
        # This happens when LD_LIBRARY_PATH was not set.
        # Remove the env var as a last resort:
        env.pop(lp_key, None)
    return env


def open_url(url: str) -> None:
    if sys.platform == "linux":
        env = get_env()
        subprocess.Popen(["xdg-open", url], env=env)
    else:
        webbrowser.open(url)


def open_webui(root_url: str) -> None:
    print("Opening dashboard")
    open_url(root_url)


def open_apibrowser(root_url: str) -> None:
    print("Opening api browser")
    open_url(root_url + "/api")


def open_dir(d: str) -> None:
    """From: http://stackoverflow.com/a/1795849/965332"""
    Path(d).mkdir(parents=True, exist_ok=True)
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-a", "Finder", d])
    elif sys.platform == "win32":
        os.startfile(d)  # type: ignore[attr-defined]
    else:
        env = get_env()
        subprocess.Popen(["xdg-open", d], env=env)
    if sys.platform == "darwin":
        subprocess.Popen(["open", d])
    elif sys.platform == "win32":
        os.startfile(d)  # type: ignore[attr-defined]
    else:
        env = get_env()
        subprocess.Popen(["xdg-open", d], env=env)


def _fetch_json(url: str, timeout_s: float = 2.0) -> Optional[Dict[str, Any]]:
    try:
        req = Request(url, headers={"User-Agent": "aw-qt"})
        with urlopen(req, timeout=timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, HTTPError, ValueError):
        return None



class TrayIcon(QSystemTrayIcon):
    def __init__(
        self,
        manager: Manager,
        icon: QIcon,
        parent: Optional[QWidget] = None,
        testing: bool = False,
    ) -> None:
        QSystemTrayIcon.__init__(self, icon, parent)
        self._parent = parent  # QSystemTrayIcon also tries to save parent info but it screws up the type info
        self.setToolTip("ActivityWatch" + (" (testing)" if testing else ""))

        self.manager = manager
        self.testing = testing

        self.root_url = f"http://127.0.0.1:{5666 if self.testing else 5600}"
        self.activated.connect(self.on_activated)

        self._tracking_action = None
        self._last_update_action = None
        self._open_dashboard_action = None
        self._open_logs_action = None
        self._open_settings_action = None
        self._quit_action = None
        self._icon_tracking = self._make_status_icon(icon, True)
        self._icon_idle = self._make_status_icon(icon, False)

        self._build_rootmenu()

        self._tracking_timer = QtCore.QTimer(self._parent)
        self._tracking_timer.setInterval(10000)
        self._tracking_timer.timeout.connect(self._update_tracking_status)
        self._tracking_timer.start()
        self._update_tracking_status()

    def on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            open_webui(self.root_url)
            return
        if reason in (
            QSystemTrayIcon.ActivationReason.Context,
            QSystemTrayIcon.ActivationReason.Trigger,
        ):
            self._show_menu()

    def _build_rootmenu(self) -> None:
        # Use a parentless QMenu to avoid inheriting a disabled state on macOS.
        menu = QMenu()
        self._menu = menu

        if self.testing:
            menu.addAction("Running in testing mode")  # .setEnabled(False)
            menu.addSeparator()

        # openWebUIIcon = QIcon.fromTheme("open")
        self._open_dashboard_action = menu.addAction(
            "Open Dashboard", lambda: open_webui(self.root_url)
        )
        self._open_dashboard_action.setEnabled(True)
        menu.addSeparator()
        self._tracking_action = menu.addAction("Status: checking…")
        self._tracking_action.triggered.connect(lambda: None)
        self._last_update_action = menu.addAction("Last update: —")
        self._last_update_action.triggered.connect(lambda: None)

        menu.addSeparator()
        menu.addSeparator()

        exitIcon = QIcon.fromTheme(
            "application-exit", QIcon("media/application_exit.png")
        )
        # This check is an attempted solution to: https://github.com/ActivityWatch/activitywatch/issues/62
        # Seems to be in agreement with: https://github.com/OtterBrowser/otter-browser/issues/1313
        #   "it seems that the bug is also triggered when creating a QIcon with an invalid path"
        if exitIcon.availableSizes():
            self._quit_action = menu.addAction(
                exitIcon, "Quit ActivityWatch", lambda: exit(self.manager)
            )
        else:
            self._quit_action = menu.addAction(
                "Quit ActivityWatch", lambda: exit(self.manager)
            )
        menu.addSeparator()
        self._quit_action.setEnabled(True)

        self.setContextMenu(menu)
        menu.setEnabled(True)
        menu.aboutToShow.connect(self._update_tracking_status)

    def _show_menu(self) -> None:
        if self._menu is None:
            return
        self._update_tracking_status()
        for action in [
            self._open_dashboard_action,
            self._open_logs_action,
            self._open_settings_action,
            self._quit_action,
        ]:
            if action is not None:
                action.setEnabled(True)
        self._menu.setEnabled(True)
        self._menu.exec(QCursor.pos())

        def show_module_failed_dialog(module: Module) -> None:
            box = QMessageBox(self._parent)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setText(f"Module {module.name} quit unexpectedly")
            box.setDetailedText(module.read_log(self.testing))

            restart_button = QPushButton("Restart", box)
            restart_button.clicked.connect(module.start)
            box.addButton(restart_button, QMessageBox.ButtonRole.AcceptRole)
            box.setStandardButtons(QMessageBox.StandardButton.Cancel)

            box.show()

        def check_module_status() -> None:
            unexpected_exits = self.manager.get_unexpected_stops()
            if unexpected_exits:
                for module in unexpected_exits:
                    show_module_failed_dialog(module)
                    module.stop()

        QtCore.QTimer.singleShot(2000, check_module_status)

    def _make_status_icon(self, base_icon: QIcon, tracking: bool) -> QIcon:
        size = base_icon.actualSize(QtCore.QSize(18, 18))
        pixmap = base_icon.pixmap(size)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        dot_size = max(3, int(min(size.width(), size.height()) * 0.32))
        margin = 1
        rect = QtCore.QRect(
            size.width() - dot_size - margin,
            size.height() - dot_size - margin,
            dot_size,
            dot_size,
        )

        if tracking:
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 0)))
            painter.drawEllipse(rect)
        else:
            pen = QPen(QColor(0, 0, 0))
            pen.setWidth(max(1, dot_size // 3))
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawEllipse(rect)

        painter.end()
        icon = QIcon(pixmap)
        if sys.platform == "darwin":
            icon.setIsMask(True)
        return icon

    def _get_tracking_state(self) -> Dict[str, Any]:
        buckets = _fetch_json(self.root_url + "/api/0/buckets/")
        if not buckets:
            info = _fetch_json(self.root_url + "/api/0/info")
            if not info:
                return {
                    "server": False,
                    "tracking": False,
                    "afk": False,
                    "window": False,
                    "stale": False,
                    "last_seen": None,
                }
            buckets = {}

        now = datetime.now(timezone.utc)
        recent_window_s = 600
        stale_window_s = 3600

        last_seen: Optional[datetime] = None

        def parse_ts(bucket: Dict[str, Any]) -> Optional[datetime]:
            last_updated = bucket.get("last_updated")
            if not last_updated:
                return None
            try:
                ts = iso8601.parse_date(last_updated)
            except Exception:
                return None
            if not ts.tzinfo:
                ts = ts.replace(tzinfo=timezone.utc)
            return ts

        def is_recent(bucket: Dict[str, Any]) -> bool:
            ts = parse_ts(bucket)
            if not ts:
                return False
            return (now - ts).total_seconds() <= recent_window_s

        def is_window_bucket(bucket: Dict[str, Any]) -> bool:
            if bucket.get("type") != "currentwindow":
                return False
            bucket_id = str(bucket.get("id", ""))
            return not bucket_id.startswith("aw-watcher-android")

        for b in buckets.values():
            if b.get("type") not in ("afkstatus", "currentwindow"):
                continue
            ts = parse_ts(b)
            if ts and (last_seen is None or ts > last_seen):
                last_seen = ts

        afk_recent = any(
            b.get("type") == "afkstatus" and is_recent(b) for b in buckets.values()
        )
        window_recent = any(
            is_window_bucket(b) and is_recent(b) for b in buckets.values()
        )
        stale = False
        if last_seen is not None:
            age_s = (now - last_seen).total_seconds()
            stale = age_s > recent_window_s and age_s <= stale_window_s

        return {
            "server": True,
            "tracking": afk_recent and window_recent,
            "afk": afk_recent,
            "window": window_recent,
            "stale": stale,
            "last_seen": last_seen,
        }

    def _apply_tracking_state(self, state: Dict[str, Any]) -> None:
        if not state.get("server"):
            label = "Status: server offline"
            icon = self._icon_idle
            tooltip = "ActivityWatch — server offline"
        else:
            if state.get("tracking"):
                label = "Status: tracking"
                icon = self._icon_tracking
            elif state.get("stale"):
                label = "Status: tracking (stale)"
                icon = self._icon_idle
            else:
                label = "Status: not tracking"
                icon = self._icon_idle

            tooltip = (
                "ActivityWatch — "
                + ("tracking" if state.get("tracking") else "not tracking")
                + f" (afk: {'ok' if state.get('afk') else 'no'}, window: {'ok' if state.get('window') else 'no'})"
            )

        if self._tracking_action is not None:
            self._tracking_action.setText(label)
        if getattr(self, "_last_update_action", None) is not None:
            last_seen = state.get("last_seen")
            if last_seen:
                self._last_update_action.setText(
                    "Last update: " + last_seen.astimezone().strftime("%H:%M")
                )
            else:
                self._last_update_action.setText("Last update: —")

        self.setIcon(icon)
        self.setToolTip(tooltip + (" (testing)" if self.testing else ""))

    def _update_tracking_status(self) -> None:
        state = self._get_tracking_state()
        self._apply_tracking_state(state)


    def _build_modulemenu(self, moduleMenu: QMenu) -> None:
        moduleMenu.clear()

        def add_module_menuitem(module: Module) -> None:
            title = module.name
            ac = moduleMenu.addAction(title, lambda: module.toggle(self.testing))

            ac.setData(module)
            ac.setCheckable(True)
            ac.setChecked(module.is_alive())

        for location, modules in [
            ("bundled", self.manager.modules_bundled),
            ("system", self.manager.modules_system),
        ]:
            header = moduleMenu.addAction(location)
            header.setEnabled(False)

            for module in sorted(modules, key=lambda m: m.name):
                add_module_menuitem(module)


def exit(manager: Manager) -> None:
    # TODO: Do cleanup actions
    # TODO: Save state for resume
    print("Shutdown initiated, stopping all services...")
    manager.stop_all()
    # Terminate entire process group, just in case.
    # os.killpg(0, signal.SIGINT)

    QApplication.quit()


def run(manager: Manager, testing: bool = False) -> Any:
    logger.info("Creating trayicon...")
    # print(QIcon.themeSearchPaths())

    app = QApplication(sys.argv)

    # This is needed for the icons to get picked up with PyInstaller
    scriptdir = Path(__file__).parent

    # When run from source:
    #   __file__ is aw_qt/trayicon.py
    #   scriptdir is ./aw_qt
    #   logodir is ./media/logo
    QtCore.QDir.addSearchPath("icons", str(scriptdir.parent / "media/logo/"))

    # When run from .app:
    #   __file__ is ./Contents/MacOS/aw-qt
    #   scriptdir is ./Contents/MacOS
    #   logodir is ./Contents/Resources/aw_qt/media/logo
    QtCore.QDir.addSearchPath(
        "icons", str(scriptdir.parent.parent / "Resources/aw_qt/media/logo/")
    )

    # logger.info(f"search paths: {QtCore.QDir.searchPaths('icons')}")

    # Without this, Ctrl+C will have no effect
    signal.signal(signal.SIGINT, lambda *args: exit(manager))
    # Ensure cleanup happens on SIGTERM
    signal.signal(signal.SIGTERM, lambda *args: exit(manager))

    timer = QtCore.QTimer()
    timer.start(100)  # You may change this if you wish.
    timer.timeout.connect(lambda: None)  # Let the interpreter run each 500 ms.

    # root widget
    widget = QWidget()

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            widget,
            "Systray",
            "I couldn't detect any system tray on this system. Either get one or run the ActivityWatch modules from the console.",
        )
        sys.exit(1)

    if sys.platform == "darwin":
        icon = QIcon("icons:clockicon.png")
        # Allow macOS to use filters for changing the icon's color
        icon.setIsMask(True)
    else:
        icon = QIcon("icons:clockicon.png")

    trayIcon = TrayIcon(manager, icon, widget, testing=testing)
    trayIcon.show()

    QApplication.setQuitOnLastWindowClosed(False)

    logger.info("Initialized aw-qt and trayicon successfully")
    # Run the application, blocks until quit
    return app.exec()
