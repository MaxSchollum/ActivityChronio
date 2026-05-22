<template lang="pug">
div.trends-view
  .trends-topbar
    button.trends-brand(@click="$router.push('/chronio')")
      .trends-logo
      span Chronio
    .trends-title
      h1 Stats
      span {{ rangeLabel }}
    .range-control(aria-label="Trend range")
      button(
        v-for="range in ranges"
        :key="range"
        :class="{ active: rangeDays === range }"
        :disabled="loading"
        @click="setRange(range)"
      ) {{ range }} days

  .trends-body
    aside.trends-sidebar
      nav.sidebar-nav
        button.sidebar-nav-item(@click="$router.push('/chronio')") Activities
        button.sidebar-nav-item.active Stats
        button.sidebar-nav-item(@click="openReports") Reports
      .sidebar-summary
        span Days tracked
        strong {{ trackedDays }} / {{ dailyPoints.length }}
        small {{ rangeLabel }}

    main.trends-main
      .trends-message(v-if="loading")
        .loading-line
        strong Loading {{ rangeDays }} days of trend data
        span(v-if="heatmapProgress") {{ heatmapProgress }}
      .trends-message.error(v-else-if="error")
        strong Trend data could not be loaded
        span {{ error }}
        button(@click="loadTrends") Retry
      .trends-message(v-else-if="!host")
        strong No activity buckets found
        span Chronio needs window and AFK activity before it can calculate trends.
      template(v-else)
        .metric-row
          .metric
            span Average tracked hours
            strong {{ averageTrackedHours }}
            small Per day in the selected range
          .metric
            span Average productivity
            strong(:class="productivityTone(averageProductivity)") {{ formatProductivity(averageProductivity) }}
            small Scored tracked time in this range
          .metric
            span Most productive day
            strong {{ topWeekdayLabel }}
            small {{ topWeekdayDetail }}

        .trends-message.empty(v-if="!hasDailyData")
          strong No tracked activity in this range
          span The dashboard will fill in after Chronio records active window time.

        .chart-grid(v-else)
          section.chart-panel
            header
              h2 Daily productivity
              span Productive category score as a percentage of tracked time
            .chart-frame
              line-chart(:chart-data="scoreChartData" :chart-options="scoreChartOptions")

          section.chart-panel
            header
              h2 Category mix
              span Share of tracked time by day
            .chart-frame
              line-chart(:chart-data="categoryChartData" :chart-options="categoryChartOptions")

        section.heatmap-panel(v-if="hasDailyData")
          header
            h2 Productive hours
            span Average category score by weekday and hour
          .heatmap(v-if="!heatmapEmpty")
            .heatmap-corner
            .heatmap-hour(v-for="hour in heatmapHours" :key="'hour-' + hour") {{ formatHeatmapHour(hour) }}
            template(v-for="row in heatmapRows")
              .heatmap-day(:key="'day-' + row.weekday") {{ row.label }}
              .heatmap-cell(
                v-for="cell in row.cells"
                :key="cell.key"
                :style="{ backgroundColor: heatmapColor(cell.score) }"
                :title="cell.title"
              )
                span(v-if="Math.abs(cell.score) >= 0.05") {{ formatCellScore(cell.score) }}
          .heatmap-empty(v-else) Productive hour detail is not available for this range.
</template>

<script lang="ts">
import moment from 'moment';
import 'chart.js/auto';
import { Line } from 'vue-chartjs/legacy';
import queries from '~/queries';
import { useActivityStore } from '~/stores/activity';
import { useBucketsStore } from '~/stores/buckets';
import { useCategoryStore } from '~/stores/categories';
import { useSettingsStore } from '~/stores/settings';
import { getClient } from '~/util/awclient';
import { chronioProductivityPercent } from '~/util/chronio';
import { get_today_with_offset } from '~/util/time';
import {
  TimePeriod,
  dateToTimeperiod,
  timeperiodToStr,
  timeperiodsDaysOfPeriod,
  timeperiodsHoursOfPeriod,
} from '~/util/timeperiod';
import { IEvent } from '~/util/interfaces';

interface PeriodResult {
  cat_events?: IEvent[];
}

