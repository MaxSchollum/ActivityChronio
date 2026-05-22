from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from aw_core.models import Event

from aw_watcher_screenshot.capture import CapturedScreenshot
from aw_watcher_screenshot.watcher import (
    AFK_LOOKBACK_SECONDS,
    BUCKET_TYPE,
    DEFAULT_INTERVAL_SECONDS,
    ScreenshotWatcher,
    ScreenshotSettings,
    build_file_key,
    load_settings,
    set_capture_paused,
)


CAPTURE_TIME = datetime(2026, 5, 22, 13, 14, 15, 123000, tzinfo=timezone.utc)


class FakeClient:
    client_hostname = "test-host"

    def __init__(self, enabled=True, afk_events=None, screenshot_events=None):
        self.settings = {
            "chronioScreenshotsEnabled": enabled,
            "chronioScreenshotIntervalSeconds": 300,
            "chronioScreenshotQuality": 60,
            "chronioScreenshotRetentionDays": 30,
            "chronioScreenshotStorageLimitMb": 2048,
        }
        self.afk_events = afk_events or []
        self.screenshot_events = screenshot_events or []
        self.event_queries = []
        self.events = []
        self.buckets = []
        self.deleted_events = []
        self.saved_settings = []

    def get_setting(self, key):
        return self.settings.get(key)

    def get_events(self, bucket_id, **kwargs):
        self.event_queries.append((bucket_id, kwargs))
        if bucket_id.startswith("aw-watcher-screenshot_"):
            return self.screenshot_events
        return self.afk_events

    def insert_event(self, bucket_id, event):
        self.events.append((bucket_id, event))

    def delete_event(self, bucket_id, event_id):
        self.deleted_events.append((bucket_id, event_id))

    def set_setting(self, key, value):
        self.saved_settings.append((key, value))

    def create_bucket(self, bucket_id, bucket_type):
        self.buckets.append((bucket_id, bucket_type))

    def wait_for_start(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class FakeCapture:
    def __init__(self):
        self.paths = []
        self.jpeg_qualities = []

    def capture(self, output_path: Path, jpeg_quality: int) -> CapturedScreenshot:
        self.paths.append(output_path)
        self.jpeg_qualities.append(jpeg_quality)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"jpeg")
        return CapturedScreenshot(
            path=output_path,
            width=1280,
            height=720,
            byte_size=output_path.stat().st_size,
        )


class UnreadableAfkClient(FakeClient):
    def get_events(self, bucket_id, **kwargs):
        raise RuntimeError("AFK bucket unavailable")


def not_afk_event() -> Event:
    return Event(
        timestamp=CAPTURE_TIME - timedelta(seconds=1),
        duration=2,
        data={"status": "not-afk"},
    )


def test_disabled_setting_skips_afk_lookup_and_capture(tmp_path):
    client = FakeClient(enabled=False, afk_events=[not_afk_event()])
    capture = FakeCapture()

    event = ScreenshotWatcher(client, capture_backend=capture, root=tmp_path).capture_once(
        timestamp=CAPTURE_TIME
    )

    assert event is None
    assert client.event_queries == []
    assert capture.paths == []
    assert client.events == []


def test_paused_setting_skips_afk_lookup_and_capture(tmp_path):
    client = FakeClient(enabled=True, afk_events=[not_afk_event()])
    client.settings["chronioScreenshotCapturePaused"] = True
    capture = FakeCapture()

    event = ScreenshotWatcher(client, capture_backend=capture, root=tmp_path).capture_once(
        timestamp=CAPTURE_TIME
    )

    assert event is None
    assert client.event_queries == []
    assert capture.paths == []
    assert client.events == []


@pytest.mark.parametrize("afk_events", [[], [Event(timestamp=CAPTURE_TIME, data={"status": "afk"})]])
def test_afk_state_must_confirm_not_afk_before_capture(tmp_path, afk_events):
    client = FakeClient(afk_events=afk_events)
    capture = FakeCapture()

    event = ScreenshotWatcher(client, capture_backend=capture, root=tmp_path).capture_once(
        timestamp=CAPTURE_TIME
    )

    assert event is None
    assert capture.paths == []
    assert client.events == []
    assert client.event_queries == [
        (
            "aw-watcher-afk_test-host",
            {
                "limit": -1,
                "start": CAPTURE_TIME - timedelta(seconds=AFK_LOOKBACK_SECONDS),
                "end": CAPTURE_TIME,
            },
        )
    ]


def test_stale_not_afk_event_does_not_confirm_capture(tmp_path):
    client = FakeClient(
        afk_events=[
            Event(
                timestamp=CAPTURE_TIME - timedelta(seconds=30),
                data={"status": "not-afk"},
            )
        ]
    )
    capture = FakeCapture()

    event = ScreenshotWatcher(client, capture_backend=capture, root=tmp_path).capture_once(
        timestamp=CAPTURE_TIME
    )

    assert event is None
    assert capture.paths == []
    assert client.events == []


def test_afk_read_failure_fails_closed_before_capture(tmp_path):
    client = UnreadableAfkClient(afk_events=[not_afk_event()])
    capture = FakeCapture()

    event = ScreenshotWatcher(client, capture_backend=capture, root=tmp_path).capture_once(
        timestamp=CAPTURE_TIME
    )

    assert event is None
    assert capture.paths == []
    assert client.events == []


