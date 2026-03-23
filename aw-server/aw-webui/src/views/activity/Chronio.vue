<template lang="pug">
div.chronio-view
  .chronio-topbar
    .chronio-brand
      .chronio-logo
      span Chronio
    .chronio-controls
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
      .chronio-seg
        button(
          v-for="seg in segments"
          :key="seg.key"
          :class="{ 'is-active': activeSegment === seg.key }"
          @click="activeSegment = seg.key"
        ) {{ seg.label }}
      .chronio-slider
        .track
        .thumb(:style="{ left: sliderPercent + '%' }")
      .chronio-metric
        span.label Tracked:
        span.value {{ trackedTime }}
      .chronio-search
        span.icon
        input(type="text" placeholder="Search…" v-model="searchQuery")

  div.chronio-loading(v-if="loading")
    span Loading activity data…

  .chronio-grid(v-else)
    .chronio-col
      .chronio-section
        .chronio-section-title Stats

      .chronio-card
        .chronio-card-title Most Used Apps
        ul.chronio-list(v-if="mostUsed.length")
          li(v-for="app in mostUsed" :key="app.name")
            span.name {{ app.name }}
            span.time {{ app.time }}
            span.dot(:style="{ background: app.color }")
        .chronio-empty(v-else) No app data for this period

      .chronio-card
        .chronio-card-title Productivity Score
        .chronio-bars(v-if="productivityBars.length")
          span.bar(
            v-for="(bar, i) in productivityBars"
            :key="i"
            :style="{ height: bar.height + '%', background: bar.color }"
          )
        .chronio-empty(v-else) No category data yet

    .chronio-col
      .chronio-section
        .chronio-section-title Activity Timeline
      .chronio-timeline(v-if="timeline.length")
        template(v-for="item in timelineWithMarkers")
          .chronio-time(v-if="item.type === 'time'" :key="'t-' + item.label") {{ item.label }}
          .chronio-block(
            v-else
            :key="'b-' + item.label + item.range"
            :style="{ background: item.color, minHeight: item.height + 'px', cursor: 'pointer' }"
            @click="selectEvent(item.event)"
          )
            .block-header
              .title {{ item.label }}
              .time {{ item.range }}
            .tag(v-if="item.tag") {{ item.tag }}
      .chronio-empty(v-else) No timeline data for this period

    .chronio-col
      .chronio-section
        .chronio-section-title Activity Details
      .chronio-card.detail(v-if="selectedDetail")
        .detail-header
          .app
            .app-icon(:style="{ background: selectedDetail.color || 'rgba(255,255,255,0.08)' }")
            .app-meta
              .name {{ selectedDetail.name }}
              .status {{ selectedDetail.status }}
          .status-dot(v-if="selectedDetail.isActive")
        .detail-time {{ selectedDetail.duration }}
        .detail-sub Started at {{ selectedDetail.startTime }}
        .detail-pill(v-if="selectedDetail.category") {{ selectedDetail.category }}
      .chronio-card.detail(v-else)
        .chronio-empty Click a timeline block to see details

      .chronio-section.inline
        .chronio-section-title Recent Sessions
        a.view-all(@click="") View all
      .chronio-card
        table.chronio-table(v-if="recent.length")
          thead
            tr
              th App
              th Time
              th Dur.
          tbody
            tr(v-for="(row, i) in recent" :key="i" @click="selectEvent(row.event)" style="cursor: pointer")
              td
                span.dot(:style="{ background: row.color }")
                | {{ row.app }}
              td {{ row.time }}
              td {{ row.dur }}
        .chronio-empty(v-else) No recent sessions
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

interface SegmentDef {
  key: string;
  label: string;
  startHour: number;
  endHour: number;
}

const SEGMENTS: SegmentDef[] = [
  { key: 'morning', label: 'Morning', startHour: 6, endHour: 12 },
  { key: 'afternoon', label: 'Afternoon', startHour: 12, endHour: 17 },
  { key: 'evening', label: 'Evening', startHour: 17, endHour: 21 },
  { key: 'night', label: 'Night', startHour: 21, endHour: 6 },
];

// Stable gradient colors per app name
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

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function formatHHMM(ts: string): string {
  return moment(ts).format('HH:mm');
}

function gradientForApp(app: string, index: number): string {
  return GRADIENTS[index % GRADIENTS.length];
}

