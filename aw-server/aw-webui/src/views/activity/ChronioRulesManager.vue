<template lang="pug">
div.rules-manager
  .rules-toolbar
    label.rules-field
      span Category
      select(v-model="draft.categoryKey")
        option(value="" disabled) Choose a category
        option(v-for="category in categoryOptions" :key="category.key" :value="category.key")
          | {{ category.label }}
    label.rules-field
      span Rule type
      select(v-model="draft.type")
        option(value="app") App
        option(value="title") Title
        option(value="regex") Category regex
    label.rules-field(v-if="draft.type !== 'regex'")
      span App
      input(v-model.trim="draft.app" type="text" placeholder="Cursor")
    label.rules-field(v-if="draft.type === 'title'")
      span Title
      input(v-model.trim="draft.title" type="text" placeholder="Project notes")
    label.rules-field.rules-field-wide(v-if="draft.type === 'regex'")
      span Pattern
      input(v-model.trim="draft.regex" type="text" placeholder="Cursor|GitHub")
    button.rules-primary(:disabled="!draftIsValid" @click="createRule") Add rule

  p.rules-status(v-if="status") {{ status }}

  .rules-empty(v-if="!ruleGroups.length")
    | No categorization rules yet.

  section.rule-group(v-for="group in ruleGroups" :key="group.key")
    h3 {{ group.label }}
    .rules-table
      .rules-head
        span Match type
        span Pattern
        span Actions
      .rules-row(v-for="row in group.rules" :key="row.key")
        span.rule-type {{ row.typeLabel }}
        .rule-pattern
          template(v-if="editingKey === row.key")
            .edit-grid
              input(v-if="row.kind !== 'regex'" v-model.trim="editing.app" type="text" placeholder="App")
              input(
                v-if="row.kind === 'title'"
                v-model.trim="editing.title"
                type="text"
                placeholder="Title"
              )
              input(
                v-if="row.kind === 'regex'"
                v-model.trim="editing.regex"
                type="text"
                placeholder="Pattern"
              )
              label.case-toggle(v-if="row.kind === 'regex'")
                input(v-model="editing.ignoreCase" type="checkbox")
                span Case insensitive
            p.rule-error(v-if="editError") {{ editError }}
          template(v-else)
            code {{ row.pattern }}
            small(v-if="row.kind === 'regex' && row.ignoreCase") Case insensitive
        .rule-actions
          template(v-if="editingKey === row.key")
            button(:disabled="!editIsValid" @click="saveEdit(row)") Save
            button(@click="cancelEdit") Cancel
          template(v-else)
            button(@click="startEdit(row)") Edit
            button.danger(@click="deleteRule(row)") Delete
</template>

<script lang="ts">
import { useCategoryStore } from '~/stores/categories';
import { validateRegex } from '~/util/validate';

type ManagedRuleKind = 'app' | 'title' | 'regex';

interface RuleDraft {
  app: string;
  categoryKey: string;
  ignoreCase: boolean;
  regex: string;
  title: string;
  type: ManagedRuleKind;
}

interface RuleRow {
  categoryId: number;
  categoryKey: string;
  categoryLabel: string;
  ignoreCase?: boolean;
  key: string;
  kind: ManagedRuleKind;
  manualIndex?: number;
  pattern: string;
  typeLabel: string;
}

function emptyDraft(): RuleDraft {
  return {
    app: '',
    categoryKey: '',
    ignoreCase: false,
    regex: '',
    title: '',
    type: 'app',
  };
}

