<template lang="pug">
.chronio-month
  header.month-header
    h1 {{ label }}
    p Click a day to open the detailed daily review.
  .month-weekdays
    span(v-for="weekday in weekdays" :key="weekday") {{ weekday }}
  .month-grid
    button.month-day(
      v-for="day in days"
      :key="day.key"
      :class="{'month-day--muted': !day.inMonth, 'month-day--today': day.isToday}"
      :disabled="!day.inMonth"
      @click="day.inMonth && $emit('select-day', day.date)"
    )
      span {{ day.day }}
      em(:title="day.productivityTitle") {{ day.trackedTime }}
      .month-bar(:title="day.productivityTitle")
        i(:style="{width: day.productiveWidth, background: day.barColor}")
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

.month-day span {
  font-size: 13px;
  font-weight: 600;
}

.month-day em {
  color: var(--muted);
  font-size: 11px;
  font-style: normal;
  min-height: 14px;
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
