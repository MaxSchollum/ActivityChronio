<template lang="pug">
div.chronio-view
  .chronio-topbar
    .chronio-brand
      .chronio-logo
      span Chronio
    .chronio-topbar-right
      .chronio-date-nav
        button.chronio-nav-btn(@click="prevDay") &larr;
        .chronio-chip.date(@click="showDatePicker = !showDatePicker")
          span {{ periodDisplay }}
          input.date-input(
            v-if="showDatePicker"
            type="date"
            :value="selectedDate"
            @input="onDateChange($event.target.value)"
            @keydown.enter.prevent="onDateChange($event.target.value)"
            @click.stop
            @blur="showDatePicker = false"
          )
        button.chronio-nav-btn(@click="nextDay" :disabled="isToday") &rarr;
        button.chronio-today-btn(v-if="!isToday" @click="goToToday") Today
      .chronio-period-toggle
        button(:class="{active: selectedPeriod === 'day'}" @click="setPeriod('day')") Day
        button(:class="{active: selectedPeriod === 'week'}" @click="setPeriod('week')") Week
        button(:class="{active: selectedPeriod === 'month'}" @click="setPeriod('month')") Month
      .chronio-metric
        span.label Tracked:
        span.value {{ totalTrackedTime }}
      .chronio-metric(v-if="productivityScore !== '—'")
        span.label Productivity:
        span.value.prod-score(:class="productivityScoreClass") {{ productivityScore }}%
      .chronio-metric.goal-metric(v-if="goalSummary.total > 0")
        span.label Goals:
        span.value {{ goalSummary.hit }}/{{ goalSummary.total }}
      .chronio-afk-badge(:class="afkStatus" :title="afkStatus === 'active' ? 'AFK idle detection active' : 'No AFK data — idle time not filtered'")
        | {{ afkStatus === 'active' ? 'AFK ✓' : 'AFK ⚠' }}
      .chronio-search(:class="{active: isSearchActive}")
        input(
          ref="searchInput"
          type="text"
          placeholder="Search activity..."
          v-model="searchQuery"
          @keydown.escape.prevent="clearAdvancedSearch"
        )
        button.search-clear(
          v-if="isSearchActive"
          type="button"
          title="Clear search"
          aria-label="Clear search"
          @click="clearAdvancedSearch"
        ) ×
      button.chronio-nav-btn(@click="$router.push('/chronio/settings')" title="Settings") Settings

  div.chronio-loading(v-if="loading")
    span Loading activity data&hellip;

  .chronio-body(v-else :class="'period-' + selectedPeriod")

    //- ─── LEFT SIDEBAR ───────────────────────────────────────────────
    .chronio-sidebar
      nav.sidebar-nav
        .sidebar-nav-item(:class="{ active: !showWeeklyReport }" @click="closeReport") Activities
        .sidebar-nav-item(@click="$router.push('/chronio/stats')") Stats
        .sidebar-nav-item(:class="{ active: showWeeklyReport }" @click="openWeeklyReport") Reports
        .sidebar-nav-item(@click="$router.push('/chronio/settings')") Settings

      .sidebar-export-actions
        button.sidebar-export-btn(
          :disabled="!exportRows.length"
          @click="exportPeriod('csv')"
        ) Export CSV
        button.sidebar-export-btn(
          :disabled="!exportRows.length"
          @click="exportPeriod('json')"
        ) Export JSON

      .sidebar-tree
        .sidebar-summary-row(
          @click="selectedCatFilter = null"
          :class="{active: selectedCatFilter === null}"
        )
          span.sr-name All Activities
          span.sr-time {{ totalTrackedTime }}
        .sidebar-summary-row(
          @click="selectedCatFilter = '__unassigned__'"
          :class="{active: selectedCatFilter === '__unassigned__'}"
        )
          span.sr-name Uncategorized
          span.sr-time {{ unassignedTime }}

        .sidebar-divider

        .sidebar-section-header
          span Categories
          button.sidebar-add-btn(@click.stop="createTopCategory") +

        template(v-for="row in sidebarFlatTree" :key="row.key")
          //- Inline-create row (#38)
          .sidebar-inline-create(
            v-if="row.isInlineCreate"
            :style="{paddingLeft: (row.depth * 14 + 10) + 'px'}"
          )
            span.sr-expand-spacer
            .sr-dot(:style="{background: '#4b8bff'}")
            input.sr-rename-input(
              ref="inlineCreateInput"
              :value="inlineCreateValue"
              placeholder="Name…"
              @input="inlineCreateValue = $event.target.value"
              @keydown.enter.prevent="commitInlineCreate"
              @keydown.escape.prevent="cancelInlineCreate"
              @blur="cancelInlineCreate"
              @click.stop
            )

          //- Normal category row
          .sidebar-cat-row(
            v-else
            draggable="true"
            :style="{paddingLeft: (row.depth * 14 + 10) + 'px'}"
            :class="{active: selectedCatFilter === row.key, 'drop-target': dragOverCatKey === row.key}"
            @click="onSidebarRowClick(row)"
            @dblclick.stop="startRename(row)"
            @contextmenu.prevent="onSidebarRowRightClick(row, $event)"
            @dragstart="onSidebarDragStart(row, $event)"
            @dragenter.prevent="onSidebarDragOver(row, $event)"
            @dragover.prevent="onSidebarDragOver(row, $event)"
            @dragleave="dragOverCatKey = null"
            @drop.prevent="onSidebarDrop(row, $event)"
          )
            .sr-main
              span.sr-expand-btn(v-if="row.hasChildren" @click.stop="toggleSidebarExpand(row)") {{ sidebarExpanded[row.key] ? '▾' : '▸' }}
              span.sr-expand-spacer(v-else)
              .sr-dot(
                :style="{background: row.color}"
                @click.stop="openColorPicker(row, $event)"
              )
              input.sr-rename-input(
                v-if="renamingKey === row.key"
                ref="renameInput"
                :value="renameValue"
                @input="renameValue = $event.target.value"
                @keydown.enter.prevent="commitRename(row)"
                @keydown.escape.prevent="cancelRename"
                @blur="cancelRename"
                @click.stop
              )
              span.sr-name(v-else) {{ row.label }}
              span.sr-score-dot(
                v-if="row.score !== 0"
                :class="row.score > 0 ? 'score-productive' : 'score-distracting'"
                :title="row.score > 0 ? 'Productive' : 'Distracting'"
              )
              span.sr-time {{ row.time }}
              span.sr-drag-handle(
                draggable="true"
                @dragstart.stop="onHandleDragStart(row, $event)"
                @click.stop
                title="Drag to reorder"
              ) ⠿
            .sr-goal(v-if="row.goal")
              .sr-goal-label
                span {{ row.goal.label }}
                span(:class="{hit: row.goal.hit}") {{ row.goal.hit ? 'Hit' : 'In progress' }}
              .sr-goal-track
                .sr-goal-fill(:class="{hit: row.goal.hit}" :style="{width: row.goal.percent + '%'}")

        //- Mini calendar (#52)
        .sidebar-calendar
          .cal-header
            button.cal-nav(@click="prevCalMonth") ‹
            span.cal-title {{ calendarMonthLabel }}
            button.cal-nav(@click="nextCalMonth") ›
          .cal-grid
            span.cal-dow(v-for="(d, i) in ['S','M','T','W','T','F','S']" :key="i") {{ d }}
            .cal-day(
              v-for="cell in calendarDays"
              :key="cell.key"
              :class="{ 'in-month': cell.inMonth, 'is-today': cell.isToday, 'is-selected': cell.isSelected, 'has-data': cell.hasData }"
              @click="cell.inMonth && onDateChange(cell.date)"
            )
              span(v-if="cell.inMonth") {{ cell.day }}
              .cal-dot(v-if="cell.hasData && cell.inMonth")

        //- Context menu
        .sidebar-ctx-menu(
          v-if="ctxMenu"
          :style="{top: ctxMenu.y + 'px', left: ctxMenu.x + 'px'}"
          @click.stop
        )
          .ctx-item(@click="startRename(ctxMenu.row)") Rename
          .ctx-item(@click="createChildCategory(ctxMenu.row)") Add subcategory
          .ctx-divider
          .ctx-score-row
            span Score:
            button.ctx-score-btn(
              :class="{active: ctxMenu.row.score > 0}"
              @click="setCategoryScore(ctxMenu.row, 10)"
            ) Productive
            button.ctx-score-btn.neutral(
              :class="{active: ctxMenu.row.score === 0}"
              @click="setCategoryScore(ctxMenu.row, 0)"
            ) Neutral
            button.ctx-score-btn.distracting(
              :class="{active: ctxMenu.row.score < 0}"
              @click="setCategoryScore(ctxMenu.row, -10)"
            ) Distracting
          .ctx-goal-row
            span Daily goal:
            .ctx-goal-input
              input(
                type="number"
                min="1"
                step="5"
                placeholder="None"
                :value="goalTargetValue(ctxMenu.row)"
                @change="setCategoryGoal(ctxMenu.row, $event)"
              )
              em min
          .ctx-divider
          .ctx-item.ctx-danger(@click="deleteCategory(ctxMenu.row)") Delete

        //- Color picker popover (#7)
        .color-picker-popover(
          v-if="colorPickerRow"
          :style="{top: colorPickerPos.y + 'px', left: colorPickerPos.x + 'px'}"
          @click.stop
        )
          .cp-swatches
            .cp-swatch(
              v-for="c in COLOR_SWATCHES"
              :key="c"
              :style="{background: c}"
              :class="{selected: colorPickerRow && colorPickerRow.color === c}"
              @click="applyColor(c)"
            )
          .cp-custom
            label Custom:
            input(type="color" :value="colorPickerRow ? colorPickerRow.color : '#ffffff'" @input="applyColor($event.target.value)")

    .chronio-center.search-center(v-if="isSearchActive")
      .center-header.search-header
        .center-title
          | Search results:&nbsp;
          strong {{ searchResultCountLabel }}
        button.search-close(type="button" @click="clearAdvancedSearch") Clear

      .search-controls
        label.search-control
          span From
          input(
            type="date"
            v-model="searchStartDate"
            :max="searchEndDate"
          )
        label.search-control
          span To
          input(
            type="date"
            v-model="searchEndDate"
            :min="searchStartDate"
          )
        label.search-control.search-control-category
          span Category
          select(v-model="searchCategory")
            option(value="") All categories
            option(
              v-for="option in searchCategoryOptions"
              :key="option.value"
              :value="option.value"
            ) {{ option.label }}
      .search-range-note Search covers up to 30 days.

      .search-state(v-if="searchLoading") Loading matching activity...
      .search-state.search-error(v-else-if="searchError") {{ searchError }}
      .search-state(v-else-if="!searchResults.length") No matching activity in this range.
      .search-results-scroll(v-else)
        button.search-result-row(
          v-for="result in searchResults"
          :key="result.key"
          type="button"
          @click="openAdvancedSearchResult(result)"
        )
          .search-result-when
            span.search-result-day {{ result.dayLabel }}
            span.search-result-time {{ result.timeLabel }}
          .search-result-main
            .search-result-app {{ result.app }}
            .search-result-title(:title="result.title") {{ result.title }}
          .search-result-category(:title="result.categoryLabel")
            span.search-result-dot(:style="{background: result.categoryColor}")
            span {{ result.categoryLabel }}

    ChronioReport(
      v-else-if="showWeeklyReport"
      :rows="exportRows"
      :start-date="periodStart"
      :end-date="periodEndDate"
      :label="periodDisplay"
      @close="closeReport"
    )

    ChronioWeek(
      v-else-if="selectedPeriod === 'week'"
      :days="weekDays"
      :label="periodDisplay"
      :score-label="scoreLabel(activeWindowEvents)"
      @select-day="selectDay"
    )

    ChronioMonth(
      v-else-if="selectedPeriod === 'month'"
      :days="monthDays"
      :label="periodDisplay"
      @select-day="selectDay"
    )

    //- ─── CENTER: ALL ACTIVITIES ─────────────────────────────────────
    .chronio-center(v-else @click.self="clearSelection")
      .center-header
        .center-title
          | {{ centerTitle }}:&nbsp;
          strong {{ centerTrackedTime }}
        .view-toggle
          button(:class="{active: viewMode === 'unified'}" @click="setViewMode('unified')") Unified
          button(:class="{active: viewMode === 'apps'}" @click="setViewMode('apps')") Apps
          button(:class="{active: viewMode === 'chrono'}" @click="setViewMode('chrono')") Chrono

      //- Empty state (#45)
      .act-day-empty(v-if="!loading && !activeWindowEvents.length")
        .act-empty-icon ○
        p(v-if="isFuture") No data yet for this day
        p(v-else) No activity recorded for {{ dateDisplay }}
        button.act-empty-prev(@click="goToPrevActiveDay") ← Previous day with data

      .activities-scroll(v-else ref="activitiesScroll" @click.self="clearSelection")
        //- UNIFIED VIEW
        template(v-if="viewMode === 'unified'")
          .act-empty(v-if="!filteredActivitiesTree.length") No activity data for this period
          template(v-else v-for="catNode in filteredActivitiesTree" :key="catNode.catKey")
            .act-row.act-row--cat(
              @click="toggleExpandCat(catNode.catKey)"
              :data-row-key="catActivityRowKey(catNode.catKey)"
              :class="{expanded: expandedCats[catNode.catKey], 'row-selected': selectedRowKeys[catActivityRowKey(catNode.catKey)]}"
            )
              span.act-expand {{ expandedCats[catNode.catKey] ? '▾' : '▸' }}
              .act-dot(:style="{background: catNode.color}")
              span.act-name {{ catNode.catLabel }}
              span.act-dur {{ formatDuration(catNode.duration) }}

            template(v-if="expandedCats[catNode.catKey]" v-for="appNode in catNode.apps" :key="catNode.catKey + '/' + appNode.app")
              .act-row.act-row--app(
                draggable="true"
                :data-row-key="appRowKey(catNode.catKey, appNode.app)"
                :class="{'row-selected': selectedRowKeys[appRowKey(catNode.catKey, appNode.app)]}"
                @click="onUnifiedAppRowClick(catNode.catKey, appNode, $event)"
                @dragstart="onDragStartApp(appNode, $event, appRowKey(catNode.catKey, appNode.app))"
                @dragend="onDragEnd"
              )
                .act-indent
                span.act-expand(v-if="appNode.titles && appNode.titles.length") {{ expandedApps[catNode.catKey + '/' + appNode.app] ? '▾' : '▸' }}
                span.act-expand-spacer(v-else)
                .act-app-icon(:style="{background: appNode.color}" :title="appNode.colorTitle")
                span.act-name {{ appNode.app }}
                span.act-drag-hint ↖
                span.act-dur {{ formatDuration(appNode.duration) }}

              template(v-if="expandedApps[catNode.catKey + '/' + appNode.app]" v-for="t in appNode.titles" :key="catNode.catKey + '/' + appNode.app + '/' + t.title")
                .act-row.act-row--title(
                  draggable="true"
                  :data-row-key="titleRowKey(catNode.catKey, appNode.app, t.title)"
                  :class="{'row-selected': selectedRowKeys[titleRowKey(catNode.catKey, appNode.app, t.title)]}"
                  @click="onContextRowClick(catNode.catKey, appNode.app, t, $event)"
                  @dragstart="onDragStartTitle(appNode.app, t, $event, titleRowKey(catNode.catKey, appNode.app, t.title))"
                  @dragend="onDragEnd"
                )
                  .act-indent2
                  span.act-expand(v-if="t.events && t.events.length" @click.stop="toggleExpandContext(catNode.catKey + '/' + appNode.app + '/' + t.title)") {{ expandedContexts[catNode.catKey + '/' + appNode.app + '/' + t.title] ? '▾' : '▸' }}
                  span.act-expand-spacer(v-else)
                  span.act-title(:title="t.title") {{ t.title }}
                  span.act-dur {{ formatDuration(t.duration) }}
                template(v-if="t.events && expandedContexts[catNode.catKey + '/' + appNode.app + '/' + t.title]" v-for="e in t.events" :key="e.timestamp + (e.data && e.data.title || '')")
                  .act-row.act-row--context-event(
                    draggable="true"
                    @click="onActivityRowClick('', {type:'title', app: appNode.app, title: displayEventTitle(e), rawTitle: e.data && e.data.title || ''}, $event)"
                    @dragstart="onDragStartEvent(e, $event)"
                    @dragend="onDragEnd"
                  )
                    .act-indent3
                    span.act-title(:title="displayEventTitle(e)") {{ displayEventTitle(e) }}
                    span.act-time {{ formatHHMM(e.timestamp) }}
                    span.act-dur {{ formatDuration(e.duration) }}

        //- APPS VIEW (#40) — flat app list sorted by time
        template(v-else-if="viewMode === 'apps'")
          .act-empty(v-if="!flatAppsList.length") No activity data for this period
          template(v-else v-for="appNode in flatAppsList" :key="'flat/' + appNode.app")
            .act-row.act-row--app(
              draggable="true"
              :data-row-key="'flat/' + appNode.app"
              :class="{'row-selected': selectedRowKeys['flat/' + appNode.app]}"
              @click="onAppsAppRowClick(appNode, $event)"
              @dragstart="onDragStartApp(appNode, $event, 'flat/' + appNode.app)"
              @dragend="onDragEnd"
            )
              span.act-expand(@click.stop="toggleExpandApp('flat/' + appNode.app)") {{ expandedApps['flat/' + appNode.app] ? '▾' : '▸' }}
              .act-app-icon(:style="{background: appNode.color}" :title="appNode.colorTitle")
              span.act-name {{ appNode.app }}
              span.act-drag-hint ↖
              span.act-dur {{ formatDuration(appNode.duration) }}
            template(v-if="expandedApps['flat/' + appNode.app]" v-for="t in appNode.titles" :key="'flat/' + appNode.app + '/' + t.title")
              .act-row.act-row--title(
                draggable="true"
                :data-row-key="'flat/' + appNode.app + '/' + t.title"
                :class="{'row-selected': selectedRowKeys['flat/' + appNode.app + '/' + t.title]}"
                @click="onActivityRowClick('flat/' + appNode.app + '/' + t.title, {type:'title', app: appNode.app, title: t.title, rawTitle: t.rawTitle || t.title}, $event)"
                @dragstart="onDragStartTitle(appNode.app, t, $event, 'flat/' + appNode.app + '/' + t.title)"
                @dragend="onDragEnd"
              )
                .act-indent2
                span.act-title(:title="t.title") {{ t.title }}
                span.act-dur {{ formatDuration(t.duration) }}

        //- CHRONOLOGICAL VIEW — grouped by merged timeline block, expandable
        template(v-else)
          .act-empty(v-if="!chronoGrouped.length") No activity data for this period
          template(v-else v-for="group in chronoGrouped" :key="group.key")
            .act-row.act-row--chrono-group(
              :data-startms="group.startMs"
              :data-row-key="chronoGroupRowKey(group.key)"
              :class="{'row-selected': selectedRowKeys[chronoGroupRowKey(group.key)]}"
              @click="toggleChronoBlock(group.key)"
            )
              span.act-caret {{ expandedTimelineBlocks[group.key] ? '▾' : '▸' }}
              .act-app-icon(:style="{background: group.color}" :title="group.colorTitle")
              span.act-app {{ group.label }}
              span.act-time-range {{ group.range }}
              span.act-dur {{ formatDuration((group.endMs - group.startMs) / 1000) }}

            template(v-if="expandedTimelineBlocks[group.key]" v-for="e in group.subEvents" :key="e.timestamp + e.data.title")
              .act-row.act-row--chrono-sub(
                draggable="true"
                :data-row-key="chronoEventRowKey(group.key, e)"
                :class="{'row-selected': selectedRowKeys[chronoEventRowKey(group.key, e)]}"
                @click="onChronoEventRowClick(group.key, e, $event)"
                @dragstart="onDragStartEvent(e, $event)"
                @dragend="onDragEnd"
              )
                .act-indent
                span.act-app-label {{ displayEventApp(e) }}:
                span.act-title(:title="displayEventTitle(e)") {{ displayEventTitle(e) }}
                span.act-time {{ formatHHMM(e.timestamp) }}
                span.act-dur {{ formatDuration(e.duration) }}

      .chronio-center-footer
        button.chronio-shortcuts-hint(type="button" title="Show keyboard shortcuts (?)" @click="openShortcutReference") ⌨ Shortcuts

    //- ─── RIGHT: TIMELINE ────────────────────────────────────────────
    ChronioDay(
      v-if="selectedPeriod === 'day'"
      ref="timeline"
      :timeline="timeline"
      :timeline-canvas="timelineCanvas"
      :active-event-count="activeWindowEvents.length"
      @block-click="onTimelineBlockClick"
    )

  //- ── TOAST NOTIFICATIONS (#78) ───────────────────────────────────────
  .chronio-toasts
    .chronio-toast(
      v-for="t in toasts"
      :key="t.id"
    )
      span.toast-msg {{ t.message }}
      button.toast-undo(v-if="t.undo" @click="undoToast(t)") Undo
      button.toast-close(@click="dismissToast(t)") ×

  //- ── ONBOARDING MODAL (#12) ──────────────────────────────────────────
  .onboarding-overlay(v-if="showOnboarding" @click.self="dismissOnboarding")
    .onboarding-modal
      .onboarding-step(v-if="onboardingStep === 0")
        .ob-emoji 🕐
        h2 Welcome to Chronio
        p Your personal activity tracker. See exactly what you worked on, when, and for how long.
      .onboarding-step(v-else-if="onboardingStep === 1")
        .ob-emoji 🗂️
        h2 Organize your work
        p Drag any app or tab from the center panel into a project folder on the left to categorize it. Chronio remembers the rule for every future day.
      .onboarding-step(v-else-if="onboardingStep === 2")
        .ob-emoji 📊
        h2 Your productivity score
        p Right-click any project folder to mark it Productive or Distracting. Your daily score updates automatically.
      .ob-dots
        span.ob-dot(v-for="i in 3" :key="i" :class="{active: onboardingStep === i - 1}" @click="onboardingStep = i - 1")
      .ob-actions
        button.ob-btn-ghost(v-if="onboardingStep > 0" @click="onboardingStep--") Back
        button.ob-btn-primary(v-if="onboardingStep < 2" @click="onboardingStep++") Next
        button.ob-btn-primary(v-else @click="dismissOnboarding") Get started

  .shortcut-overlay(v-if="showShortcutReference" @click.self="closeShortcutReference")
    .shortcut-modal(role="dialog" aria-modal="true" aria-labelledby="shortcut-title")
      .shortcut-header
        h2#shortcut-title Keyboard shortcuts
        button.shortcut-close(type="button" aria-label="Close keyboard shortcuts" @click="closeShortcutReference") ×
      .shortcut-list
        .shortcut-row(v-for="shortcut in shortcutReferenceRows" :key="shortcut.keys")
          kbd {{ shortcut.keys }}
          span {{ shortcut.action }}