export default {
  name: 'ChronioView',

  data() {
    return {
      selectedDate: '',
      activeSegment: 'morning' as string,
      searchQuery: '',
      showDatePicker: false,
      loading: true,
      selectedEventIndex: null as number | null,
      segments: SEGMENTS,
      windowEvents: [] as any[],
      afkEvents: [] as any[],
    };
  },

  computed: {
    activityStore() {
      return useActivityStore();
    },
    bucketsStore() {
      return useBucketsStore();
    },
    settingsStore() {
      return useSettingsStore();
    },
    categoryStore() {
      return useCategoryStore();
    },

    isToday(): boolean {
      return moment(this.selectedDate).isSame(moment(), 'day');
    },

    host(): string {
      // Pick the first host that has both window and AFK buckets
      const hosts = this.bucketsStore.hosts;
      for (const h of hosts) {
        if (
          this.bucketsStore.bucketsWindow(h).length > 0 &&
          this.bucketsStore.bucketsAFK(h).length > 0
        ) {
          return h;
        }
      }
      return hosts.length > 0 ? hosts[0] : '';
    },

    dateDisplay(): string {
      if (!this.selectedDate) return '—';
      return moment(this.selectedDate).format('MMM D, YYYY');
    },

    currentSegment(): SegmentDef {
      return SEGMENTS.find(s => s.key === this.activeSegment) || SEGMENTS[0];
    },

    segmentStart(): moment.Moment {
      return moment(this.selectedDate).hour(this.currentSegment.startHour).minute(0).second(0);
    },

    segmentEnd(): moment.Moment {
      const seg = this.currentSegment;
      if (seg.endHour <= seg.startHour) {
        // Night wraps to next day
        return moment(this.selectedDate).add(1, 'day').hour(seg.endHour).minute(0).second(0);
      }
      return moment(this.selectedDate).hour(seg.endHour).minute(0).second(0);
    },

    sliderPercent(): number {
      const now = moment();
      const start = this.segmentStart;
      const end = this.segmentEnd;
      if (now.isBefore(start)) return 0;
      if (now.isAfter(end)) return 100;
      return ((now.valueOf() - start.valueOf()) / (end.valueOf() - start.valueOf())) * 100;
    },

    // Build not-afk intervals from AFK events (skip zero-duration pings)
    notAfkIntervals(): { start: number; end: number }[] {
      return (this.afkEvents || [])
        .filter(e => e.data?.status === 'not-afk' && e.duration > 0)
        .map(e => ({
          start: moment(e.timestamp).valueOf(),
          end: moment(e.timestamp).add(e.duration, 'seconds').valueOf(),
        }));
    },

    // Filter window events: must overlap with a not-afk interval AND the selected segment
    segmentEvents(): any[] {
      const events = this.windowEvents || [];
      const intervals = this.notAfkIntervals;
      const segStart = this.segmentStart.valueOf();
      const segEnd = this.segmentEnd.valueOf();

      return events.filter(e => {
        const eStart = moment(e.timestamp).valueOf();
        const eEnd = eStart + e.duration * 1000;
        // Must overlap with segment
        if (eEnd <= segStart || eStart >= segEnd) return false;
        // Must have meaningful overlap with at least one not-afk interval
        const totalNotAfk = intervals.reduce((sum, iv) => {
          const overlapStart = Math.max(eStart, iv.start);
          const overlapEnd = Math.min(eEnd, iv.end);
          return sum + Math.max(0, overlapEnd - overlapStart);
        }, 0);
        const eventDur = eEnd - eStart;
        // Require at least 10% of the event to be not-afk
        return totalNotAfk > 0 && (totalNotAfk / eventDur) > 0.1;
      });
    },

    filteredEvents(): any[] {
      if (!this.searchQuery) return this.segmentEvents;
      const q = this.searchQuery.toLowerCase();
      return this.segmentEvents.filter(e => {
        const app = (e.data?.app || '').toLowerCase();
        const title = (e.data?.title || '').toLowerCase();
        return app.includes(q) || title.includes(q);
      });
    },

    trackedTime(): string {
      const total = this.activityStore.active?.duration || 0;
      return formatDuration(total);
    },

    mostUsed(): { name: string; time: string; color: string }[] {
      const topApps = this.activityStore.window?.top_apps || [];
      return topApps.slice(0, 8).map(e => ({
        name: e.data?.app || 'Unknown',
        time: formatDuration(e.duration),
        color: getColorFromString(e.data?.app || ''),
      }));
    },

    productivityBars(): { height: number; color: string }[] {
      const cats = this.activityStore.category?.top || [];
      if (!cats.length) return [];
      const maxDur = Math.max(...cats.map(c => c.duration), 1);
      return cats.slice(0, 8).map(c => ({
        height: Math.max(5, (c.duration / maxDur) * 100),
        color: c.data?.$color || '#4b8bff',
      }));
    },

    // Build timeline blocks from events, merging nearby events for the same app
    timeline(): any[] {
      const events = this.filteredEvents;
      if (!events.length) return [];

      // Sort by timestamp
      const sorted = [...events].sort(
        (a, b) => moment(a.timestamp).valueOf() - moment(b.timestamp).valueOf()
      );

      // Pass 1: Merge consecutive events for the same app (any gap)
      const merged1: any[] = [];
      let current: any = null;

      for (const e of sorted) {
        const app = e.data?.app || 'Unknown';

        if (current && current.app === app) {
          // Always merge consecutive same-app events
          const eEnd = moment(e.timestamp).add(e.duration, 'seconds');
          if (eEnd.isAfter(current.end)) {
            current.end = eEnd;
          }
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

      // Pass 2: Absorb short blocks (<30s) into surrounding blocks of the same app
      const blocks: any[] = [];
      for (let i = 0; i < merged1.length; i++) {
        const b = merged1[i];
        const prev = blocks.length > 0 ? blocks[blocks.length - 1] : null;

        // If this is a very short block and next/prev is same app, absorb it
        if (b.duration < 30 && prev && prev.app !== b.app) {
          // Check if next block is same app as prev
          const next = i + 1 < merged1.length ? merged1[i + 1] : null;
          if (next && next.app === prev.app) {
            // Absorb this short block into prev, then next will merge with prev
            prev.end = b.end;
            prev.duration += b.duration;
            continue;
          }
        }

        // Merge with prev if same app
        if (prev && prev.app === b.app) {
          prev.end = b.end;
          prev.duration += b.duration;
        } else {
          blocks.push({ ...b });
        }
      }

      // Build display objects, filtering out short blocks
      const appIndexMap: Record<string, number> = {};
      let idx = 0;

      return blocks
        .filter(b => b.duration >= 60) // skip blocks shorter than 1 minute
        .map(b => {
          if (!(b.app in appIndexMap)) {
            appIndexMap[b.app] = idx++;
          }
          return {
            label: b.app,
            range: formatHHMM(b.start.toISOString()) + ' - ' + formatHHMM(b.end.toISOString()),
            tag: '',
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

      for (const block of this.timeline) {
        // Extract hour from the range start
        const hourStr = block.range.split(' - ')[0];
        const hour = parseInt(hourStr.split(':')[0]);

        if (hour !== lastHour) {
          result.push({ type: 'time', label: hourStr });
          lastHour = hour;
        }
        result.push({ ...block, type: 'block' });
      }
      return result;
    },

    recent(): any[] {
      const events = this.filteredEvents;
      if (!events.length) return [];

      // Most recent events first
      const sorted = [...events]
        .sort((a, b) => moment(b.timestamp).valueOf() - moment(a.timestamp).valueOf())
        .slice(0, 10);

      // Deduplicate by app, keeping the most recent
      const seen = new Set<string>();
      const deduped: any[] = [];
      for (const e of sorted) {
        const app = e.data?.app || 'Unknown';
        if (seen.has(app)) continue;
        seen.add(app);
        deduped.push(e);
        if (deduped.length >= 5) break;
      }

      return deduped.map(e => {
        const app = e.data?.app || 'Unknown';
        const start = moment(e.timestamp);
        const end = moment(e.timestamp).add(e.duration, 'seconds');
        return {
          app,
          time: formatHHMM(start.toISOString()) + ' - ' + formatHHMM(end.toISOString()),
          dur: formatDuration(e.duration),
          color: getColorFromString(app),
          event: e,
        };
      });
    },

    selectedDetail(): any {
      if (this.selectedEventIndex === null) {
        // Show most recent event by default
        const events = this.filteredEvents;
        if (!events.length) return null;
        const latest = [...events].sort(
          (a, b) => moment(b.timestamp).valueOf() - moment(a.timestamp).valueOf()
        )[0];
        return this.buildDetail(latest);
      }
      return this.buildDetail(this.selectedEventIndex);
    },
  },

  methods: {
    buildDetail(event: any): any {
      if (!event) return null;
      const app = event.data?.app || 'Unknown';
      const cat = event.data?.$category;
      const catLabel = cat && cat.length > 0 ? cat.join(' > ') : '';
      const isToday = moment(event.timestamp).isSame(moment(), 'day');

      return {
        name: app,
        status: isToday ? 'Today' : moment(event.timestamp).format('MMM D'),
        isActive: isToday && moment(event.timestamp).add(event.duration, 'seconds').isAfter(moment().subtract(5, 'minutes')),
        duration: formatDuration(event.duration),
        startTime: formatHHMM(event.timestamp),
        category: catLabel,
        color: getColorFromString(app),
      };
    },

    selectEvent(event: any) {
      this.selectedEventIndex = event;
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

    async refresh() {
      if (!this.host) return;
      this.loading = true;

      const settingsStore = this.settingsStore;
      const timeperiod = dateToTimeperiod(this.selectedDate, settingsStore.startOfDay);

      // Fetch aggregated data first (top apps, categories, duration)
      await this.activityStore.ensure_loaded({
        timeperiod,
        host: this.host,
        filter_afk: true,
        include_audible: false,
        include_stopwatch: false,
        force: true,
        always_active_pattern: settingsStore.always_active_pattern,
      });

      // Then fetch raw window + AFK events for the timeline
      const windowBuckets = this.bucketsStore.bucketsWindow(this.host);
      const afkBuckets = this.bucketsStore.bucketsAFK(this.host);
      const startDate = moment(this.selectedDate).startOf('day').toDate();
      const endDate = moment(this.selectedDate).endOf('day').toDate();
      const params = { start: startDate, end: endDate, limit: -1 };

      // These can run in parallel since ensure_loaded is done
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

    detectSegment() {
      const hour = moment().hour();
      if (hour >= 6 && hour < 12) this.activeSegment = 'morning';
      else if (hour >= 12 && hour < 17) this.activeSegment = 'afternoon';
      else if (hour >= 17 && hour < 21) this.activeSegment = 'evening';
      else this.activeSegment = 'night';
    },
  },

  watch: {
    host() {
      if (this.host) this.refresh();
    },
  },

  async mounted() {
    const settingsStore = this.settingsStore;
    await settingsStore.ensureLoaded();

    this.selectedDate = get_today_with_offset(settingsStore.startOfDay);
    this.detectSegment();

    await this.bucketsStore.ensureLoaded();
    if (this.host) {
      await this.refresh();
    } else {
      this.loading = false;
    }
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
  --glow: 0 20px 60px rgba(0, 0, 0, 0.45);
  color: var(--text);
  background: radial-gradient(1200px 700px at 10% -10%, rgba(80, 120, 255, 0.12), transparent 60%),
              radial-gradient(900px 700px at 90% 10%, rgba(255, 110, 70, 0.12), transparent 55%),
              var(--bg);
  border-radius: 16px;
  padding: 20px;
  font-family: system-ui, -apple-system, sans-serif;
  min-height: 100vh;
}

.chronio-topbar {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 16px;
  align-items: center;
  margin-bottom: 18px;
}

.chronio-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  letter-spacing: 0.4px;
}

.chronio-logo {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid #4b8bff;
  box-shadow: 0 0 0 4px rgba(75, 139, 255, 0.15);
}

.chronio-controls {
  display: grid;
  grid-template-columns: auto auto 1fr auto auto;
  gap: 12px;
  align-items: center;
}

.chronio-date-nav {
  display: flex;
  align-items: center;
  gap: 8px;
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
  &:hover { color: #fff; border-color: rgba(255,255,255,0.2); }
  &:disabled { opacity: 0.3; cursor: not-allowed; }
}

.chronio-chip {
  padding: 6px 12px;
  border-radius: 10px;
  background: var(--panel);
  border: 1px solid var(--border);
  font-size: 12px;
  color: var(--muted);
  cursor: pointer;
  position: relative;
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

.chronio-seg {
  display: inline-flex;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}

.chronio-seg button {
  background: transparent;
  border: 0;
  color: var(--muted);
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
}

.chronio-seg button.is-active {
  background: rgba(75, 139, 255, 0.2);
  color: var(--text);
}

.chronio-slider {
  position: relative;
  height: 8px;
}

.chronio-slider .track {
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  position: absolute;
  top: 2px;
  left: 0;
  right: 0;
}

.chronio-slider .thumb {
  position: absolute;
  top: -2px;
  width: 12px;
  height: 12px;
  background: #4b8bff;
  border-radius: 50%;
  box-shadow: 0 0 0 4px rgba(75, 139, 255, 0.2);
  transition: left 0.3s ease;
}

.chronio-metric {
  display: inline-flex;
  gap: 6px;
  font-size: 12px;
  color: var(--muted);
}

.chronio-metric .value {
  color: var(--text);
  font-weight: 600;
}

.chronio-search {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 12px;
  background: var(--panel);
  border: 1px solid var(--border);
}

.chronio-search input {
  background: transparent;
  border: 0;
  color: var(--text);
  outline: none;
  font-size: 12px;
  width: 140px;
}

.chronio-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: var(--muted);
  font-size: 14px;
}

.chronio-empty {
  color: var(--muted);
  font-size: 12px;
  padding: 12px 0;
}

.chronio-grid {
  display: grid;
  grid-template-columns: 1fr 1.4fr 1fr;
  gap: 16px;
}

.chronio-col {
  display: grid;
  gap: 16px;
  align-content: start;
}

.chronio-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chronio-section.inline {
  margin-top: 4px;
}

.chronio-section-title {
  font-size: 12px;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: var(--muted);
}

.chronio-tabs {
  display: inline-flex;
  gap: 6px;
  background: var(--panel);
  border: 1px solid var(--border);
  padding: 4px;
  border-radius: 12px;
}

.chronio-tabs button {
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  padding: 4px 10px;
  cursor: pointer;
}

.chronio-tabs button.is-active {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text);
  border-radius: 8px;
}

.chronio-card {
  background: var(--panel-2);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 16px;
  box-shadow: var(--glow);
}

.chronio-card.detail {
  padding: 18px;
}

.chronio-card-title {
  font-size: 14px;
  margin-bottom: 12px;
}

.chronio-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}

.chronio-list li {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 10px;
  align-items: center;
  font-size: 13px;
}

.chronio-list .time {
  color: var(--muted);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.chronio-bars {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(20px, 1fr));
  gap: 6px;
  align-items: end;
  height: 80px;
}

.chronio-bars .bar {
  background: linear-gradient(180deg, #4b8bff, rgba(75, 139, 255, 0.2));
  border-radius: 6px;
  min-height: 4px;
}

.chronio-timeline {
  display: grid;
  gap: 6px;
  position: relative;
  max-height: 70vh;
  overflow-y: auto;
}

.chronio-time {
  font-size: 11px;
  color: var(--muted);
  padding-top: 4px;
}

.chronio-block {
  border-radius: 14px;
  padding: 10px 14px;
  color: #fff;
  transition: transform 0.1s ease, box-shadow 0.1s ease;
}

.chronio-block:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.chronio-block .block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chronio-block .title {
  font-weight: 600;
  font-size: 13px;
}

.chronio-block .time {
  font-size: 11px;
  opacity: 0.85;
}

.chronio-block .tag {
  font-size: 11px;
  opacity: 0.8;
  margin-top: 4px;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.app {
  display: flex;
  gap: 10px;
  align-items: center;
}

.app-icon {
  width: 34px;
  height: 34px;
  border-radius: 8px;
}

.app-meta .name {
  font-weight: 600;
}

.app-meta .status {
  font-size: 11px;
  color: var(--muted);
}

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #26d07c;
  box-shadow: 0 0 0 4px rgba(38, 208, 124, 0.2);
}

.detail-time {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 28px;
  margin: 6px 0 2px;
}

.detail-sub {
  font-size: 12px;
  color: var(--muted);
}

.detail-pill {
  margin-top: 10px;
  display: inline-flex;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(75, 139, 255, 0.15);
  color: #7db0ff;
  font-size: 11px;
}

.chronio-table {
  width: 100%;
  font-size: 12px;
  color: var(--muted);
}

.chronio-table th {
  font-weight: 600;
  text-transform: uppercase;
  font-size: 10px;
  letter-spacing: 0.8px;
  color: var(--muted);
  padding-bottom: 8px;
}

.chronio-table td {
  padding: 6px 0;
  color: var(--text);
}

.chronio-table td .dot {
  margin-right: 6px;
}

.chronio-table tr:hover td {
  color: #fff;
}

.view-all {
  color: #7db0ff;
  font-size: 11px;
  cursor: pointer;
}

@media (max-width: 1200px) {
  .chronio-grid {
    grid-template-columns: 1fr;
  }
  .chronio-controls {
    grid-template-columns: 1fr;
  }
  .chronio-search input {
    width: 100%;
  }
}
</style>
