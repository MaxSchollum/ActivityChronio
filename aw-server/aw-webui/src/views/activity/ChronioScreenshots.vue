<template lang="pug">
.chronio-screenshots
  .screenshots-header
    span Screenshots
    span.screenshots-count(v-if="screenshots.length") {{ screenshots.length }}
  .screenshots-state(v-if="loading") Loading
  .screenshots-state(v-else-if="!screenshots.length") No screenshots
  .screenshots-filmstrip(v-else)
    button.screenshot-thumb(
      v-for="screenshot in screenshots"
      :key="screenshot.key"
      type="button"
      :title="screenshot.label"
      @click="activeScreenshot = screenshot"
    )
      img(:src="screenshot.imageUrl" :alt="screenshot.label")
      span {{ screenshot.time }}

  .screenshot-overlay(v-if="activeScreenshot" @click.self="activeScreenshot = null")
    .screenshot-lightbox(role="dialog" aria-modal="true")
      header
        strong {{ activeScreenshot.label }}
        button(type="button" title="Close" @click="activeScreenshot = null") x
      img(:src="activeScreenshot.imageUrl" :alt="activeScreenshot.label")
      footer
        button.danger(type="button" @click="$emit('delete-hour', activeScreenshot)")
          | Delete screenshots for this hour
</template>

<script lang="ts">
export default {
  name: 'ChronioScreenshots',
  props: {
    loading: {
      type: Boolean,
      default: false,
    },
    screenshots: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      activeScreenshot: null as any,
    };
  },
  watch: {
    screenshots(next: any[]) {
      if (
        this.activeScreenshot &&
        !next.some((screenshot: any) => screenshot.key === this.activeScreenshot.key)
      ) {
        this.activeScreenshot = null;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.chronio-screenshots {
  background: rgba(15, 17, 23, 0.92);
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  gap: 8px;
  height: 154px;
  min-height: 0;
  padding: 10px;
}

.screenshots-header {
  align-items: center;
  color: var(--muted);
  display: flex;
  font-size: 11px;
  justify-content: space-between;
  text-transform: uppercase;
}

.screenshots-count {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  color: var(--text);
  line-height: 1;
  padding: 3px 6px;
}

.screenshots-state {
  align-items: center;
  color: var(--muted);
  display: flex;
  flex: 1;
  font-size: 12px;
  justify-content: center;
}

.screenshots-filmstrip {
  display: flex;
  flex: 1;
  gap: 6px;
  min-height: 0;
  overflow-x: auto;
}

.screenshot-thumb {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--muted);
  cursor: pointer;
  display: flex;
  flex: 0 0 108px;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  overflow: hidden;
  padding: 4px;
  text-align: left;

  &:hover {
    border-color: var(--border-hover);
    color: var(--text);
  }

  img {
    background: #0b0d12;
    border-radius: 4px;
    display: block;
    flex: 1;
    min-height: 0;
    object-fit: cover;
    width: 100%;
  }

  span {
    font-size: 10px;
    line-height: 1;
  }
}

.screenshot-overlay {
  align-items: center;
  background: rgba(0, 0, 0, 0.74);
  display: flex;
  inset: 0;
  justify-content: center;
  padding: 28px;
  position: fixed;
  z-index: 60;
}

.screenshot-lightbox {
  background: var(--panel-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--glow);
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: min(88vh, 920px);
  max-width: min(90vw, 1280px);
  padding: 12px;

  header,
  footer {
    align-items: center;
    display: flex;
    gap: 12px;
    justify-content: space-between;
  }

  header {
    font-size: 13px;
  }

  header button,
  footer button {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text);
    cursor: pointer;
    padding: 6px 10px;
  }

  footer {
    justify-content: flex-end;
  }

  footer .danger {
    border-color: rgba(239, 68, 68, 0.45);
    color: #fda4af;
  }

  img {
    background: #080a0f;
    border-radius: 6px;
    display: block;
    max-height: calc(88vh - 120px);
    max-width: 100%;
    object-fit: contain;
  }
}
</style>
