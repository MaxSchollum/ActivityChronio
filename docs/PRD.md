# Chronio — Product Requirements Document

Chronio is a personal macOS activity tracker forked from ActivityWatch. Core goal: sit down on Monday and see exactly what you did at 3 PM on Wednesday last week. Group apps/tabs into productivity levels, see a productivity percentage. Inspired by Timing.app.

---

## What's Built Today

> All shipped features live on the `claude/romantic-neumann` branch.

| Feature | Status |
|---------|--------|
| Real data from AW server (window + AFK events) | Done |
| AFK filtering (not-afk overlap, >10% threshold) | Done |
| 3-column layout: sidebar / activities / timeline | Done |
| Prev/next day navigation + date picker | Done |
| Chrome/Safari/Firefox tab granularity | Done |
| Unified view: category > app > title hierarchy | Done |
| Chronological view: flat time-sorted events | Done |
| Timeline: proportional blocks, hour gridlines | Done |
| Auto-scroll to "now" / first event | Done |
| Gap detection (>15min = separate blocks) | Done |
| Click timeline block > scroll to chrono view | Done |
| Full-screen mode (no AW chrome) | Done |
| Category auto-classification from regex rules | Done |
| Sidebar category filter | Done |
| Search (substring on app/title) | Done |

---

## What's Built (as of 2026-03-30)

| Feature | Notes |
|---------|-------|
| Real data from AW server | Window + AFK events |
| AFK filtering | >10% not-afk threshold, clips to first overlap |
| 3-column layout | Sidebar / activity list / timeline |
| Day navigation + date picker | Prev/next + calendar input |
| Browser tab granularity | Chrome, Safari, Firefox |
| Unified + chronological views | Toggle between hierarchy and flat time-sort |
| Timeline | Proportional blocks, category colors, hour gridlines, gap detection |
| Live refresh + "Now" line | 60s interval (today only), now-line updates per minute |
| Timeline hover tooltip | App, title, category, time range, duration |
| Full-screen standalone mode | No ActivityWatch chrome, `localhost:5600` → `/chronio` |
| Drag-to-categorize | App rows + title rows → sidebar category, saves immediately |
| Toast + Undo | 4s auto-dismiss, Undo reverts and saves |
| Sidebar category CRUD | Create, rename, delete, subcategory via context menu |
| Color picker | Preset palette + custom hex |
| Right-click context menu | Score, color, rename, delete |
| Productivity score | Topbar %, green/yellow/red; "— ?" when no categories scored |
| Expand/collapse persists | localStorage |
| Sidebar category filter | Filters list + dims timeline |
| Search | Substring on app + title |
| Stats/Reports nav disabled | "Coming in V2" tooltip |
| "Uncategorized" terminology | Unified throughout |
| Softer default color palette | Work #22c55e, Media #ef4444, Comms #06b6d4 |
| Tab title format | "Service: Page Title" extracted from browser window titles |
| loginwindow filtered | + ScreenSaverEngine |
| First-run onboarding | 3-step overlay, dismissed to localStorage |

## What's NOT Built (open V1 issues)

