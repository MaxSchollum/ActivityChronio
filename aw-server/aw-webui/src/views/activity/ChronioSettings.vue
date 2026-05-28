<template lang="pug">
div.chronio-settings-view
  header.settings-topbar
    button.settings-brand(@click="$router.push('/chronio')")
      span.settings-logo
      span Chronio
    .settings-topbar-actions
      span.settings-save-state(v-if="saveState") {{ saveState }}
      button.settings-back(@click="$router.push('/chronio')") Back to activities

  .settings-shell
    nav.settings-nav
      button(:class="{active: activeSection === 'tracking'}" @click="scrollTo('tracking')") Tracking
      button(:class="{active: activeSection === 'categories'}" @click="scrollTo('categories')") Categories
      button(:class="{active: activeSection === 'rules'}" @click="scrollTo('rules')") Rules
      button(:class="{active: activeSection === 'appearance'}" @click="scrollTo('appearance')") Appearance
      button(:class="{active: activeSection === 'screenshots'}" @click="scrollTo('screenshots')") Screenshots
      button(:class="{active: activeSection === 'privacy'}" @click="scrollTo('privacy')") Privacy
      button(:class="{active: activeSection === 'data'}" @click="scrollTo('data')") Data

    main.settings-content
      section.settings-section(ref="tracking" id="tracking")
        .section-heading
          h1 Settings
          p Tracking behavior and Chronio-specific review controls.
        .settings-grid
          label.settings-field
            span AFK timeout
            .number-field
              input(
                type="number"
                min="1"
                :value="settingsStore.chronioAfkTimeoutMinutes"
                @change="updateNumber('chronioAfkTimeoutMinutes', $event)"
              )
              em min
          label.settings-field.settings-field-wide
            span Always-active pattern
            input(
              type="text"
              :value="settingsStore.always_active_pattern"
              placeholder="Regex for activity that should stay active"
              @change="updateText('always_active_pattern', $event)"
            )
          label.settings-field.settings-field-wide
            span Ignored apps
            textarea(
              v-model="ignoredAppsText"
              rows="4"
              placeholder="One app name per line"
              @blur="saveList('chronioIgnoredApps', ignoredAppsText)"
            )

      section.settings-section(ref="categories" id="categories")
        .section-heading
          h2 Categories
          p Import, export, or reset the category tree used by daily review.
        .button-row
          button.settings-action(@click="exportCategories") Export categories
          label.settings-action.file-action
            span Import categories
            input(type="file" accept="application/json,.json" @change="importCategories")
          button.settings-action.warning(@click="restoreCategories") Restore defaults
        p.settings-inline-status(v-if="categoryStatus") {{ categoryStatus }}

      section.settings-section(ref="rules" id="rules")
        .section-heading
          h2 Rules
          p Review and change the categorization rules saved by drag-and-drop or add one manually.
        ChronioRulesManager

      section.settings-section(ref="appearance" id="appearance")
        .section-heading
          h2 Appearance
          p Day boundaries and display controls used across Chronio review views.
        .settings-grid
          label.settings-field
            span Start of day
            input(type="time" :value="settingsStore.startOfDay" @change="updateText('startOfDay', $event)")
          label.settings-field
            span Start of week
            select(:value="settingsStore.startOfWeek" @change="updateText('startOfWeek', $event)")
              option Saturday
              option Sunday
              option Monday
          label.settings-field
            span Theme
            select(:value="settingsStore.theme" @change="updateTheme")
              option(value="auto") Auto
              option(value="light") Light
              option(value="dark") Dark

      section.settings-section(ref="screenshots" id="screenshots")
        .section-heading
          h2 Screenshots
          p Capture settings are stored now for the local screenshot watcher and apply on its next capture cycle.
        .settings-grid
          label.settings-toggle
            input(
              type="checkbox"
              :checked="settingsStore.chronioScreenshotsEnabled"
              @change="updateBoolean('chronioScreenshotsEnabled', $event)"
            )
            span Enable screenshots
          label.settings-field
            span Capture interval
            .number-field
              input(
                type="number"
                min="5"
                :value="settingsStore.chronioScreenshotIntervalSeconds"
                @change="updateNumber('chronioScreenshotIntervalSeconds', $event)"
              )
              em sec
          label.settings-field
            span JPEG quality
            .number-field
              input(
                type="number"
                min="1"
                max="100"
                :value="settingsStore.chronioScreenshotQuality"
                @change="updateNumber('chronioScreenshotQuality', $event)"
              )
              em %
          label.settings-field
            span Storage limit
            .number-field
              input(
                type="number"
                min="128"
                :value="settingsStore.chronioScreenshotStorageLimitMb"
                @change="updateNumber('chronioScreenshotStorageLimitMb', $event)"
              )
              em MB
          label.settings-field
            span Auto-cleanup age
            .number-field
              input(
                type="number"
                min="1"
                :value="settingsStore.chronioScreenshotRetentionDays"
                @change="updateNumber('chronioScreenshotRetentionDays', $event)"
              )
              em days

      section.settings-section(ref="privacy" id="privacy")
        .section-heading
          h2 Privacy
          p Matching recorded window activity is hidden from Chronio views after refresh. Screenshot capture must honor these exclusions before excluded frames can be shown or exported.
        .settings-grid
          label.settings-field.settings-field-wide
            span Excluded apps
            textarea(
              v-model="excludedAppsText"
              rows="4"
              placeholder="One app name per line"
              @blur="saveList('chronioExcludedApps', excludedAppsText)"
            )
          label.settings-field.settings-field-wide
            span Excluded title patterns
            textarea(
              v-model="excludedTitlePatternsText"
              rows="4"
              placeholder="One regex or title fragment per line"
              @blur="saveList('chronioExcludedTitlePatterns', excludedTitlePatternsText)"
            )

      section.settings-section(ref="data" id="data")
        .section-heading
          h2 Data
          p Chronio keeps activity data local. Export the open review period from Activities.
        .button-row
          button.settings-action(@click="$router.push('/chronio')") Open Activities export