</template>

<script lang="ts">
import moment from 'moment';
import Fuse from 'fuse.js';
import _ from 'lodash';
import Papa from 'papaparse';
import { useActivityStore } from '~/stores/activity';
import { useBucketsStore } from '~/stores/buckets';
import { useCategoryStore } from '~/stores/categories';
import { useSettingsStore } from '~/stores/settings';
import { get_today_with_offset } from '~/util/time';
import { getColorFromString } from '~/util/color';
import { getClient } from '~/util/awclient';
import { extractBrowserSubContext, supportsBrowserSubContext } from '~/util/browserSubContext';
import ChronioDay from './ChronioDay.vue';
import ChronioMonth from './ChronioMonth.vue';
import ChronioReport from './ChronioReport.vue';
import ChronioWeek from './ChronioWeek.vue';

// System processes that are never real user activity
const SYSTEM_PROCESS_BLOCKLIST = new Set([
  'loginwindow', 'ScreenSaverEngine',
  'SecurityAgent', 'UserNotificationCenter', 'Notification Center',
  'coreauthd', 'universalAccessAuthWarn', 'TokenEater',
  'WidgetKit Simulator', 'Developer',
]);

// Color swatches for the color picker (#7)
const COLOR_SWATCHES = [
  '#4b8bff', '#8a3bff', '#ff6a1f', '#ff4f9a', '#1db954',
  '#0ea5e9', '#f59e0b', '#e6683c', '#a855f7', '#ec4899',
  '#14b8a6', '#ef4444', '#84cc16', '#f97316', '#64748b',
];

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

const HOUR_PX = 56; // pixels per hour on the timeline canvas
const MAX_MERGE_GAP_MS = 15 * 60 * 1000; // don't merge same-app blocks separated by >15 min
const ADVANCED_SEARCH_DAYS = 30;
const ADVANCED_SEARCH_LIMIT = 300;

// Browser names to strip from window titles
const BROWSER_SUFFIXES = [
  'Google Chrome', 'Chrome', 'Safari', 'Firefox', 'Arc',
  'Brave Browser', 'Microsoft Edge', 'Opera',
];

const BROWSER_APP_NAMES = new Set(BROWSER_SUFFIXES);

const KNOWN_BROWSER_SITES: { label: string; patterns: RegExp[] }[] = [
  {
    label: 'X / Twitter',
    patterns: [/(^|\W)x\.com($|\W)/i, /twitter/i, /^X$/i, /(?:^|\s[/-]\s)X$/i],
  },
  { label: 'ChatGPT', patterns: [/chatgpt/i, /chat\.openai\.com/i] },
  { label: 'Instagram', patterns: [/instagram/i] },
  { label: 'GitHub', patterns: [/github/i] },
  { label: 'YouTube', patterns: [/youtube/i] },
  { label: 'Gmail', patterns: [/gmail/i] },
  { label: 'Google Docs', patterns: [/google docs/i, /docs\.google/i] },
  { label: 'Google Calendar', patterns: [/google calendar/i, /calendar\.google/i] },
  { label: 'Reddit', patterns: [/reddit/i] },
  { label: 'Slack', patterns: [/slack/i] },
  { label: 'Notion', patterns: [/notion/i] },
  { label: 'Linear', patterns: [/linear/i] },
  { label: 'Codex', patterns: [/\bcodex\b/i] },
];

const SHORTCUT_REFERENCE_ROWS = [
  { keys: '← / →', action: 'Previous / next day' },
  { keys: 'T', action: 'Jump to today' },
  { keys: 'U', action: 'Unified view' },
  { keys: 'A', action: 'Apps view' },
  { keys: 'C', action: 'Chronological view' },
  { keys: '↑ / ↓', action: 'Move through activity rows' },
  { keys: 'Space', action: 'Expand or collapse selected row' },
  { keys: '1–9', action: 'Assign selection to sidebar category' },
  { keys: '/ / ⌘F', action: 'Focus search' },
  { keys: 'Escape', action: 'Clear filters and selection' },
  { keys: '?', action: 'Show this reference' },
];