export default {
  name: 'ChronioRulesManager',

  data() {
    return {
      categoryStore: useCategoryStore(),
      draft: emptyDraft(),
      editing: emptyDraft(),
      editingKey: '',
      status: '',
    };
  },

  computed: {
    categoryOptions(): { key: string; label: string }[] {
      return this.categoryStore.classes
        .filter((category: any) => category.name.join('>') !== 'Uncategorized')
        .map((category: any) => ({
          key: category.name.join('>'),
          label: category.name.join(' / '),
        }))
        .sort((left: { label: string }, right: { label: string }) =>
          left.label.localeCompare(right.label)
        );
    },

    rows(): RuleRow[] {
      return this.categoryStore.classes.flatMap((category: any) => {
        const categoryKey = category.name.join('>');
        const categoryLabel = category.name.join(' / ');
        const rows: RuleRow[] = [];
        if (category.rule?.type === 'regex' && category.rule.regex) {
          rows.push({
            categoryId: category.id,
            categoryKey,
            categoryLabel,
            ignoreCase: !!category.rule.ignore_case,
            key: `${category.id}:regex`,
            kind: 'regex',
            pattern: category.rule.regex,
            typeLabel: 'Category regex',
          });
        }
        (category.data?.chronioManualRules || []).forEach((rule: any, manualIndex: number) => {
          if (!rule?.app) return;
          const isTitleRule = rule.type === 'title';
          const pattern = isTitleRule
            ? `${rule.app} / ${rule.title || rule.rawTitle || ''}`
            : rule.app;
          rows.push({
            categoryId: category.id,
            categoryKey,
            categoryLabel,
            key: `${category.id}:manual:${manualIndex}`,
            kind: isTitleRule ? 'title' : 'app',
            manualIndex,
            pattern,
            typeLabel: isTitleRule ? 'Title' : 'App',
          });
        });
        return rows;
      });
    },

    ruleGroups(): { key: string; label: string; rules: RuleRow[] }[] {
      const groups = new Map<string, { key: string; label: string; rules: RuleRow[] }>();
      this.rows.forEach((row: RuleRow) => {
        if (!groups.has(row.categoryKey)) {
          groups.set(row.categoryKey, {
            key: row.categoryKey,
            label: row.categoryLabel,
            rules: [],
          });
        }
        groups.get(row.categoryKey).rules.push(row);
      });
      return Array.from(groups.values()).sort((left, right) =>
        left.label.localeCompare(right.label)
      );
    },

    draftIsValid(): boolean {
      if (!this.draft.categoryKey) return false;
      if (this.draft.type === 'regex') return validateRegex(this.draft.regex || '');
      if (!this.draft.app) return false;
      return this.draft.type !== 'title' || !!this.draft.title;
    },

    editIsValid(): boolean {
      if (!this.editingKey) return false;
      if (this.editing.type === 'regex') return validateRegex(this.editing.regex || '');
      if (!this.editing.app) return false;
      return this.editing.type !== 'title' || !!this.editing.title;
    },

    editError(): string {
      if (!this.editingKey || this.editIsValid) return '';
      if (this.editing.type === 'regex') return 'Enter a valid regex pattern.';
      if (!this.editing.app) return 'Enter the app to match.';
      return 'Enter the title to match.';
    },
  },

  mounted() {
    this.setDefaultCategory();
  },

  methods: {
    setDefaultCategory() {
      if (!this.draft.categoryKey && this.categoryOptions.length) {
        this.draft.categoryKey = this.categoryOptions[0].key;
      }
    },

    findCategory(rowOrKey: RuleRow | string) {
      const key = typeof rowOrKey === 'string' ? rowOrKey : rowOrKey.categoryKey;
      return this.categoryStore.classes.find((category: any) => category.name.join('>') === key);
    },

    async saveCategory(category: any, message: string) {
      this.categoryStore.updateClass(category);
      await this.categoryStore.save();
      this.status = message;
      window.setTimeout(() => {
        if (this.status === message) this.status = '';
      }, 1800);
    },

    manualRuleFromDraft(draft: RuleDraft) {
      return draft.type === 'title'
        ? { type: 'title', app: draft.app, title: draft.title, rawTitle: draft.title }
        : { type: 'app', app: draft.app };
    },

    async createRule() {
      if (!this.draftIsValid) return;
      const category = this.findCategory(this.draft.categoryKey);
      if (!category) return;

      if (this.draft.type === 'regex') {
        await this.saveCategory(
          {
            ...category,
            rule: {
              type: 'regex',
              regex: this.draft.regex,
              ignore_case: this.draft.ignoreCase,
            },
          },
          'Category regex saved.'
        );
      } else {
        const manualRules = [...(category.data?.chronioManualRules || [])];
        manualRules.push(this.manualRuleFromDraft(this.draft));
        await this.saveCategory(
          {
            ...category,
            data: { ...(category.data || {}), chronioManualRules: manualRules },
          },
          'Manual rule saved.'
        );
      }

      const categoryKey = this.draft.categoryKey;
      this.draft = emptyDraft();
      this.draft.categoryKey = categoryKey;
    },

    startEdit(row: RuleRow) {
      const category = this.findCategory(row);
      if (!category) return;
      this.editingKey = row.key;
      this.editing = emptyDraft();
      this.editing.categoryKey = row.categoryKey;
      this.editing.type = row.kind;
      if (row.kind === 'regex') {
        this.editing.regex = category.rule.regex || '';
        this.editing.ignoreCase = !!category.rule.ignore_case;
        return;
      }
      const rule = category.data?.chronioManualRules?.[row.manualIndex];
      this.editing.app = rule?.app || '';
      this.editing.title = rule?.title || rule?.rawTitle || '';
    },

    cancelEdit() {
      this.editingKey = '';
      this.editing = emptyDraft();
    },

    async saveEdit(row: RuleRow) {
      if (!this.editIsValid) return;
      const category = this.findCategory(row);
      if (!category) return;

      if (row.kind === 'regex') {
        await this.saveCategory(
          {
            ...category,
            rule: {
              type: 'regex',
              regex: this.editing.regex,
              ignore_case: this.editing.ignoreCase,
            },
          },
          'Category regex updated.'
        );
      } else {
        const manualRules = [...(category.data?.chronioManualRules || [])];
        manualRules.splice(row.manualIndex, 1, this.manualRuleFromDraft(this.editing));
        await this.saveCategory(
          {
            ...category,
            data: { ...(category.data || {}), chronioManualRules: manualRules },
          },
          'Manual rule updated.'
        );
      }
      this.cancelEdit();
    },

    async deleteRule(row: RuleRow) {
      if (
        !window.confirm(`Delete the ${row.typeLabel.toLowerCase()} rule for ${row.categoryLabel}?`)
      ) {
        return;
      }
      const category = this.findCategory(row);
      if (!category) return;

      if (row.kind === 'regex') {
        await this.saveCategory({ ...category, rule: { type: 'none' } }, 'Category regex deleted.');
      } else {
        const manualRules = [...(category.data?.chronioManualRules || [])];
        manualRules.splice(row.manualIndex, 1);
        await this.saveCategory(
          {
            ...category,
            data: { ...(category.data || {}), chronioManualRules: manualRules },
          },
          'Manual rule deleted.'
        );
      }
      if (this.editingKey === row.key) this.cancelEdit();
    },
  },
};
</script>

