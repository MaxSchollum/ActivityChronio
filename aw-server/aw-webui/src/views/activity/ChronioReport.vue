<template lang="pug">
.chronio-report
  .report-toolbar
    button.report-command(@click="$emit('close')") Back to activities
    button.report-command.primary(@click="printReport") Print

  article.report-page
    header.report-header
      p Weekly Report
      h1 {{ label }}
      span {{ totalTrackedLabel }} tracked across {{ trackedDayCount }} days

    .report-empty(v-if="!hasRows") No tracked activity is available for this week.

    template(v-else)
      .report-metrics
        .report-metric
          span Total tracked
          strong {{ totalTrackedLabel }}
        .report-metric
          span Productivity
          strong {{ productivityLabel }}
        .report-metric
          span Recorded events
          strong {{ reportRows.length }}

      section.report-section
        h2 Productivity trend
        ol.trend-list
          li(v-for="day in productivityTrend" :key="day.date")
            .trend-label
              strong {{ day.label }}
              span {{ day.trackedLabel }}
            .trend-meter
              i(v-if="day.seconds" :style="{ width: day.score + '%' }")
            em {{ day.seconds ? day.score + '%' : '-' }}

      .report-columns
        section.report-section
          h2 Top categories
          ol.summary-list
            li(v-for="category in topCategories" :key="category.label")
              span {{ category.label }}
              strong {{ formatDuration(category.seconds) }}

        section.report-section
          h2 Most-used apps
          ol.summary-list
            li(v-for="app in mostUsedApps" :key="app.label")
              span {{ app.label }}
              strong {{ formatDuration(app.seconds) }}
</template>

<script lang="ts">
import moment from 'moment';
import { chronioProductivityPercent } from '~/util/chronio';

type ReportRow = {
  timestamp: string;
  app: string;
  title: string;
  category: string;
  durationSeconds: number;
  productivityScore: number;
};

type DurationSummary = {
  label: string;
  seconds: number;
};

function formatDuration(seconds: number): string {
  if (!seconds || seconds < 1) return '0s';
  if (seconds < 60) return Math.round(seconds) + 's';
  const totalMinutes = Math.round(seconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours > 0) return hours + 'h ' + minutes + 'm';
  return minutes + 'm';
}

function summarize(rows: ReportRow[], labelFor: (row: ReportRow) => string): DurationSummary[] {
  const durations: Record<string, number> = {};
  rows.forEach((row: ReportRow) => {
    const label = labelFor(row) || 'Uncategorized';
    durations[label] = (durations[label] || 0) + row.durationSeconds;
  });
  return Object.keys(durations)
    .map((label: string) => ({ label, seconds: durations[label] }))
    .sort((a: DurationSummary, b: DurationSummary) => b.seconds - a.seconds)
    .slice(0, 6);
}

export default {
  name: 'ChronioReport',
  props: {
    rows: {
      type: Array,
      required: true,
    },
    startDate: {
      type: String,
      required: true,
    },
    endDate: {
      type: String,
      required: true,
    },
    label: {
      type: String,
      required: true,
    },
  },

  computed: {
    reportRows(): ReportRow[] {
      return this.rows as ReportRow[];
    },

    hasRows(): boolean {
      return this.reportRows.length > 0;
    },

    totalTrackedSeconds(): number {
      return this.reportRows.reduce(
        (seconds: number, row: ReportRow) => seconds + row.durationSeconds,
        0
      );
    },

    totalTrackedLabel(): string {
      return formatDuration(this.totalTrackedSeconds);
    },

    trackedDayCount(): number {
      return new Set(
        this.reportRows.map((row: ReportRow) => moment(row.timestamp).format('YYYY-MM-DD'))
      ).size;
    },

    productivityLabel(): string {
      const score = chronioProductivityPercent(this.reportRows);
      return score === null ? '-' : score + '%';
    },

    productivityTrend(): any[] {
      const start = moment(this.startDate);
      const end = moment(this.endDate);
      const days: any[] = [];
      const cursor = start.clone();
      while (cursor.isSameOrBefore(end, 'day')) {
        const date = cursor.format('YYYY-MM-DD');
        const rows = this.reportRows.filter(
          (row: ReportRow) => moment(row.timestamp).format('YYYY-MM-DD') === date
        );
        const seconds = rows.reduce(
          (total: number, row: ReportRow) => total + row.durationSeconds,
          0
        );
        days.push({
          date,
          label: cursor.format('ddd, MMM D'),
          score: chronioProductivityPercent(rows) || 0,
          seconds,
          trackedLabel: formatDuration(seconds),
        });
        cursor.add(1, 'day');
      }
      return days;
    },

    topCategories(): DurationSummary[] {
      return summarize(this.reportRows, (row: ReportRow) => row.category);
    },

    mostUsedApps(): DurationSummary[] {
      return summarize(this.reportRows, (row: ReportRow) => row.app);
    },
  },

  methods: {
    formatDuration(seconds: number): string {
      return formatDuration(seconds);
    },

    printReport() {
      window.print();
    },
  },
};
</script>

