<template lang="pug">
div.chronio-view
  .chronio-topbar
    .chronio-brand
      .chronio-logo
      span Chronio
    .chronio-topbar-right
      .chronio-date-nav
        button.chronio-nav-btn(@click="prevDay") &larr;
        .chronio-chip.date(@click="showDatePicker = !showDatePicker")
          span {{ dateDisplay }}
          input.date-input(
            v-if="showDatePicker"
            type="date"
            :value="selectedDate"
            @input="onDateChange($event.target.value)"
            @blur="showDatePicker = false"
          )
        button.chronio-nav-btn(@click="nextDay" :disabled="isToday") &rarr;
      .chronio-metric
        span.label Tracked:
        span.value {{ totalTrackedTime }}
      .chronio-search
        input(type="text" placeholder="Search…" v-model="searchQuery")

  div.chronio-loading(v-if="loading")
    span Loading activity data&hellip;

  .chronio-body(v-else)

    //- ─── LEFT SIDEBAR ───────────────────────────────────────────────
    .chronio-sidebar
      nav.sidebar-nav
        .sidebar-nav-item.active Activities
        .sidebar-nav-item Stats
        .sidebar-nav-item Reports

      .sidebar-tree
        .sidebar-summary-row(
          @click="selectedCatFilter = null"
          :class="{active: selectedCatFilter === null}"
        )
          span.sr-name All Activities
          span.sr-time {{ totalTrackedTime }}
        .sidebar-summary-row(
          @click="selectedCatFilter = '__unassigned__'"
          :class="{active: selectedCatFilter === '__unassigned__'}"
        )
          span.sr-name Unassigned
          span.sr-time {{ unassignedTime }}

        .sidebar-divider

        .sidebar-section-header
          span Projects
          button.sidebar-add-btn(@click.stop="createTopCategory") +

        template(v-for="row in sidebarFlatTree" :key="row.key")
          //- Inline-create row (#38)
          .sidebar-inline-create(
            v-if="row.isInlineCreate"
            :style="{paddingLeft: (row.depth * 14 + 10) + 'px'}"
          )
            span.sr-expand-spacer
            .sr-dot(:style="{background: '#4b8bff'}")
            input.sr-rename-input(
              ref="inlineCreateInput"
              :value="inlineCreateValue"
              placeholder="Name…"
              @input="inlineCreateValue = $event.target.value"
              @keydown.enter.prevent="commitInlineCreate"
              @keydown.escape.prevent="cancelInlineCreate"
              @blur="cancelInlineCreate"
              @click.stop
            )

          //- Normal category row
          .sidebar-cat-row(
            v-else
            draggable="true"
            :style="{paddingLeft: (row.depth * 14 + 10) + 'px'}"
            :class="{active: selectedCatFilter === row.key, 'drop-target': dragOverCatKey === row.key}"
            @click="onSidebarRowClick(row)"
            @dblclick.stop="startRename(row)"
            @contextmenu.prevent="onSidebarRowRightClick(row, $event)"
            @dragstart="onSidebarDragStart(row, $event)"
            @dragenter.prevent="onSidebarDragOver(row, $event)"
            @dragover.prevent="onSidebarDragOver(row, $event)"
            @dragleave="dragOverCatKey = null"
            @drop.prevent="onSidebarDrop(row, $event)"
          )
            span.sr-expand-btn(v-if="row.hasChildren" @click.stop="toggleSidebarExpand(row)") {{ sidebarExpanded[row.key] ? '▾' : '▸' }}
            span.sr-expand-spacer(v-else)
            .sr-dot(
              :style="{background: row.color}"
              @click.stop="openColorPicker(row, $event)"
            )
            input.sr-rename-input(
              v-if="renamingKey === row.key"
              ref="renameInput"
              :value="renameValue"
              @input="renameValue = $event.target.value"
              @keydown.enter.prevent="commitRename(row)"
              @keydown.escape.prevent="cancelRename"
              @blur="cancelRename"
              @click.stop
            )
            span.sr-name(v-else) {{ row.label }}
            span.sr-score-dot(
              v-if="row.score !== 0"
              :class="row.score > 0 ? 'score-productive' : 'score-distracting'"
              :title="row.score > 0 ? 'Productive' : 'Distracting'"
            )
            span.sr-time {{ row.time }}
            span.sr-drag-handle(
              draggable="true"
              @dragstart.stop="onHandleDragStart(row, $event)"
              @click.stop
              title="Drag to reorder"
            ) ⠿

        //- Context menu
        .sidebar-ctx-menu(
          v-if="ctxMenu"
          :style="{top: ctxMenu.y + 'px', left: ctxMenu.x + 'px'}"
          @click.stop
        )
          .ctx-item(@click="startRename(ctxMenu.row)") Rename
          .ctx-item(@click="createChildCategory(ctxMenu.row)") Add subcategory
          .ctx-divider
          .ctx-score-row
            span Score:
            button.ctx-score-btn(
              :class="{active: ctxMenu.row.score > 0}"
              @click="setCategoryScore(ctxMenu.row, 10)"
            ) Productive
            button.ctx-score-btn.neutral(
              :class="{active: ctxMenu.row.score === 0}"
              @click="setCategoryScore(ctxMenu.row, 0)"
            ) Neutral
            button.ctx-score-btn.distracting(
              :class="{active: ctxMenu.row.score < 0}"
              @click="setCategoryScore(ctxMenu.row, -10)"
            ) Distracting
          .ctx-divider
          .ctx-item.ctx-danger(@click="deleteCategory(ctxMenu.row)") Delete

        //- Color picker popover (#7)
        .color-picker-popover(
          v-if="colorPickerRow"
          :style="{top: colorPickerPos.y + 'px', left: colorPickerPos.x + 'px'}"
          @click.stop
        )
          .cp-swatches
            .cp-swatch(
              v-for="c in COLOR_SWATCHES"
              :key="c"
              :style="{background: c}"
              :class="{selected: colorPickerRow && colorPickerRow.color === c}"
              @click="applyColor(c)"
            )
          .cp-custom
            label Custom:
            input(type="color" :value="colorPickerRow ? colorPickerRow.color : '#ffffff'" @input="applyColor($event.target.value)")

    //- ─── CENTER: ALL ACTIVITIES ─────────────────────────────────────
    .chronio-center(@click.self="clearSelection")
      .center-header
        .center-title
          | {{ selectedCatFilter && selectedCatFilter !== '__unassigned__' ? selectedCatFilter.split('>').pop() : 'All Activities' }}:&nbsp;
          strong {{ totalTrackedTime }}
        .view-toggle
          button(:class="{active: viewMode === 'unified'}" @click="viewMode = 'unified'") Unified
          button(:class="{active: viewMode === 'apps'}" @click="viewMode = 'apps'") Apps
          button(:class="{active: viewMode === 'chrono'}" @click="viewMode = 'chrono'") Chrono

      //- Empty state (#45)
      .act-day-empty(v-if="!loading && !activeWindowEvents.length")
        .act-empty-icon ○
        p(v-if="isFuture") No data yet for this day
        p(v-else) No activity recorded for {{ dateDisplay }}
        button.act-empty-prev(@click="goToPrevActiveDay") ← Previous day with data

      .activities-scroll(v-else ref="activitiesScroll" @click.self="clearSelection")
        //- UNIFIED VIEW
        template(v-if="viewMode === 'unified'")
          .act-empty(v-if="!filteredActivitiesTree.length") No activity data for this period
          template(v-else v-for="catNode in filteredActivitiesTree" :key="catNode.catKey")
            .act-row.act-row--cat(
              @click="toggleExpandCat(catNode.catKey)"
              :class="{expanded: expandedCats[catNode.catKey]}"
            )
              span.act-expand {{ expandedCats[catNode.catKey] ? '▾' : '▸' }}
              .act-dot(:style="{background: catNode.color}")
              span.act-name {{ catNode.catLabel }}
              span.act-dur {{ formatDuration(catNode.duration) }}

            template(v-if="expandedCats[catNode.catKey]" v-for="appNode in catNode.apps" :key="catNode.catKey + '/' + appNode.app")
              .act-row.act-row--app(
                draggable="true"
                :class="{'row-selected': selectedRowKeys[appRowKey(catNode.catKey, appNode.app)]}"
                @click="toggleExpandApp(catNode.catKey + '/' + appNode.app)"
                @dragstart="onDragStartApp(appNode, $event)"
                @dragend="onDragEnd"
              )
                .act-indent
                span.act-expand(v-if="appNode.titles && appNode.titles.length") {{ expandedApps[catNode.catKey + '/' + appNode.app] ? '▾' : '▸' }}
                span.act-expand-spacer(v-else)
                .act-app-icon(:style="{background: appNode.color}")
                span.act-name {{ appNode.app }}
                span.act-drag-hint ↖
                span.act-dur {{ formatDuration(appNode.duration) }}

              template(v-if="expandedApps[catNode.catKey + '/' + appNode.app]" v-for="t in appNode.titles" :key="catNode.catKey + '/' + appNode.app + '/' + t.title")
                .act-row.act-row--title(
                  draggable="true"
                  :class="{'row-selected': selectedRowKeys[titleRowKey(catNode.catKey, appNode.app, t.title)]}"
                  @click="onActivityRowClick(titleRowKey(catNode.catKey, appNode.app, t.title), {type:'title', app: appNode.app, title: t.title, rawTitle: t.title}, $event)"
                  @dragstart="onDragStartTitle(appNode.app, t, $event)"
                  @dragend="onDragEnd"
                )
                  .act-indent2
                  span.act-title(:title="t.title") {{ t.title }}
                  span.act-dur {{ formatDuration(t.duration) }}

        //- APPS VIEW (#40) — flat app list sorted by time
        template(v-else-if="viewMode === 'apps'")
          .act-empty(v-if="!flatAppsList.length") No activity data for this period
          template(v-else v-for="appNode in flatAppsList" :key="'flat/' + appNode.app")
            .act-row.act-row--app(
              draggable="true"
              :class="{'row-selected': selectedRowKeys['flat/' + appNode.app]}"
              @click="onActivityRowClick('flat/' + appNode.app, {type:'app', app: appNode.app, title: ''}, $event)"
              @dragstart="onDragStartApp(appNode, $event)"
              @dragend="onDragEnd"
            )
              span.act-expand(@click.stop="toggleExpandApp('flat/' + appNode.app)") {{ expandedApps['flat/' + appNode.app] ? '▾' : '▸' }}
              .act-app-icon(:style="{background: appNode.color}")
              span.act-name {{ appNode.app }}
              span.act-drag-hint ↖
              span.act-dur {{ formatDuration(appNode.duration) }}
            template(v-if="expandedApps['flat/' + appNode.app]" v-for="t in appNode.titles" :key="'flat/' + appNode.app + '/' + t.title")
              .act-row.act-row--title(
                draggable="true"
                :class="{'row-selected': selectedRowKeys['flat/' + appNode.app + '/' + t.title]}"
                @click="onActivityRowClick('flat/' + appNode.app + '/' + t.title, {type:'title', app: appNode.app, title: t.title, rawTitle: t.title}, $event)"
                @dragstart="onDragStartTitle(appNode.app, t, $event)"
                @dragend="onDragEnd"
              )
                .act-indent2
                span.act-title(:title="t.title") {{ t.title }}
                span.act-dur {{ formatDuration(t.duration) }}

        //- CHRONOLOGICAL VIEW — grouped by merged timeline block, expandable
        template(v-else)
          .act-empty(v-if="!chronoGrouped.length") No activity data for this period
          template(v-else v-for="group in chronoGrouped" :key="group.key")
            .act-row.act-row--chrono-group(
              :data-startms="group.startMs"
              @click="toggleChronoBlock(group.key)"
            )
              span.act-caret {{ expandedTimelineBlocks[group.key] ? '▾' : '▸' }}
              .act-app-icon(:style="{background: group.color}")
              span.act-app {{ group.label }}
              span.act-time-range {{ group.range }}
              span.act-dur {{ formatDuration((group.endMs - group.startMs) / 1000) }}

            template(v-if="expandedTimelineBlocks[group.key]" v-for="e in group.subEvents" :key="e.timestamp + e.data.title")
              .act-row.act-row--chrono-sub
                .act-indent
                span.act-app-label {{ e.data.app }}:
                span.act-title(:title="e.data.title") {{ cleanTitle(e.data.title || '', e.data.app || '') }}
                span.act-time {{ formatHHMM(e.timestamp) }}
                span.act-dur {{ formatDuration(e.duration) }}

    //- ─── RIGHT: TIMELINE ────────────────────────────────────────────
    .chronio-timeline-panel
      .timeline-scroll(ref="timelineScroll")
        .chronio-empty(v-if="!timeline.length && !activeWindowEvents.length") —
        .chronio-empty(v-else-if="!timeline.length") No events long enough to display
        .timeline-canvas(v-else :style="{height: timelineCanvas.totalHeight + 'px'}")
          //- Hour gridlines + labels
          .tl-hour(
            v-for="h in timelineCanvas.hours"
            :key="h.h"
            :style="{top: h.top + 'px'}"
          )
            span.tl-hour-label {{ h.label }}
            .tl-hour-line
          //- Current time indicator
          .tl-now-line(
            v-if="timelineCanvas.nowPx !== null"
            :style="{top: timelineCanvas.nowPx + 'px'}"
          )
          //- Activity blocks
          .tl-block(
            v-for="block in timelineCanvas.blocks"
            :key="'b-' + block.label + block.range"
            :style="{background: block.color, top: block.top + 'px', height: block.heightPx + 'px'}"
            :title="blockTooltip(block)"
            @click="onTimelineBlockClick(block)"
          )
            .tl-block-inner(v-if="block.heightPx > 20")
              .tl-title {{ block.label }}
              .tl-time-range(v-if="block.heightPx > 38") {{ block.range }}

  //- ── ONBOARDING MODAL (#12) ──────────────────────────────────────────
  .onboarding-overlay(v-if="showOnboarding" @click.self="dismissOnboarding")
    .onboarding-modal
      .onboarding-step(v-if="onboardingStep === 0")
        .ob-emoji 🕐
        h2 Welcome to Chronio
        p Your personal activity tracker. See exactly what you worked on, when, and for how long.
      .onboarding-step(v-else-if="onboardingStep === 1")
        .ob-emoji 🗂️
        h2 Organize your work
        p Drag any app or tab from the center panel into a project folder on the left to categorize it. Chronio remembers the rule for every future day.
      .onboarding-step(v-else-if="onboardingStep === 2")
        .ob-emoji 📊
        h2 Your productivity score
        p Right-click any project folder to mark it Productive or Distracting. Your daily score updates automatically.
      .ob-dots
        span.ob-dot(v-for="i in 3" :key="i" :class="{active: onboardingStep === i - 1}" @click="onboardingStep = i - 1")
      .ob-actions
        button.ob-btn-ghost(v-if="onboardingStep > 0" @click="onboardingStep--") Back
        button.ob-btn-primary(v-if="onboardingStep < 2" @click="onboardingStep++") Next
        button.ob-btn-primary(v-else @click="dismissOnboarding") Get started
