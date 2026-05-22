aw-watcher-screenshot
=====================

Captures local Chronio screenshots on macOS while ActivityWatch confirms the
user is not AFK.

The watcher stores JPEG files below:

`~/Library/Application Support/ActivityChronio/screenshots/YYYY-MM-DD/`

It creates the ActivityWatch bucket
`aw-watcher-screenshot_{hostname}` with bucket type `screenshot`. Screenshot
events use zero duration and store a controlled file reference in metadata:

```json
{
  "file_key": "YYYY-MM-DD/YYYY-MM-DDTHH-MM-SS.mmmZ.jpg",
  "mime_type": "image/jpeg",
  "width": 1280,
  "height": 720,
  "byte_size": 153600
}
```

`file_key` is always relative to the screenshot root. Absolute screenshot
paths are not written to ActivityWatch event data.

## Settings

The watcher reads the ActivityWatch settings written by Chronio:

- `chronioScreenshotsEnabled` must be enabled before any capture.
- `chronioScreenshotIntervalSeconds` controls the loop interval when set to a
  positive number. Otherwise the watcher falls back to five minutes.
- `chronioScreenshotQuality` controls JPEG quality from 1 to 100. Otherwise
  the watcher falls back to the PRD quality of 60.
- `chronioScreenshotRetentionDays` removes screenshot files and events older
  than the configured age while the watcher is enabled.
- `chronioScreenshotStorageLimitMb` removes the oldest remaining screenshot
  files and events while their disk usage exceeds the configured limit.

Every capture also requires an `aw-watcher-afk_{hostname}` event covering the
capture timestamp with `data.status == "not-afk"`. Missing, stale, AFK, or
unreadable AFK state skips capture.

The watcher-local pause state is stored as the ActivityWatch setting
`chronioScreenshotCapturePaused`. Use the watcher CLI to persist it:

```sh
poetry run aw-watcher-screenshot --pause
poetry run aw-watcher-screenshot --resume
```

The maximum capture width stays fixed at the PRD default of 1280px. The
Chronio day-view shortcut and the watcher CLI both use the pause setting.

## Run

From this directory:

```sh
poetry install
poetry run aw-watcher-screenshot
```

The default backend shells out to macOS `screencapture` and `sips`.