function formatDuration(seconds: number): string {
  if (!seconds || seconds < 1) return '0s';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function formatHHMM(ts: any): string {
  return moment(ts).format('HH:mm');
}

function formatHourLabel(hour: number): string {
  const normalized = ((hour % 24) + 24) % 24;
  if (normalized === 0) return '12am';
  if (normalized < 12) return `${normalized}am`;
  if (normalized === 12) return '12pm';
  return `${normalized - 12}pm`;
}

function gradientForApp(app: string, index: number): string {
  return GRADIENTS[index % GRADIENTS.length];
}

export default {
  name: 'ChronioView',
  components: {
    ChronioDay,
    ChronioMonth,
    ChronioReport,
    ChronioWeek,
  },

  data() {
    return {
      selectedDate: '' as string,
      selectedPeriod: 'day' as 'day' | 'week' | 'month',
      searchQuery: '' as string,
      searchStartDate: '' as string,
      searchEndDate: '' as string,
      searchCategory: '' as string,
      searchSourceRows: [] as any[],
      searchLoading: false as boolean,
      searchError: '' as string,
      searchLoadedRangeKey: '' as string,
      searchDebounceTimer: null as any,
      searchRequestId: 0 as number,
      showWeeklyReport: false as boolean,
      showDatePicker: false as boolean,
      loading: true as boolean,
      selectedEvent: null as any,
      windowEvents: [] as any[],
      afkEvents: [] as any[],
      // expand/filter state
      expandedCats: {} as Record<string, boolean>,
      expandedApps: {} as Record<string, boolean>,
      expandedContexts: {} as Record<string, boolean>,
      expandedTimelineBlocks: {} as Record<string, boolean>,
      sidebarExpanded: {} as Record<string, boolean>,
      selectedCatFilter: null as string | null,
      viewMode: 'unified' as 'unified' | 'apps' | 'chrono',
      // inline rename state (#6 / #30)
      renamingKey: null as string | null,
      renameValue: '' as string,
      // inline create state (#38)
      inlineCreateParent: null as string | null,
      inlineCreateValue: '' as string,
      // context menu state
      ctxMenu: null as { row: any; x: number; y: number } | null,
      // color picker state (#7)
      colorPickerRow: null as any,
      colorPickerPos: { x: 0, y: 0 },
      COLOR_SWATCHES: COLOR_SWATCHES,
      // drag-drop state (#3)
      dragOverCatKey: null as string | null,
      isDraggingActivity: false as boolean,
      // multi-select state (#37)
      selectedRowKeys: {} as Record<string, boolean>,
      selectedRowPayloads: {} as Record<string, any>,
      lastClickedKey: null as string | null,
      showShortcutReference: false as boolean,
      shortcutReferenceRows: SHORTCUT_REFERENCE_ROWS,
      // drag-category state (#32)
      draggingSidebarKey: null as string | null,
      // sidebar reorder state (#46)
      reorderDragKey: null as string | null,
      reorderDropKey: null as string | null,
      // onboarding state (#12)
      showOnboarding: false as boolean,
      onboardingStep: 0 as number,
      // live refresh (#9)
      refreshTimer: null as any,
      // #35: guard to skip silent refresh if a full refresh is already in flight
      isRefreshing: false as boolean,
      // #78: toast notifications for drag-to-categorize
      toasts: [] as { id: number; message: string; undo: (() => void) | null; timer: any }[],
      nextToastId: 0 as number,
      // Mini calendar (#52)
      calendarYear: 0 as number,
      calendarMonth: 0 as number,   // 0-based (moment month)
      calendarDots: {} as Record<string, boolean>,
      // keyboard handler ref (#44)
      keyHandler: null as any,
      pendingTimelineScrollMs: null as number | null,
    };
  },

  computed: {
    activityStore() { return useActivityStore(); },
    bucketsStore() { return useBucketsStore(); },
    settingsStore() { return useSettingsStore(); },
    categoryStore() { return useCategoryStore(); },

    isToday(): boolean {
      const today = moment();
      if (this.selectedPeriod === 'week') {
        return moment(this.periodStart).isSame(this.periodStartFor(today, 'week'), 'day');
      }
      if (this.selectedPeriod === 'month') return moment(this.selectedDate).isSame(today, 'month');
      return moment(this.selectedDate).isSame(today, 'day');
    },

    isFuture(): boolean {
      return moment(this.selectedDate).isAfter(moment(), 'day');
    },

    host(): string {
      const hosts = this.bucketsStore.hosts;
      for (const h of hosts) {
        if (
          this.bucketsStore.bucketsWindow(h).length > 0 &&
          this.bucketsStore.bucketsAFK(h).length > 0
        ) return h;
      }
      return hosts.length > 0 ? hosts[0] : '';
    },

    dateDisplay(): string {
      if (!this.selectedDate) return '—';
      return moment(this.selectedDate).format('MMM D, YYYY');
    },

    periodStart(): string {
      return this.periodStartFor(moment(this.selectedDate), this.selectedPeriod).format('YYYY-MM-DD');
    },

    periodDisplay(): string {
      if (!this.selectedDate) return '—';
      if (this.selectedPeriod === 'week') {
        const start = moment(this.periodStart);
        return start.format('MMM D') + ' - ' + start.clone().add(6, 'days').format('MMM D, YYYY');
      }
      if (this.selectedPeriod === 'month') return moment(this.selectedDate).format('MMMM YYYY');
      return this.dateDisplay;
    },

    periodEndDate(): string {
      if (!this.periodStart) return '';
      return moment(this.periodStart)
        .add(1, this.selectedPeriod)
        .subtract(1, 'day')
        .format('YYYY-MM-DD');
    },

    exportRows(): any[] {
      return [...(this.activeWindowEvents as any[])]
        .sort((a: any, b: any) => moment(a.timestamp).valueOf() - moment(b.timestamp).valueOf())
        .map((event: any) => {
          const category = this.classifyEventCategory(event);
          const identity = this.eventIdentity(event);
          return {
            timestamp: moment(event.timestamp).toISOString(),
            app: identity.app,
            title: identity.title,
            category: category.join(' > '),
            durationSeconds: event.duration || 0,
            productivityScore:
              (this.categoryStore as any).get_category_score(category) || 0,
          };
        });
    },

    // AFK intervals for the day
    notAfkIntervals(): { start: number; end: number }[] {
      return this.notAfkIntervalsFor(this.afkEvents);
    },

    // Full-day AFK-filtered window events (no segment restriction)
    activeWindowEvents(): any[] {
      return this.activeEventsFor(this.windowEvents, this.afkEvents);
    },

    afkStatus(): 'active' | 'no-data' {
      if (this.loading) return 'no-data';
      return this.notAfkIntervals.length > 0 ? 'active' : 'no-data';
    },

    calendarMonthLabel(): string {
      return moment().year(this.calendarYear).month(this.calendarMonth).format('MMM YYYY');
    },

    calendarDays(): any[] {
      if (!this.calendarYear) return [];
      const firstDay = moment().year(this.calendarYear).month(this.calendarMonth).date(1);
      const daysInMonth = firstDay.daysInMonth();
      const startDow = firstDay.day(); // 0=Sun
      const today = moment().format('YYYY-MM-DD');
      const cells: any[] = [];
      // Pad before start
      for (let i = 0; i < startDow; i++) {
        cells.push({ key: 'pad-' + i, inMonth: false, date: '', day: 0, hasData: false, isToday: false, isSelected: false });
      }
      for (let d = 1; d <= daysInMonth; d++) {
        const date = moment().year(this.calendarYear).month(this.calendarMonth).date(d).format('YYYY-MM-DD');
        cells.push({
          key: date,
          inMonth: true,
          date,
          day: d,
          hasData: !!this.calendarDots[date],
          isToday: date === today,
          isSelected: date === this.selectedDate,
        });
      }
      return cells;
    },

    totalTrackedTime(): string {
      const total = (this.activeWindowEvents as any[]).reduce(
        (sum: number, e: any) => sum + (e.duration || 0), 0
      );
      return formatDuration(total);
    },

    scopedActiveWindowEvents(): any[] {
      let events: any[] = this.activeWindowEvents;
      if (this.selectedCatFilter === '__unassigned__') {
        events = events.filter((e: any) => this.classifyEventCategory(e)[0] === 'Uncategorized');
      } else if (this.selectedCatFilter) {
        const selected = this.selectedCatFilter;
        events = events.filter((e: any) => {
          const key = this.classifyEventCategory(e).join('>');
          return key === selected || key.startsWith(selected + '>');
        });
      }
      return events;
    },

    isSearchActive(): boolean {
      return !!this.searchQuery.trim();
    },

    searchCategoryOptions(): { label: string; value: string }[] {
      const options = (this.categoryStore as any).all_categories
        .map((category: string[]) => ({
          label: category.join(' > '),
          value: category.join('>'),
        }))
        .filter((option: any) => option.value !== 'Uncategorized');
      return [{ label: 'Uncategorized', value: '__unassigned__' }].concat(options);
    },

    searchResults(): any[] {
      if (!this.isSearchActive) return [];
      let rows = this.searchSourceRows as any[];
      if (this.searchCategory === '__unassigned__') {
        rows = rows.filter((row: any) => row.category[0] === 'Uncategorized');
      } else if (this.searchCategory) {
        const category = this.searchCategory;
        rows = rows.filter((row: any) =>
          row.categoryKey === category || row.categoryKey.startsWith(category + '>')
        );
      }
      const fuse = new Fuse(rows, {
        ignoreLocation: true,
        keys: ['app', 'title', 'matchText', 'categoryLabel'],
        threshold: 0.34,
      });
      return fuse.search(this.searchQuery.trim(), { limit: ADVANCED_SEARCH_LIMIT })
        .map((result: any) => result.item);
    },

    searchResultCountLabel(): string {
      if (this.searchLoading) return 'Searching';
      const count = this.searchResults.length;
      return count === 1 ? '1 match' : `${count} matches`;
    },

    centerTitle(): string {
      if (this.selectedCatFilter === '__unassigned__') return 'Uncategorized';
      return this.selectedCatFilter ? this.selectedCatFilter.split('>').pop() || 'All Activities' : 'All Activities';
    },

    centerTrackedTime(): string {
      const total = (this.scopedActiveWindowEvents as any[]).reduce(
        (sum: number, e: any) => sum + (e.duration || 0), 0
      );
      return formatDuration(total);
    },

    /* #4: weighted productivity score — sum(dur * score) / (total_dur * 10) * 100 */
    productivityScore(): number | '—' {
      const total = (this.activeWindowEvents as any[]).reduce(
        (s: number, e: any) => s + (e.duration || 0), 0
      );
      if (total === 0) return '—';
      const catStore = this.categoryStore as any;
      let weighted = 0;
      for (const cat of this.activitiesTree as any[]) {
        const score: number = catStore.get_category_score(cat.category) || 0;
        weighted += cat.duration * score;
      }
      return Math.round(Math.max(0, Math.min(100, (weighted / (total * 10)) * 100)));
    },

    productivityScoreClass(): string {
      const s = this.productivityScore;
      if (s === '—') return '';
      if ((s as number) >= 70) return 'prod-green';
      if ((s as number) >= 40) return 'prod-yellow';
      return 'prod-red';
    },

    goalSummary(): { hit: number; total: number } {
      if (this.selectedPeriod !== 'day') return { hit: 0, total: 0 };
      const durations: Record<string, number> = this.categoryDurations;
      const goals = ((this.categoryStore as any).classes as any[])
        .map((category: any) => ({
          key: category.name.join('>'),
          targetSeconds: Number(category.data?.dailyTargetMinutes || 0) * 60,
        }))
        .filter((goal: any) => goal.targetSeconds > 0);
      return {
        hit: goals.filter((goal: any) => (durations[goal.key] || 0) >= goal.targetSeconds).length,
        total: goals.length,
      };
    },

    // ─── ACTIVITIES TREE ─────────────────────────────────────────────
    // Builds category → app → title hierarchy from AFK-filtered events
    activitiesTree(): any[] {
      const events: any[] = this.activeWindowEvents;
      const categories: any[] = (this.categoryStore as any).classes;

      // Pre-compile regexes once; strip Python-style inline flags like (?m) which are invalid in JS
      const regexes: [any, RegExp][] = categories
        .filter((c: any) => c.rule?.type === 'regex' && c.rule.regex)
        .flatMap((c: any) => {
          try {
            const pattern = c.rule.regex.replace(/\(\?[imsx]+\)/g, '');
            return [[c, new RegExp(pattern, (c.rule.ignore_case ? 'i' : '') + 'm')]];
          } catch (e) {
            console.warn('Invalid category regex:', c.rule.regex, e);
            return [];
          }
        });

      const catMap: Record<string, any> = {};

      for (const e of events) {
        const identity = this.eventIdentity(e);
        const app: string = identity.app;
        const rawTitle: string = e.data?.title || '';
        const title: string = identity.title;
        const dur: number = e.duration || 0;

        const manualCat = this.matchManualCategory(identity, categories);
        const catName: string[] = manualCat || this.matchRegexCategory(identity.matchText, regexes);
        const catKey = catName.join('>');

        if (!catMap[catKey]) {
          catMap[catKey] = {
            catKey,
            catLabel: catName[catName.length - 1],
            category: catName,
            color: (this.categoryStore as any).get_category_color(catName),
            duration: 0,
            apps: {},
          };
        }
        catMap[catKey].duration += dur;

        const hasSubCtx = supportsBrowserSubContext(app);
        if (!catMap[catKey].apps[app]) {
          catMap[catKey].apps[app] = {
            app,
            hasSubContext: hasSubCtx,
            color: catMap[catKey].color,
            colorTitle: 'Category: ' + catName.join(' > '),
            duration: 0,
            titles: {} as Record<string, any>,
          };
        }
        catMap[catKey].apps[app].duration += dur;
        if (!catMap[catKey].apps[app].titles[title]) {
          catMap[catKey].apps[app].titles[title] = {
            title,
            rawTitle,
            duration: 0,
            events: hasSubCtx ? [] as any[] : null,
          };
        }
        catMap[catKey].apps[app].titles[title].duration += dur;
        if (hasSubCtx) {
          catMap[catKey].apps[app].titles[title].events.push(e);
        }
      }

      return Object.values(catMap)
        .sort((a: any, b: any) => b.duration - a.duration)
        .map((cat: any) => ({
          ...cat,
          apps: Object.values(cat.apps)
            .sort((a: any, b: any) => b.duration - a.duration)
            .map((app: any) => ({
              ...app,
              titles: Object.values(app.titles as Record<string, any>)
                .sort((a: any, b: any) => b.duration - a.duration),
            })),
        }));
    },

    filteredActivitiesTree(): any[] {
      let tree: any[] = this.activitiesTree;

      if (this.selectedCatFilter === '__unassigned__') {
        tree = tree.filter((n: any) => n.category[0] === 'Uncategorized');
      } else if (this.selectedCatFilter) {
        const f = this.selectedCatFilter;
        tree = tree.filter((n: any) => n.catKey === f || n.catKey.startsWith(f + '>'));
      }

      if (this.searchQuery) {
        const q = this.searchQuery.toLowerCase();
        tree = tree
          .map((cat: any) => ({
            ...cat,
            apps: cat.apps
              .map((a: any) => ({
                ...a,
                titles: a.titles.filter(
                  (t: any) =>
                    a.app.toLowerCase().includes(q) || t.title.toLowerCase().includes(q)
                ),
              }))
              .filter(
                (a: any) =>
                  a.app.toLowerCase().includes(q) || a.titles.length > 0
              ),
          }))
          .filter((cat: any) => cat.apps.length > 0);
      }

      return tree;
    },

    // Duration per category key (including parent accumulation)
    categoryDurations(): Record<string, number> {
      const result: Record<string, number> = {};
      for (const node of this.activitiesTree as any[]) {
        const name: string[] = node.category;
        for (let i = 1; i <= name.length; i++) {
          const key = name.slice(0, i).join('>');
          result[key] = (result[key] || 0) + node.duration;
        }
      }
      return result;
    },

    unassignedTime(): string {
      const uncat = (this.activitiesTree as any[]).find(
        (n: any) => n.category[0] === 'Uncategorized'
      );
      return uncat ? formatDuration(uncat.duration) : '';
    },

    // Flat sidebar tree respecting expand/collapse state
    sidebarFlatTree(): any[] {
      const rows: any[] = [];
      const durations: Record<string, number> = this.categoryDurations;
      const expanded: Record<string, boolean> = this.sidebarExpanded;
      const catStore = this.categoryStore as any;

      const flatten = (cats: any[], depth: number) => {
        for (const cat of cats) {
          const key: string = cat.name.join('>');
          const dur = durations[key] || 0;
          const score = catStore.get_category_score(cat.name);
          const targetMinutes = Number(cat.data?.dailyTargetMinutes || 0);
          const goal =
            this.selectedPeriod === 'day' && targetMinutes > 0
              ? {
                  hit: dur >= targetMinutes * 60,
                  label: `${formatDuration(dur)} / ${formatDuration(targetMinutes * 60)}`,
                  percent: Math.min(100, Math.round((dur / (targetMinutes * 60)) * 100)),
                }
              : null;
          rows.push({
            key,
            id: cat.id,
            label: cat.name[cat.name.length - 1],
            fullName: cat.name,
            depth,
            color: catStore.get_category_color(cat.name),
            hasChildren: cat.children && cat.children.length > 0,
            time: dur > 0 ? formatDuration(dur) : '',
            score,
            goal,
            dailyTargetMinutes: targetMinutes > 0 ? targetMinutes : null,
          });
          if (expanded[key] && cat.children && cat.children.length > 0) {
            flatten(cat.children, depth + 1);
          }
        }
      };

      flatten(
        catStore.classes_hierarchy.filter((cat: any) => cat.name.join('>') !== 'Uncategorized'),
        0
      );

      // Inject inline-create row at the right position (#38)
      if (this.inlineCreateParent !== null) {
        const parentKey = this.inlineCreateParent;
        let insertIdx = rows.length;
        let depth = 0;
        if (parentKey !== '') {
          const parentIdx = rows.findIndex((r: any) => r.key === parentKey);
          if (parentIdx >= 0) {
            depth = rows[parentIdx].depth + 1;
            insertIdx = parentIdx + 1;
            while (insertIdx < rows.length && rows[insertIdx].depth >= depth) insertIdx++;
          }
        }
        rows.splice(insertIdx, 0, {
          key: '__inline_create__',
          id: -1,
          label: '',
          depth,
          isInlineCreate: true,
          color: '#4b8bff',
          hasChildren: false,
          time: '',
          score: 0,
          goal: null,
          dailyTargetMinutes: null,
          fullName: [],
        });
      }

      return rows;
    },

    shortcutCategories(): any[] {
      const catStore = this.categoryStore as any;
      return catStore.classes_hierarchy
        .filter((cat: any) => cat.name.length === 1 && cat.name[0] !== 'Uncategorized')
        .slice(0, 9);
    },

    // #40: Flat app list sorted by total time
    flatAppsList(): any[] {
      const appMap: Record<string, any> = {};
      for (const cat of this.filteredActivitiesTree as any[]) {
        for (const appNode of cat.apps) {
          if (!appMap[appNode.app]) {
            appMap[appNode.app] = {
              app: appNode.app,
              color: appNode.color,
              colorTitle: appNode.colorTitle,
              duration: 0,
              titles: [] as any[],
              categories: {} as Record<string, { duration: number; color: string; title: string }>,
            };
          }
          appMap[appNode.app].duration += appNode.duration;
          if (!appMap[appNode.app].categories[cat.catKey]) {
            appMap[appNode.app].categories[cat.catKey] = {
              duration: 0,
              color: cat.color,
              title: 'Category: ' + cat.category.join(' > '),
            };
          }
          appMap[appNode.app].categories[cat.catKey].duration += appNode.duration;
          for (const t of appNode.titles) {
            const existing = appMap[appNode.app].titles.find((x: any) => x.title === t.title);
            if (existing) existing.duration += t.duration;
            else appMap[appNode.app].titles.push({ ...t });
          }
        }
      }
      return Object.values(appMap)
        .sort((a: any, b: any) => b.duration - a.duration)
        .map((a: any) => {
          const dominant = _.maxBy(Object.values(a.categories), (c: any) => c.duration) as any;
          return {
            ...a,
            color: dominant ? dominant.color : a.color,
            colorTitle: dominant ? dominant.title : a.colorTitle,
            titles: [...a.titles].sort((x: any, y: any) => y.duration - x.duration),
          };
        });
    },

    // #37/#51: ordered list of visible row keys for selection and keyboard navigation
    visibleActivityRowKeys(): any[] {
      const result: any[] = [];
      if (this.viewMode === 'unified') {
        for (const catNode of this.filteredActivitiesTree as any[]) {
          result.push({
            key: this.catActivityRowKey(catNode.catKey),
            expansion: { type: 'cat', key: catNode.catKey },
          });
          if (!this.expandedCats[catNode.catKey]) continue;
          for (const appNode of catNode.apps) {
            const aKey = this.appRowKey(catNode.catKey, appNode.app);
            result.push({
              key: aKey,
              payload: { type: 'app', app: appNode.app, title: '' },
              expansion: { type: 'app', key: catNode.catKey + '/' + appNode.app },
            });
            if (this.expandedApps[catNode.catKey + '/' + appNode.app]) {
              for (const t of appNode.titles) {
                const ctxKey = catNode.catKey + '/' + appNode.app + '/' + t.title;
                result.push({
                  key: this.titleRowKey(catNode.catKey, appNode.app, t.title),
                  payload: { type: 'title', app: appNode.app, title: t.title, rawTitle: t.rawTitle || t.title },
                  expansion: t.events && t.events.length
                    ? { type: 'ctx', key: ctxKey }
                    : undefined,
                });
                if (t.events && t.events.length && this.expandedContexts[ctxKey]) {
                  for (const e of t.events) {
                    const identity = this.eventIdentity(e);
                    result.push({
                      key: '',
                      payload: { type: 'title', app: appNode.app, title: identity.title, rawTitle: e.data?.title || '' },
                    });
                  }
                }
              }
            }
          }
        }
      } else if (this.viewMode === 'apps') {
        for (const appNode of this.flatAppsList as any[]) {
          result.push({
            key: 'flat/' + appNode.app,
            payload: { type: 'app', app: appNode.app, title: '' },
            expansion: { type: 'app', key: 'flat/' + appNode.app },
          });
          if (this.expandedApps['flat/' + appNode.app]) {
            for (const t of appNode.titles) {
              result.push({
                key: 'flat/' + appNode.app + '/' + t.title,
                payload: { type: 'title', app: appNode.app, title: t.title, rawTitle: t.rawTitle || t.title },
              });
            }
          }
        }
      } else {
        for (const group of this.chronoGrouped as any[]) {
          const groupIdentity = this.eventIdentity(group.event);
          result.push({
            key: this.chronoGroupRowKey(group.key),
            payload: { type: 'app', app: groupIdentity.app, title: '' },
            expansion: { type: 'chrono', key: group.key },
          });
          if (!this.expandedTimelineBlocks[group.key]) continue;
          for (const e of group.subEvents) {
            const identity = this.eventIdentity(e);
            result.push({
              key: this.chronoEventRowKey(group.key, e),
              payload: {
                type: 'title',
                app: identity.app,
                title: identity.title,
                rawTitle: identity.rawTitle || identity.title,
              },
            });
          }
        }
      }
      return result;
    },

    // Map each app to its category color (for timeline coloring)
    appCategoryColors(): Record<string, string> {
      const map: Record<string, string> = {};
      for (const cat of this.activitiesTree as any[]) {
        for (const app of cat.apps) {
          if (!map[app.app]) map[app.app] = cat.color;
        }
      }
      return map;
    },

    // Map each app to its category key (for timeline dim filter)
    appCategoryKeys(): Record<string, string> {
      const map: Record<string, string> = {};
      for (const cat of this.activitiesTree as any[]) {
        for (const app of cat.apps) {
          if (!map[app.app]) map[app.app] = cat.catKey;
        }
      }
      return map;
    },

    weekDays(): any[] {
      const start = moment(this.periodStart);
      return Array.from({ length: 7 }, (_, index) => {
        const day = start.clone().add(index, 'days');
        const date = day.format('YYYY-MM-DD');
        const events = this.eventsForDate(this.scopedActiveWindowEvents as any[], date);
        const timeline = this.buildTimeline(events);
        return {
          activeEventCount: events.length,
          date,
          dayLabel: day.format('MMM D'),
          timeline,
          timelineCanvas: this.buildTimelineCanvas(timeline, date),
          trackedTime: formatDuration(this.sumDuration(events)),
          weekday: day.format('ddd'),
        };
      });
    },

    monthDays(): any[] {
      const monthStart = moment(this.selectedDate).startOf('month');
      const gridStart = monthStart.clone().startOf('isoWeek');
      const monthEnd = monthStart.clone().endOf('month');
      const gridEnd = monthEnd.clone().endOf('isoWeek');
      const maxDuration = Math.max(
        1,
        ...Array.from({ length: monthStart.daysInMonth() }, (_, index) =>
          this.sumDuration(
            this.eventsForDate(
              this.activeWindowEvents as any[],
              monthStart.clone().add(index, 'days').format('YYYY-MM-DD')
            )
          )
        )
      );
      const days: any[] = [];
      const cursor = gridStart.clone();
      while (cursor.isSameOrBefore(gridEnd, 'day')) {
        const date = cursor.format('YYYY-MM-DD');
        const events = this.eventsForDate(this.activeWindowEvents as any[], date);
        const duration = this.sumDuration(events);
        days.push({
          barColor: this.scoreForEvents(events) < 0 ? '#ef4444' : '#22c55e',
          date,
          day: cursor.date(),
          inMonth: cursor.isSame(monthStart, 'month'),
          isToday: cursor.isSame(moment(), 'day'),
          key: date,
          productiveWidth:
            duration > 0 ? Math.max(8, Math.round((duration / maxDuration) * 100)) + '%' : '0',
          trackedTime: duration > 0 ? formatDuration(duration) : '',
        });
        cursor.add(1, 'day');
      }
      return days;
    },

    // Timeline: merge consecutive same-app events, full day
    timeline(): any[] {
      const events: any[] = this.scopedActiveWindowEvents;
      if (!events.length) return [];
      const sorted = [...events].sort(
        (a: any, b: any) => moment(a.timestamp).valueOf() - moment(b.timestamp).valueOf()
      );

      // Pass 1: merge consecutive same-app events, but only if gap < MAX_MERGE_GAP_MS
      const merged1: any[] = [];
      let current: any = null;
      for (const e of sorted) {
        const identity = this.eventIdentity(e);
        const app: string = identity.app;
        const eStart = moment(e.timestamp).valueOf();
        const gapMs = current ? eStart - current.end.valueOf() : Infinity;
        if (current && current.app === app && gapMs < MAX_MERGE_GAP_MS) {
          const eEnd = moment(e.timestamp).add(e.duration, 'seconds');
          if (eEnd.isAfter(current.end)) current.end = eEnd;
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
          category: this.classifyEventCategory(e),
        };
      }
      if (current) merged1.push(current);

      // Pass 2: absorb very short interruptions
      const blocks: any[] = [];
      for (let i = 0; i < merged1.length; i++) {
        const b = merged1[i];
        const prev = blocks.length > 0 ? blocks[blocks.length - 1] : null;
        if (b.duration < 30 && prev && prev.app !== b.app) {
          const next = i + 1 < merged1.length ? merged1[i + 1] : null;
          const prevGap = b.start.valueOf() - prev.end.valueOf();
          const nextGap = next ? next.start.valueOf() - b.end.valueOf() : Infinity;
          if (next && next.app === prev.app && prevGap < MAX_MERGE_GAP_MS && nextGap < MAX_MERGE_GAP_MS) {
            prev.end = b.end;
            prev.duration += b.duration;
            continue;
          }
        }
        const gapMs = prev ? b.start.valueOf() - prev.end.valueOf() : Infinity;
        if (prev && prev.app === b.app && gapMs < MAX_MERGE_GAP_MS) {
          prev.end = b.end;
          prev.duration += b.duration;
        } else {
          blocks.push({ ...b });
        }
      }

      const appIndexMap: Record<string, number> = {};
      const catColors = this.appCategoryColors;
      let idx = 0;
      return blocks
        .filter((b: any) => b.duration >= 60)
        .map((b: any) => {
          if (!(b.app in appIndexMap)) appIndexMap[b.app] = idx++;
          // Use category color if available, else fall back to gradient
          const catColor = (this.categoryStore as any).get_category_color(b.category || ['Uncategorized']) || catColors[b.app];
          const color = catColor
            ? catColor
            : gradientForApp(b.app, appIndexMap[b.app]);
          return {
            label: b.app,
            catKey: this.appCategoryKeys[b.app] || 'Uncategorized',
            range: formatHHMM(b.start.toISOString()) + ' – ' + formatHHMM(b.end.toISOString()),
            color,
            colorTitle: 'Category: ' + (b.category || ['Uncategorized']).join(' > '),
            event: b.event,
            startMs: b.start.valueOf(),
            endMs: b.end.valueOf(),
          };
        });
    },

    timelineCanvas(): { blocks: any[]; hours: any[]; nowPx: number | null; totalHeight: number; canvasStartMs: number } {
      const dayStart = moment(this.selectedDate).startOf('day').valueOf();
      const SCALE = HOUR_PX / 3600000; // px per millisecond
      const blocks_raw = this.timeline as any[];

      // Default visible window: 8am–10pm
      const default8am = moment(this.selectedDate).hour(8).startOf('hour').valueOf();
      const default10pm = moment(this.selectedDate).hour(22).startOf('hour').valueOf();

      // Extend if there's content outside the default window
      const earliestContent = blocks_raw.length > 0
        ? Math.min(...blocks_raw.map((b: any) => b.startMs))
        : default8am;
      const latestContent = blocks_raw.length > 0
        ? Math.max(...blocks_raw.map((b: any) => b.endMs))
        : default10pm;

      // Canvas bounds: snap to hour boundaries
      const canvasStartMs = moment(Math.min(earliestContent, default8am)).startOf('hour').valueOf();
      const canvasEndMs = moment(Math.max(latestContent, default10pm)).add(1, 'hour').startOf('hour').valueOf();

      const startHour = Math.round((canvasStartMs - dayStart) / 3600000);
      const endHour = Math.round((canvasEndMs - dayStart) / 3600000);

      // Hour labels + gridlines for visible range only
      const hours = Array.from({ length: endHour - startHour + 1 }, (_, i) => {
        const h = startHour + i;
        const label = formatHourLabel(h);
        return { h, label, top: i * HOUR_PX };
      });

      // Position blocks relative to canvasStartMs
      const blocks = blocks_raw.map((item: any) => {
        const topPx = (item.startMs - canvasStartMs) * SCALE;
        const heightPx = Math.max(4, (item.endMs - item.startMs) * SCALE);
        return { ...item, top: topPx, heightPx };
      });

      // Current time red line (today only, if within visible range)
      let nowPx: number | null = null;
      if (this.isToday) {
        const nowMs = moment().valueOf();
        if (nowMs >= canvasStartMs && nowMs <= canvasEndMs) {
          nowPx = (nowMs - canvasStartMs) * SCALE;
        }
      }

      return { blocks, hours, nowPx, totalHeight: (endHour - startHour) * HOUR_PX, canvasStartMs };
    },

    // Chronological view: timeline blocks as top-level rows, individual events nested inside
    chronoGrouped(): any[] {
      const blocks: any[] = this.timeline as any[];
      const allEvents: any[] = this.scopedActiveWindowEvents;
      const q = this.searchQuery.toLowerCase();

      return blocks
        .filter((block: any) => !q || block.label.toLowerCase().includes(q))
        .map((block: any) => {
          const key = block.label + '-' + block.startMs;
          const subEvents = allEvents
            .filter((e: any) => {
              const t = moment(e.timestamp).valueOf();
              return t >= block.startMs && t < block.endMs && (e.duration || 0) >= 5;
            })
            .sort((a: any, b: any) => moment(a.timestamp).valueOf() - moment(b.timestamp).valueOf());
          return { ...block, key, subEvents };
        });
    },

    // Flat chronological event list for the chrono view
    chronoEvents(): any[] {
      const events: any[] = this.scopedActiveWindowEvents;
      if (!events.length) return [];

      let filtered = events;
      if (this.searchQuery) {
        const q = this.searchQuery.toLowerCase();
        filtered = events.filter((e: any) =>
          (e.data?.app || '').toLowerCase().includes(q) ||
          (e.data?.title || '').toLowerCase().includes(q)
        );
      }

      const categories: any[] = (this.categoryStore as any).classes;
      const regexes: [any, RegExp][] = categories
        .filter((c: any) => c.rule?.type === 'regex' && c.rule.regex)
        .map((c: any) => [c, new RegExp(c.rule.regex, (c.rule.ignore_case ? 'i' : '') + 'm')]);

      return [...filtered]
        .sort((a: any, b: any) => moment(a.timestamp).valueOf() - moment(b.timestamp).valueOf())
        .filter((e: any) => (e.duration || 0) >= 5)
        .map((e: any) => {
          const identity = this.eventIdentity(e);
          const app: string = identity.app;
          const catName = this.matchManualCategory(identity, categories) || this.matchRegexCategory(identity.matchText, regexes);
          return {
            ts: e.timestamp,
            app,
            title: identity.title,
            timeStr: formatHHMM(e.timestamp),
            duration: e.duration,
            catColor: (this.categoryStore as any).get_category_color(catName),
            appColor: getColorFromString(app),
          };
        });
    },
  },

  methods: {
    // Expose module-level helpers to the template
    formatDuration(seconds: number): string {
      return formatDuration(seconds);
    },

    notAfkIntervalsFor(afkEvents: any[]): { start: number; end: number }[] {
      return (afkEvents || [])
        .filter((event: any) => event.data?.status === 'not-afk' && event.duration > 0)
        .map((event: any) => ({
          start: moment(event.timestamp).valueOf(),
          end: moment(event.timestamp).add(event.duration, 'seconds').valueOf(),
        }));
    },

    activeEventsFor(windowEvents: any[], afkEvents: any[]): any[] {
      const events = (windowEvents || []).filter((event: any) => !this.shouldHideFromChronio(event));
      const intervals = this.notAfkIntervalsFor(afkEvents);
      // Fail-open: if no AFK data is available for this day, preserve tracked window events.
      if (intervals.length === 0) {
        return events.filter((event: any) => !SYSTEM_PROCESS_BLOCKLIST.has(event.data?.app));
      }

      const segments: any[] = [];
      for (const event of events) {
        if (SYSTEM_PROCESS_BLOCKLIST.has(event.data?.app)) continue;
        const eventStart = moment(event.timestamp).valueOf();
        const eventEnd = eventStart + event.duration * 1000;
        if (eventEnd <= eventStart) continue;

        for (const interval of intervals) {
          const start = Math.max(eventStart, interval.start);
          const end = Math.min(eventEnd, interval.end);
          const durationMs = end - start;
          if (durationMs <= 1000) continue;
          segments.push({
            ...event,
            timestamp: moment(start).toISOString(),
            duration: durationMs / 1000,
          });
        }
      }
      return segments;
    },

    resetAdvancedSearchRange() {
      const end = moment(this.selectedDate || get_today_with_offset(this.settingsStore.startOfDay));
      this.searchEndDate = end.format('YYYY-MM-DD');
      this.searchStartDate = end.clone().subtract(ADVANCED_SEARCH_DAYS - 1, 'days').format('YYYY-MM-DD');
    },

    normalizedAdvancedSearchRange(): { start: any; end: any } {
      let end = moment(this.searchEndDate, 'YYYY-MM-DD', true);
      let start = moment(this.searchStartDate, 'YYYY-MM-DD', true);
      if (!end.isValid() || !start.isValid()) {
        this.resetAdvancedSearchRange();
        end = moment(this.searchEndDate, 'YYYY-MM-DD', true);
        start = moment(this.searchStartDate, 'YYYY-MM-DD', true);
      }
      if (start.isAfter(end, 'day')) start = end.clone();

      const earliestAllowed = end.clone().subtract(ADVANCED_SEARCH_DAYS - 1, 'days');
      if (start.isBefore(earliestAllowed, 'day')) start = earliestAllowed;

      const normalizedStart = start.format('YYYY-MM-DD');
      const normalizedEnd = end.format('YYYY-MM-DD');
      if (this.searchStartDate !== normalizedStart) this.searchStartDate = normalizedStart;
      if (this.searchEndDate !== normalizedEnd) this.searchEndDate = normalizedEnd;
      return { start: start.startOf('day'), end: end.startOf('day') };
    },

    queueAdvancedSearch() {
      if (!this.isSearchActive) return;
      if (this.searchDebounceTimer) clearTimeout(this.searchDebounceTimer);
      if (!this.searchLoadedRangeKey) this.searchLoading = true;
      this.searchDebounceTimer = setTimeout(() => {
        this.searchDebounceTimer = null;
        this.loadAdvancedSearch();
      }, 220);
    },

    async loadAdvancedSearch() {
      if (!this.isSearchActive) return;
      const range = this.normalizedAdvancedSearchRange();
      const rangeKey = range.start.format('YYYY-MM-DD') + '/' + range.end.format('YYYY-MM-DD');
      if (this.searchLoadedRangeKey === rangeKey) {
        this.searchLoading = false;
        return;
      }

      const requestId = ++this.searchRequestId;
      this.searchLoading = true;
      this.searchError = '';

      const allHosts: string[] = (this.bucketsStore.hosts as string[])
        .filter((host: string) => host && host !== 'unknown' && !/^\d+\.\d+\.\d+\.\d+$/.test(host));
      const windowBuckets: string[] = allHosts.flatMap((host: string) => this.bucketsStore.bucketsWindow(host));
      const afkBuckets: string[] = allHosts.flatMap((host: string) => this.bucketsStore.bucketsAFK(host));
      if (!windowBuckets.length) {
        this.searchSourceRows = [];
        this.searchError = 'No window activity buckets are available for search.';
        this.searchLoading = false;
        return;
      }

      const days: any[] = [];
      const cursor = range.start.clone();
      while (cursor.isSameOrBefore(range.end, 'day')) {
        days.push(cursor.clone());
        cursor.add(1, 'day');
      }

      try {
        const rowsByDay = await Promise.all(days.map(async (day: any) => {
          const params = {
            start: day.clone().startOf('day').toDate(),
            end: day.clone().add(1, 'day').startOf('day').toDate(),
            limit: -1,
          };
          const [windowEventArrays, afkEventArrays] = await Promise.all([
            Promise.all(windowBuckets.map((bucket: string) =>
              getClient().getEvents(bucket, params).catch(() => [])
            )),
            Promise.all(afkBuckets.map((bucket: string) =>
              getClient().getEvents(bucket, params).catch(() => [])
            )),
          ]);
          return this.activeEventsFor(windowEventArrays.flat(), afkEventArrays.flat())
            .map((event: any) => this.advancedSearchRow(event));
        }));
        if (requestId !== this.searchRequestId) return;
        this.searchSourceRows = rowsByDay.flat()
          .sort((a: any, b: any) => b.startMs - a.startMs);
        this.searchLoadedRangeKey = rangeKey;
      } catch (error) {
        if (requestId !== this.searchRequestId) return;
        this.searchSourceRows = [];
        this.searchError = 'Search could not load activity for this date range.';
      } finally {
        if (requestId === this.searchRequestId) this.searchLoading = false;
      }
    },

    advancedSearchRow(event: any): any {
      const identity = this.eventIdentity(event);
      const category = this.classifyEventCategory(event);
      const start = moment(event.timestamp);
      const end = start.clone().add(event.duration || 0, 'seconds');
      const categoryLabel = category.join(' > ');
      return {
        app: identity.app,
        category,
        categoryColor: (this.categoryStore as any).get_category_color(category),
        categoryKey: category.join('>'),
        categoryLabel,
        date: start.format('YYYY-MM-DD'),
        dayLabel: start.format('ddd, MMM D'),
        event,
        key: [event.id || '', start.valueOf(), identity.app, identity.title].join('/'),
        matchText: [identity.matchText, categoryLabel].filter(Boolean).join('\n'),
        startMs: start.valueOf(),
        timeLabel: formatHHMM(start.toISOString()) + ' - ' + formatHHMM(end.toISOString()),
        title: identity.title,
      };
    },

    clearAdvancedSearch() {
      if (this.searchDebounceTimer) clearTimeout(this.searchDebounceTimer);
      this.searchDebounceTimer = null;
      this.searchRequestId++;
      this.searchQuery = '';
      this.searchCategory = '';
      this.searchError = '';
      this.searchLoading = false;
    },

    openAdvancedSearchResult(result: any) {
      const alreadyOnDay = this.selectedPeriod === 'day' && this.selectedDate === result.date;
      this.pendingTimelineScrollMs = result.startMs;
      this.selectedPeriod = 'day';
      this.selectedDate = result.date;
      this.syncRoute();
      if (alreadyOnDay) this.$nextTick(() => this.scrollTimeline());
    },

    periodStartFor(date: any, period: 'day' | 'week' | 'month'): any {
      const start = moment(date);
      if (period === 'month') return start.startOf('month');
      if (period === 'week') {
        const weekStart = this.settingsStore.startOfWeek || 'Monday';
        const startDay = weekStart === 'Saturday' ? 6 : weekStart === 'Sunday' ? 0 : 1;
        return start.startOf('day').subtract((start.day() - startDay + 7) % 7, 'days');
      }
      return start.startOf('day');
    },

    sumDuration(events: any[]): number {
      return events.reduce((total: number, event: any) => total + (event.duration || 0), 0);
    },

    eventsForDate(events: any[], date: string): any[] {
      const start = moment(date).startOf('day');
      const end = start.clone().add(1, 'day');
      return events.filter((event: any) => {
        const timestamp = moment(event.timestamp);
        return timestamp.isSameOrAfter(start) && timestamp.isBefore(end);
      });
    },

    scoreForEvents(events: any[]): number {
      return events.reduce((total: number, event: any) => {
        const score = (this.categoryStore as any).get_category_score(this.classifyEventCategory(event));
        return total + ((event.duration || 0) / 3600) * score;
      }, 0);
    },

    scoreLabel(events: any[]): string {
      const score = this.scoreForEvents(events);
      return (score >= 0 ? '+' : '') + score.toFixed(1);
    },

    buildTimeline(events: any[]): any[] {
      if (!events.length) return [];
      let filtered = events;
      if (this.searchQuery) {
        const q = this.searchQuery.toLowerCase();
        filtered = events.filter((event: any) => {
          return (
            (event.data?.app || '').toLowerCase().includes(q) ||
            (event.data?.title || '').toLowerCase().includes(q)
          );
        });
      }

      const sorted = [...filtered].sort(
        (a: any, b: any) => moment(a.timestamp).valueOf() - moment(b.timestamp).valueOf()
      );
      const merged: any[] = [];
      let current: any = null;
      for (const event of sorted) {
        const app = this.eventIdentity(event).app;
        const eventStart = moment(event.timestamp).valueOf();
        const gapMs = current ? eventStart - current.end.valueOf() : Infinity;
        if (current && current.app === app && gapMs < MAX_MERGE_GAP_MS) {
          const eventEnd = moment(event.timestamp).add(event.duration, 'seconds');
          if (eventEnd.isAfter(current.end)) current.end = eventEnd;
          current.duration += event.duration;
          continue;
        }
        if (current) merged.push(current);
        current = {
          app,
          category: this.classifyEventCategory(event),
          duration: event.duration,
          end: moment(event.timestamp).add(event.duration, 'seconds'),
          event,
          start: moment(event.timestamp),
        };
      }
      if (current) merged.push(current);

      const blocks: any[] = [];
      for (let index = 0; index < merged.length; index++) {
        const block = merged[index];
        const previous = blocks.length > 0 ? blocks[blocks.length - 1] : null;
        if (block.duration < 30 && previous && previous.app !== block.app) {
          const next = index + 1 < merged.length ? merged[index + 1] : null;
          const previousGap = block.start.valueOf() - previous.end.valueOf();
          const nextGap = next ? next.start.valueOf() - block.end.valueOf() : Infinity;
          if (
            next &&
            next.app === previous.app &&
            previousGap < MAX_MERGE_GAP_MS &&
            nextGap < MAX_MERGE_GAP_MS
          ) {
            previous.end = block.end;
            previous.duration += block.duration;
            continue;
          }
        }
        const gapMs = previous ? block.start.valueOf() - previous.end.valueOf() : Infinity;
        if (previous && previous.app === block.app && gapMs < MAX_MERGE_GAP_MS) {
          previous.end = block.end;
          previous.duration += block.duration;
        } else {
          blocks.push({ ...block });
        }
      }

      const appIndexes: Record<string, number> = {};
      const categoryColors = this.appCategoryColors;
      let appCount = 0;
      return blocks
        .filter((block: any) => block.duration >= 60)
        .map((block: any) => {
          if (!(block.app in appIndexes)) appIndexes[block.app] = appCount++;
          const categoryColor =
            (this.categoryStore as any).get_category_color(block.category || ['Uncategorized']) ||
            categoryColors[block.app];
          return {
            color: categoryColor || gradientForApp(block.app, appIndexes[block.app]),
            colorTitle: 'Category: ' + (block.category || ['Uncategorized']).join(' > '),
            endMs: block.end.valueOf(),
            event: block.event,
            label: block.app,
            range: formatHHMM(block.start.toISOString()) + ' – ' + formatHHMM(block.end.toISOString()),
            startMs: block.start.valueOf(),
          };
        });
    },

    buildTimelineCanvas(blocksRaw: any[], date: string): any {
      const scale = HOUR_PX / 3600000;
      const dayStart = moment(date).startOf('day').valueOf();
      const default8am = moment(date).hour(8).startOf('hour').valueOf();
      const default10pm = moment(date).hour(22).startOf('hour').valueOf();
      const earliestContent =
        blocksRaw.length > 0 ? Math.min(...blocksRaw.map((block: any) => block.startMs)) : default8am;
      const latestContent =
        blocksRaw.length > 0 ? Math.max(...blocksRaw.map((block: any) => block.endMs)) : default10pm;
      const canvasStartMs = moment(Math.min(earliestContent, default8am)).startOf('hour').valueOf();
      const canvasEndMs = moment(Math.max(latestContent, default10pm))
        .add(1, 'hour')
        .startOf('hour')
        .valueOf();
      const startHour = Math.round((canvasStartMs - dayStart) / 3600000);
      const endHour = Math.round((canvasEndMs - dayStart) / 3600000);
      const hours = Array.from({ length: endHour - startHour + 1 }, (_, index) => {
        const hour = startHour + index;
        const label = formatHourLabel(hour);
        return { h: hour, label, top: index * HOUR_PX };
      });
      const blocks = blocksRaw.map((block: any) => ({
        ...block,
        heightPx: Math.max(4, (block.endMs - block.startMs) * scale),
        top: (block.startMs - canvasStartMs) * scale,
      }));
      let nowPx: number | null = null;
      if (moment(date).isSame(moment(), 'day')) {
        const nowMs = moment().valueOf();
        if (nowMs >= canvasStartMs && nowMs <= canvasEndMs) nowPx = (nowMs - canvasStartMs) * scale;
      }
      return { blocks, canvasStartMs, hours, nowPx, totalHeight: (endHour - startHour) * HOUR_PX };
    },

    blockTooltip(block: any): string {
      return block.label + '\n' + block.range + ' - ' + formatDuration((block.endMs - block.startMs) / 1000);
    },

    // #77: full opacity for matching blocks, dim non-matching when a filter is active
    blockOpacity(block: any): number {
      const f = this.selectedCatFilter;
      if (!f) return 1;
      if (f === '__unassigned__') {
        return block.catKey === 'Uncategorized' ? 1 : 0.15;
      }
      const matches = block.catKey === f || block.catKey.startsWith(f + '>');
      return matches ? 1 : 0.15;
    },
    formatHHMM(ts: any): string {
      return formatHHMM(ts);
    },

    normalizeTitleForMatching(title: string): string {
      return (title || '')
        .replace(/^\s*(?:\(\d+\)|\[\d+\]|\d+)\s+/, '')
        .trim();
    },

    isBrowserApp(app: string): boolean {
      return BROWSER_APP_NAMES.has(app);
    },

    browserSiteFor(title: string, url: string): { label: string; pageTitle: string } | null {
      const normalized = this.normalizeTitleForMatching(title);
      let host = '';
      if (url) {
        try {
          host = new URL(url).host.replace(/^www\./, '');
        } catch (e) {
          host = url;
        }
      }
      const siteHints = [host, url].filter(Boolean).join('\n');
      const site =
        KNOWN_BROWSER_SITES.find((s: any) => s.patterns.some((re: RegExp) => re.test(siteHints))) ||
        KNOWN_BROWSER_SITES.find((s: any) => s.patterns.some((re: RegExp) => re.test(normalized)));
      if (!site) return null;

      const parts = normalized.split(/\s+(?:-|—|\|)\s+/).filter(Boolean);
      let pageTitle = normalized;
      if (parts.length > 1) {
        const first = parts[0];
        const last = parts[parts.length - 1];
        if (site.patterns.some((re: RegExp) => re.test(last))) {
          pageTitle = parts.slice(0, -1).join(' - ');
        } else if (site.patterns.some((re: RegExp) => re.test(first))) {
          pageTitle = parts.slice(1).join(' - ');
        }
      }

      return { label: site.label, pageTitle: pageTitle || site.label };
    },

    eventIdentity(e: any): any {
      const rawApp: string = e.data?.app || 'Unknown';
      const rawTitle: string = e.data?.title || '';
      const url: string = e.data?.url || '';
      const readableTitle = this.cleanTitle(rawTitle, rawApp);
      const normalizedTitle = this.normalizeTitleForMatching(readableTitle);

      if (this.isBrowserApp(rawApp)) {
        const site = this.browserSiteFor(readableTitle, url);
        if (site) {
          const contextTitle = extractBrowserSubContext(site.label, normalizedTitle);
          const pageTitle = site.pageTitle && site.pageTitle !== site.label
            ? site.pageTitle
            : normalizedTitle;
          const title = contextTitle || (supportsBrowserSubContext(site.label) ? site.label : pageTitle);
          return {
            rawApp,
            app: site.label,
            title: title || site.label,
            rawTitle,
            url,
            matchText: [site.label, title, pageTitle, normalizedTitle, rawTitle, url].filter(Boolean).join('\n'),
          };
        }
      }

      const app = rawApp === 'Unknown' && normalizedTitle ? normalizedTitle : rawApp;
      return {
        rawApp,
        app,
        title: normalizedTitle || app,
        rawTitle,
        url,
        matchText: [app, normalizedTitle, rawTitle, url].filter(Boolean).join('\n'),
      };
    },

    displayEventApp(e: any): string {
      return this.eventIdentity(e).app;
    },

    displayEventTitle(e: any): string {
      return this.eventIdentity(e).title;
    },

    listHasApp(app: string, apps: string[]): boolean {
      const normalizedApp = (app || '').trim().toLowerCase();
      return apps.some((entry: string) => entry.trim().toLowerCase() === normalizedApp);
    },

    titlePatternMatches(value: string, pattern: string): boolean {
      const trimmed = pattern.trim();
      if (!trimmed) return false;
      try {
        return new RegExp(trimmed, 'i').test(value);
      } catch (e) {
        return value.toLowerCase().includes(trimmed.toLowerCase());
      }
    },

    shouldHideFromChronio(e: any): boolean {
      const hiddenApps = [
        ...(this.settingsStore.chronioIgnoredApps || []),
        ...(this.settingsStore.chronioExcludedApps || []),
      ];
      if (this.listHasApp(e.data?.app || '', hiddenApps)) return true;

      const titleValue = [e.data?.title || '', e.data?.url || ''].filter(Boolean).join('\n');
      return (this.settingsStore.chronioExcludedTitlePatterns || []).some((pattern: string) =>
        this.titlePatternMatches(titleValue, pattern)
      );
    },

    matchRegexCategory(str: string, regexes: [any, RegExp][]): string[] {
      const matches = regexes.filter(([, re]: [any, RegExp]) => re.test(str));
      return matches.length > 0
        ? (_.maxBy(matches, ([c]: [any, RegExp]) => (c as any).name.length) as any)[0].name
        : ['Uncategorized'];
    },

    manualRuleMatches(identity: any, rule: any): boolean {
      if (!rule) return false;
      const app = (rule.app || '').toLowerCase();
      const title = this.normalizeTitleForMatching(rule.title || rule.rawTitle || '').toLowerCase();
      if (rule.type === 'app') return app && identity.app.toLowerCase() === app;
      return app && title &&
        identity.app.toLowerCase() === app &&
        this.normalizeTitleForMatching(identity.title || '').toLowerCase() === title;
    },

    matchManualCategory(identity: any, categories: any[]): string[] | null {
      const matches = categories.filter((c: any) =>
        (c.data?.chronioManualRules || []).some((rule: any) => this.manualRuleMatches(identity, rule))
      );
      if (!matches.length) return null;
      return (_.maxBy(matches, (c: any) => c.name.length) as any).name;
    },

    manualRuleKey(rule: any): string {
      const type = rule?.type === 'app' ? 'app' : 'title';
      const app = (rule?.app || '').toLowerCase();
      const title = this.normalizeTitleForMatching(rule?.title || rule?.rawTitle || '').toLowerCase();
      return [type, app, title].join('\u0000');
    },

    addManualCategorizationRule(targetCat: any, rule: any, catStore: any) {
      const key = this.manualRuleKey(rule);
      const targetKey = targetCat.name.join('>');
      for (const cat of catStore.classes) {
        const existingRules = cat.data?.chronioManualRules || [];
        const nextRules = existingRules.filter((existing: any) => this.manualRuleKey(existing) !== key);
        if (cat.name.join('>') === targetKey) {
          nextRules.push(rule);
        }
        const changed = nextRules.length !== existingRules.length || cat.name.join('>') === targetKey;
        if (changed) {
          catStore.updateClass({
            ...cat,
            data: { ...(cat.data || {}), chronioManualRules: nextRules },
          });
        }
      }
    },

    classifyEventCategory(e: any): string[] {
      const categories: any[] = (this.categoryStore as any).classes;
      const identity = this.eventIdentity(e);
      const manual = this.matchManualCategory(identity, categories);
      if (manual) return manual;
      const regexes: [any, RegExp][] = categories
        .filter((c: any) => c.rule?.type === 'regex' && c.rule.regex)
        .flatMap((c: any) => {
          try {
            const pattern = c.rule.regex.replace(/\(\?[imsx]+\)/g, '');
            return [[c, new RegExp(pattern, (c.rule.ignore_case ? 'i' : '') + 'm')]];
          } catch (err) {
            return [];
          }
        });
      return this.matchRegexCategory(identity.matchText, regexes);
    },

    // Strip browser name suffix from window titles for better readability
    cleanTitle(title: string, app: string): string {
      if (!title) return app;
      for (const b of BROWSER_SUFFIXES) {
        const suffix = ' - ' + b;
        if (title.endsWith(suffix)) {
          return title.slice(0, title.length - suffix.length);
        }
      }
      return title;
    },

    toggleChronoBlock(key: string) {
      this.$set(this.expandedTimelineBlocks, key, !this.expandedTimelineBlocks[key]);
    },

    setViewMode(mode: 'unified' | 'apps' | 'chrono') {
      if (this.viewMode === mode) return;
      this.viewMode = mode;
      this.clearSelection();
    },

    onTimelineBlockClick(block: any) {
      // Switch to chrono view and scroll to this block's time
      this.setViewMode('chrono');
      this.$nextTick(() => {
        const scroll = this.$refs.activitiesScroll as HTMLElement | undefined;
        if (!scroll) return;
        const row = scroll.querySelector(`[data-startms="${block.startMs}"]`) as HTMLElement | null;
        if (row) {
          scroll.scrollTop = Math.max(0, row.offsetTop - 60);
        }
      });
    },

    toggleExpandCat(key: string) {
      this.$set(this.expandedCats, key, !this.expandedCats[key]);
      this.saveExpandState();
    },

    toggleExpandApp(key: string) {
      this.$set(this.expandedApps, key, !this.expandedApps[key]);
    },

    toggleExpandContext(key: string) {
      this.$set(this.expandedContexts, key, !this.expandedContexts[key]);
    },

    onContextRowClick(catKey: string, appName: string, t: any, evt: MouseEvent) {
      if (this.isDraggingActivity) return;
      if (t.events && t.events.length) {
        if (evt.metaKey || evt.ctrlKey || evt.shiftKey) {
          const key = this.titleRowKey(catKey, appName, t.title);
          this.onActivityRowClick(key, { type: 'title', app: appName, title: t.title, rawTitle: t.rawTitle || t.title }, evt);
        } else {
          this.toggleExpandContext(catKey + '/' + appName + '/' + t.title);
        }
      } else {
        const key = this.titleRowKey(catKey, appName, t.title);
        this.onActivityRowClick(key, { type: 'title', app: appName, title: t.title, rawTitle: t.rawTitle || t.title }, evt);
      }
    },

    toggleSidebarNode(key: string) {
      this.$set(this.sidebarExpanded, key, !this.sidebarExpanded[key]);
      this.saveExpandState();
    },

    // #28: toggle expand state for a row
    toggleSidebarExpand(row: any) {
      this.$set(this.sidebarExpanded, row.key, !this.sidebarExpanded[row.key]);
      this.saveExpandState();
    },

    // #28 + #29: row click — toggle select (deselect if already selected); also expand if has children
    onSidebarRowClick(row: any) {
      this.ctxMenu = null;
      // #29: toggle filter — deselect if already selected
      if (this.selectedCatFilter === row.key) {
        this.selectedCatFilter = null;
      } else {
        this.selectedCatFilter = row.key;
        // #28: auto-expand when selecting a parent
        if (row.hasChildren && !this.sidebarExpanded[row.key]) {
          this.$set(this.sidebarExpanded, row.key, true);
          this.saveExpandState();
        }
      }
    },

    // #6 / #30: right-click context menu
    onSidebarRowRightClick(row: any, evt: MouseEvent) {
      this.ctxMenu = { row, x: evt.clientX, y: evt.clientY };
      const close = () => { this.ctxMenu = null; window.removeEventListener('click', close); };
      window.addEventListener('click', close);
    },

    // #6 / #30: inline rename
    startRename(row: any) {
      this.ctxMenu = null;
      this.renamingKey = row.key;
      this.renameValue = row.label;
      this.$nextTick(() => {
        const input = (this.$refs.renameInput as HTMLInputElement[] | HTMLInputElement);
        const el = Array.isArray(input) ? input[0] : input;
        if (el) { el.focus(); el.select(); }
      });
    },

    commitRename(row: any) {
      const newLabel = this.renameValue.trim();
      if (!newLabel) { this.cancelRename(); return; }
      const catStore = this.categoryStore as any;
      const oldName: string[] = row.key.split('>');
      const cat = catStore.classes.find((c: any) => c.name.join('>') === row.key);
      if (!cat) { this.cancelRename(); return; }
      const newName: string[] = [...oldName.slice(0, -1), newLabel];
      catStore.updateClass({ ...cat, name: newName });
      catStore.save();
      this.renamingKey = null;
    },

    cancelRename() {
      this.renamingKey = null;
    },

    // #31 + #38: + button uses inline create, subcategory if selected
    createTopCategory() {
      const parentKey = this.selectedCatFilter && this.selectedCatFilter !== '__unassigned__'
        ? this.selectedCatFilter : '';
      this.startInlineCreate(parentKey);
    },

    // #6 + #38: create child via context menu — inline
    createChildCategory(row: any) {
      this.ctxMenu = null;
      this.$set(this.sidebarExpanded, row.key, true);
      this.startInlineCreate(row.key);
    },

    // #38: inline create flow
    startInlineCreate(parentKey: string) {
      this.inlineCreateParent = parentKey;
      this.inlineCreateValue = '';
      if (parentKey) this.$set(this.sidebarExpanded, parentKey, true);
      this.$nextTick(() => {
        const input = this.$refs.inlineCreateInput as HTMLInputElement[] | HTMLInputElement;
        const el = Array.isArray(input) ? input[0] : input;
        if (el) el.focus();
      });
    },

    commitInlineCreate() {
      const label = this.inlineCreateValue.trim();
      if (!label) { this.cancelInlineCreate(); return; }
      const parentName: string[] = this.inlineCreateParent ? this.inlineCreateParent.split('>') : [];
      (this.categoryStore as any).addClass({
        name: [...parentName, label],
        rule: { type: 'none' },
        data: { color: '#4b8bff' },
      });
      (this.categoryStore as any).save();
      this.inlineCreateParent = null;
      this.inlineCreateValue = '';
    },

    cancelInlineCreate() {
      this.inlineCreateParent = null;
      this.inlineCreateValue = '';
    },

    // #6: delete category and all its children
    deleteCategory(row: any) {
      this.ctxMenu = null;
      if (!window.confirm(`Delete "${row.label}" and all its subcategories?`)) return;
      const catStore = this.categoryStore as any;
      const prefix = row.key + '>';
      const idsToDelete: number[] = catStore.classes
        .filter((c: any) => c.name.join('>') === row.key || c.name.join('>').startsWith(prefix))
        .map((c: any) => c.id);
      for (const id of idsToDelete) catStore.removeClass(id);
      catStore.save();
      if (this.selectedCatFilter === row.key) this.selectedCatFilter = null;
    },

    // ─── COLOR PICKER (#7) ────────────────────────────────────────
    openColorPicker(row: any, evt: MouseEvent) {
      if (this.colorPickerRow && this.colorPickerRow.key === row.key) {
        this.colorPickerRow = null;
        return;
      }
      const rect = (evt.target as HTMLElement).getBoundingClientRect();
      this.colorPickerPos = { x: rect.right + 6, y: rect.top };
      this.colorPickerRow = row;
      const close = (e: MouseEvent) => {
        if (!(e.target as HTMLElement).closest('.color-picker-popover')) {
          this.colorPickerRow = null;
          window.removeEventListener('click', close);
        }
      };
      this.$nextTick(() => window.addEventListener('click', close));
    },

    applyColor(color: string) {
      const catStore = this.categoryStore as any;
      const cat = catStore.classes.find((c: any) => c.name.join('>') === this.colorPickerRow.key);
      if (!cat) return;
      catStore.updateClass({ ...cat, data: { ...cat.data, color } });
      catStore.save();
    },

    // ─── PRODUCTIVITY SCORE (#8) ──────────────────────────────────
    setCategoryScore(row: any, score: number) {
      this.ctxMenu = null;
      const catStore = this.categoryStore as any;
      const cat = catStore.classes.find((c: any) => c.name.join('>') === row.key);
      if (!cat) return;
      catStore.updateClass({ ...cat, data: { ...cat.data, score } });
      catStore.save();
    },

    goalTargetValue(row: any): string {
      return row.dailyTargetMinutes ? String(row.dailyTargetMinutes) : '';
    },

    setCategoryGoal(row: any, event: Event) {
      const target = event.target as HTMLInputElement;
      const minutes = Number(target.value);
      const catStore = this.categoryStore as any;
      const cat = catStore.classes.find((c: any) => c.name.join('>') === row.key);
      if (!cat) return;
      const data = { ...(cat.data || {}) };
      if (Number.isFinite(minutes) && minutes > 0) {
        data.dailyTargetMinutes = Math.round(minutes);
      } else {
        delete data.dailyTargetMinutes;
      }
      catStore.updateClass({ ...cat, data });
      catStore.save();
    },

    // ─── DRAG-TO-CATEGORIZE (#3) ──────────────────────────────────
    onDragStartApp(appNode: any, evt: DragEvent, rowKey = '') {
      // #43: log to aid debugging
      this.isDraggingActivity = true;
      const selected = Object.values(this.selectedRowPayloads as Record<string, any>);
      const items = rowKey && this.selectedRowKeys[rowKey] && selected.length > 0
        ? selected
        : [{ type: 'app', app: appNode.app, title: '', rawTitle: '' }];
      const payload = JSON.stringify(items);
      evt.dataTransfer!.setData('application/chronio', payload);
      evt.dataTransfer!.effectAllowed = 'copy';
      console.warn('[Chronio] dragstart app', appNode.app, 'items:', items.length);
    },

    onDragStartTitle(app: string, t: any, evt: DragEvent, rowKey = '') {
      this.isDraggingActivity = true;
      // If items are selected and this row is among them, drag all selected
      const selected = Object.values(this.selectedRowPayloads as Record<string, any>);
      const items = rowKey && this.selectedRowKeys[rowKey] && selected.length > 0
        ? selected
        : [{ type: 'title', app, title: t.title, rawTitle: t.rawTitle || t.title }];
      evt.dataTransfer!.setData('application/chronio', JSON.stringify(items));
      evt.dataTransfer!.effectAllowed = 'copy';
      console.warn('[Chronio] dragstart title', t.title, 'items:', items.length);
    },

    onDragStartEvent(e: any, evt: DragEvent) {
      this.isDraggingActivity = true;
      const identity = this.eventIdentity(e);
      const payload = [{
        type: 'title',
        app: identity.app,
        title: identity.title,
        rawTitle: identity.rawTitle || identity.title,
      }];
      evt.dataTransfer!.setData('application/chronio', JSON.stringify(payload));
      evt.dataTransfer!.effectAllowed = 'copy';
    },

    onDragEnd() {
      // Clean up any drag state
      this.dragOverCatKey = null;
      setTimeout(() => { this.isDraggingActivity = false; }, 0);
    },

    onDropToCategory(row: any, evt: DragEvent) {
      this.dragOverCatKey = null;
      const catStore = this.categoryStore as any;
      const cat = catStore.classes.find((c: any) => c.name.join('>') === row.key);
      if (!cat) return;

      // Check if this is a sidebar-category reparent drag (#32)
      const sidebarKey = evt.dataTransfer!.getData('application/chronio-cat');
      if (sidebarKey) {
        this.reparentCategory(sidebarKey, row.key);
        return;
      }

      const raw = evt.dataTransfer!.getData('application/chronio');
      if (!raw) return;

      let items: any[];
      try {
        const parsed = JSON.parse(raw);
        items = Array.isArray(parsed) ? parsed : [parsed];
      } catch { return; }

      // Snapshot rule state before mutation so we can undo
      const catId = cat.id;
      const prevRule = JSON.parse(JSON.stringify(cat.rule));

      for (const payload of items) {
        const rule = payload.type === 'app'
          ? { type: 'app', app: payload.app }
          : {
              type: 'title',
              app: payload.app,
              title: payload.title,
              rawTitle: payload.rawTitle || payload.title,
            };
        this.addManualCategorizationRule(cat, rule, catStore);
      }
      catStore.save();
      this.clearSelection();

      // #78: toast with undo
      const label = items.length === 1
        ? (items[0].title || items[0].app)
        : `${items.length} items`;
      this.showToast(
        `"${label}" → ${row.label} — rule saved`,
        () => {
          const c = (this.categoryStore as any).classes.find((x: any) => x.id === catId);
          if (c) {
            c.rule.type = prevRule.type;
            c.rule.regex = prevRule.regex;
            (this.categoryStore as any).save();
          }
        },
      );
    },

    // ─── TOAST HELPERS (#78) ─────────────────────────────────────────
    showToast(message: string, undo: (() => void) | null = null) {
      const id = ++this.nextToastId;
      const timer = setTimeout(() => this.dismissToastById(id), 4000);
      this.toasts.push({ id, message, undo, timer });
    },
    dismissToast(t: any) {
      clearTimeout(t.timer);
      this.dismissToastById(t.id);
    },
    dismissToastById(id: number) {
      this.toasts = this.toasts.filter((t: any) => t.id !== id);
    },
    undoToast(t: any) {
      if (t.undo) t.undo();
      this.dismissToast(t);
    },

    // ─── SIDEBAR DRAG-TO-REPARENT (#32) ──────────────────────────
    onSidebarDragStart(row: any, evt: DragEvent) {
      this.draggingSidebarKey = row.key;
      evt.dataTransfer!.setData('application/chronio-cat', row.key);
      evt.dataTransfer!.effectAllowed = 'move';
    },

    onSidebarDragOver(row: any, evt: DragEvent) {
      const dragKey = this.draggingSidebarKey;
      // Prevent dropping onto self or descendant
      if (dragKey && (row.key === dragKey || row.key.startsWith(dragKey + '>'))) return;
      this.dragOverCatKey = row.key;
    },

    onSidebarDrop(row: any, evt: DragEvent) {
      this.dragOverCatKey = null;
      this.draggingSidebarKey = null;

      // #46: handle reorder-drag from handle
      const reorderKey = evt.dataTransfer!.getData('application/chronio-reorder');
      if (reorderKey && reorderKey !== row.key) {
        this.reorderCategory(reorderKey, row.key);
        return;
      }

      // #32: handle reparent drag from row
      const sidebarKey = evt.dataTransfer!.getData('application/chronio-cat');
      if (sidebarKey && sidebarKey !== row.key && !row.key.startsWith(sidebarKey + '>')) {
        this.reparentCategory(sidebarKey, row.key);
        return;
      }

      // Activity categorize drop
      this.onDropToCategory(row, evt);
    },

    // #46: reorder category among siblings (swap positions in classes array)
    reorderCategory(fromKey: string, toKey: string) {
      const catStore = this.categoryStore as any;
      const fromName = fromKey.split('>');
      const toName = toKey.split('>');
      // Only reorder within same parent
      const fromParent = fromName.slice(0, -1).join('>');
      const toParent = toName.slice(0, -1).join('>');
      if (fromParent !== toParent) return;

      const classes = catStore.classes;
      const fromIdx = classes.findIndex((c: any) => c.name.join('>') === fromKey);
      const toIdx = classes.findIndex((c: any) => c.name.join('>') === toKey);
      if (fromIdx < 0 || toIdx < 0) return;

      const [item] = classes.splice(fromIdx, 1);
      const newToIdx = classes.findIndex((c: any) => c.name.join('>') === toKey);
      classes.splice(newToIdx, 0, item);
      catStore.save();
    },

    reparentCategory(fromKey: string, toKey: string) {
      const catStore = this.categoryStore as any;
      const oldName: string[] = fromKey.split('>');
      const newParent: string[] = toKey.split('>');
      const leaf = oldName[oldName.length - 1];
      const newName: string[] = [...newParent, leaf];

      const cat = catStore.classes.find((c: any) => c.name.join('>') === fromKey);
      if (!cat) return;
      catStore.updateClass({ ...cat, name: newName });
      catStore.save();
    },

    // ─── MULTI-SELECT (#37) ───────────────────────────────────────
    appRowKey(catKey: string, app: string): string {
      return catKey + '/APP:' + app;
    },

    catActivityRowKey(catKey: string): string {
      return 'CAT:' + catKey;
    },

    titleRowKey(catKey: string, app: string, title: string): string {
      return catKey + '/APP:' + app + '/T:' + title;
    },

    chronoGroupRowKey(groupKey: string): string {
      return 'CHRONO:' + groupKey;
    },

    chronoEventRowKey(groupKey: string, e: any): string {
      const identity = this.eventIdentity(e);
      return this.chronoGroupRowKey(groupKey) + '/EVENT:' + e.timestamp + '/' + identity.app + '/' + identity.title;
    },

    // Unified view app rows: modifier key → multiselect, plain click → expand toggle
    onUnifiedAppRowClick(catKey: string, appNode: any, evt: MouseEvent) {
      if (this.isDraggingActivity) return;
      if (evt.metaKey || evt.ctrlKey || evt.shiftKey) {
        const key = this.appRowKey(catKey, appNode.app);
        this.onActivityRowClick(key, { type: 'app', app: appNode.app, title: '' }, evt);
      } else {
        this.toggleExpandApp(catKey + '/' + appNode.app);
      }
    },

    onAppsAppRowClick(appNode: any, evt: MouseEvent) {
      if (this.isDraggingActivity) return;
      const key = 'flat/' + appNode.app;
      if (evt.metaKey || evt.ctrlKey || evt.shiftKey) {
        this.onActivityRowClick(key, { type: 'app', app: appNode.app, title: '' }, evt);
      } else {
        this.toggleExpandApp(key);
      }
    },

    onChronoEventRowClick(groupKey: string, e: any, evt: MouseEvent) {
      if (this.isDraggingActivity) return;
      const identity = this.eventIdentity(e);
      this.onActivityRowClick(
        this.chronoEventRowKey(groupKey, e),
        {
          type: 'title',
          app: identity.app,
          title: identity.title,
          rawTitle: identity.rawTitle || identity.title,
        },
        evt
      );
    },

    onActivityRowClick(key: string, payload: any, evt: MouseEvent) {
      evt.preventDefault();
      if (evt.shiftKey && this.lastClickedKey) {
        // Range select
        const rows = this.visibleActivityRowKeys as any[];
        const fromIdx = rows.findIndex((r: any) => r.key === this.lastClickedKey);
        const toIdx = rows.findIndex((r: any) => r.key === key);
        if (fromIdx >= 0 && toIdx >= 0) {
          const lo = Math.min(fromIdx, toIdx);
          const hi = Math.max(fromIdx, toIdx);
          for (let i = lo; i <= hi; i++) {
            this.$set(this.selectedRowKeys, rows[i].key, true);
            if (rows[i].payload) this.$set(this.selectedRowPayloads, rows[i].key, rows[i].payload);
          }
        }
      } else if (evt.metaKey || evt.ctrlKey) {
        // Toggle
        if (this.selectedRowKeys[key]) {
          this.$delete(this.selectedRowKeys, key);
          this.$delete(this.selectedRowPayloads, key);
        } else {
          this.$set(this.selectedRowKeys, key, true);
          this.$set(this.selectedRowPayloads, key, payload);
        }
      } else {
        // Single select — clear others
        this.selectedRowKeys = {};
        this.selectedRowPayloads = {};
        this.$set(this.selectedRowKeys, key, true);
        this.$set(this.selectedRowPayloads, key, payload);
      }
      this.lastClickedKey = key;
    },

    clearSelection() {
      this.selectedRowKeys = {};
      this.selectedRowPayloads = {};
      this.lastClickedKey = null;
    },

    selectKeyboardActivityRow(row: any) {
      this.selectedRowKeys = {};
      this.selectedRowPayloads = {};
      this.$set(this.selectedRowKeys, row.key, true);
      if (row.payload) this.$set(this.selectedRowPayloads, row.key, row.payload);
      this.lastClickedKey = row.key;
      this.scrollActivityRowIntoView(row.key);
    },

    scrollActivityRowIntoView(key: string) {
      this.$nextTick(() => {
        const scroll = this.$refs.activitiesScroll as HTMLElement | undefined;
        if (!scroll) return;
        const rows = Array.from(scroll.querySelectorAll('[data-row-key]')) as HTMLElement[];
        const row = rows.find((el: HTMLElement) => el.dataset.rowKey === key);
        if (row) row.scrollIntoView({ block: 'nearest' });
      });
    },

    moveActivitySelection(direction: number): boolean {
      const rows = this.visibleActivityRowKeys as any[];
      if (!rows.length) return false;

      let selectedIdx = rows.findIndex((row: any) =>
        row.key === this.lastClickedKey && this.selectedRowKeys[row.key]
      );
      if (selectedIdx < 0) selectedIdx = direction > 0 ? -1 : rows.length;
      const nextIdx = Math.max(0, Math.min(rows.length - 1, selectedIdx + direction));
      this.selectKeyboardActivityRow(rows[nextIdx]);
      return true;
    },

    toggleSelectedActivityExpansion(): boolean {
      const selected = (this.visibleActivityRowKeys as any[])
        .find((row: any) => row.key === this.lastClickedKey && this.selectedRowKeys[row.key]);
      if (!selected || !selected.expansion) return false;

      if (selected.expansion.type === 'cat') this.toggleExpandCat(selected.expansion.key);
      else if (selected.expansion.type === 'app') this.toggleExpandApp(selected.expansion.key);
      else if (selected.expansion.type === 'ctx') this.toggleExpandContext(selected.expansion.key);
      else this.toggleChronoBlock(selected.expansion.key);
      return true;
    },

    assignSelectionToShortcutCategory(position: number): boolean {
      const catStore = this.categoryStore as any;
      const targetCat = (this.shortcutCategories as any[])[position];
      const selected = Object.values(this.selectedRowPayloads as Record<string, any>);
      if (!targetCat || selected.length === 0) return false;

      for (const payload of selected) {
        const rule = payload.type === 'app'
          ? { type: 'app', app: payload.app }
          : {
              type: 'title',
              app: payload.app,
              title: payload.title,
              rawTitle: payload.rawTitle || payload.title,
            };
        this.addManualCategorizationRule(targetCat, rule, catStore);
      }
      catStore.save();
      this.clearSelection();
      return true;
    },

    focusSearch() {
      const input = this.$refs.searchInput as HTMLInputElement | undefined;
      if (input) input.focus();
    },

    clearShortcutFiltersAndSelection() {
      this.clearAdvancedSearch();
      this.selectedCatFilter = null;
      this.clearSelection();
    },

    openShortcutReference() {
      this.showShortcutReference = true;
    },

    closeShortcutReference() {
      this.showShortcutReference = false;
    },

    isShortcutEditingTarget(target: EventTarget | null): boolean {
      if (!(target instanceof HTMLElement)) return false;
      const tag = target.tagName;
      return tag === 'INPUT' ||
        tag === 'TEXTAREA' ||
        tag === 'SELECT' ||
        target.isContentEditable ||
        !!target.closest('[contenteditable="true"]');
    },

    // ─── KEYBOARD NAVIGATION (#44/#51) ───────────────────────────
    onGlobalKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && !e.altKey && e.key.toLowerCase() === 'f') {
        e.preventDefault();
        this.focusSearch();
        return;
      }
      if (this.isShortcutEditingTarget(e.target) || e.metaKey || e.ctrlKey || e.altKey) return;

      if (this.showShortcutReference) {
        if (e.key === 'Escape') {
          e.preventDefault();
          this.closeShortcutReference();
        }
        return;
      }
      if (this.showOnboarding) return;

      if (e.key === 'ArrowLeft') { e.preventDefault(); this.prevDay(); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); if (!this.isToday) this.nextDay(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); this.moveActivitySelection(-1); }
      else if (e.key === 'ArrowDown') { e.preventDefault(); this.moveActivitySelection(1); }
      else if (e.key === 't' || e.key === 'T') { e.preventDefault(); this.goToToday(); }
      else if (e.key === 'u' || e.key === 'U') { e.preventDefault(); this.setViewMode('unified'); }
      else if (e.key === 'a' || e.key === 'A') { e.preventDefault(); this.setViewMode('apps'); }
      else if (e.key === 'c' || e.key === 'C') { e.preventDefault(); this.setViewMode('chrono'); }
      else if (e.key === '/') { e.preventDefault(); this.focusSearch(); }
      else if (e.key === '?') { e.preventDefault(); this.openShortcutReference(); }
      else if (e.key === 'Escape') { e.preventDefault(); this.clearShortcutFiltersAndSelection(); }
      else if ((e.key === ' ' || e.key === 'Spacebar') && this.toggleSelectedActivityExpansion()) {
        e.preventDefault();
      } else if (/^[1-9]$/.test(e.key) && this.assignSelectionToShortcutCategory(Number(e.key) - 1)) {
        e.preventDefault();
      }
    },

    goToToday() {
      const today = get_today_with_offset(this.settingsStore.startOfDay);
      if (this.selectedDate !== today) {
        this.selectedDate = today;
        this.refresh();
      }
    },

    // #45: go to previous day (best effort — just go back one day)
    goToPrevActiveDay() {
      this.prevDay();
    },

    // ─── SIDEBAR REORDER (#46) ────────────────────────────────────
    onHandleDragStart(row: any, evt: DragEvent) {
      this.reorderDragKey = row.key;
      evt.dataTransfer!.setData('application/chronio-reorder', row.key);
      evt.dataTransfer!.effectAllowed = 'move';
    },

    // ─── ONBOARDING (#12) ────────────────────────────────────────
    checkOnboarding() {
      if (!localStorage.getItem('chronio_onboarding_complete')) {
        this.showOnboarding = true;
      }
    },

    dismissOnboarding() {
      this.showOnboarding = false;
      localStorage.setItem('chronio_onboarding_complete', '1');
    },

    // #11: persist expand/collapse to localStorage
    saveExpandState() {
      try {
        localStorage.setItem('chronio-sidebar-expanded', JSON.stringify(this.sidebarExpanded));
        localStorage.setItem('chronio-expanded-cats', JSON.stringify(this.expandedCats));
      } catch (e) {
        // localStorage unavailable
      }
    },

    loadExpandState() {
      try {
        const sidebar = localStorage.getItem('chronio-sidebar-expanded');
        if (sidebar) this.sidebarExpanded = JSON.parse(sidebar);
        const cats = localStorage.getItem('chronio-expanded-cats');
        if (cats) this.expandedCats = JSON.parse(cats);
      } catch (e) {
        // localStorage unavailable
      }
    },

    // ─── MINI CALENDAR (#52) ─────────────────────────────────────────
    prevCalMonth() {
      const m = moment().year(this.calendarYear).month(this.calendarMonth).subtract(1, 'month');
      this.calendarYear = m.year();
      this.calendarMonth = m.month();
      this.loadCalendarDots();
    },
    nextCalMonth() {
      const m = moment().year(this.calendarYear).month(this.calendarMonth).add(1, 'month');
      this.calendarYear = m.year();
      this.calendarMonth = m.month();
      this.loadCalendarDots();
    },
    async loadCalendarDots() {
      const monthStart = moment().year(this.calendarYear).month(this.calendarMonth).startOf('month').toDate();
      const monthEnd = moment().year(this.calendarYear).month(this.calendarMonth).endOf('month').toDate();
      const params = { start: monthStart, end: monthEnd, limit: -1 };
      const allHosts: string[] = (this.bucketsStore.hosts as string[])
        .filter((h: string) => h && h !== 'unknown' && !/^\d+\.\d+\.\d+\.\d+$/.test(h));
      const allWindowBuckets: string[] = allHosts.flatMap((h: string) => this.bucketsStore.bucketsWindow(h));
      try {
        const arrays = await Promise.all(
          allWindowBuckets.map((b: string) => getClient().getEvents(b, params).catch(() => []))
        );
        const dots: Record<string, boolean> = {};
        arrays.flat().forEach((e: any) => {
          const d = moment(e.timestamp).format('YYYY-MM-DD');
          dots[d] = true;
        });
        this.calendarDots = dots;
      } catch (e) {
        // silently ignore calendar fetch errors
      }
    },

    prevDay() {
      this.selectedDate = moment(this.selectedDate)
        .subtract(1, this.selectedPeriod)
        .format('YYYY-MM-DD');
      this.syncRoute();
      this.refresh();
    },
    nextDay() {
      if (this.isToday) return;
      this.selectedDate = moment(this.selectedDate).add(1, this.selectedPeriod).format('YYYY-MM-DD');
      this.syncRoute();
      this.refresh();
    },
    onDateChange(dateStr: string) {
      this.selectedDate = dateStr;
      this.showDatePicker = false;
      this.syncRoute();
      this.refresh();
    },

    setPeriod(period: 'day' | 'week' | 'month') {
      this.showWeeklyReport = false;
      if (this.selectedPeriod === period) return;
      this.selectedPeriod = period;
      this.syncRoute();
      this.refresh();
    },

    selectDay(date: string) {
      this.showWeeklyReport = false;
      this.selectedPeriod = 'day';
      this.selectedDate = date;
      this.syncRoute();
      this.refresh();
    },

    openWeeklyReport() {
      this.selectedCatFilter = null;
      this.showWeeklyReport = true;
      if (this.selectedPeriod === 'week') return;
      this.selectedPeriod = 'week';
      this.syncRoute();
      this.refresh();
    },

    closeReport() {
      this.showWeeklyReport = false;
    },

    exportCsv(): string {
      const columns = [
        'timestamp',
        'app',
        'title',
        'category',
        'duration (seconds)',
        'productivity score',
      ];
      const rows = (this.exportRows as any[]).map((row: any) => [
        row.timestamp,
        row.app,
        row.title,
        row.category,
        row.durationSeconds,
        row.productivityScore,
      ]);
      return Papa.unparse(rows, { columns });
    },

    exportPeriod(format: 'csv' | 'json') {
      if (!(this.exportRows as any[]).length) return;
      const filename =
        'chronio-' + this.periodStart + '-to-' + this.periodEndDate + '.' + format;
      const content =
        format === 'csv'
          ? this.exportCsv()
          : JSON.stringify(this.exportRows, null, 2);
      const type = format === 'csv' ? 'text/csv;charset=utf-8' : 'application/json;charset=utf-8';
      const url = URL.createObjectURL(new Blob([content], { type }));
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    },

    routePath(): string {
      return '/chronio/' + this.selectedPeriod + '/' + this.selectedDate;
    },

    syncRoute(replace = false) {
      if (!this.selectedDate || this.$route.path === this.routePath()) return;
      const navigation = replace ? this.$router.replace(this.routePath()) : this.$router.push(this.routePath());
      navigation.catch(() => undefined);
    },

    async refresh(silent = false) {
      if (!this.host) return;
      // #35: skip silent refresh if a full (non-silent) refresh is already running
      if (silent && this.isRefreshing) return;
      this.isRefreshing = true;
      if (!silent) this.loading = true;

      try {
        // Collect all same-machine hostname variants (exclude IP addresses and 'unknown')
        const allHosts: string[] = (this.bucketsStore.hosts as string[])
          .filter((h: string) => h && h !== 'unknown' && !/^\d+\.\d+\.\d+\.\d+$/.test(h));

        const allWindowBuckets: string[] = allHosts.flatMap((h: string) => this.bucketsStore.bucketsWindow(h));
        const allAfkBuckets: string[] = allHosts.flatMap((h: string) => this.bucketsStore.bucketsAFK(h));

        const start = this.periodStartFor(moment(this.selectedDate), this.selectedPeriod);
        const end = start.clone().add(1, this.selectedPeriod);
        const startDate = start.toDate();
        const endDate = end.toDate();
        const params = { start: startDate, end: endDate, limit: -1 };

        // Fetch from all same-machine buckets in parallel and merge
        const windowEvtArrays = await Promise.all(
          allWindowBuckets.map((b: string) => getClient().getEvents(b, params).catch(() => []))
        );
        const afkEvtArrays = await Promise.all(
          allAfkBuckets.map((b: string) => getClient().getEvents(b, params).catch(() => []))
        );

        // Merge and sort by timestamp descending
        const mergeEvents = (arrays: any[][]) =>
          arrays.flat().sort((a: any, b: any) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

        this.windowEvents = mergeEvents(windowEvtArrays);
        this.afkEvents = mergeEvents(afkEvtArrays);
        if (!silent) {
          this.loading = false;
          this.$nextTick(() => this.scrollTimeline());
        }
      } finally {
        this.isRefreshing = false;
      }
    },

    startLiveRefresh() {
      this.stopLiveRefresh();
      // Refresh every 60s silently on today's view only
      this.refreshTimer = setInterval(() => {
        if (this.isToday) this.refresh(true);
      }, 60000);
    },

    stopLiveRefresh() {
      if (this.refreshTimer) {
        clearInterval(this.refreshTimer);
        this.refreshTimer = null;
      }
    },

    scrollTimeline() {
      const timeline = this.$refs.timeline as any;
      if (!timeline) return;
      if (this.pendingTimelineScrollMs !== null) {
        timeline.scrollToTimestamp(this.pendingTimelineScrollMs);
        this.pendingTimelineScrollMs = null;
        return;
      }
      timeline.scrollToNow();
    },
  },

  watch: {
    host() {
      if (this.host) this.refresh();
    },
    // #39: auto-expand app rows when a category filter is selected
    selectedCatFilter(newVal: string | null) {
      if (newVal && newVal !== '__unassigned__') {
        this.$nextTick(() => {
          for (const catNode of this.filteredActivitiesTree as any[]) {
            for (const appNode of catNode.apps) {
              this.$set(this.expandedApps, catNode.catKey + '/' + appNode.app, true);
            }
          }
        });
      }
    },
    searchQuery(query: string) {
      if (query.trim()) {
        if (!this.searchStartDate || !this.searchEndDate) this.resetAdvancedSearchRange();
        this.queueAdvancedSearch();
      } else {
        this.searchRequestId++;
        this.searchLoading = false;
        this.searchError = '';
      }
    },
    searchStartDate() {
      this.searchLoadedRangeKey = '';
      if (this.isSearchActive) this.queueAdvancedSearch();
    },
    searchEndDate() {
      this.searchLoadedRangeKey = '';
      if (this.isSearchActive) this.queueAdvancedSearch();
    },
    $route(to: any) {
      const period = to.params.period;
      const date = to.params.date;
      if (period && ['day', 'week', 'month'].includes(period) && period !== this.selectedPeriod) {
        this.selectedPeriod = period;
      }
      if (this.showWeeklyReport && this.selectedPeriod !== 'week') {
        this.showWeeklyReport = false;
      }
      if (date && date !== this.selectedDate && moment(date, 'YYYY-MM-DD', true).isValid()) {
        this.selectedDate = date;
      }
      if (this.host) this.refresh();
    },
  },

  async mounted() {
    const settingsStore = this.settingsStore;
    await settingsStore.ensureLoaded();
    const routePeriod = this.$route.params.period;
    const routeDate = this.$route.params.date;
    if (routePeriod && ['day', 'week', 'month'].includes(routePeriod)) {
      this.selectedPeriod = routePeriod;
    }
    this.selectedDate =
      routeDate && moment(routeDate, 'YYYY-MM-DD', true).isValid()
        ? routeDate
        : get_today_with_offset(settingsStore.startOfDay);
    this.resetAdvancedSearchRange();
    this.syncRoute(true);
    const today = moment(this.selectedDate);
    this.calendarYear = today.year();
    this.calendarMonth = today.month();
    await this.bucketsStore.ensureLoaded();
    await (this.categoryStore as any).load();
    this.loadExpandState();
    this.checkOnboarding();
    if (this.host) {
      await this.refresh();
      this.loadCalendarDots();
    } else {
      this.loading = false;
    }
    this.startLiveRefresh();
    this.keyHandler = this.onGlobalKeyDown.bind(this);
    window.addEventListener('keydown', this.keyHandler);
  },

  beforeDestroy() {
    this.stopLiveRefresh();
    if (this.searchDebounceTimer) clearTimeout(this.searchDebounceTimer);
    if (this.keyHandler) window.removeEventListener('keydown', this.keyHandler);
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
  --border-hover: rgba(255, 255, 255, 0.15);
  --glow: 0 20px 60px rgba(0, 0, 0, 0.45);
  color: var(--text);
  background: radial-gradient(1200px 700px at 10% -10%, rgba(80, 120, 255, 0.12), transparent 60%),
              radial-gradient(900px 700px at 90% 10%, rgba(255, 110, 70, 0.12), transparent 55%),
              var(--bg);
  font-family: system-ui, -apple-system, sans-serif;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* ── TOPBAR ──────────────────────────────────────────────────────── */
.chronio-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.chronio-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 15px;
  letter-spacing: 0.4px;
}