</template>

<script lang="ts">
import moment from 'moment';
import _ from 'lodash';
import { useActivityStore } from '~/stores/activity';
import { useBucketsStore } from '~/stores/buckets';
import { useCategoryStore } from '~/stores/categories';
import { useSettingsStore } from '~/stores/settings';
import { get_today_with_offset } from '~/util/time';
import { dateToTimeperiod } from '~/util/timeperiod';
import { getColorFromString } from '~/util/color';
import { getClient } from '~/util/awclient';

// System processes that are never real user activity
const SYSTEM_PROCESS_BLOCKLIST = new Set(['loginwindow', 'ScreenSaverEngine']);

// Color swatches for the color picker (#7)
const COLOR_SWATCHES = [
  '#4b8bff', '#8a3bff', '#ff6a1f', '#ff4f9a', '#1db954',
  '#0ea5e9', '#f59e0b', '#e6683c', '#a855f7', '#ec4899',
  '#14b8a6', '#ef4444', '#84cc16', '#f97316', '#64748b',
];

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

const GRADIENTS: string[] = [
  'linear-gradient(135deg, #3c7bff, #5aa1ff)',
  'linear-gradient(135deg, #8a3bff, #c04cff)',
  'linear-gradient(135deg, #ff6a1f, #ff9447)',
  'linear-gradient(135deg, #ff4f9a, #ff7bc2)',
  'linear-gradient(135deg, #1db954, #2fe07b)',
  'linear-gradient(135deg, #e6683c, #f0956e)',
  'linear-gradient(135deg, #0ea5e9, #38bdf8)',
  'linear-gradient(135deg, #f59e0b, #fbbf24)',
];

const HOUR_PX = 56; // pixels per hour on the timeline canvas
const MAX_MERGE_GAP_MS = 15 * 60 * 1000; // don't merge same-app blocks separated by >15 min

// Browser names to strip from window titles
const BROWSER_SUFFIXES = [
  'Google Chrome', 'Chrome', 'Safari', 'Firefox', 'Arc',
  'Brave Browser', 'Microsoft Edge', 'Opera',
];

