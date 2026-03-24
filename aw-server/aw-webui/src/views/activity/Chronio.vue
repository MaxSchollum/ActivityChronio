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
          span Private
          button.sidebar-add-btn(@click.stop="createTopCategory") +

        template(v-for="row in sidebarFlatTree" :key="row.key")
          .sidebar-cat-row(
            :style="{paddingLeft: (row.depth * 14 + 10) + 'px'}"
            :class="{active: selectedCatFilter === row.key}"
            @click="selectedCatFilter = row.key"
          )
            button.sr-expand-btn(
              v-if="row.hasChildren"
              @click.stop="toggleSidebarNode(row.key)"
            ) {{ sidebarExpanded[row.key] ? '▾' : '▸' }}
            span.sr-expand-spacer(v-else)
            .sr-dot(:style="{background: row.color}")
            span.sr-name {{ row.label }}
            span.sr-time {{ row.time }}

    //- ─── CENTER: ALL ACTIVITIES ─────────────────────────────────────
    .chronio-center
      .center-header
        .center-title
          | All Activities:&nbsp;
          strong {{ totalTrackedTime }}
        .view-toggle
          button(:class="{active: viewMode === 'unified'}" @click="viewMode = 'unified'") Unified
          button(:class="{active: viewMode === 'chrono'}" @click="viewMode = 'chrono'") Chronological

      .activities-scroll
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
                @click="toggleExpandApp(catNode.catKey + '/' + appNode.app)"
              )
                .act-indent
                .act-app-icon(:style="{background: appNode.color}")
                span.act-name {{ appNode.app }}
                span.act-dur {{ formatDuration(appNode.duration) }}

              template(v-if="expandedApps[catNode.catKey + '/' + appNode.app]" v-for="t in appNode.titles" :key="catNode.catKey + '/' + appNode.app + '/' + t.title")
                .act-row.act-row--title
                  .act-indent2
                  span.act-title(:title="t.title") {{ t.title }}
                  span.act-dur {{ formatDuration(t.duration) }}

        //- CHRONOLOGICAL VIEW
        template(v-else)
          .act-empty(v-if="!chronoEvents.length") No activity data for this period
          .act-row.act-row--chrono(
            v-else
            v-for="e in chronoEvents"
            :key="e.ts"
          )
            .act-dot(:style="{background: e.catColor}")
            .act-app-icon(:style="{background: e.appColor}")
            span.act-app {{ e.app }}
            span.act-title(:title="e.title") {{ e.title }}
            span.act-time {{ e.timeStr }}
            span.act-dur {{ formatDuration(e.duration) }}

    //- ─── RIGHT: TIMELINE ────────────────────────────────────────────
    .chronio-timeline-panel
      .timeline-scroll
        .chronio-empty(v-if="!timeline.length") No timeline data for this period
        template(v-else v-for="item in timelineWithMarkers")
          .tl-time(v-if="item.type === 'time'" :key="'t-' + item.label") {{ item.label }}
          .tl-block(
            v-else
            :key="'b-' + item.label + item.range"
            :style="{background: item.color, minHeight: item.height + 'px'}"
            @click="selectedEvent = item.event"
            @mouseenter="showTooltip(item, $event)"
            @mouseleave="hideTooltip"
          )
            .tl-block-header
              .tl-title {{ item.label }}
              .tl-time-range {{ item.range }}
        .tl-now-line(v-if="nowLinePosition.show" :style="{top: nowLinePosition.top}")
          span.tl-now-label {{ nowLinePosition.label }}
      .tl-tooltip(
        v-if="tooltip"
        :style="{left: tooltip.x + 12 + 'px', top: tooltip.y - 10 + 'px'}"
      )
        .tl-tooltip-app {{ tooltip.app }}
        .tl-tooltip-title {{ tooltip.title }}
        .tl-tooltip-cat {{ tooltip.category }}
        .tl-tooltip-meta {{ tooltip.range }} &middot; {{ tooltip.duration }}
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

