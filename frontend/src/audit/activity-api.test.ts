import { expect, test } from 'vitest';
import { auditPath, decodeAuditPage } from './types';

const event = { id: 1, created_at: '2026-10-27T00:00:00+00:00', actor: { id: 1, email: 'hr@example.test' }, action: 'division.settings_changed', action_label: 'Pengaturan divisi diubah', target: { type: 'division', id: '20000000-0000-0000-0000-000000000001', label: 'Synthetic Division' }, changes: { kinerja_enabled: { old: false, new: true }, private: 'secret' } };
const page = { count: 1, next: null, previous: null, results: [event] };

test('decoder retains only safe fields and actual boolean settings diffs', () => {
  const decoded = decodeAuditPage(page);
  expect(decoded.results[0].changes).toEqual({ kinerja_enabled: { old: false, new: true } });
  expect(JSON.stringify(decoded)).not.toContain('secret');
});

test.each([
  null, [], { ...page, count: -1 }, { ...page, count: 0 }, { ...page, results: {} },
  { ...page, results: Array(51).fill(event) },
  { ...page, results: [{ ...event, actor: null }] },
  { ...page, results: [{ ...event, created_at: 'not-a-date' }] },
  { ...page, results: [{ ...event, target: { ...event.target, id: 'bad' } }] },
])('malformed response rejects with a protocol error %#', value => {
  expect(() => decodeAuditPage(value)).toThrow();
});

test('unknown actions and malformed metadata use safe fallbacks', () => {
  const unknown = decodeAuditPage({ ...page, results: [{ ...event, action: 'future.action', changes: { secret: 'hidden' }, target: { ...event.target, type: 'unknown', label: null } }] }).results[0];
  expect(unknown.action_label).toBe('Aktivitas lain');
  expect(unknown.changes).toEqual({});
  for (const changes of [null, [], { kinerja_enabled: { old: 0, new: 1 } }]) {
    expect(decodeAuditPage({ ...page, results: [{ ...event, changes }] }).results[0].changes).toEqual({});
  }
});

test('filter URL encodes literal email plus signs and uses local page numbers', () => {
  expect(auditPath({ actor: 'a+b@example.test', action: '', date_from: '', date_to: '' }, 2)).toBe('/api/audit-events/?actor=a%2Bb%40example.test&page=2');
});
