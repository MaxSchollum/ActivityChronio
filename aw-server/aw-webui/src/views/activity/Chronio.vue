<template lang="pug">
div.chronio-view
  .chronio-topbar
    .chronio-brand
      .chronio-logo
      span Chronio
    .chronio-controls
      .chronio-chip.date
        span Dec 17, 2021
      .chronio-seg
        button.is-active Morning
        button Afternoon
        button Evening
        button Night
      .chronio-slider
        .track
        .thumb
      .chronio-metric
        span.label Tracked:
        span.value 6h 42m
      .chronio-search
        span.icon
        input(type="text" placeholder="Search…")

  .chronio-grid
    .chronio-col
      .chronio-section
        .chronio-section-title Stats
        .chronio-tabs
          button.is-active Days
          button Months
          button Year

      .chronio-card
        .chronio-card-title Most Used Apps
        ul.chronio-list
          li(v-for="app in mostUsed" :key="app.name")
            span.name {{ app.name }}
            span.time {{ app.time }}
            span.dot(:style="{ background: app.color }")

      .chronio-card
        .chronio-card-title Productivity Score
        .chronio-bars
          span.bar(v-for="n in 6" :key="n" :style="{ height: (n * 10 + 20) + '%' }")

    .chronio-col
      .chronio-section
        .chronio-section-title Activity Timeline
      .chronio-timeline
        .chronio-time(v-for="t in times" :key="t") {{ t }}
        .chronio-block(v-for="block in timeline" :key="block.label" :style="{ background: block.color }")
          .title {{ block.label }}
          .time {{ block.range }}
          .tag {{ block.tag }}

    .chronio-col
      .chronio-section
        .chronio-section-title Activity Details
      .chronio-card.detail
        .detail-header
          .app
            .app-icon
            .app-meta
              .name Google Chrome
              .status Currently Active
          .status-dot
        .detail-time 00:24:14
        .detail-sub Started at 14:10
        .detail-pill Productive

      .chronio-section.inline
        .chronio-section-title Recent Sessions
        a.view-all View all
      .chronio-card
        table.chronio-table
          thead
            tr
              th App
              th Time
              th Dur.
          tbody
            tr(v-for="row in recent" :key="row.app")
              td
                span.dot(:style="{ background: row.color }")
                | {{ row.app }}
              td {{ row.time }}
              td {{ row.dur }}
</template>

<script lang="ts">
export default {
  name: 'ChronioView',
  data() {
    return {
      mostUsed: [
        { name: 'Google Chrome', time: '2h 14m', color: '#4b8bff' },
        { name: 'VS Code', time: '1h 55m', color: '#9a5bff' },
        { name: 'Slack', time: '1h 12m', color: '#ff7a2f' },
        { name: 'Figma', time: '45m', color: '#ff4f9a' },
        { name: 'Spotify', time: '30m', color: '#26d07c' },
      ],
      times: ['8:00', '8:15', '8:30', '8:45', '9:00', '9:15', '9:30'],
      timeline: [
        {
          label: 'Chrome',
          range: '8:00 - 16:24',
          tag: 'Research & Development',
          color: 'linear-gradient(135deg, #3c7bff, #5aa1ff)',
        },
        {
          label: 'VS Code',
          range: '10:25 - 11:40',
          tag: 'Frontend Components',
          color: 'linear-gradient(135deg, #8a3bff, #c04cff)',
        },
        {
          label: 'Slack',
          range: '11:45 - 12:20',
          tag: 'Messages',
          color: 'linear-gradient(135deg, #ff6a1f, #ff9447)',
        },
        {
          label: 'Figma',
          range: '12:35 - 13:10',
          tag: 'Mockups',
          color: 'linear-gradient(135deg, #ff4f9a, #ff7bc2)',
        },
        {
          label: 'Spotify',
          range: '13:10 - 13:40',
          tag: 'Focus',
          color: 'linear-gradient(135deg, #1db954, #2fe07b)',
        },
      ],
      recent: [
        { app: 'Slack', time: '13:45 - 14:20', dur: '25m', color: '#ff7a2f' },
        { app: 'VS Code', time: '12:30 - 13:45', dur: '1h 15m', color: '#9a5bff' },
        { app: 'Chrome', time: '11:00 - 12:30', dur: '1h 30m', color: '#4b8bff' },
        { app: 'Figma', time: '10:15 - 11:00', dur: '45m', color: '#ff4f9a' },
        { app: 'Spotify', time: '09:45 - 10:15', dur: '30m', color: '#26d07c' },
      ],
    };
  },
};
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

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
  font-family: 'Space Grotesk', system-ui, -apple-system, sans-serif;
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

.chronio-chip {
  padding: 6px 12px;
  border-radius: 10px;
  background: var(--panel);
  border: 1px solid var(--border);
  font-size: 12px;
  color: var(--muted);
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
  left: 60%;
  width: 12px;
  height: 12px;
  background: #4b8bff;
  border-radius: 50%;
  box-shadow: 0 0 0 4px rgba(75, 139, 255, 0.2);
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

.chronio-grid {
  display: grid;
  grid-template-columns: 1fr 1.4fr 1fr;
  gap: 16px;
}

.chronio-col {
  display: grid;
  gap: 16px;
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
  grid-template-columns: repeat(6, 1fr);
  gap: 6px;
  align-items: end;
  height: 80px;
}

.chronio-bars .bar {
  background: linear-gradient(180deg, #4b8bff, rgba(75, 139, 255, 0.2));
  border-radius: 6px;
}

.chronio-timeline {
  display: grid;
  gap: 10px;
  position: relative;
}

.chronio-time {
  font-size: 11px;
  color: var(--muted);
}

.chronio-block {
  border-radius: 14px;
  padding: 12px 14px;
  display: grid;
  gap: 8px;
  color: #fff;
}

.chronio-block .title {
  font-weight: 600;
}

.chronio-block .time {
  font-size: 11px;
  opacity: 0.85;
  justify-self: end;
}

.chronio-block .tag {
  font-size: 11px;
  opacity: 0.8;
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
  background: rgba(255, 255, 255, 0.08);
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
  font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
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

.view-all {
  color: #7db0ff;
  font-size: 11px;
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