<style lang="scss" scoped>
.chronio-report {
  background: #11141c;
  color: #e9eefb;
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow: auto;
  padding: 18px;
}

.report-toolbar {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin: 0 auto 14px;
  max-width: 920px;
  width: 100%;
}

.report-command {
  background: rgba(20, 24, 33, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  color: #e9eefb;
  cursor: pointer;
  font-size: 12px;
  min-height: 32px;
  padding: 0 12px;
}

.report-command.primary {
  background: #4b8bff;
  border-color: #4b8bff;
  color: #07152f;
  font-weight: 600;
}

.report-page {
  background: #fff;
  border-radius: 6px;
  box-sizing: border-box;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.28);
  color: #172033;
  display: grid;
  gap: 22px;
  margin: 0 auto;
  max-width: 920px;
  padding: 42px;
  width: 100%;
}

.report-header p,
.report-header h1,
.report-header span,
.report-section h2 {
  letter-spacing: 0;
  margin: 0;
}

.report-header {
  border-bottom: 1px solid #d6ddea;
  display: grid;
  gap: 5px;
  padding-bottom: 18px;
}

.report-header p {
  color: #4b8bff;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

.report-header h1 {
  font-size: 28px;
}

.report-header span,
.report-metric span,
.trend-label span {
  color: #5c667a;
  font-size: 12px;
}

.report-empty {
  border: 1px dashed #bdc7da;
  border-radius: 6px;
  color: #5c667a;
  padding: 36px 18px;
  text-align: center;
}

.report-metrics {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.report-metric {
  border: 1px solid #d6ddea;
  border-radius: 6px;
  display: grid;
  gap: 5px;
  padding: 13px 14px;
}

.report-metric strong {
  font-size: 23px;
}

.report-section {
  display: grid;
  gap: 12px;
}

.report-section h2 {
  font-size: 15px;
}

.trend-list,
.summary-list {
  display: grid;
  gap: 8px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.trend-list li {
  align-items: center;
  display: grid;
  gap: 10px;
  grid-template-columns: 124px minmax(0, 1fr) 38px;
}

.trend-label {
  display: grid;
  gap: 1px;
}

.trend-label strong,
.summary-list span,
.trend-list em {
  font-size: 12px;
}

.trend-list em {
  color: #5c667a;
  font-style: normal;
  text-align: right;
}

.trend-meter {
  background: #e8edf7;
  border-radius: 4px;
  height: 9px;
  overflow: hidden;
}

.trend-meter i {
  background: #22c55e;
  display: block;
  height: 100%;
  min-width: 3px;
}

.report-columns {
  display: grid;
  gap: 28px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.summary-list li {
  align-items: baseline;
  border-bottom: 1px solid #e7ecf5;
  display: flex;
  gap: 10px;
  justify-content: space-between;
  min-height: 28px;
  padding-bottom: 7px;
}

.summary-list span {
  overflow-wrap: anywhere;
}

.summary-list strong {
  flex: 0 0 auto;
  font-size: 12px;
}

@media (max-width: 760px) {
  .report-page {
    padding: 24px;
  }

  .report-columns,
  .report-metrics {
    grid-template-columns: 1fr;
  }
}

@media print {
  .chronio-report {
    background: #fff;
    color: #172033;
    display: block;
    overflow: visible;
    padding: 0;
  }

  .report-toolbar {
    display: none;
  }

  .report-page {
    border-radius: 0;
    box-shadow: none;
    max-width: none;
    min-height: 100vh;
    padding: 0;
  }
}
</style>