<style lang="scss" scoped>
.rules-manager {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rules-toolbar {
  align-items: end;
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
}

.rules-field {
  display: flex;
  flex-direction: column;
  font-size: 13px;
  gap: 7px;
  min-width: 0;
}

.rules-field span {
  font-weight: 600;
}

.rules-field input,
.rules-field select,
.edit-grid input {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font: inherit;
  min-height: 36px;
  min-width: 0;
  outline: none;
  padding: 8px 10px;
}

.rules-field input:focus,
.rules-field select:focus,
.edit-grid input:focus {
  border-color: #4b8bff;
}

.rules-field-wide {
  grid-column: span 2;
}

button {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  cursor: pointer;
  font: inherit;
  min-height: 34px;
  padding: 0 11px;
}

button:hover:not(:disabled) {
  border-color: var(--border-hover);
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.rules-primary {
  background: rgba(75, 139, 255, 0.18);
  border-color: rgba(125, 176, 255, 0.45);
}

.rules-status,
.rule-error {
  color: #7db0ff;
  font-size: 12px;
  margin: 0;
}

.rule-error {
  color: #ff9e9e;
}

.rules-empty {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--muted);
  font-size: 13px;
  padding: 14px;
}

.rule-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rule-group h3 {
  font-size: 13px;
  letter-spacing: 0;
  margin: 0;
}

.rules-table {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}

.rules-head,
.rules-row {
  align-items: start;
  display: grid;
  gap: 12px;
  grid-template-columns: 132px minmax(0, 1fr) auto;
  padding: 10px 12px;
}

.rules-head {
  background: var(--panel-2);
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.rules-row {
  border-top: 1px solid var(--border);
  font-size: 13px;
}

.rule-type {
  color: var(--muted);
}

.rule-pattern {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.rule-pattern code {
  color: var(--text);
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.rule-pattern small {
  color: var(--muted);
}

.rule-actions {
  display: flex;
  gap: 6px;
}

.rule-actions .danger {
  color: #ffb1b1;
}

.edit-grid {
  display: grid;
  gap: 7px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.case-toggle {
  align-items: center;
  color: var(--muted);
  display: inline-flex;
  font-size: 12px;
  gap: 6px;
}

.case-toggle input {
  min-height: auto;
}

@media (max-width: 860px) {
  .rules-toolbar,
  .rules-head,
  .rules-row {
    grid-template-columns: 1fr;
  }

  .rules-field-wide {
    grid-column: auto;
  }

  .rules-head {
    display: none;
  }
}
</style>
