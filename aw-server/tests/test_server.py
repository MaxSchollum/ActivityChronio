import random
from datetime import datetime, timedelta

import pytest


@pytest.fixture()
def bucket(flask_client):
    "Context manager for creating and deleting a testing bucket"
    try:
        bucket_id = "test"
        r = flask_client.post(
            f"/api/0/buckets/{bucket_id}",
            json={"client": "test", "type": "test", "hostname": "test"},
        )
        assert r.status_code == 200
        yield bucket_id
    finally:
        r = flask_client.delete(f"/api/0/buckets/{bucket_id}")
        assert r.status_code == 200


def test_info(flask_client):
    r = flask_client.get("/api/0/info")
    assert r.status_code == 200
    assert r.json["testing"]


def test_buckets(flask_client, bucket, benchmark):
    @benchmark
    def list_buckets():
        r = flask_client.get("/api/0/buckets/")
        print(r.json)
        assert r.status_code == 200
        assert len(r.json) == 1


def test_heartbeats(flask_client, bucket, benchmark):
    # FIXME: Currently tests using the memory storage method
    # TODO: Test with a longer data section and see if there's a significant difference
    # TODO: Test with a larger bucket and see if there's a significant difference
    @benchmark
    def heartbeat():
        now = datetime.now()
        r = flask_client.post(
            f"/api/0/buckets/{bucket}/heartbeat?pulsetime=1",
            json={"timestamp": now, "duration": 0, "data": {"random": random.random()}},
        )
        assert r.status_code == 200


def test_get_events(flask_client, bucket, benchmark):
    n_events = 100
    start_time = datetime.now() - timedelta(days=100)
    for i in range(n_events):
        now = start_time + timedelta(hours=i)
        r = flask_client.post(
            f"/api/0/buckets/{bucket}/heartbeat?pulsetime=0",
            json={"timestamp": now, "duration": 0, "data": {"random": random.random()}},
        )
        assert r.status_code == 200

    @benchmark
    def get_events():
        r = flask_client.get(f"/api/0/buckets/{bucket}/events")
        assert r.status_code == 200
        assert r.json
        assert len(r.json) == n_events

        r = flask_client.get(f"/api/0/buckets/{bucket}/events?limit=-1")
        assert r.status_code == 200
        assert r.json
        assert len(r.json) == n_events

        r = flask_client.get(f"/api/0/buckets/{bucket}/events?limit=10")
        assert r.status_code == 200
        assert r.json
        assert len(r.json) == 10

        r = flask_client.get(f"/api/0/buckets/{bucket}/events?limit=100")
        assert r.status_code == 200
        assert r.json
        assert len(r.json) == n_events

        r = flask_client.get(f"/api/0/buckets/{bucket}/events?limit=1000")
        assert r.status_code == 200
        assert r.json
        assert len(r.json) == n_events


@pytest.fixture()
def screenshot_bucket(flask_client):
    bucket_id = "test-screenshots"
    try:
        r = flask_client.post(
            f"/api/0/buckets/{bucket_id}",
            json={"client": "test", "type": "screenshot", "hostname": "test"},
        )
        assert r.status_code == 200
        yield bucket_id
    finally:
        r = flask_client.delete(f"/api/0/buckets/{bucket_id}")
        assert r.status_code == 200


def _create_screenshot_event(flask_client, bucket_id, file_key, timestamp):
    r = flask_client.post(
        f"/api/0/buckets/{bucket_id}/events",
        json={
            "timestamp": timestamp.isoformat(),
            "duration": 0,
            "data": {"file_key": file_key, "mime_type": "image/jpeg"},
        },
    )
    assert r.status_code == 200
    r = flask_client.get(f"/api/0/buckets/{bucket_id}/events?limit=1")
    assert r.status_code == 200
    return r.json[0]


def test_get_chronio_screenshot_image(flask_client, screenshot_bucket, tmp_path, monkeypatch):
    monkeypatch.setenv("CHRONIO_SCREENSHOT_ROOT", str(tmp_path))
    image = tmp_path / "2026-05-22" / "frame.jpg"
    image.parent.mkdir()
    image.write_bytes(b"jpeg")
    event = _create_screenshot_event(
        flask_client,
        screenshot_bucket,
        "2026-05-22/frame.jpg",
        datetime.now() - timedelta(hours=1),
    )

    r = flask_client.get(
        f"/api/0/chronio/screenshots/{screenshot_bucket}/{event['id']}/image"
    )

    assert r.status_code == 200
    assert r.data == b"jpeg"


def test_chronio_screenshot_image_rejects_traversal(
    flask_client, screenshot_bucket, tmp_path, monkeypatch
):
    monkeypatch.setenv("CHRONIO_SCREENSHOT_ROOT", str(tmp_path))
    event = _create_screenshot_event(
        flask_client,
        screenshot_bucket,
        "../outside.jpg",
        datetime.now() - timedelta(hours=1),
    )

    r = flask_client.get(
        f"/api/0/chronio/screenshots/{screenshot_bucket}/{event['id']}/image"
    )

    assert r.status_code == 404


def test_delete_chronio_screenshot_hour(
    flask_client, screenshot_bucket, tmp_path, monkeypatch
):
    monkeypatch.setenv("CHRONIO_SCREENSHOT_ROOT", str(tmp_path))
    image = tmp_path / "2026-05-22" / "frame.jpg"
    image.parent.mkdir()
    image.write_bytes(b"jpeg")
    timestamp = datetime.now() - timedelta(hours=1)
    start = timestamp.replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)
    event = _create_screenshot_event(
        flask_client, screenshot_bucket, "2026-05-22/frame.jpg", timestamp
    )

    r = flask_client.delete(
        f"/api/0/chronio/screenshots/{screenshot_bucket}",
        query_string={
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
    )

    assert r.status_code == 200
    assert r.json == {"deleted": 1}
    assert not image.exists()
    assert flask_client.get(
        f"/api/0/buckets/{screenshot_bucket}/events/{event['id']}"
    ).status_code == 404


# TODO: Add benchmark for basic AFK-filtering query