function formatDuration(seconds: number): string {
  if (!seconds || seconds < 1) return '0s';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function formatHHMM(ts: any): string {
  return moment(ts).format('HH:mm');
}

function gradientForApp(app: string, index: number): string {
  return GRADIENTS[index % GRADIENTS.length];
}

export default {
  name: 'ChronioView',

  data() {
    return {
      selectedDate: '' as string,
      searchQuery: '' as string,
      showDatePicker: false as boolean,
      loading: true as boolean,
      selectedEvent: null as any,
      windowEvents: [] as any[],
      afkEvents: [] as any[],
      // expand/filter state
      expandedCats: {} as Record<string, boolean>,
      expandedApps: {} as Record<string, boolean>,
      expandedTimelineBlocks: {} as Record<string, boolean>,
      sidebarExpanded: {} as Record<string, boolean>,
      selectedCatFilter: null as string | null,
      viewMode: 'unified' as 'unified' | 'apps' | 'chrono',
      // inline rename state (#6 / #30)
      renamingKey: null as string | null,
      renameValue: '' as string,
      // inline create state (#38)
      inlineCreateParent: null as string | null,
      inlineCreateValue: '' as string,
      // context menu state
      ctxMenu: null as { row: any; x: number; y: number } | null,
      // color picker state (#7)
      colorPickerRow: null as any,
      colorPickerPos: { x: 0, y: 0 },
      COLOR_SWATCHES: COLOR_SWATCHES,
      // drag-drop state (#3)
      dragOverCatKey: null as string | null,
      // multi-select state (#37)
      selectedRowKeys: {} as Record<string, boolean>,
      selectedRowPayloads: {} as Record<string, any>,
      lastClickedKey: null as string | null,
      // drag-category state (#32)
      draggingSidebarKey: null as string | null,
      // sidebar reorder state (#46)
      reorderDragKey: null as string | null,
      reorderDropKey: null as string | null,
      // onboarding state (#12)
      showOnboarding: false as boolean,
      onboardingStep: 0 as number,
      // live refresh (#9)
      refreshTimer: null as any,
      // #35: guard to skip silent refresh if a full refresh is already in flight
      isRefreshing: false as boolean,
      // keyboard handler ref (#44)
      keyHandler: null as any,
    };
  },

  computed: {
    activityStore() { return useActivityStore(); },
    bucketsStore() { return useBucketsStore(); },
    settingsStore() { return useSettingsStore(); },
    categoryStore() { return useCategoryStore(); },

    isToday(): boolean {
      return moment(this.selectedDate).isSame(moment(), 'day');
    },

    isFuture(): boolean {
      return moment(this.selectedDate).isAfter(moment(), 'day');
    },

    host(): string {
      const hosts = this.bucketsStore.hosts;
      for (const h of hosts) {
        if (
          this.bucketsStore.bucketsWindow(h).length > 0 &&
          this.bucketsStore.bucketsAFK(h).length > 0
        ) return h;
      }
      return hosts.length > 0 ? hosts[0] : '';
    },

    dateDisplay(): string {
      if (!this.selectedDate) return '—';
      return moment(this.selectedDate).format('MMM D, YYYY');
    },

    // AFK intervals for the day
    notAfkIntervals(): { start: number; end: number }[] {
      return (this.afkEvents || [])
        .filter((e: any) => e.data?.status === 'not-afk' && e.duration > 0)
        .map((e: any) => ({
          start: moment(e.timestamp).valueOf(),
          end: moment(e.timestamp).add(e.duration, 'seconds').valueOf(),
        }));
    },

    // Full-day AFK-filtered window events (no segment restriction)
    activeWindowEvents(): any[] {
      const events = this.windowEvents || [];
      const intervals = this.notAfkIntervals;
      return events.filter((e: any) => {
        if (SYSTEM_PROCESS_BLOCKLIST.has(e.data?.app)) return false;
        const eStart = moment(e.timestamp).valueOf();
        const eEnd = eStart + e.duration * 1000;
        const totalNotAfk = intervals.reduce((sum: number, iv: any) => {
          return sum + Math.max(0, Math.min(eEnd, iv.end) - Math.max(eStart, iv.start));
        }, 0);
        const eventDur = eEnd - eStart;
        return totalNotAfk > 0 && totalNotAfk / eventDur > 0.1;
      });
    },

    totalTrackedTime(): string {
      const total = (this.activeWindowEvents as any[]).reduce(
        (sum: number, e: any) => sum + (e.duration || 0), 0
      );
      return formatDuration(total);
    },

    // ─── ACTIVITIES TREE ─────────────────────────────────────────────
    // Builds category → app → title hierarchy from AFK-filtered events
    activitiesTree(): any[] {
      const events: any[] = this.activeWindowEvents;
      const categories: any[] = (this.categoryStore as any).classes;

      // Pre-compile regexes once; strip Python-style inline flags like (?m) which are invalid in JS
      const regexes: [any, RegExp][] = categories
        .filter((c: any) => c.rule?.type === 'regex' && c.rule.regex)
        .flatMap((c: any) => {
          try {
            const pattern = c.rule.regex.replace(/\(\?[imsx]+\)/g, '');
            return [[c, new RegExp(pattern, (c.rule.ignore_case ? 'i' : '') + 'm')]];
          } catch (e) {
            console.warn('Invalid category regex:', c.rule.regex, e);
            return [];
          }
        });

      const catMap: Record<string, any> = {};

      for (const e of events) {
        const app: string = e.data?.app || 'Unknown';
        const rawTitle: string = e.data?.title || '';
        const title: string = this.cleanTitle(rawTitle, app);
        const dur: number = e.duration || 0;

        // Classify: app name + raw title
        const str = app + '\n' + rawTitle;
        const matches = regexes.filter(([, re]: [any, RegExp]) => re.test(str));
        const catName: string[] = matches.length > 0
          ? (_.maxBy(matches, ([c]: [any, RegExp]) => (c as any).name.length) as any)[0].name
          : ['Uncategorized'];
        const catKey = catName.join('>');

        if (!catMap[catKey]) {
          catMap[catKey] = {
            catKey,
            catLabel: catName[catName.length - 1],
            category: catName,
            color: (this.categoryStore as any).get_category_color(catName),
            duration: 0,
            apps: {},
          };
        }
        catMap[catKey].duration += dur;

        if (!catMap[catKey].apps[app]) {
          catMap[catKey].apps[app] = {
            app,
            color: getColorFromString(app),
            duration: 0,
            titles: {} as Record<string, number>,
          };
        }
        catMap[catKey].apps[app].duration += dur;
        catMap[catKey].apps[app].titles[title] =
          (catMap[catKey].apps[app].titles[title] || 0) + dur;
      }

      return Object.values(catMap)
        .sort((a: any, b: any) => b.duration - a.duration)
        .map((cat: any) => ({
          ...cat,
          apps: Object.values(cat.apps)
            .sort((a: any, b: any) => b.duration - a.duration)
            .map((app: any) => ({
              ...app,
              titles: Object.entries(app.titles as Record<string, number>)
                .sort(([, a], [, b]) => (b as number) - (a as number))
                .map(([title, dur]) => ({ title, duration: dur })),
            })),
        }));
    },

    filteredActivitiesTree(): any[] {
      let tree: any[] = this.activitiesTree;

      if (this.selectedCatFilter === '__unassigned__') {
        tree = tree.filter((n: any) => n.category[0] === 'Uncategorized');
      } else if (this.selectedCatFilter) {
        const f = this.selectedCatFilter;
        tree = tree.filter((n: any) => n.catKey === f || n.catKey.startsWith(f + '>'));
      }

      if (this.searchQuery) {
        const q = this.searchQuery.toLowerCase();
        tree = tree
          .map((cat: any) => ({
            ...cat,
            apps: cat.apps
              .map((a: any) => ({
                ...a,
                titles: a.titles.filter(
                  (t: any) =>
                    a.app.toLowerCase().includes(q) || t.title.toLowerCase().includes(q)
                ),
              }))
              .filter(
                (a: any) =>
                  a.app.toLowerCase().includes(q) || a.titles.length > 0
              ),
          }))
          .filter((cat: any) => cat.apps.length > 0);
      }

      return tree;
    },

    // Duration per category key (including parent accumulation)
    categoryDurations(): Record<string, number> {
      const result: Record<string, number> = {};
      for (const node of this.activitiesTree as any[]) {
        const name: string[] = node.category;
        for (let i = 1; i <= name.length; i++) {
          const key = name.slice(0, i).join('>');
          result[key] = (result[key] || 0) + node.duration;
        }
      }
      return result;
    },

    unassignedTime(): string {
      const uncat = (this.activitiesTree as any[]).find(
        (n: any) => n.category[0] === 'Uncategorized'
      );
      return uncat ? formatDuration(uncat.duration) : '';
    },

    // Flat sidebar tree respecting expand/collapse state
    sidebarFlatTree(): any[] {
      const rows: any[] = [];
      const durations: Record<string, number> = this.categoryDurations;
      const expanded: Record<string, boolean> = this.sidebarExpanded;
      const catStore = this.categoryStore as any;

      const flatten = (cats: any[], depth: number) => {
        for (const cat of cats) {
          const key: string = cat.name.join('>');
          const dur = durations[key] || 0;
          const score = catStore.get_category_score(cat.name);
          rows.push({
            key,
            id: cat.id,
            label: cat.name[cat.name.length - 1],
            fullName: cat.name,
            depth,
            color: catStore.get_category_color(cat.name),
            hasChildren: cat.children && cat.children.length > 0,
            time: dur > 0 ? formatDuration(dur) : '',
            score,
          });
          if (expanded[key] && cat.children && cat.children.length > 0) {
            flatten(cat.children, depth + 1);
          }
        }
      };

      flatten(catStore.classes_hierarchy, 0);

      // Inject inline-create row at the right position (#38)
      if (this.inlineCreateParent !== null) {
        const parentKey = this.inlineCreateParent;
        let insertIdx = rows.length;
        let depth = 0;
        if (parentKey !== '') {
          const parentIdx = rows.findIndex((r: any) => r.key === parentKey);
          if (parentIdx >= 0) {
            depth = rows[parentIdx].depth + 1;
            insertIdx = parentIdx + 1;
            while (insertIdx < rows.length && rows[insertIdx].depth >= depth) insertIdx++;
          }
        }
        rows.splice(insertIdx, 0, {
          key: '__inline_create__',
          id: -1,
          label: '',
          depth,
          isInlineCreate: true,
          color: '#4b8bff',
          hasChildren: false,
          time: '',
          score: 0,
          fullName: [],
        });
      }

      return rows;
    },

    // #40: Flat app list sorted by total time
    flatAppsList(): any[] {
      const appMap: Record<string, any> = {};
      for (const cat of this.filteredActivitiesTree as any[]) {
        for (const appNode of cat.apps) {
          if (!appMap[appNode.app]) {
            appMap[appNode.app] = { app: appNode.app, color: appNode.color, duration: 0, titles: [] as any[] };
          }
          appMap[appNode.app].duration += appNode.duration;
          for (const t of appNode.titles) {
            const existing = appMap[appNode.app].titles.find((x: any) => x.title === t.title);
            if (existing) existing.duration += t.duration;
            else appMap[appNode.app].titles.push({ ...t });
          }
        }
      }
      return Object.values(appMap)
        .sort((a: any, b: any) => b.duration - a.duration)
        .map((a: any) => ({ ...a, titles: [...a.titles].sort((x: any, y: any) => y.duration - x.duration) }));
    },

    // #37: ordered list of visible row keys for shift-range select
    visibleActivityRowKeys(): { key: string; payload: any }[] {
      const result: { key: string; payload: any }[] = [];
      if (this.viewMode === 'unified') {
        for (const catNode of this.filteredActivitiesTree as any[]) {
          if (!this.expandedCats[catNode.catKey]) continue;
          for (const appNode of catNode.apps) {
            const aKey = this.appRowKey(catNode.catKey, appNode.app);
            result.push({ key: aKey, payload: { type: 'app', app: appNode.app, title: '' } });
            if (this.expandedApps[catNode.catKey + '/' + appNode.app]) {
              for (const t of appNode.titles) {
                result.push({
                  key: this.titleRowKey(catNode.catKey, appNode.app, t.title),
                  payload: { type: 'title', app: appNode.app, title: t.title, rawTitle: t.title },
                });
              }
            }
          }
        }
      } else if (this.viewMode === 'apps') {
        for (const appNode of this.flatAppsList as any[]) {
          result.push({ key: 'flat/' + appNode.app, payload: { type: 'app', app: appNode.app, title: '' } });
          if (this.expandedApps['flat/' + appNode.app]) {
            for (const t of appNode.titles) {
              result.push({
                key: 'flat/' + appNode.app + '/' + t.title,
                payload: { type: 'title', app: appNode.app, title: t.title, rawTitle: t.title },
              });
            }
          }
        }
      }
      return result;
    },

    // Map each app to its category color (for timeline coloring)
    appCategoryColors(): Record<string, string> {
      const map: Record<string, string> = {};
      for (const cat of this.activitiesTree as any[]) {
        for (const app of cat.apps) {
          if (!map[app.app]) map[app.app] = cat.color;
        }
      }
      return map;
    },

    // Timeline: merge consecutive same-app events, full day
    timeline(): any[] {
      const events: any[] = this.activeWindowEvents;
      if (!events.length) return [];

      // Apply search filter to timeline too
      let filtered = events;
      if (this.searchQuery) {
        const q = this.searchQuery.toLowerCase();
        filtered = events.filter((e: any) => {
          return (e.data?.app || '').toLowerCase().includes(q) ||
            (e.data?.title || '').toLowerCase().includes(q);
        });
      }

      const sorted = [...filtered].sort(
        (a: any, b: any) => moment(a.timestamp).valueOf() - moment(b.timestamp).valueOf()
      );

      // Pass 1: merge consecutive same-app events, but only if gap < MAX_MERGE_GAP_MS
      const merged1: any[] = [];
      let current: any = null;
      for (const e of sorted) {
        const app: string = e.data?.app || 'Unknown';
        const eStart = moment(e.timestamp).valueOf();
        const gapMs = current ? eStart - current.end.valueOf() : Infinity;
        if (current && current.app === app && gapMs < MAX_MERGE_GAP_MS) {
          const eEnd = moment(e.timestamp).add(e.duration, 'seconds');
          if (eEnd.isAfter(current.end)) current.end = eEnd;
          current.duration += e.duration;
          continue;
        }
        if (current) merged1.push(current);
        current = {
          app,
          start: moment(e.timestamp),
          end: moment(e.timestamp).add(e.duration, 'seconds'),
          duration: e.duration,
          event: e,
        };
      }
      if (current) merged1.push(current);

      // Pass 2: absorb very short interruptions
      const blocks: any[] = [];
      for (let i = 0; i < merged1.length; i++) {
        const b = merged1[i];
        const prev = blocks.length > 0 ? blocks[blocks.length - 1] : null;
        if (b.duration < 30 && prev && prev.app !== b.app) {
          const next = i + 1 < merged1.length ? merged1[i + 1] : null;
          if (next && next.app === prev.app) {
            prev.end = b.end;
            prev.duration += b.duration;
            continue;
          }
        }
        if (prev && prev.app === b.app) {
          prev.end = b.end;
          prev.duration += b.duration;
        } else {
          blocks.push({ ...b });
        }
      }

      const appIndexMap: Record<string, number> = {};
      const catColors = this.appCategoryColors;
      let idx = 0;
      return blocks
        .filter((b: any) => b.duration >= 60)
        .map((b: any) => {
          if (!(b.app in appIndexMap)) appIndexMap[b.app] = idx++;
          // Use category color if available, else fall back to gradient
          const catColor = catColors[b.app];
          const color = catColor
            ? catColor
            : gradientForApp(b.app, appIndexMap[b.app]);
          return {
            label: b.app,
            range: formatHHMM(b.start.toISOString()) + ' – ' + formatHHMM(b.end.toISOString()),
            color,
            event: b.event,
            startMs: b.start.valueOf(),
            endMs: b.end.valueOf(),
          };
        });
    },

    timelineCanvas(): { blocks: any[]; hours: any[]; nowPx: number | null; totalHeight: number; canvasStartMs: number } {
      const dayStart = moment(this.selectedDate).startOf('day').valueOf();
      const SCALE = HOUR_PX / 3600000; // px per millisecond
      const blocks_raw = this.timeline as any[];

      // Default visible window: 8am–10pm
      const default8am = moment(this.selectedDate).hour(8).startOf('hour').valueOf();
      const default10pm = moment(this.selectedDate).hour(22).startOf('hour').valueOf();

      // Extend if there's content outside the default window
      const earliestContent = blocks_raw.length > 0
        ? Math.min(...blocks_raw.map((b: any) => b.startMs))
        : default8am;
      const latestContent = blocks_raw.length > 0
        ? Math.max(...blocks_raw.map((b: any) => b.endMs))
        : default10pm;

      // Canvas bounds: snap to hour boundaries
      const canvasStartMs = moment(Math.min(earliestContent, default8am)).startOf('hour').valueOf();
      const canvasEndMs = moment(Math.max(latestContent, default10pm)).add(1, 'hour').startOf('hour').valueOf();

      const startHour = Math.round((canvasStartMs - dayStart) / 3600000);
      const endHour = Math.round((canvasEndMs - dayStart) / 3600000);

      // Hour labels + gridlines for visible range only
      const hours = Array.from({ length: endHour - startHour + 1 }, (_, i) => {
        const h = startHour + i;
        const label = h === 0 || h === 24 ? '12am' : h < 12 ? `${h}am` : h === 12 ? '12pm' : `${h - 12}pm`;
        return { h, label, top: i * HOUR_PX };
      });

      // Position blocks relative to canvasStartMs
      const blocks = blocks_raw.map((item: any) => {
        const topPx = (item.startMs - canvasStartMs) * SCALE;
        const heightPx = Math.max(4, (item.endMs - item.startMs) * SCALE);
        return { ...item, top: topPx, heightPx };
      });

      // Current time red line (today only, if within visible range)
      let nowPx: number | null = null;
      if (this.isToday) {
        const nowMs = moment().valueOf();
        if (nowMs >= canvasStartMs && nowMs <= canvasEndMs) {
          nowPx = (nowMs - canvasStartMs) * SCALE;
        }
      }

      return { blocks, hours, nowPx, totalHeight: (endHour - startHour) * HOUR_PX, canvasStartMs };
    },

    // Chronological view: timeline blocks as top-level rows, individual events nested inside
    chronoGrouped(): any[] {
      const blocks: any[] = this.timeline as any[];
      const allEvents: any[] = this.activeWindowEvents;
      const q = this.searchQuery.toLowerCase();

      return blocks
        .filter((block: any) => !q || block.label.toLowerCase().includes(q))
        .map((block: any) => {
          const key = block.label + '-' + block.startMs;
          const subEvents = allEvents
            .filter((e: any) => {
              const t = moment(e.timestamp).valueOf();
              return t >= block.startMs && t < block.endMs && (e.duration || 0) >= 5;
            })
            .sort((a: any, b: any) => moment(a.timestamp).valueOf() - moment(b.timestamp).valueOf());
          return { ...block, key, subEvents };
        });
    },

    // Flat chronological event list for the chrono view
    chronoEvents(): any[] {
      const events: any[] = this.activeWindowEvents;
      if (!events.length) return [];

      let filtered = events;
      if (this.searchQuery) {
        const q = this.searchQuery.toLowerCase();
        filtered = events.filter((e: any) =>
          (e.data?.app || '').toLowerCase().includes(q) ||
          (e.data?.title || '').toLowerCase().includes(q)
        );
      }

      const categories: any[] = (this.categoryStore as any).classes;
      const regexes: [any, RegExp][] = categories
        .filter((c: any) => c.rule?.type === 'regex' && c.rule.regex)
        .map((c: any) => [c, new RegExp(c.rule.regex, (c.rule.ignore_case ? 'i' : '') + 'm')]);

      return [...filtered]
        .sort((a: any, b: any) => moment(a.timestamp).valueOf() - moment(b.timestamp).valueOf())
        .filter((e: any) => (e.duration || 0) >= 5)
        .map((e: any) => {
          const app: string = e.data?.app || 'Unknown';
          const rawTitle: string = e.data?.title || '';
          const str = app + '\n' + rawTitle;
          const matches = regexes.filter(([, re]: [any, RegExp]) => re.test(str));
          const catName: string[] = matches.length > 0
            ? (_.maxBy(matches, ([c]: [any, RegExp]) => (c as any).name.length) as any)[0].name
            : ['Uncategorized'];
          return {
            ts: e.timestamp,
            app,
            title: this.cleanTitle(rawTitle, app),
            timeStr: formatHHMM(e.timestamp),
            duration: e.duration,
            catColor: (this.categoryStore as any).get_category_color(catName),
            appColor: getColorFromString(app),
          };
        });
    },
  },

  methods: {
    // Expose module-level helpers to the template
    formatDuration(seconds: number): string {
      return formatDuration(seconds);
    },

    blockTooltip(block: any): string {
      return block.label + '\n' + block.range + ' - ' + formatDuration((block.endMs - block.startMs) / 1000);
    },
    formatHHMM(ts: any): string {
      return formatHHMM(ts);
    },

    // Strip browser name suffix from window titles for better readability
    cleanTitle(title: string, app: string): string {
      if (!title) return app;
      for (const b of BROWSER_SUFFIXES) {
        const suffix = ' - ' + b;
        if (title.endsWith(suffix)) {
          return title.slice(0, title.length - suffix.length);
        }
      }
      return title;
    },

    toggleChronoBlock(key: string) {
      this.$set(this.expandedTimelineBlocks, key, !this.expandedTimelineBlocks[key]);
    },

    onTimelineBlockClick(block: any) {
      // Switch to chrono view and scroll to this block's time
      this.viewMode = 'chrono';
      this.$nextTick(() => {
        const scroll = this.$refs.activitiesScroll as HTMLElement | undefined;
        if (!scroll) return;
        const row = scroll.querySelector(`[data-startms="${block.startMs}"]`) as HTMLElement | null;
        if (row) {
          scroll.scrollTop = Math.max(0, row.offsetTop - 60);
        }
      });
    },

    toggleExpandCat(key: string) {
      this.$set(this.expandedCats, key, !this.expandedCats[key]);
      this.saveExpandState();
    },

    toggleExpandApp(key: string) {
      this.$set(this.expandedApps, key, !this.expandedApps[key]);
    },

    toggleSidebarNode(key: string) {
      this.$set(this.sidebarExpanded, key, !this.sidebarExpanded[key]);
      this.saveExpandState();
    },

    // #28: toggle expand state for a row
    toggleSidebarExpand(row: any) {
      this.$set(this.sidebarExpanded, row.key, !this.sidebarExpanded[row.key]);
      this.saveExpandState();
    },

    // #28 + #29: row click — toggle select (deselect if already selected); also expand if has children
    onSidebarRowClick(row: any) {
      this.ctxMenu = null;
      // #29: toggle filter — deselect if already selected
      if (this.selectedCatFilter === row.key) {
        this.selectedCatFilter = null;
      } else {
        this.selectedCatFilter = row.key;
        // #28: auto-expand when selecting a parent
        if (row.hasChildren && !this.sidebarExpanded[row.key]) {
          this.$set(this.sidebarExpanded, row.key, true);
          this.saveExpandState();
        }
      }
    },

    // #6 / #30: right-click context menu
    onSidebarRowRightClick(row: any, evt: MouseEvent) {
      this.ctxMenu = { row, x: evt.clientX, y: evt.clientY };
      const close = () => { this.ctxMenu = null; window.removeEventListener('click', close); };
      window.addEventListener('click', close);
    },

    // #6 / #30: inline rename
    startRename(row: any) {
      this.ctxMenu = null;
      this.renamingKey = row.key;
      this.renameValue = row.label;
      this.$nextTick(() => {
        const input = (this.$refs.renameInput as HTMLInputElement[] | HTMLInputElement);
        const el = Array.isArray(input) ? input[0] : input;
        if (el) { el.focus(); el.select(); }
      });
    },

    commitRename(row: any) {
      const newLabel = this.renameValue.trim();
      if (!newLabel) { this.cancelRename(); return; }
      const catStore = this.categoryStore as any;
      const oldName: string[] = row.key.split('>');
      const cat = catStore.classes.find((c: any) => c.name.join('>') === row.key);
      if (!cat) { this.cancelRename(); return; }
      const newName: string[] = [...oldName.slice(0, -1), newLabel];
      catStore.updateClass({ ...cat, name: newName });
      catStore.save();
      this.renamingKey = null;
    },

    cancelRename() {
      this.renamingKey = null;
    },

    // #31 + #38: + button uses inline create, subcategory if selected
    createTopCategory() {
      const parentKey = this.selectedCatFilter && this.selectedCatFilter !== '__unassigned__'
        ? this.selectedCatFilter : '';
      this.startInlineCreate(parentKey);
    },

    // #6 + #38: create child via context menu — inline
    createChildCategory(row: any) {
      this.ctxMenu = null;
      this.$set(this.sidebarExpanded, row.key, true);
      this.startInlineCreate(row.key);
    },

    // #38: inline create flow
    startInlineCreate(parentKey: string) {
      this.inlineCreateParent = parentKey;
      this.inlineCreateValue = '';
      if (parentKey) this.$set(this.sidebarExpanded, parentKey, true);
      this.$nextTick(() => {
        const input = this.$refs.inlineCreateInput as HTMLInputElement[] | HTMLInputElement;
        const el = Array.isArray(input) ? input[0] : input;
        if (el) el.focus();
      });
    },

    commitInlineCreate() {
      const label = this.inlineCreateValue.trim();
      if (!label) { this.cancelInlineCreate(); return; }
      const parentName: string[] = this.inlineCreateParent ? this.inlineCreateParent.split('>') : [];
      (this.categoryStore as any).addClass({
        name: [...parentName, label],
        rule: { type: 'none' },
        data: { color: '#4b8bff' },
      });
      (this.categoryStore as any).save();
      this.inlineCreateParent = null;
      this.inlineCreateValue = '';
    },

    cancelInlineCreate() {
      this.inlineCreateParent = null;
      this.inlineCreateValue = '';
    },

    // #6: delete category and all its children
    deleteCategory(row: any) {
      this.ctxMenu = null;
      if (!window.confirm(`Delete "${row.label}" and all its subcategories?`)) return;
      const catStore = this.categoryStore as any;
      const prefix = row.key + '>';
      const idsToDelete: number[] = catStore.classes
        .filter((c: any) => c.name.join('>') === row.key || c.name.join('>').startsWith(prefix))
        .map((c: any) => c.id);
      for (const id of idsToDelete) catStore.removeClass(id);
      catStore.save();
      if (this.selectedCatFilter === row.key) this.selectedCatFilter = null;
    },

    // ─── COLOR PICKER (#7) ────────────────────────────────────────
    openColorPicker(row: any, evt: MouseEvent) {
      if (this.colorPickerRow && this.colorPickerRow.key === row.key) {
        this.colorPickerRow = null;
        return;
      }
      const rect = (evt.target as HTMLElement).getBoundingClientRect();
      this.colorPickerPos = { x: rect.right + 6, y: rect.top };
      this.colorPickerRow = row;
      const close = (e: MouseEvent) => {
        if (!(e.target as HTMLElement).closest('.color-picker-popover')) {
          this.colorPickerRow = null;
          window.removeEventListener('click', close);
        }
      };
      this.$nextTick(() => window.addEventListener('click', close));
    },

    applyColor(color: string) {
      const catStore = this.categoryStore as any;
      const cat = catStore.classes.find((c: any) => c.name.join('>') === this.colorPickerRow.key);
      if (!cat) return;
      catStore.updateClass({ ...cat, data: { ...cat.data, color } });
      catStore.save();
    },

    // ─── PRODUCTIVITY SCORE (#8) ──────────────────────────────────
    setCategoryScore(row: any, score: number) {
      this.ctxMenu = null;
      const catStore = this.categoryStore as any;
      const cat = catStore.classes.find((c: any) => c.name.join('>') === row.key);
      if (!cat) return;
      catStore.updateClass({ ...cat, data: { ...cat.data, score } });
      catStore.save();
    },

    // ─── DRAG-TO-CATEGORIZE (#3) ──────────────────────────────────
    onDragStartApp(appNode: any, evt: DragEvent) {
      // #43: log to aid debugging
      const selected = Object.values(this.selectedRowPayloads as Record<string, any>);
      const items = selected.length > 0 ? selected : [{ type: 'app', app: appNode.app, title: '', rawTitle: '' }];
      const payload = JSON.stringify(items);
      evt.dataTransfer!.setData('application/chronio', payload);
      evt.dataTransfer!.effectAllowed = 'copy';
      console.warn('[Chronio] dragstart app', appNode.app, 'items:', items.length);
    },

    onDragStartTitle(app: string, t: any, evt: DragEvent) {
      // If items are selected and this row is among them, drag all selected
      const selected = Object.values(this.selectedRowPayloads as Record<string, any>);
      const items = selected.length > 0
        ? selected
        : [{ type: 'title', app, title: t.title, rawTitle: t.title }];
      evt.dataTransfer!.setData('application/chronio', JSON.stringify(items));
      evt.dataTransfer!.effectAllowed = 'copy';
      console.warn('[Chronio] dragstart title', t.title, 'items:', items.length);
    },

    onDragEnd() {
      // Clean up any drag state
      this.dragOverCatKey = null;
    },

    onDropToCategory(row: any, evt: DragEvent) {
      this.dragOverCatKey = null;
      const catStore = this.categoryStore as any;
      const cat = catStore.classes.find((c: any) => c.name.join('>') === row.key);
      if (!cat) return;

      // Check if this is a sidebar-category reparent drag (#32)
      const sidebarKey = evt.dataTransfer!.getData('application/chronio-cat');
      if (sidebarKey) {
        this.reparentCategory(sidebarKey, row.key);
        return;
      }

      const raw = evt.dataTransfer!.getData('application/chronio');
      if (!raw) return;

      let items: any[];
      try {
        const parsed = JSON.parse(raw);
        items = Array.isArray(parsed) ? parsed : [parsed];
      } catch { return; }

      for (const payload of items) {
        let pattern: string;
        if (payload.type === 'app') {
          pattern = '(?m)^' + escapeRegex(payload.app) + '$';
        } else {
          pattern = escapeRegex(payload.title);
        }
        catStore.appendClassRule(cat.id, pattern);
      }
      catStore.save();
      this.clearSelection();
    },

    // ─── SIDEBAR DRAG-TO-REPARENT (#32) ──────────────────────────
    onSidebarDragStart(row: any, evt: DragEvent) {
      this.draggingSidebarKey = row.key;
      evt.dataTransfer!.setData('application/chronio-cat', row.key);
      evt.dataTransfer!.effectAllowed = 'move';
    },

    onSidebarDragOver(row: any, evt: DragEvent) {
      const dragKey = this.draggingSidebarKey;
      // Prevent dropping onto self or descendant
      if (dragKey && (row.key === dragKey || row.key.startsWith(dragKey + '>'))) return;
      this.dragOverCatKey = row.key;
    },

    onSidebarDrop(row: any, evt: DragEvent) {
      this.dragOverCatKey = null;
      this.draggingSidebarKey = null;

      // #46: handle reorder-drag from handle
      const reorderKey = evt.dataTransfer!.getData('application/chronio-reorder');
      if (reorderKey && reorderKey !== row.key) {
        this.reorderCategory(reorderKey, row.key);
        return;
      }

      // #32: handle reparent drag from row
      const sidebarKey = evt.dataTransfer!.getData('application/chronio-cat');
      if (sidebarKey && sidebarKey !== row.key && !row.key.startsWith(sidebarKey + '>')) {
        this.reparentCategory(sidebarKey, row.key);
        return;
      }

      // Activity categorize drop
      this.onDropToCategory(row, evt);
    },

    // #46: reorder category among siblings (swap positions in classes array)
    reorderCategory(fromKey: string, toKey: string) {
      const catStore = this.categoryStore as any;
      const fromName = fromKey.split('>');
      const toName = toKey.split('>');
      // Only reorder within same parent
      const fromParent = fromName.slice(0, -1).join('>');
      const toParent = toName.slice(0, -1).join('>');
      if (fromParent !== toParent) return;

      const classes = catStore.classes;
      const fromIdx = classes.findIndex((c: any) => c.name.join('>') === fromKey);
      const toIdx = classes.findIndex((c: any) => c.name.join('>') === toKey);
      if (fromIdx < 0 || toIdx < 0) return;

      const [item] = classes.splice(fromIdx, 1);
      const newToIdx = classes.findIndex((c: any) => c.name.join('>') === toKey);
      classes.splice(newToIdx, 0, item);
      catStore.save();
    },

    reparentCategory(fromKey: string, toKey: string) {
      const catStore = this.categoryStore as any;
      const oldName: string[] = fromKey.split('>');
      const newParent: string[] = toKey.split('>');
      const leaf = oldName[oldName.length - 1];
      const newName: string[] = [...newParent, leaf];

      const cat = catStore.classes.find((c: any) => c.name.join('>') === fromKey);
      if (!cat) return;
      catStore.updateClass({ ...cat, name: newName });
      catStore.save();
    },

    // ─── MULTI-SELECT (#37) ───────────────────────────────────────
    appRowKey(catKey: string, app: string): string {
      return catKey + '/APP:' + app;
    },

    titleRowKey(catKey: string, app: string, title: string): string {
      return catKey + '/APP:' + app + '/T:' + title;
    },

    onActivityRowClick(key: string, payload: any, evt: MouseEvent) {
      evt.preventDefault();
      if (evt.shiftKey && this.lastClickedKey) {
        // Range select
        const rows = this.visibleActivityRowKeys as any[];
        const fromIdx = rows.findIndex((r: any) => r.key === this.lastClickedKey);
        const toIdx = rows.findIndex((r: any) => r.key === key);
        if (fromIdx >= 0 && toIdx >= 0) {
          const lo = Math.min(fromIdx, toIdx);
          const hi = Math.max(fromIdx, toIdx);
          for (let i = lo; i <= hi; i++) {
            this.$set(this.selectedRowKeys, rows[i].key, true);
            this.$set(this.selectedRowPayloads, rows[i].key, rows[i].payload);
          }
        }
      } else if (evt.metaKey || evt.ctrlKey) {
        // Toggle
        if (this.selectedRowKeys[key]) {
          this.$delete(this.selectedRowKeys, key);
          this.$delete(this.selectedRowPayloads, key);
        } else {
          this.$set(this.selectedRowKeys, key, true);
          this.$set(this.selectedRowPayloads, key, payload);
        }
      } else {
        // Single select — clear others
        this.selectedRowKeys = {};
        this.selectedRowPayloads = {};
        this.$set(this.selectedRowKeys, key, true);
        this.$set(this.selectedRowPayloads, key, payload);
      }
      this.lastClickedKey = key;
    },

    clearSelection() {
      this.selectedRowKeys = {};
      this.selectedRowPayloads = {};
      this.lastClickedKey = null;
    },

    // ─── KEYBOARD NAVIGATION (#44) ───────────────────────────────
    onGlobalKeyDown(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      if (e.key === 'ArrowLeft') { e.preventDefault(); this.prevDay(); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); if (!this.isToday) this.nextDay(); }
      else if (e.key === 't' || e.key === 'T') { e.preventDefault(); this.goToToday(); }
      else if (e.key === 'Escape') { this.clearSelection(); }
    },

    goToToday() {
      const today = get_today_with_offset(this.settingsStore.startOfDay);
      if (this.selectedDate !== today) {
        this.selectedDate = today;
        this.refresh();
      }
    },

    // #45: go to previous day (best effort — just go back one day)
    goToPrevActiveDay() {
      this.prevDay();
    },

    // ─── SIDEBAR REORDER (#46) ────────────────────────────────────
    onHandleDragStart(row: any, evt: DragEvent) {
      this.reorderDragKey = row.key;
      evt.dataTransfer!.setData('application/chronio-reorder', row.key);
      evt.dataTransfer!.effectAllowed = 'move';
    },

    // ─── ONBOARDING (#12) ────────────────────────────────────────
    checkOnboarding() {
      if (!localStorage.getItem('chronio_onboarding_complete')) {
        this.showOnboarding = true;
      }
    },

    dismissOnboarding() {
      this.showOnboarding = false;
      localStorage.setItem('chronio_onboarding_complete', '1');
    },

    // #11: persist expand/collapse to localStorage
    saveExpandState() {
      try {
        localStorage.setItem('chronio-sidebar-expanded', JSON.stringify(this.sidebarExpanded));
        localStorage.setItem('chronio-expanded-cats', JSON.stringify(this.expandedCats));
      } catch (e) {
        // localStorage unavailable
      }
    },

    loadExpandState() {
      try {
        const sidebar = localStorage.getItem('chronio-sidebar-expanded');
        if (sidebar) this.sidebarExpanded = JSON.parse(sidebar);
        const cats = localStorage.getItem('chronio-expanded-cats');
        if (cats) this.expandedCats = JSON.parse(cats);
      } catch (e) {
        // localStorage unavailable
      }
    },

    prevDay() {
      this.selectedDate = moment(this.selectedDate).subtract(1, 'day').format('YYYY-MM-DD');
      this.refresh();
    },
    nextDay() {
      if (this.isToday) return;
      this.selectedDate = moment(this.selectedDate).add(1, 'day').format('YYYY-MM-DD');
      this.refresh();
    },
    onDateChange(dateStr: string) {
      this.selectedDate = dateStr;
      this.showDatePicker = false;
      this.refresh();
    },

    async refresh(silent = false) {
      if (!this.host) return;
      // #35: skip silent refresh if a full (non-silent) refresh is already running
      if (silent && this.isRefreshing) return;
      this.isRefreshing = true;
      if (!silent) this.loading = true;

      try {
        const settingsStore = this.settingsStore;
        const timeperiod = dateToTimeperiod(this.selectedDate, settingsStore.startOfDay);

        // #35: don't force-reload the activity store on silent background refresh
        await this.activityStore.ensure_loaded({
          timeperiod,
          host: this.host,
          filter_afk: true,
          include_audible: false,
          include_stopwatch: false,
          force: !silent,
          always_active_pattern: settingsStore.always_active_pattern,
        });

        const windowBuckets = this.bucketsStore.bucketsWindow(this.host);
        const afkBuckets = this.bucketsStore.bucketsAFK(this.host);
        const startDate = moment(this.selectedDate).startOf('day').toDate();
        const endDate = moment(this.selectedDate).endOf('day').toDate();
        const params = { start: startDate, end: endDate, limit: -1 };

        const [windowEvts, afkEvts] = await Promise.all([
          windowBuckets.length > 0
            ? getClient().getEvents(windowBuckets[0], params)
            : Promise.resolve([]),
          afkBuckets.length > 0
            ? getClient().getEvents(afkBuckets[0], params)
            : Promise.resolve([]),
        ]);

        this.windowEvents = windowEvts || [];
        this.afkEvents = afkEvts || [];
        if (!silent) {
          this.loading = false;
          this.$nextTick(() => this.scrollTimeline());
        }
      } finally {
        this.isRefreshing = false;
      }
    },

    startLiveRefresh() {
      this.stopLiveRefresh();
      // Refresh every 60s silently on today's view only
      this.refreshTimer = setInterval(() => {
        if (this.isToday) this.refresh(true);
      }, 60000);
    },

    stopLiveRefresh() {
      if (this.refreshTimer) {
        clearInterval(this.refreshTimer);
        this.refreshTimer = null;
      }
    },

    scrollTimeline() {
      const el = this.$refs.timelineScroll as HTMLElement | undefined;
      if (!el) return;
      const SCALE = HOUR_PX / 3600000;
      const { canvasStartMs, nowPx } = this.timelineCanvas;
      let targetPx: number;
      if (this.isToday && nowPx !== null) {
        // Scroll so "now" sits about 1/3 from the top
        targetPx = nowPx - el.clientHeight / 3;
      } else {
        // Scroll to top (canvas already starts at first event / 8am)
        targetPx = 0;
      }
      el.scrollTop = Math.max(0, targetPx);
    },
  },

  watch: {
    host() {
      if (this.host) this.refresh();
    },
    // #39: auto-expand app rows when a category filter is selected
    selectedCatFilter(newVal: string | null) {
      if (newVal && newVal !== '__unassigned__') {
        this.$nextTick(() => {
          for (const catNode of this.filteredActivitiesTree as any[]) {
            for (const appNode of catNode.apps) {
              this.$set(this.expandedApps, catNode.catKey + '/' + appNode.app, true);
            }
          }
        });
      }
    },
  },

  async mounted() {
    const settingsStore = this.settingsStore;
    await settingsStore.ensureLoaded();
    this.selectedDate = get_today_with_offset(settingsStore.startOfDay);
    await this.bucketsStore.ensureLoaded();
    await (this.categoryStore as any).load();
    this.loadExpandState();
    this.checkOnboarding();
    if (this.host) {
      await this.refresh();
    } else {
      this.loading = false;
    }
    this.startLiveRefresh();
    this.keyHandler = this.onGlobalKeyDown.bind(this);
    window.addEventListener('keydown', this.keyHandler);
  },

  beforeDestroy() {
    this.stopLiveRefresh();
    if (this.keyHandler) window.removeEventListener('keydown', this.keyHandler);
  },
};
</script>