</template>

<script lang="ts">
import { useCategoryStore } from '~/stores/categories';
import { useSettingsStore } from '~/stores/settings';
import { detectPreferredTheme } from '~/util/theme';
import ChronioRulesManager from './ChronioRulesManager.vue';

type ListSettingKey = 'chronioIgnoredApps' | 'chronioExcludedApps' | 'chronioExcludedTitlePatterns';

export default {
  name: 'ChronioSettings',

  components: {
    ChronioRulesManager,
  },

  data() {
    return {
      activeSection: 'tracking',
      categoryStatus: '',
      excludedAppsText: '',
      excludedTitlePatternsText: '',
      ignoredAppsText: '',
      saveState: '',
      settingsStore: useSettingsStore(),
      categoryStore: useCategoryStore(),
    };
  },

  async mounted() {
    await this.settingsStore.ensureLoaded();
    await this.categoryStore.load();
    this.syncListEditors();
  },

  methods: {
    syncListEditors() {
      this.ignoredAppsText = this.listText(this.settingsStore.chronioIgnoredApps);
      this.excludedAppsText = this.listText(this.settingsStore.chronioExcludedApps);
      this.excludedTitlePatternsText = this.listText(
        this.settingsStore.chronioExcludedTitlePatterns
      );
    },

    listText(items: string[]): string {
      return (items || []).join('\n');
    },

    parseList(value: string): string[] {
      return value
        .split('\n')
        .map((line: string) => line.trim())
        .filter(
          (line: string, index: number, lines: string[]) => line && lines.indexOf(line) === index
        );
    },

    async savePatch(patch: Record<string, any>) {
      await this.settingsStore.update(patch);
      this.saveState = 'Saved';
      window.setTimeout(() => {
        this.saveState = '';
      }, 1800);
    },

    async updateBoolean(key: string, event: Event) {
      const target = event.target as HTMLInputElement;
      await this.savePatch({ [key]: target.checked });
    },

    async updateNumber(key: string, event: Event) {
      const target = event.target as HTMLInputElement;
      const value = Number(target.value);
      if (Number.isFinite(value)) await this.savePatch({ [key]: value });
    },

    async updateText(key: string, event: Event) {
      const target = event.target as HTMLInputElement | HTMLSelectElement;
      await this.savePatch({ [key]: target.value });
    },

    async saveList(key: ListSettingKey, text: string) {
      await this.savePatch({ [key]: this.parseList(text) });
      this.syncListEditors();
    },

    async updateTheme(event: Event) {
      const target = event.target as HTMLSelectElement;
      const theme = target.value as 'light' | 'dark' | 'auto';
      await this.savePatch({ theme });
      const detectedTheme = theme === 'auto' ? detectPreferredTheme() : theme;
      const themeLink = document.createElement('link');
      themeLink.href = '/dark.css';
      themeLink.rel = 'stylesheet';
      document.querySelector(`link[href="${new URL(themeLink.href).pathname}"]`)?.remove();
      if (detectedTheme === 'dark') document.querySelector('head').appendChild(themeLink);
    },

    scrollTo(section: string) {
      this.activeSection = section;
      const target = this.$refs[section] as HTMLElement;
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    },

    exportCategories() {
      const text = JSON.stringify({ categories: this.categoryStore.classes }, null, 2);
      const element = document.createElement('a');
      element.href = 'data:application/json;charset=utf-8,' + encodeURIComponent(text);
      element.download = 'chronio-categories.json';
      element.style.display = 'none';
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
      this.categoryStatus = 'Category JSON exported.';
    },

    async importCategories(event: Event) {
      const target = event.target as HTMLInputElement;
      const file = target.files && target.files[0];
      if (!file) return;
      try {
        const imported = JSON.parse(await file.text());
        if (!Array.isArray(imported.categories)) {
          throw new Error('Category export is missing a categories array.');
        }
        this.categoryStore.import(imported.categories);
        await this.categoryStore.save();
        this.categoryStatus = 'Category JSON imported.';
      } catch (error) {
        this.categoryStatus = error instanceof Error ? error.message : 'Category import failed.';
      } finally {
        target.value = '';
      }
    },

    async restoreCategories() {
      if (!window.confirm('Restore the default Chronio categories?')) return;
      await this.categoryStore.restoreDefaultClasses();
      await this.categoryStore.save();
      this.categoryStatus = 'Default categories restored.';
    },
  },
};
</script>

