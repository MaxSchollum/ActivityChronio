from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from aw_core.models import Event

from aw_watcher_screenshot.capture import CapturedScreenshot
from aw_watcher_screenshot.watcher import (
    BUCKET_TYPE,
    DEFAULT_INTERVAL_SECONDS,
    ScreenshotWatcher,
    build_file_key,
    load_settings,
)


CAPTURE_TIME = datetime(2026, 5, 22, 13, 14, 15, 123000, tzinfo=timezone.utc)


class FakeClient:
    client_hostname = "test-host"

    def __init__(self, enabled=True, afk_events=None):
        self.settings = {
            "chronioScreenshotsEnabled": enabled,
            "chronioScreenshotIntervalSeconds": 60,
        }
        self.afk_events = afk_events or []
        self.event_queries = []
        self.events = []
        self.buckets = []

    def get_setting(self, key):
        return self.settings.get(key)

    def get_events(self, bucket_id, **kwargs):
        self.event_queries.append((bucket_id, kwargs))
        return self.afk_events

    def insert_event(self, bucket_id, event):
        self.events.append((bucket_id, event))

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

    def capture(self, output_path: Path) -> CapturedScreenshot:
        self.paths.append(output_path)
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
            {"limit": 1, "start": CAPTURE_TIME, "end": CAPTURE_TIME},
        )
    ]


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