.chronio-logo {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 2px solid #4b8bff;
  box-shadow: 0 0 0 4px rgba(75, 139, 255, 0.15);
}

.chronio-topbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.chronio-date-nav {
  display: flex;
  align-items: center;
  gap: 6px;
}

.chronio-period-toggle {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  display: inline-flex;
  overflow: hidden;

  button {
    background: transparent;
    border: 0;
    color: var(--muted);
    cursor: pointer;
    font-size: 12px;
    min-height: 30px;
    min-width: 52px;
    padding: 0 10px;
  }

  button + button {
    border-left: 1px solid var(--border);
  }

  button.active {
    background: rgba(75, 139, 255, 0.14);
    color: var(--text);
  }
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
  transition: color 0.15s, border-color 0.15s;
  &:hover { color: #fff; border-color: var(--border-hover); }
  &:disabled { opacity: 0.3; cursor: not-allowed; }
}

.chronio-chip {
  padding: 5px 12px;
  border-radius: 10px;
  background: var(--panel);
  border: 1px solid var(--border);
  font-size: 12px;
  color: var(--muted);
  cursor: pointer;
  position: relative;
  white-space: nowrap;
}

.chronio-chip.date {
  min-width: 148px;
  text-align: center;
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

.chronio-metric {
  display: inline-flex;
  gap: 6px;
  width: 108px;
  font-size: 12px;
  color: var(--muted);
  white-space: nowrap;
  .value { color: var(--text); font-weight: 600; }
}

.chronio-afk-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 10px;
  white-space: nowrap;
  cursor: default;
  &.active { background: rgba(29, 185, 84, 0.15); color: #1db954; }
  &.no-data { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
}

.chronio-search {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border-radius: 10px;
  background: var(--panel);
  border: 1px solid var(--border);
  &.active { border-color: rgba(75,139,255,0.45); }
  input {
    background: transparent;
    border: 0;
    color: var(--text);
    outline: none;
    font-size: 12px;
    width: 160px;
    &::placeholder { color: var(--muted); }
  }
}

.search-clear {
  background: transparent;
  border: 0;
  color: var(--muted);
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  padding: 0;
  &:hover { color: var(--text); }
}

/* ── LOADING ─────────────────────────────────────────────────────── */
.chronio-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--muted);
  font-size: 14px;
}

/* ── BODY: 3-COLUMN LAYOUT ───────────────────────────────────────── */
.chronio-body {
  display: grid;
  grid-template-columns: 240px 1fr 280px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.chronio-body.period-week,
.chronio-body.period-month {
  grid-template-columns: 240px minmax(0, 1fr);
}

@media print {
  .chronio-view {
    background: #fff;
    height: auto;
    min-height: 100vh;
    overflow: visible;
  }

  .chronio-topbar,
  .chronio-sidebar {
    display: none;
  }

  .chronio-body {
    display: block;
    min-height: auto;
    overflow: visible;
  }
}

/* ── SIDEBAR ─────────────────────────────────────────────────────── */
.chronio-sidebar {
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  background: rgba(15, 17, 23, 0.6);
}

.sidebar-nav {
  padding: 12px 0 8px;
  border-bottom: 1px solid var(--border);
}

.sidebar-nav-item {
  padding: 7px 16px;
  font-size: 13px;
  color: var(--muted);
  cursor: pointer;
  border-radius: 0;
  &:hover { color: var(--text); background: rgba(255,255,255,0.04); }
  &.active { color: #4b8bff; background: rgba(75,139,255,0.08); font-weight: 500; }
}

.sidebar-export-actions {
  border-bottom: 1px solid var(--border);
  display: grid;
  gap: 6px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  padding: 10px 12px;
}

.sidebar-export-btn {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--muted);
  cursor: pointer;
  font-size: 12px;
  min-height: 30px;
  padding: 0 7px;
  white-space: nowrap;

  &:hover:not(:disabled) {
    border-color: var(--border-hover);
    color: var(--text);
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.35;
  }
}

.sidebar-tree {
  padding: 8px 0;
  flex: 1;
}

.sidebar-summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 13px;
  border-radius: 6px;
  margin: 1px 6px;
  &:hover { background: rgba(255,255,255,0.05); }
  &.active { background: rgba(75,139,255,0.12); color: #7db0ff; }
  .sr-name { font-weight: 500; }
  .sr-time { color: var(--muted); font-size: 12px; }
}

.sidebar-divider {
  height: 1px;
  background: var(--border);
  margin: 8px 12px;
}

.sidebar-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 12px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--muted);
}

