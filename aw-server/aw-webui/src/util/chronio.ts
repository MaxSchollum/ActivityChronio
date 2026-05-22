import moment, { Moment } from 'moment';
import Papa from 'papaparse';
import { Category } from './classes';
import { IEvent } from './interfaces';

const UNCATEGORIZED = ['Uncategorized'];

export type ChronioPeriod = 'day' | 'week' | 'month';

export type ChronioIdentity = {
  app: string;
  title: string;
  matchText: string;
};

export type ChronioExportRow = {
  timestamp: string;
  app: string;
  title: string;
  category: string;
  durationSeconds: number;
  productivityScore: number;
};

export type ChronioDateCategorySummary = {
  date: string;
  trackedSeconds: number;
  categories: Record<string, number>;
};

export function chronioPeriodStart(
  date: Moment | string,
  period: ChronioPeriod,
  startOfWeek = 'Monday'
): Moment {
  const start = moment(date);
  if (period === 'month') return start.startOf('month');
  if (period === 'week') {
    const startDay = startOfWeek === 'Saturday' ? 6 : startOfWeek === 'Sunday' ? 0 : 1;
    return start.startOf('day').subtract((start.day() - startDay + 7) % 7, 'days');
  }
  return start.startOf('day');
}

export function chronioEventsForDate(events: IEvent[], date: string): IEvent[] {
  const start = moment(date).startOf('day');
  const end = start.clone().add(1, 'day');
  return events.filter((event: IEvent) => {
    const timestamp = moment(event.timestamp);
    return timestamp.isSameOrAfter(start) && timestamp.isBefore(end);
  });
}

export function summarizeChronioDates(
  events: IEvent[],
  categoryForEvent: (event: IEvent) => string[]
): ChronioDateCategorySummary[] {
  const summaries: Record<string, ChronioDateCategorySummary> = {};

  events.forEach((event: IEvent) => {
    const date = moment(event.timestamp).format('YYYY-MM-DD');
    const category = categoryForEvent(event).join('>');
    const duration = event.duration || 0;
    if (!summaries[date]) {
      summaries[date] = { date, trackedSeconds: 0, categories: {} };
    }
    summaries[date].trackedSeconds += duration;
    summaries[date].categories[category] = (summaries[date].categories[category] || 0) + duration;
  });

  return Object.values(summaries).sort(
    (left: ChronioDateCategorySummary, right: ChronioDateCategorySummary) =>
      left.date.localeCompare(right.date)
  );
}

export function buildChronioExportRows(
  events: IEvent[],
  identityForEvent: (event: IEvent) => ChronioIdentity,
  categoryForEvent: (event: IEvent) => string[],
  scoreForCategory: (category: string[]) => number
): ChronioExportRow[] {
  return [...events]
    .sort(
      (left: IEvent, right: IEvent) =>
        moment(left.timestamp).valueOf() - moment(right.timestamp).valueOf()
    )
    .map((event: IEvent) => {
      const category = categoryForEvent(event);
      const identity = identityForEvent(event);
      return {
        timestamp: moment(event.timestamp).toISOString(),
        app: identity.app,
        title: identity.title,
        category: category.join(' > '),
        durationSeconds: event.duration || 0,
        productivityScore: scoreForCategory(category) || 0,
      };
    });
}

export function serializeChronioExportRows(
  rows: ChronioExportRow[],
  format: 'csv' | 'json'
): string {
  if (format === 'json') return JSON.stringify(rows, null, 2);

  const columns = [
    'timestamp',
    'app',
    'title',
    'category',
    'duration (seconds)',
    'productivity score',
  ];
  return Papa.unparse(
    rows.map((row: ChronioExportRow) => [
      row.timestamp,
      row.app,
      row.title,
      row.category,
      row.durationSeconds,
      row.productivityScore,
    ]),
    { columns }
  );
}

export function normalizeChronioTitleForMatching(title: string): string {
  return (title || '').replace(/^\s*(?:\(\d+\)|\[\d+\]|\d+)\s+/, '').trim();
}

export function matchChronioRegexCategory(value: string, regexes: [Category, RegExp][]): string[] {
  const matches = regexes.filter(([, regex]: [Category, RegExp]) => regex.test(value));
  return (
    deepestCategory(matches.map(([category]: [Category, RegExp]) => category))?.name ||
    UNCATEGORIZED
  );
}

export function chronioManualRuleMatches(identity: ChronioIdentity, rule: any): boolean {
  if (!rule) return false;
  const app = (rule.app || '').toLowerCase();
  const title = normalizeChronioTitleForMatching(rule.title || rule.rawTitle || '').toLowerCase();
  if (rule.type === 'app') return app && identity.app.toLowerCase() === app;
  return (
    app &&
    title &&
    identity.app.toLowerCase() === app &&
    normalizeChronioTitleForMatching(identity.title || '').toLowerCase() === title
  );
}

export function matchChronioManualCategory(
  identity: ChronioIdentity,
  categories: Category[]
): string[] | null {
  const matches = categories.filter((category: Category) =>
    (category.data?.chronioManualRules || []).some((rule: any) =>
      chronioManualRuleMatches(identity, rule)
    )
  );
  return deepestCategory(matches)?.name || null;
}

export function compileChronioCategoryRegexes(categories: Category[]): [Category, RegExp][] {
  return categories
    .filter((category: Category) => category.rule?.type === 'regex' && category.rule.regex)
    .flatMap((category: Category) => {
      try {
        const pattern = (category.rule.regex || '').replace(/\(\?[imsx]+\)/g, '');
        return [[category, new RegExp(pattern, (category.rule.ignore_case ? 'i' : '') + 'm')]];
      } catch (error) {
        return [];
      }
    });
}

export function classifyChronioCategory(
  identity: ChronioIdentity,
  categories: Category[]
): string[] {
  const manual = matchChronioManualCategory(identity, categories);
  if (manual) return manual;
  return matchChronioRegexCategory(identity.matchText, compileChronioCategoryRegexes(categories));
}

function deepestCategory(categories: Category[]): Category | null {
  return categories.reduce((deepest: Category | null, category: Category) => {
    return !deepest || category.name.length > deepest.name.length ? category : deepest;
  }, null);
}