<style scoped>
.chronio-view {
  --bg: #0f1117;
  --panel: rgba(20, 24, 33, 0.9);
  --panel-2: rgba(22, 26, 36, 0.9);
  --text: #e9eefb;
  --muted: #9aa4b2;
  --border: rgba(255, 255, 255, 0.08);
  --border-hover: rgba(255, 255, 255, 0.15);
  --glow: 0 20px 60px rgba(0, 0, 0, 0.45);
  color: var(--text);
  background: radial-gradient(1200px 700px at 10% -10%, rgba(80, 120, 255, 0.12), transparent 60%),
              radial-gradient(900px 700px at 90% 10%, rgba(255, 110, 70, 0.12), transparent 55%),
              var(--bg);
  font-family: system-ui, -apple-system, sans-serif;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* ── TOPBAR ──────────────────────────────────────────────────────── */
.chronio-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.chronio-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 15px;
  letter-spacing: 0.4px;
}

.chronio-logo {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 2px solid #4b8bff;
  box-shadow: 0 0 0 4px rgba(75, 139, 255, 0.15);
}

.chronio-topbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.chronio-date-nav {
  display: flex;
  align-items: center;
  gap: 6px;
}

.chronio-nav-btn {
  background: var(--panel);
  border: 1px solid var(--border);
  color: var(--muted);
  border-radius: 8px;
  padding: 4px 10px;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  transition: color 0.15s, border-color 0.15s;
  &:hover { color: #fff; border-color: var(--border-hover); }
  &:disabled { opacity: 0.3; cursor: not-allowed; }
}

.chronio-chip {
  padding: 5px 12px;
  border-radius: 10px;
  background: var(--panel);
  border: 1px solid var(--border);
  font-size: 12px;
  color: var(--muted);
  cursor: pointer;
  position: relative;
  white-space: nowrap;
}

.date-input {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 10;
  margin-top: 4px;
  background: var(--panel-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  padding: 6px;
  font-size: 12px;
}

.chronio-metric {
  display: inline-flex;
  gap: 6px;
  font-size: 12px;
  color: var(--muted);
  white-space: nowrap;
  .value { color: var(--text); font-weight: 600; }
}

.chronio-search {
  display: inline-flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: 10px;
  background: var(--panel);
  border: 1px solid var(--border);
  input {
    background: transparent;
    border: 0;
    color: var(--text);
    outline: none;
    font-size: 12px;
    width: 160px;
    &::placeholder { color: var(--muted); }
  }
}

/* ── LOADING ─────────────────────────────────────────────────────── */
.chronio-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--muted);
  font-size: 14px;
}