interface CategoryDuration {
  key: string;
  label: string;
  color: string;
  duration: number;
}

interface DailyPoint {
  date: string;
  productivity: number | null;
  trackedSeconds: number;
  categories: CategoryDuration[];
}

interface HourPoint {
  period: string;
  events: IEvent[];
}

interface HeatmapCell {
  key: string;
  score: number;
  trackedHours: number;
  title: string;
}

const RANGES = [30, 90];
const HEATMAP_QUERY_CHUNK = 24 * 5;
const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const CATEGORY_SEPARATOR = '\u001f';

function categoryName(event: IEvent): string[] {
  const name = event && event.data && event.data['$category'];
  return Array.isArray(name) && name.length > 0 ? name : ['Uncategorized'];
}

function periodStart(period: string): moment.Moment {
  return moment(period.split('/')[0]);
}

export default {
  name: 'ChronioTrends',
  components: { LineChart: Line },

  data() {
    return {
      activityStore: useActivityStore(),
      bucketsStore: useBucketsStore(),
      categoryStore: useCategoryStore(),
      settingsStore: useSettingsStore(),
      ranges: RANGES,
      rangeDays: 30,
      dailyPoints: [] as DailyPoint[],
      hourlyPoints: [] as HourPoint[],
      loading: true,
      error: '',
      heatmapProgress: '',
      loadSequence: 0,
    };
  },

  computed: {
    host(): string {
      const hosts = this.bucketsStore.hosts as string[];
      for (const host of hosts) {
        if (
          this.bucketsStore.bucketsWindow(host).length > 0 &&
          this.bucketsStore.bucketsAFK(host).length > 0
        ) {
          return host;
        }
      }
      return '';
    },

    rangeTimeperiod(): TimePeriod {
      const today = get_today_with_offset(this.settingsStore.startOfDay);
      const firstDay = moment(today)
        .subtract(this.rangeDays - 1, 'days')
        .format('YYYY-MM-DD');
      return dateToTimeperiod(firstDay, this.settingsStore.startOfDay, [this.rangeDays, 'day']);
    },

    rangeLabel(): string {
      const first = moment(this.rangeTimeperiod.start).format('MMM D');
      const last = moment(this.rangeTimeperiod.start)
        .add(this.rangeDays - 1, 'days')
        .format('MMM D, YYYY');
      return `${first} - ${last}`;
    },

    hasDailyData(): boolean {
      return this.dailyPoints.some((point: DailyPoint) => point.trackedSeconds > 0);
    },

    trackedDays(): number {
      return this.dailyPoints.filter((point: DailyPoint) => point.trackedSeconds > 0).length;
    },

    averageTrackedHours(): string {
      if (this.dailyPoints.length === 0) return '0.0h';
      const total = this.dailyPoints.reduce(
        (seconds: number, point: DailyPoint) => seconds + point.trackedSeconds,
        0
      );
      return `${(total / this.dailyPoints.length / 3600).toFixed(1)}h`;
    },

    averageProductivity(): number | null {
      const tracked = this.dailyPoints.reduce(
        (seconds: number, point: DailyPoint) => seconds + point.trackedSeconds,
        0
      );
      if (!tracked) return null;
      const weighted = this.dailyPoints.reduce((total: number, point: DailyPoint) => {
        return total + (point.productivity || 0) * point.trackedSeconds;
      }, 0);
      return Math.round(weighted / tracked);
    },

    scoreChartData() {
      return {
        labels: this.dailyPoints.map((point: DailyPoint) => moment(point.date).format('MMM D')),
        datasets: [
          {
            label: 'Productivity',
            data: this.dailyPoints.map((point: DailyPoint) => point.productivity),
            borderColor: '#2e7d53',
            backgroundColor: 'rgba(46, 125, 83, 0.14)',
            pointBackgroundColor: '#2e7d53',
            pointRadius: 2,
            pointHoverRadius: 4,
            tension: 0.25,
            fill: true,
          },
        ],
      };
    },

    scoreChartOptions() {
      return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { intersect: false, mode: 'index' },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: context => `Productivity: ${this.formatProductivity(context.parsed.y)}`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: '#9aa4b2', maxTicksLimit: this.rangeDays === 30 ? 10 : 12 },
          },
          y: {
            grid: { color: 'rgba(255, 255, 255, 0.08)' },
            min: 0,
            max: 100,
            ticks: { callback: value => `${value}%`, color: '#9aa4b2' },
            title: { color: '#9aa4b2', display: true, text: 'Productivity' },
          },
        },
      };
    },

    categoryKeys(): string[] {
      const totals: Record<string, number> = {};
      for (const point of this.dailyPoints as DailyPoint[]) {
        for (const category of point.categories) {
          totals[category.key] = (totals[category.key] || 0) + category.duration;
        }
      }
      return Object.keys(totals)
        .sort((left: string, right: string) => totals[right] - totals[left])
        .slice(0, 7);
    },

    categoryChartData() {
      const featuredKeys = new Set(this.categoryKeys);
      const categoryDatasets = this.categoryKeys.map((key: string) => {
        const sample = this.dailyPoints
          .flatMap((point: DailyPoint) => point.categories)
          .find((category: CategoryDuration) => category.key === key);
        return {
          label: sample.label,
          data: this.dailyPoints.map((point: DailyPoint) => {
            if (point.trackedSeconds === 0) return 0;
            const category = point.categories.find((entry: CategoryDuration) => entry.key === key);
            return category ? (category.duration / point.trackedSeconds) * 100 : 0;
          }),
          borderColor: sample.color,
          backgroundColor: this.colorWithAlpha(sample.color, 0.62),
          fill: true,
          pointRadius: 0,
          tension: 0.18,
        };
      });
      const hasOtherCategories = this.dailyPoints.some((point: DailyPoint) =>
        point.categories.some((category: CategoryDuration) => !featuredKeys.has(category.key))
      );

      if (hasOtherCategories) {
        categoryDatasets.push({
          label: 'Other',
          data: this.dailyPoints.map((point: DailyPoint) => {
            if (point.trackedSeconds === 0) return 0;
            const duration = point.categories
              .filter((category: CategoryDuration) => !featuredKeys.has(category.key))
              .reduce((seconds: number, category: CategoryDuration) => {
                return seconds + category.duration;
              }, 0);
            return (duration / point.trackedSeconds) * 100;
          }),
          borderColor: '#7a8797',
          backgroundColor: this.colorWithAlpha('#7a8797', 0.44),
          fill: true,
          pointRadius: 0,
          tension: 0.18,
        });
      }

      return {
        labels: this.dailyPoints.map((point: DailyPoint) => moment(point.date).format('MMM D')),
        datasets: categoryDatasets,
      };
    },

    categoryChartOptions() {
      return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { intersect: false, mode: 'index' },
        plugins: {
          legend: {
            position: 'bottom',
            labels: { boxWidth: 10, boxHeight: 10, color: '#9aa4b2' },
          },
          tooltip: {
            callbacks: {
              label: context => `${context.dataset.label}: ${context.parsed.y.toFixed(1)}%`,
            },
          },
        },
        scales: {
          x: {
            stacked: true,
            grid: { display: false },
            ticks: { color: '#9aa4b2', maxTicksLimit: this.rangeDays === 30 ? 10 : 12 },
          },
          y: {
            stacked: true,
            min: 0,
            max: 100,
            grid: { color: 'rgba(255, 255, 255, 0.08)' },
            ticks: { callback: value => `${value}%`, color: '#9aa4b2' },
            title: { color: '#9aa4b2', display: true, text: 'Tracked time' },
          },
        },
      };
    },

    heatmapHours(): number[] {
      return Array.from({ length: 24 }, (_, hour) => hour);
    },

    weekdayProductivity(): (number | null)[] {
      const totals = Array.from({ length: 7 }, () => ({ weighted: 0, trackedSeconds: 0 }));
      for (const point of this.dailyPoints as DailyPoint[]) {
        const total = totals[moment(point.date).day()];
        total.weighted += (point.productivity || 0) * point.trackedSeconds;
        total.trackedSeconds += point.trackedSeconds;
      }
      return totals.map(total => {
        return total.trackedSeconds ? Math.round(total.weighted / total.trackedSeconds) : null;
      });
    },

    topWeekday(): number {
      let topWeekday = 0;
      for (let weekday = 1; weekday < this.weekdayProductivity.length; weekday++) {
        if ((this.weekdayProductivity[weekday] || 0) > (this.weekdayProductivity[topWeekday] || 0)) {
          topWeekday = weekday;
        }
      }
      return topWeekday;
    },

    topWeekdayLabel(): string {
      if (!this.hasDailyData) return 'No data';
      return WEEKDAYS[this.topWeekday];
    },

    topWeekdayDetail(): string {
      if (!this.hasDailyData) return 'Selected range has no tracked time';
      return `${this.formatProductivity(this.weekdayProductivity[this.topWeekday])} average productivity`;
    },

    weekdayCounts(): number[] {
      const counts = Array.from({ length: 7 }, () => 0);
      for (const point of this.dailyPoints as DailyPoint[]) counts[moment(point.date).day()]++;
      return counts;
    },

    heatmapRows(): { weekday: number; label: string; cells: HeatmapCell[] }[] {
      const totals = Array.from({ length: 7 }, () =>
        Array.from({ length: 24 }, () => ({ score: 0, trackedSeconds: 0 }))
      );

      for (const point of this.hourlyPoints as HourPoint[]) {
        const start = periodStart(point.period);
        const cell = totals[start.day()][start.hour()];
        cell.score += this.scoreEvents(point.events);
        cell.trackedSeconds += this.trackedSeconds(point.events);
      }

      return WEEKDAYS.map((label: string, weekday: number) => ({
        weekday,
        label,
        cells: this.heatmapHours.map((hour: number) => {
          const sampleCount = this.weekdayCounts[weekday] || 1;
          const score = totals[weekday][hour].score / sampleCount;
          const trackedHours = totals[weekday][hour].trackedSeconds / sampleCount / 3600;
          return {
            key: `${weekday}-${hour}`,
            score,
            trackedHours,
            title: `${label} ${this.formatHeatmapHour(hour)}: ${this.formatScore(
              score
            )} average score, ${trackedHours.toFixed(1)}h tracked`,
          };
        }),
      }));
    },

    heatmapScoreLimit(): number {
      const scores = this.heatmapRows.flatMap(row =>
        row.cells.map((cell: HeatmapCell) => Math.abs(cell.score))
      );
      return Math.max(...scores, 0.5);
    },

    heatmapEmpty(): boolean {
      return (
        this.hourlyPoints.length === 0 ||
        this.heatmapRows.every(row =>
          row.cells.every((cell: HeatmapCell) => cell.trackedHours === 0)
        )
      );
    },
  },

  async mounted() {
    await this.settingsStore.ensureLoaded();
    await this.bucketsStore.ensureLoaded();
    await this.categoryStore.load();
    await this.loadTrends();
  },

  methods: {
    setRange(range: number) {
      if (range === this.rangeDays || this.loading) return;
      this.rangeDays = range;
      this.loadTrends();
    },

    openReports() {
      this.$router.push({ path: '/chronio/week', query: { report: 'weekly' } });
    },

    async loadTrends() {
      const sequence = ++this.loadSequence;
      this.loading = true;
      this.error = '';
      this.heatmapProgress = '';
      this.dailyPoints = [];
      this.hourlyPoints = [];

      try {
        if (!this.host) return;

        const queryOptions = {
          host: this.host,
          timeperiod: this.rangeTimeperiod,
          filter_afk: true,
          include_audible: false,
          filter_categories: undefined,
          always_active_pattern: this.settingsStore.always_active_pattern,
          dontQueryInactive: false,
        };

        await this.activityStore.get_buckets(queryOptions);
        this.activityStore.set_available();
        if (!this.activityStore.category.available) return;

        await this.activityStore.query_category_time_by_period(queryOptions);
        if (sequence !== this.loadSequence) return;

        this.dailyPoints = this.toDailyPoints(this.activityStore.category.by_period || {});
        await this.loadHourlyHeatmap(queryOptions.timeperiod, sequence);
      } catch (err) {
        if (sequence === this.loadSequence) {
          this.error = err instanceof Error ? err.message : String(err);
        }
      } finally {
        if (sequence === this.loadSequence) {
          this.loading = false;
          this.heatmapProgress = '';
        }
      }
    },

    toDailyPoints(byPeriod: Record<string, PeriodResult>): DailyPoint[] {
      return Object.entries(byPeriod)
        .map(([period, result]: [string, PeriodResult]) => {
          const events = result && result.cat_events ? result.cat_events : [];
          return {
            date: periodStart(period).format('YYYY-MM-DD'),
            productivity: this.productivityPercent(events),
            trackedSeconds: this.trackedSeconds(events),
            categories: this.categoryDurations(events),
          };
        })
        .sort((left: DailyPoint, right: DailyPoint) => left.date.localeCompare(right.date));
    },

    categoryDurations(events: IEvent[]): CategoryDuration[] {
      return events.map((event: IEvent) => {
        const name = categoryName(event);
        return {
          key: name.join(CATEGORY_SEPARATOR),
          label: name.join(' > '),
          color: this.categoryStore.get_category_color(name),
          duration: event.duration || 0,
        };
      });
    },

    trackedSeconds(events: IEvent[]): number {
      return events.reduce(
        (duration: number, event: IEvent) => duration + (event.duration || 0),
        0
      );
    },

    productivityPercent(events: IEvent[]): number | null {
      return chronioProductivityPercent(
        events.map((event: IEvent) => ({
          durationSeconds: event.duration || 0,
          productivityScore: this.categoryStore.get_category_score(categoryName(event)),
        }))
      );
    },

    scoreEvents(events: IEvent[]): number {
      return events.reduce((score: number, event: IEvent) => {
        return (
          score +
          ((event.duration || 0) / 3600) *
            this.categoryStore.get_category_score(categoryName(event))
        );
      }, 0);
    },

    hourlyPeriods(timeperiod: TimePeriod): string[] {
      return timeperiodsDaysOfPeriod(timeperiod)
        .flatMap((day: TimePeriod) => timeperiodsHoursOfPeriod(day))
        .map((hour: TimePeriod) => timeperiodToStr(hour))
        .filter((period: string) => periodStart(period).isBefore(moment()));
    },

    categoryQuery() {
      const shared = {
        bid_browsers: this.activityStore.buckets.browser,
        bid_stopwatch: undefined,
        categories: this.categoryStore.classes_for_query,
        filter_categories: undefined,
      };

      if (this.activityStore.buckets.android[0]) {
        return queries.categoryQuery({
          ...shared,
          bid_android: this.activityStore.buckets.android[0],
        });
      }

      return queries.categoryQuery({
        ...shared,
        bid_afk: this.activityStore.buckets.afk[0],
        bid_window: this.activityStore.buckets.window[0],
        filter_afk: true,
        always_active_pattern: this.settingsStore.always_active_pattern,
      });
    },

    async loadHourlyHeatmap(timeperiod: TimePeriod, sequence: number) {
      const periods = this.hourlyPeriods(timeperiod);
      const query = this.categoryQuery();
      const points: HourPoint[] = [];

      for (let offset = 0; offset < periods.length; offset += HEATMAP_QUERY_CHUNK) {
        if (sequence !== this.loadSequence) return;
        const chunk = periods.slice(offset, offset + HEATMAP_QUERY_CHUNK);
        this.heatmapProgress = `Loading hourly detail ${Math.min(
          offset + chunk.length,
          periods.length
        )} of ${periods.length}`;
        const results = await getClient().query(chunk, query, {
          name: 'chronioTrendsHeatmap',
          verbose: false,
        });
        results.forEach((result: PeriodResult, index: number) => {
          points.push({
            period: chunk[index],
            events: result && result.cat_events ? result.cat_events : [],
          });
        });
      }

      if (sequence === this.loadSequence) this.hourlyPoints = points;
    },

    colorWithAlpha(color: string, alpha: number): string {
      const hex = color.replace('#', '');
      if (!/^[0-9a-f]{6}$/i.test(hex)) return color;
      const channels = [0, 2, 4].map(start => parseInt(hex.slice(start, start + 2), 16));
      return `rgba(${channels[0]}, ${channels[1]}, ${channels[2]}, ${alpha})`;
    },

    heatmapColor(score: number): string {
      if (Math.abs(score) < 0.05) return 'rgba(91, 109, 129, 0.1)';
      const strength = Math.min(Math.abs(score) / this.heatmapScoreLimit, 1);
      const alpha = 0.18 + strength * 0.72;
      return score > 0 ? `rgba(33, 146, 93, ${alpha})` : `rgba(201, 72, 70, ${alpha})`;
    },

    formatScore(score: number): string {
      const rounded = Math.round(score * 10) / 10;
      return `${rounded > 0 ? '+' : ''}${rounded.toFixed(1)}`;
    },

    formatProductivity(productivity: number | null): string {
      return productivity === null ? '-' : `${Math.round(productivity)}%`;
    },

    formatCellScore(score: number): string {
      return this.formatScore(score);
    },

    formatHeatmapHour(hour: number): string {
      return moment().startOf('day').hour(hour).format('ha');
    },

    productivityTone(productivity: number | null): string {
      if (productivity === null) return 'neutral';
      if (productivity >= 70) return 'positive';
      if (productivity >= 40) return 'neutral';
      return 'negative';
    },
  },
};
</script>

