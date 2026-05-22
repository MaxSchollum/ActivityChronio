<template lang="pug">
.chronio-week
  header.week-header
    div
      h1 {{ label }}
      p Seven day review with category totals aggregated in the sidebar.
    .week-score(:title="productivityTitle")
      span Productivity
      strong {{ productivityLabel }}
  .week-columns
    article.week-day(v-for="day in days" :key="day.date")
      button.week-day-header(@click="$emit('select-day', day.date)")
        strong {{ day.weekday }}
        span {{ day.dayLabel }}
        em {{ day.trackedTime }}
      ChronioDay(
        :timeline="day.timeline"
        :timeline-canvas="day.timelineCanvas"
        :active-event-count="day.activeEventCount"
        mini
      )
</template>

<script lang="ts">
import ChronioDay from './ChronioDay.vue';

export default {
  name: 'ChronioWeek',
  components: { ChronioDay },
  props: {
    days: {
      type: Array,
      required: true,
    },
    label: {
      type: String,
      required: true,
    },
    productivityLabel: {
      type: String,
      required: true,
    },
  },
  computed: {
    productivityTitle(): string {
      return 'Productive category score as a percentage of tracked time';
    },
  },
};
</script>

<style lang="scss" scoped>
.chronio-week {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  padding: 18px;
}

.week-header {
  align-items: flex-end;
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.week-header h1 {
  font-size: 18px;
  letter-spacing: 0;
  margin: 0 0 4px;
}

.week-header p {
  color: var(--muted);
  font-size: 12px;
  margin: 0;
}

.week-score {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  display: grid;
  flex: 0 0 auto;
  gap: 2px;
  min-width: 134px;
  padding: 9px 12px;
  text-align: right;
}

.week-score span,
.week-day-header em {
  color: var(--muted);
  font-size: 11px;
  font-style: normal;
}

.week-score strong {
  font-size: 15px;
}

.week-columns {
  display: grid;
  flex: 1;
  gap: 8px;
  grid-template-columns: repeat(7, minmax(108px, 1fr));
  min-height: 0;
  overflow-x: auto;
}

.week-day {
  display: grid;
  gap: 8px;
  grid-template-rows: auto minmax(320px, 1fr);
  min-width: 108px;
  min-height: 0;
}

.week-day-header {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  cursor: pointer;
  display: grid;
  gap: 2px;
  min-height: 58px;
  padding: 8px;
  text-align: left;
}

.week-day-header:hover {
  border-color: var(--border-hover);
}

.week-day-header strong,
.week-day-header span {
  font-size: 12px;
  white-space: nowrap;
}

.week-day-header span {
  color: var(--muted);
}
</style>