/* ── BODY: 3-COLUMN LAYOUT ───────────────────────────────────────── */
.chronio-body {
  display: grid;
  grid-template-columns: 240px 1fr 280px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* ── SIDEBAR ─────────────────────────────────────────────────────── */
.chronio-sidebar {
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  background: rgba(15, 17, 23, 0.6);
}

.sidebar-nav {
  padding: 12px 0 8px;
  border-bottom: 1px solid var(--border);
}

.sidebar-nav-item {
  padding: 7px 16px;
  font-size: 13px;
  color: var(--muted);
  cursor: pointer;
  border-radius: 0;
  &:hover { color: var(--text); background: rgba(255,255,255,0.04); }
  &.active { color: #4b8bff; background: rgba(75,139,255,0.08); font-weight: 500; }
}

.sidebar-tree {
  padding: 8px 0;
  flex: 1;
}

.sidebar-summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 13px;
  border-radius: 6px;
  margin: 1px 6px;
  &:hover { background: rgba(255,255,255,0.05); }
  &.active { background: rgba(75,139,255,0.12); color: #7db0ff; }
  .sr-name { font-weight: 500; }
  .sr-time { color: var(--muted); font-size: 12px; }
}

.sidebar-divider {
  height: 1px;
  background: var(--border);
  margin: 8px 12px;
}

.sidebar-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 12px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--muted);
}