def test_capture_writes_relative_file_key_metadata(tmp_path):
    client = FakeClient(afk_events=[not_afk_event()])
    capture = FakeCapture()

    event = ScreenshotWatcher(client, capture_backend=capture, root=tmp_path).capture_once(
        timestamp=CAPTURE_TIME
    )

    expected_key = "2026-05-22/2026-05-22T13-14-15.123Z.jpg"
    assert event is not None
    assert capture.paths == [tmp_path / expected_key]
    assert capture.jpeg_qualities == [60]
    assert client.events == [("aw-watcher-screenshot_test-host", event)]
    assert event.data == {
        "file_key": expected_key,
        "mime_type": "image/jpeg",
        "width": 1280,
        "height": 720,
        "byte_size": 4,
    }
    assert str(tmp_path) not in event.data["file_key"]


def test_bucket_has_explicit_screenshot_type():
    client = FakeClient()
    watcher = ScreenshotWatcher(
        client,
        sleep_fn=lambda _seconds: (_ for _ in ()).throw(KeyboardInterrupt),
    )

    watcher.run()

    assert client.buckets == [("aw-watcher-screenshot_test-host", BUCKET_TYPE)]


def test_file_key_preserves_offset_without_retention_state():
    timestamp = datetime(2026, 5, 22, 13, 14, 15, 987000, tzinfo=timezone(timedelta(hours=2)))

    assert build_file_key(timestamp) == "2026-05-22/2026-05-22T13-14-15.987+0200.jpg"


def test_invalid_interval_falls_back_to_prd_default():
    client = FakeClient()
    client.settings["chronioScreenshotIntervalSeconds"] = 0

    assert load_settings(client).interval_seconds == DEFAULT_INTERVAL_SECONDS


def test_quality_setting_is_clamped_to_jpeg_range():
    client = FakeClient()
    client.settings["chronioScreenshotQuality"] = 140

    assert load_settings(client).jpeg_quality == 100


def test_pause_state_is_persisted_as_activitywatch_setting():
    client = FakeClient()

    set_capture_paused(client, paused=True)
    set_capture_paused(client, paused=False)

    assert client.saved_settings == [
        ("chronioScreenshotCapturePaused", True),
        ("chronioScreenshotCapturePaused", False),
    ]


def test_retention_cleanup_deletes_expired_screenshot_file_and_event(tmp_path):
    expired_key = "2026-04-01/expired.jpg"
    current_key = "2026-05-22/current.jpg"
    expired_path = write_screenshot(tmp_path, expired_key, b"old")
    current_path = write_screenshot(tmp_path, current_key, b"current")
    client = FakeClient(
        screenshot_events=[
            screenshot_event(10, CAPTURE_TIME - timedelta(days=31), expired_key),
            screenshot_event(11, CAPTURE_TIME, current_key),
        ]
    )
    settings = ScreenshotSettings(
        enabled=True,
        retention_days=30,
        storage_limit_bytes=1024,
    )

    ScreenshotWatcher(client, root=tmp_path).cleanup_once(
        timestamp=CAPTURE_TIME,
        settings=settings,
    )

    assert not expired_path.exists()
    assert current_path.exists()
    assert client.deleted_events == [("aw-watcher-screenshot_test-host", 10)]


def test_storage_cleanup_deletes_oldest_screenshot_records_first(tmp_path):
    oldest_key = "2026-05-20/oldest.jpg"
    middle_key = "2026-05-21/middle.jpg"
    newest_key = "2026-05-22/newest.jpg"
    oldest_path = write_screenshot(tmp_path, oldest_key, b"1234")
    middle_path = write_screenshot(tmp_path, middle_key, b"5678")
    newest_path = write_screenshot(tmp_path, newest_key, b"90")
    client = FakeClient(
        screenshot_events=[
            screenshot_event(20, CAPTURE_TIME - timedelta(days=2), oldest_key),
            screenshot_event(21, CAPTURE_TIME - timedelta(days=1), middle_key),
            screenshot_event(22, CAPTURE_TIME, newest_key),
        ]
    )
    settings = ScreenshotSettings(
        enabled=True,
        retention_days=30,
        storage_limit_bytes=6,
    )

    ScreenshotWatcher(client, root=tmp_path).cleanup_once(
        timestamp=CAPTURE_TIME,
        settings=settings,
    )

    assert not oldest_path.exists()
    assert middle_path.exists()
    assert newest_path.exists()
    assert client.deleted_events == [("aw-watcher-screenshot_test-host", 20)]


def test_cleanup_ignores_unsafe_file_keys(tmp_path):
    external_path = tmp_path.parent / "outside.jpg"
    external_path.write_bytes(b"keep")
    client = FakeClient(
        screenshot_events=[
            screenshot_event(30, CAPTURE_TIME - timedelta(days=31), "../outside.jpg"),
            screenshot_event(31, CAPTURE_TIME - timedelta(days=31), str(external_path)),
        ]
    )
    settings = ScreenshotSettings(enabled=True, retention_days=30)

    ScreenshotWatcher(client, root=tmp_path).cleanup_once(
        timestamp=CAPTURE_TIME,
        settings=settings,
    )

    assert external_path.exists()
    assert client.deleted_events == []


def write_screenshot(root: Path, file_key: str, contents: bytes) -> Path:
    path = root / file_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(contents)
    return path


def screenshot_event(event_id: int, timestamp: datetime, file_key: str) -> Event:
    return Event(
        id=event_id,
        timestamp=timestamp,
        data={"file_key": file_key, "mime_type": "image/jpeg"},
    )
