<template lang="pug">
.chronio-month
  header.month-header
    .month-header-copy
      h1 {{ label }}
      p Click a day to open the detailed daily review.
    .month-legend(aria-label="Productivity bar legend")
      span
        i.month-legend-dot.month-legend-dot--productive
        | Productive
      span
        i.month-legend-dot.month-legend-dot--distracting
        | Distracting
  .month-weekdays
    span(v-for="weekday in weekdays" :key="weekday") {{ weekday }}
  .month-grid
    button.month-day(
      v-for="day in days"
      :key="day.key"
      :class="{'month-day--muted': !day.inMonth, 'month-day--today': day.isToday, 'month-day--empty': !day.trackedTime}"
      :disabled="!day.inMonth"
      @click="day.inMonth && $emit('select-day', day.date)"
    )
      span {{ day.day }}
      em(:class="{'month-day-time--empty': !day.trackedTime}" :title="day.productivityTitle")
        | {{ day.trackedTime || (day.inMonth ? 'No activity' : '') }}
      .month-bar(:title="day.productivityTitle")
        i(v-if="day.trackedTime" :style="{width: day.productiveWidth, background: day.barColor}")
</template>

<script lang="ts">
export default {
  name: 'ChronioMonth',
  props: {
    days: {
      type: Array,
      required: true,
    },
    label: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      weekdays: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    };
  },
};
</script>

<style lang="scss" scoped>
.chronio-month {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  padding: 18px;
}

.month-header {
  align-items: flex-start;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: space-between;
}

.month-header h1 {
  font-size: 18px;
  letter-spacing: 0;
  margin: 0 0 4px;
}

.month-header p {
  color: var(--muted);
  font-size: 12px;
  margin: 0;
}

.month-legend {
  align-items: center;
  color: var(--muted);
  display: flex;
  flex: 0 0 auto;
  font-size: 11px;
  gap: 12px;
  padding-top: 4px;
}

.month-legend span {
  align-items: center;
  display: inline-flex;
  gap: 5px;
  white-space: nowrap;
}

.month-legend-dot {
  border-radius: 999px;
  display: inline-block;
  height: 8px;
  width: 8px;
}

.month-legend-dot--productive {
  background: #22c55e;
}

.month-legend-dot--distracting {
  background: #ef4444;
}

.month-grid,
.month-weekdays {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(7, minmax(0, 1fr));
}

.month-weekdays {
  color: var(--muted);
  flex: 0 0 auto;
  font-size: 11px;
  padding: 0 2px;
  text-transform: uppercase;
}

.month-grid {
  flex: 1;
  grid-auto-rows: minmax(88px, 1fr);
  min-height: 0;
}

.month-day {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  cursor: pointer;
  display: grid;
  gap: 8px;
  grid-template-rows: auto auto 1fr;
  min-width: 0;
  padding: 10px;
  text-align: left;
}

.month-day:hover:not(:disabled) {
  border-color: var(--border-hover);
}

.month-day:disabled {
  cursor: default;
}

.month-day--muted {
  background: transparent;
  border-style: dashed;
  opacity: 0.32;
}

.month-day--today {
  border-color: rgba(75, 139, 255, 0.7);
}

.month-day--empty:not(.month-day--muted) .month-bar {
  background: rgba(255, 255, 255, 0.04);
  border: 1px dashed rgba(255, 255, 255, 0.08);
}

.month-day span {
  font-size: 13px;
  font-weight: 600;
}

.month-day em {
  color: var(--muted);
  font-size: 13px;
  font-weight: 600;
  font-style: normal;
  min-height: 18px;
}

.month-day .month-day-time--empty {
  font-size: 11px;
  font-weight: 400;
}

.month-bar {
  align-self: end;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  height: 8px;
  overflow: hidden;
}

.month-bar i {
  border-radius: inherit;
  display: block;
  height: 100%;
  min-width: 2px;
}
</style>