.sidebar-add-btn {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--muted);
  width: 20px;
  height: 20px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  &:hover { color: var(--text); border-color: var(--border-hover); }
}

.sidebar-cat-row {
  display: flex;
  align-items: stretch;
  flex-direction: column;
  gap: 4px;
  padding: 5px 6px 5px 10px;
  cursor: pointer;
  font-size: 13px;
  border-radius: 6px;
  margin: 1px 6px;
  &:hover { background: rgba(255,255,255,0.05); }
  &.active { background: rgba(75,139,255,0.12); color: #7db0ff; }
  .sr-main {
    align-items: center;
    display: flex;
    gap: 6px;
  }
  .sr-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .sr-time { color: var(--muted); font-size: 12px; white-space: nowrap; }
}

.sr-goal {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-left: 26px;
}

.sr-goal-label {
  color: var(--muted);
  display: flex;
  font-size: 10px;
  justify-content: space-between;
  line-height: 1.1;
  span.hit { color: #1db954; }
}

.sr-goal-track {
  background: rgba(255,255,255,0.08);
  border-radius: 999px;
  height: 3px;
  overflow: hidden;
}

.sr-goal-fill {
  background: #4b8bff;
  height: 100%;
  min-width: 2px;
  &.hit { background: #1db954; }
}

.sr-expand-btn {
  background: transparent;
  border: 0;
  color: var(--muted);
  cursor: pointer;
  font-size: 10px;
  padding: 0;
  width: 14px;
  flex-shrink: 0;
  &:hover { color: var(--text); }
}

.sr-expand-spacer {
  width: 14px;
  flex-shrink: 0;
}

.sr-rename-input {
  flex: 1;
  min-width: 0;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(75,139,255,0.5);
  border-radius: 4px;
  color: var(--text);
  font-size: 13px;
  padding: 1px 6px;
  outline: none;
  height: 22px;
  box-sizing: border-box;
}

/* ─── MINI CALENDAR (#52) */
.sidebar-calendar {
  padding: 10px 10px 8px;
  border-top: 1px solid var(--border);
  margin-top: 4px;
}
.cal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.cal-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
  letter-spacing: 0.02em;
}
.cal-nav {
  background: none;
  border: none;
  color: var(--muted);
  font-size: 16px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
  &:hover { color: var(--text); }
}
.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
}
.cal-dow {
  font-size: 10px;
  color: var(--muted);
  text-align: center;
  padding: 2px 0;
  font-weight: 600;
}
.cal-day {
  position: relative;
  text-align: center;
  font-size: 11px;
  padding: 4px 2px 6px;
  border-radius: 4px;
  color: var(--muted);
  cursor: default;
  &.in-month {
    color: var(--text);
    cursor: pointer;
    &:hover { background: rgba(255,255,255,0.06); }
  }
  &.is-today {
    background: rgba(75,139,255,0.12);
    color: #7db0ff;
    font-weight: 700;
  }
  &.is-selected {
    background: rgba(75,139,255,0.25);
    color: #fff;
    font-weight: 700;
  }
}
.cal-dot {
  position: absolute;
  bottom: 2px;
  left: 50%;
  transform: translateX(-50%);
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #4b8bff;
  .is-selected & { background: #fff; }
}

.sidebar-ctx-menu {
  position: fixed;
  z-index: 999;
  background: #1e2330;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 4px 0;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5);
  min-width: 160px;
}

.ctx-item {
  padding: 7px 14px;
  font-size: 13px;
  cursor: pointer;
  color: var(--text);
  &:hover { background: rgba(255,255,255,0.06); }
  &.ctx-danger { color: #ff6b6b; }
}

.ctx-divider {
  height: 1px;
  background: var(--border);
  margin: 4px 0;
}

.ctx-score-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  font-size: 12px;
  color: var(--muted);
}

.ctx-goal-row {
  align-items: center;
  color: var(--muted);
  display: flex;
  font-size: 12px;
  gap: 6px;
  justify-content: space-between;
  padding: 6px 10px;
}

.ctx-goal-input {
  align-items: center;
  display: inline-flex;
  gap: 4px;
  input {
    background: rgba(255,255,255,0.06);
    border: 1px solid var(--border);
    border-radius: 5px;
    color: var(--text);
    font: inherit;
    min-height: 24px;
    outline: none;
    padding: 2px 6px;
    width: 66px;
  }
  em {
    color: var(--muted);
    font-style: normal;
  }
}

.ctx-score-btn {
  background: rgba(255,255,255,0.06);
  border: 1px solid var(--border);
  border-radius: 5px;
  color: var(--muted);
  font-size: 11px;
  padding: 3px 8px;
  cursor: pointer;
  &:hover { border-color: var(--border-hover); color: var(--text); }
  &.active { background: rgba(29,185,84,0.2); border-color: #1db954; color: #1db954; }
  &.distracting.active { background: rgba(239,68,68,0.2); border-color: #ef4444; color: #ef4444; }
  &.neutral.active { background: rgba(255,255,255,0.1); border-color: var(--border-hover); color: var(--text); }
}

.sr-score-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  &.score-productive { background: #1db954; }
  &.score-distracting { background: #ef4444; }
}

/* #7: Color picker popover */
.color-picker-popover {
  position: fixed;
  z-index: 1000;
  background: #1e2330;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5);
  min-width: 180px;
}

.cp-swatches {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
  margin-bottom: 8px;
}

.cp-swatch {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;
  transition: border-color 0.1s, transform 0.1s;
  &:hover { transform: scale(1.15); }
  &.selected { border-color: #fff; }
}

.cp-custom {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--muted);
  input[type="color"] {
    width: 28px;
    height: 22px;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: none;
    cursor: pointer;
    padding: 1px;
  }
}

.sr-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  cursor: pointer;
  transition: transform 0.15s;
  &:hover { transform: scale(1.4); }
}

/* #3: Drag styles */
.act-row--app,
.act-row--title {
  &[draggable="true"] { cursor: grab; }
  &[draggable="true"]:active { cursor: grabbing; }
}

.act-drag-hint {
  font-size: 10px;
  color: var(--muted);
  opacity: 0;
  white-space: nowrap;
  flex-shrink: 0;
  transition: opacity 0.15s;
}

.act-row--app:hover .act-drag-hint {
  opacity: 0.5;
}

.sidebar-cat-row.drop-target {
  background: rgba(75, 139, 255, 0.2) !important;
  border: 1px dashed rgba(75, 139, 255, 0.6);
}

/* #12: Onboarding overlay */
.onboarding-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.7);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}

.onboarding-modal {
  background: #1a1f2e;
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 40px 48px;
  max-width: 420px;
  width: 90%;
  text-align: center;
  box-shadow: 0 24px 64px rgba(0,0,0,0.6);
}

.onboarding-step {
  min-height: 130px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  .ob-emoji { font-size: 48px; line-height: 1; }
  h2 { font-size: 20px; font-weight: 700; color: var(--text); margin: 0; }
  p { font-size: 14px; color: var(--muted); line-height: 1.6; margin: 0; }
}

.ob-dots {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin: 24px 0 20px;
}

.ob-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border);
  cursor: pointer;
  transition: background 0.2s;
  &.active { background: #4b8bff; }
}

.ob-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.ob-btn-primary {
  background: #4b8bff;
  color: #fff;
  border: 0;
  border-radius: 8px;
  padding: 9px 24px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  &:hover { background: #3a7aee; }
}

.ob-btn-ghost {
  background: transparent;
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 9px 24px;
  font-size: 14px;
  cursor: pointer;
  &:hover { color: var(--text); border-color: var(--border-hover); }
}

/* #51: Shortcut reference */
.shortcut-overlay {
  position: fixed;
  inset: 0;
  z-index: 2100;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0,0,0,0.68);
  backdrop-filter: blur(4px);
}

.shortcut-modal {
  width: min(420px, calc(100vw - 32px));
  background: #1a1f2e;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 18px;
  box-shadow: 0 24px 64px rgba(0,0,0,0.6);
}

.shortcut-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  h2 {
    margin: 0;
    color: var(--text);
    font-size: 16px;
    font-weight: 650;
    letter-spacing: 0;
  }
}

