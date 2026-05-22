import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Any, Callable, Dict, Optional

from aw_core.models import Event

from .capture import CapturedScreenshot, JPEG_MIME_TYPE, MacOSScreenshotCapture

logger = logging.getLogger(__name__)

BUCKET_TYPE = "screenshot"
DEFAULT_INTERVAL_SECONDS = 5 * 60
SCREENSHOT_ENABLED_SETTING = "chronioScreenshotsEnabled"
SCREENSHOT_INTERVAL_SETTING = "chronioScreenshotIntervalSeconds"


@dataclass
class ScreenshotSettings:
    enabled: bool
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS


def screenshot_root() -> Path:
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "ActivityChronio"
        / "screenshots"
    )


def build_file_key(timestamp: datetime) -> str:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("Screenshot timestamp must be timezone-aware")

    offset = timestamp.strftime("%z")
    timezone_suffix = "Z" if offset == "+0000" else offset
    milliseconds = int(timestamp.microsecond / 1000)
    day = timestamp.strftime("%Y-%m-%d")
    name = timestamp.strftime("%Y-%m-%dT%H-%M-%S")
    return "{}/{}.{:03d}{}.jpg".format(day, name, milliseconds, timezone_suffix)


def load_settings(client: Any) -> ScreenshotSettings:
    try:
        enabled = _is_enabled_value(client.get_setting(SCREENSHOT_ENABLED_SETTING))
        interval_value = client.get_setting(SCREENSHOT_INTERVAL_SETTING)
    except Exception:
        logger.exception("Unable to read Chronio screenshot settings")
        return ScreenshotSettings(enabled=False)

    return ScreenshotSettings(
        enabled=enabled,
        interval_seconds=_positive_interval_or_default(interval_value),
    )


def _is_enabled_value(value: Any) -> bool:
    return value is True or (
        isinstance(value, str) and value.strip().lower() == "true"
    )


def _positive_interval_or_default(value: Any) -> float:
    if isinstance(value, bool):
        return DEFAULT_INTERVAL_SECONDS

    try:
        interval = float(value)
    except (TypeError, ValueError):
        return DEFAULT_INTERVAL_SECONDS

    return interval if interval > 0 else DEFAULT_INTERVAL_SECONDS


class ScreenshotWatcher:
    def __init__(
        self,
        client: Any,
        capture_backend: Optional[Any] = None,
        root: Optional[Path] = None,
        now: Optional[Callable[[], datetime]] = None,
        sleep_fn: Callable[[float], None] = sleep,
    ):
        self.client = client
        self.capture_backend = capture_backend or MacOSScreenshotCapture()
        self.root = root or screenshot_root()
        self.now = now or (lambda: datetime.now().astimezone())
        self.sleep = sleep_fn
        self.bucket_id = "aw-watcher-screenshot_{}".format(client.client_hostname)
        self.afk_bucket_id = "aw-watcher-afk_{}".format(client.client_hostname)

    def run(self) -> None:
        logger.info("aw-watcher-screenshot started")
        self.client.wait_for_start()
        self.client.create_bucket(self.bucket_id, BUCKET_TYPE)

        with self.client:
            while True:
                try:
                    settings = load_settings(self.client)
                    self.capture_once(settings=settings)
                    self.sleep(settings.interval_seconds)
                except KeyboardInterrupt:
                    logger.info("aw-watcher-screenshot stopped by keyboard interrupt")
                    break
                except Exception:
                    logger.exception("Screenshot capture cycle failed")
                    self.sleep(DEFAULT_INTERVAL_SECONDS)

    def capture_once(
        self,
        timestamp: Optional[datetime] = None,
        settings: Optional[ScreenshotSettings] = None,
    ) -> Optional[Event]:
        settings = settings or load_settings(self.client)
        if not settings.enabled:
            logger.debug("Screenshot capture is disabled")
            return None

        capture_timestamp = timestamp or self.now()
        if not self._is_confirmed_not_afk(capture_timestamp):
            logger.debug("Skipping screenshot without current not-afk AFK state")
            return None

        file_key = build_file_key(capture_timestamp)
        file_path = self.root / file_key
        try:
            captured = self.capture_backend.capture(file_path)
        except Exception:
            self._unlink_orphaned_capture(file_path)
            raise
        event = Event(
            timestamp=capture_timestamp,
            data=self._event_data(file_key, captured),
        )

        try:
            self.client.insert_event(self.bucket_id, event)
        except Exception:
            self._unlink_orphaned_capture(captured.path)
            raise
        return event

    def _is_confirmed_not_afk(self, timestamp: datetime) -> bool:
        try:
            events = self.client.get_events(
                self.afk_bucket_id,
                limit=1,
                start=timestamp,
                end=timestamp,
            )
        except Exception:
            logger.exception("Unable to read AFK state")
            return False

        return bool(events and events[0].data.get("status") == "not-afk")

    def _event_data(
        self,
        file_key: str,
        captured: CapturedScreenshot,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "file_key": file_key,
            "mime_type": captured.mime_type or JPEG_MIME_TYPE,
        }
        _put_if_present(data, "width", captured.width)
        _put_if_present(data, "height", captured.height)
        _put_if_present(data, "byte_size", captured.byte_size)
        return data

    def _unlink_orphaned_capture(self, path: Path) -> None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _put_if_present(data: Dict[str, Any], key: str, value: Optional[int]) -> None:
    if value is not None:
        data[key] = value