// System processes to always filter out (exact app name match)
const SYSTEM_PROCESSES = ['loginwindow', 'ScreenSaverEngine'];

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
      sidebarExpanded: {} as Record<string, boolean>,
      selectedCatFilter: null as string | null,
      viewMode: 'unified' as 'unified' | 'chrono',
      // Tooltip state
      tooltip: null as { app: string; title: string; category: string; range: string; duration: string; x: number; y: number } | null,
      // Live refresh state
      _refreshInterval: null as any,
      nowMinute: 0 as number,
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
        // Filter out system processes by exact app name match
        const app = e.data?.app || '';
        if (SYSTEM_PROCESSES.includes(app)) return false;

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

      // Pre-compile regexes once
      const regexes: [any, RegExp][] = categories
        .filter((c: any) => c.rule?.type === 'regex' && c.rule.regex)
        .map((c: any) => [c, new RegExp(c.rule.regex, (c.rule.ignore_case ? 'i' : '') + 'm')]);

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
          rows.push({
            key,
            label: cat.name[cat.name.length - 1],
            depth,
            color: catStore.get_category_color(cat.name),
            hasChildren: cat.children && cat.children.length > 0,
            time: dur > 0 ? formatDuration(dur) : '',
          });
          if (expanded[key] && cat.children && cat.children.length > 0) {
            flatten(cat.children, depth + 1);
          }
        }
      };

      flatten(catStore.classes_hierarchy, 0);
      return rows;
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

      // Pass 1: merge consecutive same-app events
      const merged1: any[] = [];
      let current: any = null;
      for (const e of sorted) {
        const app: string = e.data?.app || 'Unknown';
        if (current && current.app === app) {
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
      let idx = 0;
      return blocks
        .filter((b: any) => b.duration >= 60)
        .map((b: any) => {
          if (!(b.app in appIndexMap)) appIndexMap[b.app] = idx++;
          return {
            label: b.app,
            range: formatHHMM(b.start.toISOString()) + ' – ' + formatHHMM(b.end.toISOString()),
            color: gradientForApp(b.app, appIndexMap[b.app]),
            height: Math.max(36, Math.min(180, b.duration / 15)),
            event: b.event,
          };
        });
    },

    timelineWithMarkers(): any[] {
      if (!this.timeline.length) return [];
      const result: any[] = [];
      let lastHour = -1;
      for (const block of this.timeline as any[]) {
        const hourStr = block.range.split(' – ')[0];
        const hour = parseInt(hourStr.split(':')[0]);
        if (hour !== lastHour) {
          result.push({ type: 'time', label: hourStr });
          lastHour = hour;
        }
        result.push({ ...block, type: 'block' });
      }
      return result;
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

    // Now-line position for today's timeline
    nowLinePosition(): { show: boolean; top: string; label: string } {
      if (!this.isToday || !this.timeline.length) return { show: false, top: '0', label: '' };
      // Access nowMinute to force reactivity updates
      const _tick = this.nowMinute;
      const now = moment();
      const dayStart = 8;
      const dayEnd = 22;
      const currentHour = now.hours() + now.minutes() / 60;
      if (currentHour < dayStart || currentHour > dayEnd) return { show: false, top: '0', label: '' };
      const pct = ((currentHour - dayStart) / (dayEnd - dayStart)) * 100;
      return { show: true, top: pct + '%', label: now.format('HH:mm') };
    },
  },

  methods: {
    // Expose module-level helpers to the template
    formatDuration(seconds: number): string {
      return formatDuration(seconds);
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

    toggleExpandCat(key: string) {
      this.$set(this.expandedCats, key, !this.expandedCats[key]);
      this._saveExpandState();
    },

    toggleExpandApp(key: string) {
      this.$set(this.expandedApps, key, !this.expandedApps[key]);
      this._saveExpandState();
    },

    toggleSidebarNode(key: string) {
      this.$set(this.sidebarExpanded, key, !this.sidebarExpanded[key]);
      this._saveExpandState();
    },

    _saveExpandState: _.debounce(function (this: any) {
      try {
        localStorage.setItem('chronio_expandedCats', JSON.stringify(this.expandedCats));
        localStorage.setItem('chronio_expandedApps', JSON.stringify(this.expandedApps));
        localStorage.setItem('chronio_sidebarExpanded', JSON.stringify(this.sidebarExpanded));
      } catch (e) { /* localStorage full or unavailable */ }
    }, 200),

    // ─── TOOLTIP ──────────────────────────────────────────────────
    showTooltip(item: any, event: MouseEvent) {
      const e = item.event;
      const app = e?.data?.app || item.label;
      const title = e?.data?.title ? this.cleanTitle(e.data.title, app) : '';

      // Find category
      const categories: any[] = (this.categoryStore as any).classes;
      const regexes = categories
        .filter((c: any) => c.rule?.type === 'regex' && c.rule.regex)
        .map((c: any) => [c, new RegExp(c.rule.regex, (c.rule.ignore_case ? 'i' : '') + 'm')]);
      const str = app + '\n' + (e?.data?.title || '');
      const matches = regexes.filter(([, re]: any) => re.test(str));
      const catName = matches.length > 0
        ? (_.maxBy(matches, ([c]: any) => c.name.length) as any)[0].name
        : ['Uncategorized'];

      this.tooltip = {
        app,
        title: title || '(no title)',
        category: catName[catName.length - 1],
        range: item.range,
        duration: formatDuration(e?.duration || 0),
        x: event.clientX,
        y: event.clientY,
      };
    },
    hideTooltip() {
      this.tooltip = null;
    },

    // ─── LIVE REFRESH ───────────────────────────────────────────────
    _startLiveRefresh() {
      this._stopLiveRefresh();
      if (!this.isToday) return;
      this.nowMinute = Date.now();
      this._refreshInterval = setInterval(() => {
        this.nowMinute = Date.now();
        this.refresh();
      }, 60000);
    },
    _stopLiveRefresh() {
      if (this._refreshInterval) {
        clearInterval(this._refreshInterval);
        this._refreshInterval = null;
      }
    },

    createTopCategory() {
      const name = window.prompt('New project name:');
      if (!name || !name.trim()) return;
      (this.categoryStore as any).addClass({
        name: [name.trim()],
        rule: { type: 'none' },
        data: { color: '#4b8bff' },
      });
      (this.categoryStore as any).save();
    },

    prevDay() {
      this.selectedDate = moment(this.selectedDate).subtract(1, 'day').format('YYYY-MM-DD');
      this.refresh();
      this._startLiveRefresh();
    },
    nextDay() {
      if (this.isToday) return;
      this.selectedDate = moment(this.selectedDate).add(1, 'day').format('YYYY-MM-DD');
      this.refresh();
      this._startLiveRefresh();
    },
    onDateChange(dateStr: string) {
      this.selectedDate = dateStr;
      this.showDatePicker = false;
      this.refresh();
      this._startLiveRefresh();
    },

    async refresh() {
      if (!this.host) return;
      this.loading = true;

      const settingsStore = this.settingsStore;
      const timeperiod = dateToTimeperiod(this.selectedDate, settingsStore.startOfDay);

      await this.activityStore.ensure_loaded({
        timeperiod,
        host: this.host,
        filter_afk: true,
        include_audible: false,
        include_stopwatch: false,
        force: true,
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
      this.loading = false;
    },
  },

  watch: {
    host() {
      if (this.host) this.refresh();
    },
  },

  async mounted() {
    // Restore expand/collapse state from localStorage
    try {
      const cats = localStorage.getItem('chronio_expandedCats');
      const apps = localStorage.getItem('chronio_expandedApps');
      const sidebar = localStorage.getItem('chronio_sidebarExpanded');
      if (cats) this.expandedCats = JSON.parse(cats);
      if (apps) this.expandedApps = JSON.parse(apps);
      if (sidebar) this.sidebarExpanded = JSON.parse(sidebar);
    } catch (e) { /* ignore parse errors */ }

    const settingsStore = this.settingsStore;
    await settingsStore.ensureLoaded();
    this.selectedDate = get_today_with_offset(settingsStore.startOfDay);
    await this.bucketsStore.ensureLoaded();
    await (this.categoryStore as any).load();
    if (this.host) {
      await this.refresh();
    } else {
      this.loading = false;
    }
    this._startLiveRefresh();
  },

  beforeDestroy() {
    this._stopLiveRefresh();
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
  min-height: 100vh;
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

.sr-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
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
  width: 20px;
  flex-shrink: 0;
}

.act-indent2 {
  width: 36px;
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

.act-row--chrono {
  gap: 8px;
  cursor: default;
  .act-app { font-size: 12px; font-weight: 500; white-space: nowrap; }
  .act-title { flex: 1; font-size: 12px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .act-time { font-size: 11px; color: var(--muted); white-space: nowrap; flex-shrink: 0; }
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
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  position: relative;
}

.tl-time {
  font-size: 10px;
  color: var(--muted);
  padding: 4px 0 2px;
  letter-spacing: 0.4px;
}

.tl-block {
  border-radius: 10px;
  padding: 8px 12px;
  color: #fff;
  cursor: pointer;
  transition: transform 0.1s ease, box-shadow 0.1s ease;
  flex-shrink: 0;
  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  }
}

.tl-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
}

.tl-title {
  font-weight: 600;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.tl-time-range {
  font-size: 10px;
  opacity: 0.85;
  white-space: nowrap;
  flex-shrink: 0;
}

.chronio-empty {
  color: var(--muted);
  font-size: 12px;
  padding: 12px 0;
}

/* ── NOW LINE ────────────────────────────────────────────────────── */
.tl-now-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  background: #ff4444;
  z-index: 5;
  pointer-events: none;
}

.tl-now-label {
  position: absolute;
  top: -8px;
  right: 4px;
  font-size: 10px;
  color: #ff4444;
  font-weight: 600;
}

/* ── TOOLTIP ─────────────────────────────────────────────────────── */
.tl-tooltip {
  position: fixed;
  z-index: 100;
  background: rgba(15, 17, 23, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  padding: 8px 12px;
  pointer-events: none;
  max-width: 280px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
}

.tl-tooltip-app {
  font-weight: 600;
  font-size: 12px;
  color: #e9eefb;
  margin-bottom: 2px;
}

.tl-tooltip-title {
  font-size: 11px;
  color: #9aa4b2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.tl-tooltip-cat {
  font-size: 10px;
  color: #6b7a8d;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.tl-tooltip-meta {
  font-size: 11px;
  color: #9aa4b2;
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