.shortcut-close {
  width: 28px;
  height: 28px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  &:hover { border-color: var(--border-hover); color: var(--text); }
}

.shortcut-list {
  display: grid;
  gap: 4px;
}

.shortcut-row {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  min-height: 30px;
  color: var(--muted);
  font-size: 13px;
  kbd {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 24px;
    padding: 1px 7px;
    border: 1px solid var(--border-hover);
    border-radius: 5px;
    background: rgba(255,255,255,0.06);
    color: var(--text);
    font: inherit;
    font-weight: 600;
  }
}

/* #34/#51: Activity selection highlight */
.act-row.row-selected {
  background: rgba(75, 139, 255, 0.15) !important;
  border-left: 2px solid #4b8bff;
}

/* ── CENTER ──────────────────────────────────────────────────────── */
.chronio-center {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
  min-height: 0;
  overflow: hidden;
}

.center-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.center-title {
  font-size: 14px;
  color: var(--muted);
  strong { color: var(--text); }
}

.search-close {
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--muted);
  cursor: pointer;
  font-size: 12px;
  padding: 4px 10px;
  &:hover { border-color: var(--border-hover); color: var(--text); }
}

.search-controls {
  align-items: flex-end;
  border-bottom: 1px solid var(--border);
  display: grid;
  gap: 10px;
  grid-template-columns: 132px 132px minmax(160px, 1fr);
  padding: 12px 16px 8px;
}

