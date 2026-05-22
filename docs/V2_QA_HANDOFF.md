# Chronio V2 QA Handoff

Status: 2026-05-22

## Code State

V2 feature scope is on `master` at `39916e5`.

| Ticket | Scope | Master merge |
| --- | --- | --- |
| #13 | Week and month review | `5b0533d` |
| #14 | Productivity trends | `05bcd3f` |
| #15 | Screenshot watcher and viewer | `39916e5` |
| #16 | macOS packaging path | `bdadea8` |
| #17 | In-app settings | `553ca23` |
| #18 | Advanced search | `ca8b8e4` |
| #19 | Export and weekly reports | `d88d9d7` |
| #47 | Rules manager | `b33d1fb` |
| #48 | Daily category goals | `738cb77` |
| #49 | Away timeline blocks | `c46ff0b` |
| #50 | Sidebar category sparklines | `ff7dd89` |
| #51 | Keyboard shortcuts | `1b0da08` |
| #66 | Browser sub-context grouping | `64102b8` |
| #70 | Shared V2 regression coverage | `8f2e3a8` |

## Verification Run

Run on the final V2 code state or the equivalent verified #15 integration
state immediately before the `master` merge:

| Command or check | Result |
| --- | --- |
| `cd aw-server/aw-webui && npm run build` | Passes with existing Browserslist, Babel, missing `static/`, Prettier, and asset-size warnings |
| `cd aw-watcher-screenshot && make test` | Passes: screenshot watcher AFK gating, pause state, cleanup, retention, storage, and quality setting coverage |
| `cd aw-server && poetry run pytest tests/test_server.py -k chronio_screenshot` | Passes: screenshot image route, traversal rejection, and delete-hour route |
| `python3 -m py_compile aw-qt/aw_qt/config.py aw.spec aw-watcher-screenshot/aw_watcher_screenshot/capture.py aw-watcher-screenshot/aw_watcher_screenshot/watcher.py` | Passes |
| Browser check against local test server | Settings shows screenshot interval, quality, storage, and cleanup controls; Day view shows filmstrip empty state; `Shift+P` shows pause/resume toast; stale Stats "Coming in V2" tooltip removed |
| `make dist/Chronio.app` | Blocked on this machine: `pyinstaller: command not found` before artifact creation |

## QA Focus

- Load Day, Week, Month, Stats, Reports, Settings, Rules, and Search routes
  directly and through Chronio navigation.
- Recheck Day review regressions: AFK filtering, away blocks, search, category
  filtering, timeline rendering, drag-to-categorize, goals, and sidebar
  sparklines.
- In Settings, change screenshot enablement, interval, JPEG quality, storage
  limit, and cleanup age; reload and confirm those values persist.
- With Screen Recording permission granted on macOS, confirm the screenshot
  watcher captures only during not-AFK time and writes under
  `~/Library/Application Support/ActivityChronio/screenshots/YYYY-MM-DD/`.
- Confirm Day filmstrip ordering, lightbox timestamp, timeline markers, and
  delete-hour removing both screenshot files and bucket events.
- Run the packaged-app path once the packaging toolchain is installed:
  `make dist/Chronio.app` or `make dist/Chronio.dmg`.

## Residual Risks

| Risk | Severity | Owner |
| --- | --- | --- |
| Local package artifact was not produced in this handoff because PyInstaller is missing | Medium | Release verification |
| Signing and notarization require Apple Developer credentials | High | Release engineering |
| Screenshot capture depends on macOS Screen Recording permission | High | QA |
| Real screenshot capture, permission-denied UX, and packaged watcher autostart need a macOS package run | Medium | QA |
| Large-range advanced search and trends should be spot-checked with a mature local dataset | Medium | QA |

## Deliberate Deferrals

- Gatekeeper-clean signed/notarized distribution is not asserted without the
  Apple Developer signing and notarization inputs.
- Encryption at rest for screenshots remains outside V2 scope.