<style lang="scss" scoped>
.chronio-settings-view {
  --bg: #0f1117;
  --panel: #171b24;
  --panel-2: #1c2230;
  --border: rgba(255, 255, 255, 0.1);
  --border-hover: rgba(255, 255, 255, 0.24);
  --text: #f2f5fb;
  --muted: #9aa6bc;
  background: var(--bg);
  color: var(--text);
  display: flex;
  flex-direction: column;
  height: 100vh;
  min-height: 0;
}

.settings-topbar {
  align-items: center;
  border-bottom: 1px solid var(--border);
  display: flex;
  flex: 0 0 auto;
  height: 58px;
  justify-content: space-between;
  padding: 0 20px;
}

.settings-brand,
.settings-back,
.settings-action,
.settings-nav button {
  border: 1px solid var(--border);
  color: var(--text);
  cursor: pointer;
}

.settings-brand {
  align-items: center;
  background: transparent;
  border: 0;
  display: inline-flex;
  font-size: 15px;
  font-weight: 700;
  gap: 10px;
  padding: 0;
}

.settings-logo {
  border: 2px solid #4b8bff;
  border-radius: 50%;
  box-shadow: 0 0 0 4px rgba(75, 139, 255, 0.15);
  height: 26px;
  width: 26px;
}

.settings-topbar-actions {
  align-items: center;
  display: flex;
  gap: 12px;
}

.settings-save-state,
.settings-inline-status {
  color: #7db0ff;
  font-size: 12px;
  margin: 0;
}

.settings-back,
.settings-action {
  background: var(--panel);
  border-radius: 6px;
  font-size: 13px;
  min-height: 34px;
  padding: 0 12px;
}

.settings-back:hover,
.settings-action:hover,
.settings-nav button:hover {
  border-color: var(--border-hover);
}

.settings-shell {
  display: grid;
  flex: 1 1 auto;
  grid-template-columns: 210px minmax(0, 1fr);
  min-height: 0;
}

.settings-nav {
  background: rgba(15, 17, 23, 0.6);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
  padding: 14px 10px;
}

.settings-nav button {
  background: transparent;
  border-color: transparent;
  border-radius: 6px;
  font-size: 13px;
  min-height: 34px;
  padding: 0 10px;
  text-align: left;
}

.settings-nav button.active {
  background: rgba(75, 139, 255, 0.12);
  color: #7db0ff;
}

.settings-content {
  overflow-y: auto;
  padding: 28px clamp(20px, 4vw, 52px) 48px;
}

.settings-section {
  border-bottom: 1px solid var(--border);
  max-width: 840px;
  padding: 0 0 30px;
  scroll-margin-top: 24px;
}

.settings-section + .settings-section {
  padding-top: 30px;
}

.section-heading {
  margin-bottom: 18px;
}

.section-heading h1,
.section-heading h2 {
  font-size: 22px;
  letter-spacing: 0;
  line-height: 1.2;
  margin: 0 0 6px;
}

.section-heading h2 {
  font-size: 17px;
}

.section-heading p {
  color: var(--muted);
  font-size: 13px;
  line-height: 1.45;
  margin: 0;
  max-width: 680px;
}

.settings-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.settings-field,
.settings-toggle {
  display: flex;
  font-size: 13px;
  gap: 8px;
}

.settings-field {
  flex-direction: column;
}

.settings-field-wide {
  grid-column: 1 / -1;
}

.settings-field span,
.settings-toggle span {
  font-weight: 600;
}

.settings-field input,
.settings-field select,
.settings-field textarea {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font: inherit;
  min-height: 36px;
  outline: none;
  padding: 8px 10px;
}

.settings-field textarea {
  line-height: 1.45;
  min-height: 92px;
  resize: vertical;
}

.settings-field input:focus,
.settings-field select:focus,
.settings-field textarea:focus {
  border-color: #4b8bff;
}

.number-field {
  align-items: center;
  display: grid;
  gap: 8px;
  grid-template-columns: minmax(0, 1fr) auto;
}

.number-field em {
  color: var(--muted);
  font-size: 12px;
  font-style: normal;
}

.settings-toggle {
  align-items: center;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  min-height: 52px;
  padding: 0 12px;
}

.settings-toggle input {
  accent-color: #4b8bff;
  height: 16px;
  margin: 0;
  width: 16px;
}

.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.settings-action.warning {
  color: #fbbf24;
}

.settings-action:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.file-action {
  align-items: center;
  display: inline-flex;
}

.file-action input {
  display: none;
}

@media (max-width: 760px) {
  .settings-shell {
    grid-template-columns: 1fr;
  }

  .settings-nav {
    border-bottom: 1px solid var(--border);
    border-right: 0;
    flex-direction: row;
    overflow-x: auto;
  }

  .settings-nav button {
    flex: 0 0 auto;
  }

  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>
