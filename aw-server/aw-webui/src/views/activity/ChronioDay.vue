<template lang="pug">
.chronio-timeline-panel(:class="{'chronio-timeline-panel--mini': mini}")
  .timeline-scroll(ref="timelineScroll")
    .chronio-empty(v-if="!timeline.length && !activeEventCount") —
    .chronio-empty(v-else-if="!timeline.length") No events long enough to display
    .timeline-canvas(v-else :style="{height: timelineCanvas.totalHeight + 'px'}")
      .tl-hour(
        v-for="h in timelineCanvas.hours"
        :key="h.h"
        :style="{top: h.top + 'px'}"
      )
        span.tl-hour-label {{ h.label }}
        .tl-hour-line
      .tl-now-line(
        v-if="timelineCanvas.nowPx !== null"
        :style="{top: timelineCanvas.nowPx + 'px'}"
      )
      .tl-screenshot-marker(
        v-for="marker in timelineCanvas.screenshotMarkers"
        :key="marker.key"
        :style="{top: marker.top + 'px'}"
        :title="marker.label"
      )
      .tl-block(
        v-for="block in timelineCanvas.blocks"
        :key="'b-' + block.label + block.range"
        :style="{background: block.color, top: block.top + 'px', height: block.heightPx + 'px', opacity: block.opacity}"
        :title="blockTooltip(block)"
        @click="onBlockClick(block)"
      )
        .tl-block-inner(v-if="block.heightPx > 20 && !mini")
          .tl-title {{ block.label }}
          .tl-time-range(v-if="block.heightPx > 38") {{ block.range }}
</template>

<script lang="ts">
export default {
  name: 'ChronioDay',
  props: {
    activeEventCount: {
      type: Number,
      default: 0,
    },
    mini: {
      type: Boolean,
      default: false,
    },
    timeline: {
      type: Array,
      default: () => [],
    },
    timelineCanvas: {
      type: Object,
      required: true,
    },
  },
  methods: {
    blockTooltip(block: any): string {
      if (block.tooltip) return block.tooltip;
      return block.label + '\n' + block.range;
    },
    onBlockClick(block: any) {
      this.$emit('block-click', block);
    },
    scrollToNow() {
      const el = this.$refs.timelineScroll as HTMLElement | undefined;
      if (!el) return;
      const nowPx = this.timelineCanvas.nowPx;
      el.scrollTop = nowPx === null ? 0 : Math.max(0, nowPx - el.clientHeight / 3);
    },
    scrollToTimestamp(timestamp: number) {
      const el = this.$refs.timelineScroll as HTMLElement | undefined;
      if (!el) return;

      const blocks = this.timelineCanvas.blocks || [];
      const block = blocks.find((item: any) =>
        timestamp >= item.startMs && timestamp <= item.endMs
      );
      const hourHeight = this.timelineCanvas.hours?.length > 1
        ? this.timelineCanvas.hours[1].top - this.timelineCanvas.hours[0].top
        : 56;
      const targetPx = block
        ? block.top
        : ((timestamp - this.timelineCanvas.canvasStartMs) / 3600000) * hourHeight;
      el.scrollTop = Math.max(0, targetPx - el.clientHeight / 3);
    },
  },
};
</script>

<style lang="scss" scoped>
.chronio-timeline-panel {
  background: rgba(15, 17, 23, 0.4);
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.chronio-timeline-panel--mini {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 6px;
  height: 100%;

  .timeline-scroll {
    padding: 6px 5px 12px 0;
  }

  .timeline-canvas {
    margin-left: 30px;
  }

  .tl-hour {
    left: -30px;
  }

  .tl-hour-label {
    font-size: 9px;
    padding-right: 5px;
    width: 25px;
  }

  .tl-now-line {
    left: -30px;

    &::after {
      left: 30px;
    }
  }

  .tl-block {
    border-radius: 4px;
    cursor: default;
  }
}

.timeline-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 8px 10px 24px 0;
}

.timeline-canvas {
  margin-left: 44px;
  margin-right: 4px;
  position: relative;
}

.chronio-empty {
  align-items: center;
  color: var(--muted);
  display: flex;
  height: 100%;
  justify-content: center;
  min-height: 96px;
}

.tl-hour {
  align-items: flex-start;
  display: flex;
  left: -44px;
  pointer-events: none;
  position: absolute;
  right: 0;
}

.tl-hour-label {
  color: var(--muted);
  flex-shrink: 0;
  font-size: 10px;
  line-height: 1;
  margin-top: -1px;
  padding-right: 8px;
  text-align: right;
  width: 36px;
}

.tl-hour-line {
  background: var(--border);
  flex: 1;
  height: 1px;
}

.tl-now-line {
  background: #ff4040;
  height: 2px;
  left: -44px;
  pointer-events: none;
  position: absolute;
  right: 0;
  z-index: 5;

  &::after {
    background: #ff4040;
    border-radius: 50%;
    content: '';
    height: 8px;
    left: 44px;
    position: absolute;
    top: -4px;
    width: 8px;
  }
}

.tl-screenshot-marker {
  background: #f8fafc;
  border: 1px solid #0f1117;
  border-radius: 50%;
  box-shadow: 0 0 0 2px rgba(248, 250, 252, 0.28);
  height: 7px;
  pointer-events: none;
  position: absolute;
  right: 4px;
  transform: translateY(-50%);
  width: 7px;
  z-index: 4;
}

.tl-block {
  border-radius: 6px;
  cursor: pointer;
  left: 2px;
  overflow: hidden;
  position: absolute;
  right: 2px;
  transition: filter 0.15s;
  z-index: 2;

  &:hover {
    filter: brightness(1.15);
    z-index: 3;
  }
}

.tl-block-inner {
  color: rgba(255, 255, 255, 0.95);
  font-size: 10px;
  line-height: 1.25;
  overflow: hidden;
  padding: 4px 6px;
}

.tl-title {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tl-time-range {
  font-size: 9px;
  opacity: 0.85;
  white-space: nowrap;
}
</style>