.sidebar-add-btn {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--muted);
  width: 20px;
  height: 20px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  &:hover { color: var(--text); border-color: var(--border-hover); }
}

.sidebar-cat-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 6px 5px 10px;
  cursor: pointer;
  font-size: 13px;
  border-radius: 6px;
  margin: 1px 6px;
  &:hover { background: rgba(255,255,255,0.05); }
  &.active { background: rgba(75,139,255,0.12); color: #7db0ff; }
  .sr-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .sr-time { color: var(--muted); font-size: 12px; white-space: nowrap; }
}

.sr-expand-btn {
  background: transparent;
  border: 0;
  color: var(--muted);
  cursor: pointer;
  font-size: 10px;
  padding: 0;
  width: 14px;
  flex-shrink: 0;
  &:hover { color: var(--text); }
}

.sr-expand-spacer {
  width: 14px;
  flex-shrink: 0;
}

.sr-rename-input {
  flex: 1;
  min-width: 0;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(75,139,255,0.5);
  border-radius: 4px;
  color: var(--text);
  font-size: 13px;
  padding: 1px 6px;
  outline: none;
  height: 22px;
  box-sizing: border-box;
}

.sidebar-ctx-menu {
  position: fixed;
  z-index: 999;
  background: #1e2330;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 4px 0;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5);
  min-width: 160px;
}