<style lang="scss" scoped>
.trends-view {
  --bg: #0f1117;
  --border: rgba(255, 255, 255, 0.08);
  --border-hover: rgba(255, 255, 255, 0.15);
  --muted: #9aa4b2;
  --panel: rgba(20, 24, 33, 0.9);
  --panel-2: rgba(22, 26, 36, 0.9);
  --text: #e9eefb;
  min-height: 100vh;
  background:
    radial-gradient(1200px 700px at 10% -10%, rgba(80, 120, 255, 0.12), transparent 60%),
    radial-gradient(900px 700px at 90% 10%, rgba(255, 110, 70, 0.12), transparent 55%),
    var(--bg);
  color: var(--text);
  display: flex;
  flex-direction: column;
}

.trends-topbar {
  height: 58px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 0 22px;
}

.trends-brand {
  align-items: center;
  background: transparent;
  border: 0;
  color: inherit;
  display: flex;
  flex: 0 0 auto;
  font-size: 17px;
  font-weight: 650;
  gap: 10px;
  padding: 0;
}

.trends-logo {
  border: 2px solid #4b8bff;
  border-radius: 50%;
  box-shadow: 0 0 0 4px rgba(75, 139, 255, 0.15);
  height: 26px;
  width: 26px;
}

.trends-title {
  align-items: baseline;
  display: flex;
  flex: 1 1 auto;
  gap: 12px;
  min-width: 0;

  h1 {
    font-size: 18px;
    font-weight: 650;
    letter-spacing: 0;
    line-height: 1;
    margin: 0;
  }

  span {
    color: var(--muted);
    font-size: 13px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.range-control {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 7px;
  display: flex;
  flex: 0 0 auto;
  padding: 2px;

  button {
    background: transparent;
    border: 0;
    border-radius: 5px;
    color: var(--muted);
    font-size: 13px;
    height: 31px;
    min-width: 72px;
    padding: 0 12px;
  }

  button.active {
    background: rgba(75, 139, 255, 0.14);
    color: var(--text);
  }

  button:disabled {
    cursor: wait;
    opacity: 0.55;
  }
}

.trends-body {
  display: grid;
  flex: 1 1 auto;
  grid-template-columns: 214px minmax(0, 1fr);
  min-height: 0;
}

.trends-sidebar {
  background: rgba(15, 17, 23, 0.46);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding: 18px 12px;
}

.sidebar-nav {
  display: grid;
  gap: 3px;
}

.sidebar-nav-item {
  background: transparent;
  border: 0;
  border-radius: 6px;
  color: var(--muted);
  font-size: 14px;
  height: 34px;
  padding: 0 10px;
  text-align: left;
}

.sidebar-nav-item:hover:not(:disabled),
.sidebar-nav-item.active {
  background: rgba(75, 139, 255, 0.08);
  color: var(--text);
}

.sidebar-summary {
  border-top: 1px solid var(--border);
  display: grid;
  gap: 4px;
  padding: 18px 10px 0;

  span,
  small {
    color: var(--muted);
    font-size: 12px;
  }

  strong {
    font-size: 27px;
    font-weight: 650;
    letter-spacing: 0;
    line-height: 1.15;
  }
}

.trends-main {
  display: grid;
  gap: 16px;
  grid-auto-rows: min-content;
  min-width: 0;
  padding: 22px;
}

.metric-row {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.metric {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 7px;
  display: grid;
  gap: 3px;
  min-height: 92px;
  padding: 15px 16px;

  span,
  small {
    color: var(--muted);
    font-size: 12px;
  }

  strong {
    font-size: 28px;
    font-weight: 650;
    letter-spacing: 0;
    line-height: 1.15;
  }

  strong.positive {
    color: #22c55e;
  }

  strong.negative {
    color: #ef4444;
  }
}

.chart-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.chart-panel,
.heatmap-panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 7px;
  min-width: 0;
  padding: 16px;

  header {
    display: grid;
    gap: 3px;
    margin-bottom: 14px;
  }

  h2 {
    font-size: 15px;
    font-weight: 650;
    letter-spacing: 0;
    line-height: 1.2;
    margin: 0;
  }

  header span {
    color: var(--muted);
    font-size: 12px;
  }
}

.chart-frame {
  height: 390px;
  position: relative;
}

.trends-message {
  align-items: flex-start;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 7px;
  color: var(--muted);
  display: grid;
  gap: 6px;
  padding: 22px;

  strong {
    color: var(--text);
    font-size: 16px;
    font-weight: 650;
  }

  button {
    background: rgba(75, 139, 255, 0.14);
    border: 1px solid rgba(75, 139, 255, 0.36);
    border-radius: 6px;
    color: #fff;
    height: 33px;
    margin-top: 4px;
    padding: 0 13px;
  }
}

.trends-message.empty {
  border-style: dashed;
}

.trends-message.error {
  border-color: rgba(239, 68, 68, 0.42);
}

.loading-line {
  animation: load 1.2s ease-in-out infinite;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.05), rgba(75, 139, 255, 0.42), rgba(255, 255, 255, 0.05));
  background-size: 220% 100%;
  border-radius: 4px;
  height: 4px;
  width: min(320px, 100%);
}