.search-control {
  color: var(--muted);
  display: grid;
  font-size: 11px;
  gap: 4px;
  min-width: 0;
  span { line-height: 1; }
  input,
  select {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text);
    font-size: 12px;
    height: 30px;
    min-width: 0;
    padding: 4px 7px;
    width: 100%;
  }
}

.search-range-note {
  border-bottom: 1px solid var(--border);
  color: var(--muted);
  flex-shrink: 0;
  font-size: 11px;
  padding: 6px 16px;
}

.search-state {
  color: var(--muted);
  font-size: 13px;
  padding: 22px 16px;
}

.search-error {
  color: #ff8a8a;
}

.search-results-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 4px 0;
}

.search-result-row {
  align-items: center;
  background: transparent;
  border: 0;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  color: var(--text);
  cursor: pointer;
  display: grid;
  font-size: 12px;
  gap: 12px;
  grid-template-columns: 138px minmax(0, 1fr) minmax(120px, 172px);
  padding: 9px 16px;
  text-align: left;
  width: 100%;
  &:hover,
  &:focus-visible { background: rgba(75,139,255,0.1); outline: none; }
}

.search-result-when,
.search-result-main,
.search-result-category {
  min-width: 0;
}

.search-result-day,
.search-result-time {
  display: block;
  white-space: nowrap;
}