.ctx-item {
  padding: 7px 14px;
  font-size: 13px;
  cursor: pointer;
  color: var(--text);
  &:hover { background: rgba(255,255,255,0.06); }
  &.ctx-danger { color: #ff6b6b; }
}

.ctx-divider {
  height: 1px;
  background: var(--border);
  margin: 4px 0;
}

.ctx-score-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  font-size: 12px;
  color: var(--muted);
}

.ctx-score-btn {
  background: rgba(255,255,255,0.06);
  border: 1px solid var(--border);
  border-radius: 5px;
  color: var(--muted);
  font-size: 11px;
  padding: 3px 8px;
  cursor: pointer;
  &:hover { border-color: var(--border-hover); color: var(--text); }
  &.active { background: rgba(29,185,84,0.2); border-color: #1db954; color: #1db954; }
  &.distracting.active { background: rgba(239,68,68,0.2); border-color: #ef4444; color: #ef4444; }
  &.neutral.active { background: rgba(255,255,255,0.1); border-color: var(--border-hover); color: var(--text); }
}

.sr-score-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  &.score-productive { background: #1db954; }
  &.score-distracting { background: #ef4444; }
}

/* #7: Color picker popover */
.color-picker-popover {
  position: fixed;
  z-index: 1000;
  background: #1e2330;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5);
  min-width: 180px;
}

.cp-swatches {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
  margin-bottom: 8px;
}

.cp-swatch {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;
  transition: border-color 0.1s, transform 0.1s;
  &:hover { transform: scale(1.15); }
  &.selected { border-color: #fff; }
}

.cp-custom {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--muted);
  input[type="color"] {
    width: 28px;
    height: 22px;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: none;
    cursor: pointer;
    padding: 1px;
  }
}

.sr-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  cursor: pointer;
  transition: transform 0.15s;
  &:hover { transform: scale(1.4); }
}

/* #3: Drag styles */
.act-row--app,
.act-row--title {
  &[draggable="true"] { cursor: grab; }
  &[draggable="true"]:active { cursor: grabbing; }
}

.act-drag-hint {
  font-size: 10px;
  color: var(--muted);
  opacity: 0;
  white-space: nowrap;
  flex-shrink: 0;
  transition: opacity 0.15s;
}

.act-row--app:hover .act-drag-hint {
  opacity: 0.5;
}

.sidebar-cat-row.drop-target {
  background: rgba(75, 139, 255, 0.2) !important;
  border: 1px dashed rgba(75, 139, 255, 0.6);
}

/* #12: Onboarding overlay */
.onboarding-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.7);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}

