import {
  buildChronioExportRows,
  chronioEventsByDate,
  chronioEventsForDate,
  chronioPeriodStart,
  classifyChronioCategory,
  serializeChronioExportRows,
  summarizeChronioDates,
} from '~/util/chronio';
import { Category } from '~/util/classes';
import { IEvent } from '~/util/interfaces';

function event(timestamp: string, duration: number, app: string, title: string): IEvent {
  return { timestamp, duration, data: { app, title } };
}

describe('Chronio multi-day summaries', () => {
  test('keeps date boundaries and category durations separate', () => {
    const events = [
      event('2026-05-18T23:59:00', 60, 'Code', 'Regression'),
      event('2026-05-19T00:00:00', 120, 'Code', 'Regression'),
      event('2026-05-19T09:00:00', 300, 'Mail', 'Inbox'),
    ];

    expect(chronioEventsForDate(events, '2026-05-19')).toEqual([events[1], events[2]]);
    expect(chronioEventsByDate(events)).toEqual({
      '2026-05-18': [events[0]],
      '2026-05-19': [events[1], events[2]],
    });
    expect(
      summarizeChronioDates(events, (trackedEvent: IEvent) =>
        trackedEvent.data.app === 'Code' ? ['Work', 'Code'] : ['Comms', 'Email']
      )
    ).toEqual([
      {
        date: '2026-05-18',
        trackedSeconds: 60,
        categories: { 'Work>Code': 60 },
      },
      {
        date: '2026-05-19',
        trackedSeconds: 420,
        categories: { 'Work>Code': 120, 'Comms>Email': 300 },
      },
    ]);
  });

  test('interprets Chronio week starts from shared settings', () => {
    expect(chronioPeriodStart('2026-05-20T12:00:00', 'week', 'Monday').format('YYYY-MM-DD')).toBe(
      '2026-05-18'
    );
    expect(chronioPeriodStart('2026-05-20T12:00:00', 'week', 'Sunday').format('YYYY-MM-DD')).toBe(
      '2026-05-17'
    );
    expect(chronioPeriodStart('2026-05-20T12:00:00', 'week', 'Saturday').format('YYYY-MM-DD')).toBe(
      '2026-05-16'
    );
  });
});

describe('Chronio categorization', () => {
  const categories: Category[] = [
    { name: ['Work'], rule: { type: 'regex', regex: 'Codex' } },
    {
      name: ['Planning'],
      rule: { type: 'none' },
      data: { chronioManualRules: [{ type: 'app', app: 'Codex' }] },
    },
    {
      name: ['Planning', 'Sprint'],
      rule: { type: 'none' },
      data: { chronioManualRules: [{ type: 'title', app: 'Codex', title: 'Sprint plan' }] },
    },
  ];

  test('gives manual title context precedence over app and regex matches', () => {
    expect(
      classifyChronioCategory(
        {
          app: 'Codex',
          title: '(2) Sprint plan',
          matchText: ['Codex', '(2) Sprint plan'].join('\n'),
        },
        categories
      )
    ).toEqual(['Planning', 'Sprint']);
  });

  test('falls back to regex categorization without a manual match', () => {
    expect(
      classifyChronioCategory(
        { app: 'Editor', title: 'Codex review', matchText: ['Editor', 'Codex review'].join('\n') },
        categories
      )
    ).toEqual(['Work']);
  });
});

describe('Chronio exports', () => {
  test('shapes sorted rows and serializes CSV and JSON export payloads', () => {
    const events = [
      event('2026-05-19T09:15:00.000Z', 300, 'Mail', 'Inbox'),
      event('2026-05-19T09:00:00.000Z', 900, 'Codex', 'Diff review'),
    ];
    const rows = buildChronioExportRows(
      events,
      (trackedEvent: IEvent) => ({
        app: trackedEvent.data.app,
        title: trackedEvent.data.title,
        matchText: [trackedEvent.data.app, trackedEvent.data.title].join('\n'),
      }),
      (trackedEvent: IEvent) =>
        trackedEvent.data.app === 'Codex' ? ['Work', 'Code'] : ['Comms', 'Email'],
      (category: string[]) => (category[0] === 'Work' ? 10 : 0)
    );

    expect(rows).toEqual([
      {
        timestamp: '2026-05-19T09:00:00.000Z',
        app: 'Codex',
        title: 'Diff review',
        category: 'Work > Code',
        durationSeconds: 900,
        productivityScore: 10,
      },
      {
        timestamp: '2026-05-19T09:15:00.000Z',
        app: 'Mail',
        title: 'Inbox',
        category: 'Comms > Email',
        durationSeconds: 300,
        productivityScore: 0,
      },
    ]);

    expect(serializeChronioExportRows(rows, 'csv')).toContain(
      '2026-05-19T09:00:00.000Z,Codex,Diff review,Work > Code,900,10'
    );
    expect(serializeChronioExportRows(rows, 'csv')).toContain(
      '2026-05-19T09:15:00.000Z,Mail,Inbox,Comms > Email,300,0'
    );
    expect(JSON.parse(serializeChronioExportRows(rows, 'json'))).toEqual(rows);
  });
});