.search-result-time,
.search-result-title {
  color: var(--muted);
}

.search-result-app,
.search-result-title,
.search-result-category span:last-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-result-app {
  font-weight: 600;
}

.search-result-title {
  margin-top: 2px;
}

.search-result-category {
  align-items: center;
  color: var(--muted);
  display: flex;
  gap: 6px;
}

.search-result-dot {
  border-radius: 50%;
  flex: 0 0 8px;
  height: 8px;
  width: 8px;
}

.view-toggle {
  display: inline-flex;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  button {
    background: transparent;
    border: 0;
    color: var(--muted);
    padding: 4px 12px;
    font-size: 11px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    &.active { background: rgba(75,139,255,0.2); color: var(--text); }
    &:hover:not(.active) { color: var(--text); }
  }
}

.activities-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.chronio-center-footer {
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid var(--border);
  padding: 6px 12px;
  flex-shrink: 0;
}

.chronio-shortcuts-hint {
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
  padding: 3px 6px;
  font-size: 11px;
  cursor: pointer;
  &:hover { color: var(--text); background: rgba(255,255,255,0.05); }
}

.act-empty {
  color: var(--muted);
  font-size: 13px;
  padding: 20px 16px;
}

/* ── ACTIVITY ROWS ───────────────────────────────────────────────── */
.act-row {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 12px;
  min-height: 34px;
  cursor: pointer;
  &:hover { background: rgba(255,255,255,0.04); }
  .act-name { flex: 1; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .act-dur { font-size: 12px; color: var(--muted); white-space: nowrap; flex-shrink: 0; }
}

.act-row--cat {
  font-weight: 500;
  .act-expand { font-size: 10px; color: var(--muted); width: 12px; flex-shrink: 0; }
}

.act-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.act-row--app {
  .act-name { color: var(--muted); font-weight: 400; }
}

.act-indent {
  width: 32px;
  flex-shrink: 0;
}

.act-indent2 {
  width: 52px;
  flex-shrink: 0;
}

.act-indent3 {
  width: 72px;
  flex-shrink: 0;
}

.act-row--context-event {
  cursor: default;
  &:hover { background: rgba(255,255,255,0.02); }
  .act-title {
    flex: 1;
    font-size: 11px;
    color: var(--muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    opacity: 0.8;
  }
  .act-time {
    font-size: 11px;
    color: var(--muted);
    white-space: nowrap;
    flex-shrink: 0;
    opacity: 0.6;
  }
}

.act-app-icon {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  flex-shrink: 0;
}

.act-row--title {
  cursor: default;
  &:hover { background: rgba(255,255,255,0.02); }
  .act-title {
    flex: 1;
    font-size: 12px;
    color: var(--muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.act-row--chrono-group {
  cursor: pointer;
  font-weight: 500;
  gap: 7px;
  .act-caret { font-size: 10px; color: var(--muted); width: 12px; flex-shrink: 0; }
  .act-app { font-size: 13px; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .act-time-range { font-size: 11px; color: var(--muted); white-space: nowrap; flex-shrink: 0; }
  &:hover { background: rgba(255,255,255,0.05); }
}

.act-row--chrono-sub {
  cursor: default;
  min-height: 28px;
  &:hover { background: rgba(255,255,255,0.02); }
  .act-app-label { font-size: 12px; color: rgba(255,255,255,0.35); white-space: nowrap; flex-shrink: 0; margin-right: 3px; }
  .act-title { flex: 1; font-size: 12px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .act-time { font-size: 11px; color: var(--muted); white-space: nowrap; flex-shrink: 0; margin-right: 4px; }
}

/* ── RIGHT TIMELINE ──────────────────────────────────────────────── */
.chronio-timeline-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  background: rgba(15, 17, 23, 0.4);
}

.timeline-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 8px 10px 24px 0;
}

/* The full-day canvas: position:relative so children can be absolute */
.timeline-canvas {
  position: relative;
  margin-left: 44px; /* room for hour labels */
  margin-right: 4px;
}

/* Each hour row: label on left, gridline stretching right */
.tl-hour {
  position: absolute;
  left: -44px;
  right: 0;
  display: flex;
  align-items: flex-start;
  pointer-events: none;
}

.tl-hour-label {
  font-size: 10px;
  color: var(--muted);
  width: 36px;
  text-align: right;
  padding-right: 8px;
  line-height: 1;
  flex-shrink: 0;
  margin-top: -1px;
}

.tl-hour-line {
  flex: 1;
  height: 1px;
  background: var(--border);
}

/* "Now" red indicator */
.tl-now-line {
  position: absolute;
  left: -44px;
  right: 0;
  height: 2px;
  background: #ff4040;
  z-index: 5;
  pointer-events: none;
  &::after {
    content: '';
    position: absolute;
    left: 44px;
    top: -4px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #ff4040;
  }
}

/* Activity blocks: absolutely placed on the canvas */
.tl-block {
  position: absolute;
  left: 2px;
  right: 2px;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  transition: filter 0.15s;
  z-index: 2;
  &:hover {
    filter: brightness(1.15);
    z-index: 3;
  }
}

.tl-block-inner {
  padding: 3px 8px;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 1px;
}

.tl-title {
  font-weight: 600;
  font-size: 11px;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.3;
}

.tl-time-range {
  font-size: 10px;
  color: rgba(255,255,255,0.75);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chronio-empty {
  color: var(--muted);
  font-size: 12px;
  padding: 12px 0;
}

/* ── DRAG HANDLE (#46) ───────────────────────────────────────────── */
.sr-drag-handle {
  opacity: 0;
  color: var(--muted);
  font-size: 12px;
  cursor: grab;
  flex-shrink: 0;
  padding: 0 2px;
  transition: opacity 0.15s;
  user-select: none;
}

.sidebar-cat-row:hover .sr-drag-handle {
  opacity: 0.5;
}

.sidebar-cat-row:hover .sr-drag-handle:hover {
  opacity: 1;
  color: var(--text);
}

/* ── INLINE CREATE (#38) ──────────────────────────────────────────── */
.sidebar-inline-create {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px 4px 10px;
  margin: 1px 6px;
}

/* ── EMPTY STATE (#45) ────────────────────────────────────────────── */
.act-day-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 10px;
  padding: 40px 20px;
  color: var(--muted);
  .act-empty-icon { font-size: 32px; opacity: 0.3; }
  p { font-size: 14px; margin: 0; text-align: center; }
}

.act-empty-prev {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--muted);
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 13px;
  cursor: pointer;
  margin-top: 6px;
  &:hover { color: var(--text); border-color: var(--border-hover); }
}

/* ── APPS VIEW (#40) act-expand reuse ────────────────────────────── */
.act-row--app .act-expand {
  font-size: 10px;
  color: var(--muted);
  width: 12px;
  flex-shrink: 0;
  cursor: pointer;
}
.act-row--app .act-expand-spacer {
  width: 12px;
  flex-shrink: 0;
}

/* ── TODAY BUTTON (#74) ─────────────────────────────────────────── */
.chronio-today-btn {
  background: rgba(75,139,255,0.15);
  border: 1px solid rgba(75,139,255,0.3);
  border-radius: 8px;
  color: #7db0ff;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 9px;
  cursor: pointer;
  white-space: nowrap;
  &:hover { background: rgba(75,139,255,0.25); }
}

/* ── PRODUCTIVITY SCORE (#4) ─────────────────────────────────────── */
.prod-score {
  &.prod-green { color: #1db954; }
  &.prod-yellow { color: #f59e0b; }
  &.prod-red { color: #ef4444; }
}

/* ── TOAST NOTIFICATIONS (#78) ───────────────────────────────────── */
.chronio-toasts {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 9999;
  pointer-events: none;
}
.chronio-toast {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #1e2330;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 9px 14px;
  font-size: 13px;
  color: var(--text);
  box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  pointer-events: auto;
  white-space: nowrap;
}
.toast-msg { flex: 1; }
.toast-undo {
  background: rgba(75,139,255,0.15);
  border: 1px solid rgba(75,139,255,0.3);
  border-radius: 6px;
  color: #7db0ff;
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  cursor: pointer;
  &:hover { background: rgba(75,139,255,0.25); }
}
.toast-close {
  background: none;
  border: none;
  color: var(--muted);
  font-size: 16px;
  cursor: pointer;
  padding: 0 2px;
  line-height: 1;
  &:hover { color: var(--text); }
}

/* ── SCROLLBAR STYLING ───────────────────────────────────────────── */
.chronio-sidebar,
.activities-scroll,
.timeline-scroll {
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.1) transparent;
  &::-webkit-scrollbar { width: 4px; }
  &::-webkit-scrollbar-track { background: transparent; }
  &::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }
}
</style>