.onboarding-modal {
  background: #1a1f2e;
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 40px 48px;
  max-width: 420px;
  width: 90%;
  text-align: center;
  box-shadow: 0 24px 64px rgba(0,0,0,0.6);
}

.onboarding-step {
  min-height: 130px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  .ob-emoji { font-size: 48px; line-height: 1; }
  h2 { font-size: 20px; font-weight: 700; color: var(--text); margin: 0; }
  p { font-size: 14px; color: var(--muted); line-height: 1.6; margin: 0; }
}

.ob-dots {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin: 24px 0 20px;
}

.ob-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border);
  cursor: pointer;
  transition: background 0.2s;
  &.active { background: #4b8bff; }
}

.ob-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.ob-btn-primary {
  background: #4b8bff;
  color: #fff;
  border: 0;
  border-radius: 8px;
  padding: 9px 24px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  &:hover { background: #3a7aee; }
}

.ob-btn-ghost {
  background: transparent;
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 9px 24px;
  font-size: 14px;
  cursor: pointer;
  &:hover { color: var(--text); border-color: var(--border-hover); }
}

/* #34: Multi-select highlight */
.act-row--title.row-selected {
  background: rgba(75, 139, 255, 0.15) !important;
  border-left: 2px solid #4b8bff;
}

/* ── CENTER ──────────────────────────────────────────────────────── */
.chronio-center {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
  min-height: 0;
  overflow: hidden;
}

.center-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.center-title {
  font-size: 14px;
  color: var(--muted);
  strong { color: var(--text); }
}

.view-toggle {
  display: inline-flex;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  button {
    background: transparent;
    border: 0;
    color: var(--muted);
    padding: 4px 12px;
    font-size: 11px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    &.active { background: rgba(75,139,255,0.2); color: var(--text); }
    &:hover:not(.active) { color: var(--text); }
  }
}

.activities-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.act-empty {
  color: var(--muted);
  font-size: 13px;
  padding: 20px 16px;
}

/* ── ACTIVITY ROWS ───────────────────────────────────────────────── */
.act-row {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 12px;
  min-height: 34px;
  cursor: pointer;
  &:hover { background: rgba(255,255,255,0.04); }
  .act-name { flex: 1; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .act-dur { font-size: 12px; color: var(--muted); white-space: nowrap; flex-shrink: 0; }
}

.act-row--cat {
  font-weight: 500;
  .act-expand { font-size: 10px; color: var(--muted); width: 12px; flex-shrink: 0; }
}

.act-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.act-row--app {
  .act-name { color: var(--muted); font-weight: 400; }
}

.act-indent {
  width: 32px;
  flex-shrink: 0;
}

.act-indent2 {
  width: 52px;
  flex-shrink: 0;
}

.act-app-icon {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  flex-shrink: 0;
}

.act-row--title {
  cursor: default;
  &:hover { background: rgba(255,255,255,0.02); }
  .act-title {
    flex: 1;
    font-size: 12px;
    color: var(--muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.act-row--chrono-group {
  cursor: pointer;
  font-weight: 500;
  gap: 7px;
  .act-caret { font-size: 10px; color: var(--muted); width: 12px; flex-shrink: 0; }
  .act-app { font-size: 13px; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .act-time-range { font-size: 11px; color: var(--muted); white-space: nowrap; flex-shrink: 0; }
  &:hover { background: rgba(255,255,255,0.05); }
}

.act-row--chrono-sub {
  cursor: default;
  min-height: 28px;
  &:hover { background: rgba(255,255,255,0.02); }
  .act-app-label { font-size: 12px; color: rgba(255,255,255,0.35); white-space: nowrap; flex-shrink: 0; margin-right: 3px; }
  .act-title { flex: 1; font-size: 12px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .act-time { font-size: 11px; color: var(--muted); white-space: nowrap; flex-shrink: 0; margin-right: 4px; }
}

/* ── RIGHT TIMELINE ──────────────────────────────────────────────── */
.chronio-timeline-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  background: rgba(15, 17, 23, 0.4);
}

.timeline-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 8px 10px 24px 0;
}

/* The full-day canvas: position:relative so children can be absolute */
.timeline-canvas {
  position: relative;
  margin-left: 44px; /* room for hour labels */
  margin-right: 4px;
}

/* Each hour row: label on left, gridline stretching right */
.tl-hour {
  position: absolute;
  left: -44px;
  right: 0;
  display: flex;
  align-items: flex-start;
  pointer-events: none;
}

.tl-hour-label {
  font-size: 10px;
  color: var(--muted);
  width: 36px;
  text-align: right;
  padding-right: 8px;
  line-height: 1;
  flex-shrink: 0;
  margin-top: -1px;
}

.tl-hour-line {
  flex: 1;
  height: 1px;
  background: var(--border);
}

/* "Now" red indicator */
.tl-now-line {
  position: absolute;
  left: -44px;
  right: 0;
  height: 2px;
  background: #ff4040;
  z-index: 5;
  pointer-events: none;
  &::after {
    content: '';
    position: absolute;
    left: 44px;
    top: -4px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #ff4040;
  }
}

/* Activity blocks: absolutely placed on the canvas */
.tl-block {
  position: absolute;
  left: 2px;
  right: 2px;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  transition: filter 0.15s;
  z-index: 2;
  &:hover {
    filter: brightness(1.15);
    z-index: 3;
  }
}

.tl-block-inner {
  padding: 3px 8px;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 1px;
}

.tl-title {
  font-weight: 600;
  font-size: 11px;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.3;
}

.tl-time-range {
  font-size: 10px;
  color: rgba(255,255,255,0.75);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chronio-empty {
  color: var(--muted);
  font-size: 12px;
  padding: 12px 0;
}

/* ── DRAG HANDLE (#46) ───────────────────────────────────────────── */
.sr-drag-handle {
  opacity: 0;
  color: var(--muted);
  font-size: 12px;
  cursor: grab;
  flex-shrink: 0;
  padding: 0 2px;
  transition: opacity 0.15s;
  user-select: none;
}

.sidebar-cat-row:hover .sr-drag-handle {
  opacity: 0.5;
}

.sidebar-cat-row:hover .sr-drag-handle:hover {
  opacity: 1;
  color: var(--text);
}

/* ── INLINE CREATE (#38) ──────────────────────────────────────────── */
.sidebar-inline-create {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px 4px 10px;
  margin: 1px 6px;
}

/* ── EMPTY STATE (#45) ────────────────────────────────────────────── */
.act-day-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 10px;
  padding: 40px 20px;
  color: var(--muted);
  .act-empty-icon { font-size: 32px; opacity: 0.3; }
  p { font-size: 14px; margin: 0; text-align: center; }
}

.act-empty-prev {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--muted);
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 13px;
  cursor: pointer;
  margin-top: 6px;
  &:hover { color: var(--text); border-color: var(--border-hover); }
}

/* ── APPS VIEW (#40) act-expand reuse ────────────────────────────── */
.act-row--app .act-expand {
  font-size: 10px;
  color: var(--muted);
  width: 12px;
  flex-shrink: 0;
  cursor: pointer;
}
.act-row--app .act-expand-spacer {
  width: 12px;
  flex-shrink: 0;
}

/* ── SCROLLBAR STYLING ───────────────────────────────────────────── */
.chronio-sidebar,
.activities-scroll,
.timeline-scroll {
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.1) transparent;
  &::-webkit-scrollbar { width: 4px; }
  &::-webkit-scrollbar-track { background: transparent; }
  &::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }
}
</style>