.heatmap {
  display: grid;
  gap: 4px;
  grid-template-columns: 42px repeat(24, minmax(24px, 1fr));
  overflow-x: auto;
}

.heatmap-corner,
.heatmap-hour,
.heatmap-day,
.heatmap-cell {
  min-height: 28px;
}

.heatmap-hour,
.heatmap-day {
  align-items: center;
  color: var(--muted);
  display: flex;
  font-size: 11px;
}

.heatmap-hour {
  justify-content: center;
  white-space: nowrap;
}

.heatmap-cell {
  align-items: center;
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
  display: flex;
  font-size: 10px;
  justify-content: center;
  overflow: hidden;
}

.heatmap-empty {
  border: 1px dashed var(--border);
  border-radius: 6px;
  color: var(--muted);
  padding: 18px;
}

@keyframes load {
  from {
    background-position: 100% 0;
  }
  to {
    background-position: -120% 0;
  }
}

@media (max-width: 980px) {
  .trends-body {
    grid-template-columns: 1fr;
  }

  .trends-sidebar {
    border-bottom: 1px solid var(--border);
    border-right: 0;
    gap: 12px;
    padding: 12px;
  }

  .sidebar-nav {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .sidebar-summary {
    border-top: 0;
    padding-top: 4px;
  }
}

@media (max-width: 760px) {
  .trends-topbar {
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 10px 16px;
    height: auto;
    padding: 13px 14px;
  }

  .trends-title {
    flex-basis: calc(100% - 112px);
  }

  .range-control {
    width: 100%;
  }

  .range-control button {
    flex: 1 1 0;
  }

  .trends-main {
    padding: 14px;
  }

  .metric-row,
  .chart-grid {
    grid-template-columns: 1fr;
  }
}
</style>
