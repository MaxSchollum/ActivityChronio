import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep
from typing import Any, Callable, Dict, List, Optional

from aw_core.models import Event

from .capture import CapturedScreenshot, JPEG_MIME_TYPE, MacOSScreenshotCapture

logger = logging.getLogger(__name__)

BUCKET_TYPE = "screenshot"
DEFAULT_INTERVAL_SECONDS = 5 * 60
DEFAULT_JPEG_QUALITY = 60
DEFAULT_RETENTION_DAYS = 30
DEFAULT_STORAGE_LIMIT_MB = 2048
AFK_LOOKBACK_SECONDS = 10 * 60
SCREENSHOT_ENABLED_SETTING = "chronioScreenshotsEnabled"
SCREENSHOT_INTERVAL_SETTING = "chronioScreenshotIntervalSeconds"
SCREENSHOT_PAUSED_SETTING = "chronioScreenshotCapturePaused"
SCREENSHOT_QUALITY_SETTING = "chronioScreenshotQuality"
SCREENSHOT_RETENTION_SETTING = "chronioScreenshotRetentionDays"
SCREENSHOT_STORAGE_LIMIT_SETTING = "chronioScreenshotStorageLimitMb"


@dataclass
class ScreenshotSettings:
    enabled: bool
    paused: bool = False
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS
    jpeg_quality: int = DEFAULT_JPEG_QUALITY
    retention_days: float = DEFAULT_RETENTION_DAYS
    storage_limit_bytes: int = DEFAULT_STORAGE_LIMIT_MB * 1024 * 1024


@dataclass
class ScreenshotRecord:
    event: Event
    path: Path
    byte_size: int


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
        paused = _is_enabled_value(client.get_setting(SCREENSHOT_PAUSED_SETTING))
        interval_value = client.get_setting(SCREENSHOT_INTERVAL_SETTING)
        quality_value = client.get_setting(SCREENSHOT_QUALITY_SETTING)
        retention_value = client.get_setting(SCREENSHOT_RETENTION_SETTING)
        storage_limit_value = client.get_setting(SCREENSHOT_STORAGE_LIMIT_SETTING)
    except Exception:
        logger.exception("Unable to read Chronio screenshot settings")
        return ScreenshotSettings(enabled=False)

    return ScreenshotSettings(
        enabled=enabled,
        paused=paused,
        interval_seconds=_positive_number_or_default(
            interval_value, DEFAULT_INTERVAL_SECONDS
        ),
        jpeg_quality=_jpeg_quality_or_default(quality_value),
        retention_days=_positive_number_or_default(
            retention_value, DEFAULT_RETENTION_DAYS
        ),
        storage_limit_bytes=_megabytes_to_bytes(storage_limit_value),
    )


def set_capture_paused(client: Any, paused: bool) -> None:
    client.set_setting(SCREENSHOT_PAUSED_SETTING, paused)


def _is_enabled_value(value: Any) -> bool:
    return value is True or (
        isinstance(value, str) and value.strip().lower() == "true"
    )


def _positive_number_or_default(value: Any, default: float) -> float:
    if isinstance(value, bool):
        return default

    try:
        number = float(value)
    except (TypeError, ValueError):
        return default

    return number if number > 0 else default


def _megabytes_to_bytes(value: Any) -> int:
    megabytes = _positive_number_or_default(value, DEFAULT_STORAGE_LIMIT_MB)
    return int(megabytes * 1024 * 1024)


def _jpeg_quality_or_default(value: Any) -> int:
    quality = _positive_number_or_default(value, DEFAULT_JPEG_QUALITY)
    return min(100, max(1, int(quality)))


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
                    timestamp = self.now()
                    self.capture_once(timestamp=timestamp, settings=settings)
                    if settings.enabled:
                        self.cleanup_once(timestamp=timestamp, settings=settings)
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
        if settings.paused:
            logger.debug("Screenshot capture is paused")
            return None

        capture_timestamp = timestamp or self.now()
        if not self._is_confirmed_not_afk(capture_timestamp):
            logger.debug("Skipping screenshot without current not-afk AFK state")
            return None

        file_key = build_file_key(capture_timestamp)
        file_path = self.root / file_key
        try:
            captured = self.capture_backend.capture(
                file_path, jpeg_quality=settings.jpeg_quality
            )
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

    def cleanup_once(
        self,
        timestamp: Optional[datetime] = None,
        settings: Optional[ScreenshotSettings] = None,
    ) -> None:
        settings = settings or load_settings(self.client)
        cleanup_timestamp = timestamp or self.now()
        records = self._screenshot_records()
        retention_cutoff = cleanup_timestamp - timedelta(days=settings.retention_days)

        retained: List[ScreenshotRecord] = []
        for record in records:
            if record.event.timestamp < retention_cutoff:
                self._delete_record(record)
            else:
                retained.append(record)

        storage_total = sum(record.byte_size for record in retained)
        for record in retained:
            if storage_total <= settings.storage_limit_bytes:
                break
            if self._delete_record(record):
                storage_total -= record.byte_size

    def _is_confirmed_not_afk(self, timestamp: datetime) -> bool:
        try:
            events = self.client.get_events(
                self.afk_bucket_id,
                limit=-1,
                start=timestamp - timedelta(seconds=AFK_LOOKBACK_SECONDS),
                end=timestamp,
            )
        except Exception:
            logger.exception("Unable to read AFK state")
            return False

        return any(
            event.data.get("status") == "not-afk"
            and _event_covers_timestamp(event, timestamp)
            for event in events
        )

    def _screenshot_records(self) -> List[ScreenshotRecord]:
        try:
            events = self.client.get_events(self.bucket_id, limit=-1)
        except Exception:
            logger.exception("Unable to read screenshot events for cleanup")
            return []

        records = []
        for event in events:
            path = self._path_for_file_key(event.data.get("file_key"))
            if path is None:
                logger.warning("Skipping cleanup for unsafe screenshot file key")
                continue
            records.append(
                ScreenshotRecord(
                    event=event,
                    path=path,
                    byte_size=self._file_size(path),
                )
            )
        return sorted(records, key=lambda record: record.event.timestamp)

    def _path_for_file_key(self, file_key: Any) -> Optional[Path]:
        if not isinstance(file_key, str) or not file_key:
            return None

        relative_path = Path(file_key)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            return None
        return self.root / relative_path

    def _file_size(self, path: Path) -> int:
        try:
            return path.stat().st_size
        except FileNotFoundError:
            return 0
        except OSError:
            logger.warning("Unable to read screenshot file size for %s", path)
            return 0

    def _delete_record(self, record: ScreenshotRecord) -> bool:
        if record.event.id is None:
            logger.warning("Skipping cleanup for screenshot event without an id")
            return False

        try:
            self._unlink_orphaned_capture(record.path)
            self.client.delete_event(self.bucket_id, record.event.id)
        except OSError:
            logger.exception("Unable to delete screenshot file during cleanup")
            return False
        except Exception:
            logger.exception("Unable to delete screenshot event during cleanup")
            return False
        return True

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


def _event_covers_timestamp(event: Event, timestamp: datetime) -> bool:
    return event.timestamp <= timestamp <= event.timestamp + event.duration