| Gap | GitHub Issue |
|-----|-------------|
| Click entire category row to expand/collapse | [#28](https://github.com/MaxSchollum/ActivityChronio/issues/28) |
| Click selected category to deselect | [#29](https://github.com/MaxSchollum/ActivityChronio/issues/29) |
| Inline rename overlays name in-place | [#30](https://github.com/MaxSchollum/ActivityChronio/issues/30) |
| + button creates subcategory of selected folder | [#31](https://github.com/MaxSchollum/ActivityChronio/issues/31) |
| Drag category into another to reparent | [#32](https://github.com/MaxSchollum/ActivityChronio/issues/32) |
| Sub-item indentation improvements | [#33](https://github.com/MaxSchollum/ActivityChronio/issues/33) |
| Multi-select rows with Cmd+click | [#34](https://github.com/MaxSchollum/ActivityChronio/issues/34) |
| Auto-refresh without jarring blink | [#35](https://github.com/MaxSchollum/ActivityChronio/issues/35) |
| No screenshot capture | V2 |
| No week/month views | V2 |
| No macOS app packaging | V2 |

---

## V1 — "Daily Review"

**Goal:** Open Chronio on Monday, navigate to last Wednesday, see exactly what you did at 3 PM, and see that the day was 72% productive. Categories persist, drag-to-categorize works, no hand-written regex needed.

**Success criteria:** Can replace manual time-tracking. Feels like a product, not a prototype.

---

### V1-F01: Remove loginwindow

**Effort:** XS — <1 day

Hardcode-exclude `loginwindow` and `ScreenSaverEngine` from `activeWindowEvents` computed property. These are never real activity.

**File:** `Chronio.vue` — `activeWindowEvents` computed
**Approach:** Add post-filter: `events.filter(e => !['loginwindow', 'ScreenSaverEngine'].includes(e.data.app))`

---

### V1-F02: Drag-to-Categorize

**Effort:** M — 3-5 days

The core differentiator from ActivityWatch. Drag an app or title row from the center panel onto a sidebar category folder.

**User flow:**
1. See "The Atlantic" under Uncategorized in the center panel
2. Drag it onto "Media" in the sidebar
3. System creates regex rule `The Atlantic` on the Media category
4. Rule persists across all days (saved to server via `categoryStore.save()`)
5. All events for "The Atlantic" immediately re-classify

**Implementation:**
- HTML5 drag events on `.act-row--app` and `.act-row--title` rows (`draggable`, `@dragstart`)
- Drop targets on `.sidebar-cat-row` elements (`@dragover`, `@drop`)
- On drop: extract app name or title, escape regex chars, call `categoryStore.appendClassRule(catId, pattern)` then `categoryStore.save()`
- Visual feedback: highlight drop zone on dragover, green flash on success
- For title drags, use raw title (before `cleanTitle` strips browser suffix)

**Files:** `Chronio.vue` (template + methods), `categories.ts` (`appendClassRule` already exists)

---

### V1-F03: Productivity Score

**Effort:** S — 1-2 days

Display a productivity percentage in the topbar: "Productivity: 72%"

**How scoring works:**
- Categories have a `data.score` property (Work = 10, inherits to children)
- Score formula: `sum(event.duration * category_score) / (total_tracked_duration * 10) * 100`
- Categories with no score = neutral (0), negative scores for distracting activities
- Color: green (>=70%), yellow (40-70%), red (<40%)

**Implementation:**
- New computed `productivityScore` in `Chronio.vue`
- Uses `categoryStore.get_category_score()` which already traverses parents
- Display next to "Tracked: 6h 42m" in topbar

**Files:** `Chronio.vue` (computed + template)

---

### V1-F04: Timeline Category Colors

**Effort:** S — 1 day

Replace app gradient colors with category colors on timeline blocks. A block for VS Code under "Work > Programming" shows green (Work's color), not an arbitrary gradient.

**Why:** The timeline should communicate productivity at a glance. Green = productive, red = distracting.

**Implementation:**
- In `timeline` computed, classify each block's app+title using regex matching
- Use `categoryStore.get_category_color()` for the block color
- Derive a subtle gradient from the category color (lighten/darken 10%)

**Files:** `Chronio.vue` — `timeline` computed property

---

### V1-F05: Inline Category CRUD

**Effort:** M — 3-4 days

Replace `window.prompt` with proper inline editing. Add rename and delete.

**Features:**
- **Create:** Click `+` button > inline text input appears in sidebar > Enter to confirm
- **Subcategory:** Right-click category > "Add subcategory" > inline input
- **Rename:** Right-click > "Rename" > inline input pre-filled
- **Delete:** Right-click > "Delete" > confirm dialog (warn if has children)

**Implementation:**
- Context menu: simple positioned `<div>`, dismissed on click-outside
- Inline input: temporary reactive state in sidebar rendering
- Uses existing `categoryStore.addClass()`, `updateClass()`, `removeClass()`

**Files:** `Chronio.vue` (template + methods)

---

### V1-F06: Color Picker

**Effort:** S — 1-2 days

Click a category's color dot in the sidebar > popover with 12-16 preset colors + a "Custom" option (`<input type="color">`). Updates `category.data.color` via `categoryStore.updateClass()`.

**Files:** `Chronio.vue` (new popover, inline)

---

### V1-F07: Category Score Editor

**Effort:** S — 1 day

In the category context menu or color picker popover, add productivity setting:
- Productive (green, score=10)
- Neutral (gray, score=0)
- Distracting (red, score=-10)

Updates `category.data.score`. Inherits to children unless overridden.

**Files:** `Chronio.vue` — shares UI with F06
**Depends on:** V1-F06

---

### V1-F08: Live Refresh + "Now" Line

**Effort:** S — 1-2 days

- `setInterval` in `mounted()`: call `refresh()` every 60s when `isToday`
- "Now" line: red horizontal rule at current time position in timeline, updates every 60s
- Clear intervals on unmount and day navigation

**Files:** `Chronio.vue` (lifecycle + template)

---

### V1-F09: Timeline Hover Tooltip

**Effort:** S — 1 day

Hover a timeline block > tooltip shows app name, window title, category, time range, duration.

**Implementation:** `@mouseenter`/`@mouseleave` on `.tl-block`, positioned `<div>` with block data.

**Files:** `Chronio.vue`

---

### V1-F10: Persistent Expand/Collapse State

**Effort:** XS — <1 day

Store `expandedCats`, `expandedApps`, `sidebarExpanded` in `localStorage`. Restore on mount, debounce-write on change.

**Files:** `Chronio.vue` (watchers + mounted)

---

### V1-F11: First-Run Onboarding

**Effort:** S — 1-2 days

On first open (check `localStorage` flag), show a brief overlay:
1. "Welcome to Chronio"
2. "Drag apps into categories to classify them"
3. "Your productivity score updates automatically"

3 slides max, minimal. Teaches drag-to-categorize immediately.

**Files:** `Chronio.vue` or new `ChronioOnboarding.vue`
**Depends on:** V1-F02 (drag-to-categorize should exist)

---

### V1 Implementation Order

| # | Feature | Effort | Rationale |
|---|---------|--------|-----------|
| 1 | V1-F01 loginwindow fix | XS | Immediate data quality win |
| 2 | V1-F02 Drag-to-categorize | M | Core differentiator |
| 3 | V1-F03 Productivity score | S | Core metric |
| 4 | V1-F04 Timeline category colors | S | Visual coherence |
| 5 | V1-F05 Inline category CRUD | M | Essential for non-devs |
| 6 | V1-F06 Color picker | S | Category personalization |
| 7 | V1-F07 Score editor | S | Completes productivity system |
| 8 | V1-F08 Live refresh + now line | S | Feels alive |
| 9 | V1-F09 Timeline tooltip | S | Detail on demand |
| 10 | V1-F10 Persistent expand state | XS | Polish |
| 11 | V1-F11 First-run onboarding | S | Do last (references other features) |

**Estimated V1 total: ~3-4 weeks focused work**

---

## V2 — "Power User"

**Goal:** Chronio becomes a polished macOS app you'd recommend to others. Multi-day review, screenshots, proper packaging.

---

### V2-F01: Week & Month Views

**Effort:** L — 2-3 weeks

- **Week view:** 7 mini-timelines side by side, aggregated sidebar, week productivity score
- **Month view:** Calendar grid with mini productivity bars per day, click to drill into day view
- Route: `/chronio/:period?/:date?` (day/week/month)
- Extract day timeline into reusable `ChronioDay.vue` component

**Files:** New `ChronioDay.vue`, `ChronioWeek.vue`, `ChronioMonth.vue`, update `route.js`

---

### V2-F02: Productivity Trends

**Effort:** L — 2 weeks

Accessible from sidebar "Stats" nav item:
- Daily productivity line chart (30/90 days)
- Category breakdown stacked area chart
- Average tracked hours
- Most productive day-of-week / time-of-day heatmap

Uses existing `vue-chartjs` dependency and `query_category_time_by_period`.

**Files:** New `ChronioTrends.vue`
**Depends on:** V1-F03 (productivity scoring)

---

### V2-F03: Screenshot Capture

**Effort:** XL — 3-4 weeks

**Capture (new Python watcher: `aw-watcher-screenshot`):**
- macOS `screencapture` CLI, every 5 min while not-afk
- JPEG quality 60, 1280px wide (~150 KB each)
- Storage: `~/Library/Application Support/ActivityChronio/screenshots/YYYY-MM-DD/`
- New bucket: `aw-watcher-screenshot_{hostname}`
- ~22 MB/day, ~660 MB/month

**Viewing:**
- Filmstrip panel below timeline
- Click thumbnail > lightbox full-size
- Screenshot markers on timeline

**Privacy:**
- Local-only, never uploaded
- Hotkey to pause capture
- "Delete screenshots for this hour" option
- Configurable: interval, quality, max storage, auto-cleanup age

**Files:** New `aw-watcher-screenshot/` package, new `ChronioScreenshots.vue`, server static file endpoint

---

### V2-F04: macOS App Packaging

**Effort:** XL — 3-4 weeks

- PyInstaller .app bundle (rename to "Chronio")
- Custom menu bar icon
- Code signing + notarization (requires Apple Developer account)
- DMG with drag-to-Applications
- Sparkle auto-updates
- Login item (start on boot)
- `LSUIElement = true` (menu bar only, no dock icon)

**Files:** `aw-qt.spec`, `trayicon.py`, new build scripts, CI/CD pipeline

---

### V2-F05: Chronio Settings Page

**Effort:** M — 1-2 weeks

In-app settings (no more jumping to AW settings):
- Tracking: AFK timeout, always-active pattern, ignored apps
- Categories: import/export, restore defaults
- Appearance: start of day, start of week
- Screenshots: enable/disable, interval, storage limit
- Privacy: excluded apps, excluded title patterns
- Data: export as CSV/JSON

**Files:** New `ChronioSettings.vue`, update `settings.ts` with new keys

---

### V2-F06: Advanced Search

**Effort:** M — 1-2 weeks

- Fuzzy matching via Fuse.js
- Cross-day search ("when did I last visit AWS console?")
- Date range + category filters
- Search results panel replaces center column
- Cmd+F keyboard shortcut

---

### V2-F07: Export & Reports

**Effort:** M — 1 week

- CSV/JSON export of day/week/month data
- Weekly Report: printable summary with top categories, productivity trend, tracked hours
- `@media print` CSS for clean printing

**Depends on:** V2-F01 (week view data)

---

### V2 Implementation Order

| # | Feature | Effort |
|---|---------|--------|
| 1 | V2-F05 Settings page | M |
| 2 | V2-F01 Week/month views | L |
| 3 | V2-F02 Productivity trends | L |
| 4 | V2-F06 Advanced search | M |
| 5 | V2-F07 Export/reports | M |
| 6 | V2-F03 Screenshot capture | XL |
| 7 | V2-F04 macOS packaging | XL |

**Estimated V2 total: ~10-14 weeks focused work**

---

## Key Files Reference

| File | Role |
|------|------|
| `aw-server/aw-webui/src/views/activity/Chronio.vue` | Main view (~1135 lines). Nearly all V1 work happens here. |
| `aw-server/aw-webui/src/stores/categories.ts` | Category CRUD, `appendClassRule()`, `save()`, color/score getters |
| `aw-server/aw-webui/src/util/classes.ts` | Category model, `matchString()` regex matching, default categories, hierarchy building |
| `aw-server/aw-webui/src/util/color.ts` | Color resolution: predefined map, hash-based fallback, category parent chain |
| `aw-server/aw-webui/src/stores/settings.ts` | Settings persistence (server + localStorage) |
| `aw-server/aw-webui/src/stores/activity.ts` | Activity data loading, query execution |
| `aw-server/aw-webui/src/queries.ts` | AWScript query builders for desktop/Android |
| `aw-server/aw-webui/src/route.js` | Vue Router — `/chronio` route with `fullContainer: true` |
