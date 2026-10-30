import { ApiError } from '../api/client';

export const actions = {
  'employee.created': 'Pegawai ditambahkan', 'employee.updated': 'Data pegawai diubah',
  'branch.created': 'Cabang ditambahkan', 'branch.updated': 'Cabang diubah',
  'division.created': 'Divisi ditambahkan', 'division.updated': 'Divisi diubah',
  'division.deleted': 'Divisi dihapus', 'division.settings_changed': 'Pengaturan divisi diubah',
};
export type Changes = Partial<Record<'kinerja_enabled' | 'pelimpahan_enabled', { old: boolean; new: boolean }>>;
export type AuditEvent = {
  id: number; created_at: string; actor: { id: number; email: string };
  action: string; action_label: string;
  target: { type: 'employee' | 'branch' | 'division' | 'unknown'; id: string; label: string | null };
  changes: Changes;
};
export type AuditPage = { count: number; next: string | null; previous: string | null; results: AuditEvent[] };
export type AuditFilters = { actor: string; action: string; date_from: string; date_to: string };
export const emptyFilters: AuditFilters = { actor: '', action: '', date_from: '', date_to: '' };
function invalid(): never { throw new ApiError('protocol', 200, null, null); }
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return invalid();
  return value as Record<string, unknown>;
}
function positive(value: unknown): value is number { return typeof value === 'number' && Number.isSafeInteger(value) && value > 0; }
function decodeEvent(value: unknown): AuditEvent {
  const x = object(value), actor = object(x.actor), target = object(x.target);
  if (!positive(x.id) || !positive(actor.id) || typeof actor.email !== 'string' ||
      typeof x.created_at !== 'string' || !/^\d{4}-\d\d-\d\dT.+(?:Z|[+-]\d\d:\d\d)$/.test(x.created_at) || !Number.isFinite(Date.parse(x.created_at)) ||
      typeof x.action !== 'string' || typeof x.action_label !== 'string' ||
      typeof target.id !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(target.id) ||
      (target.label !== null && typeof target.label !== 'string') ||
      !['employee', 'branch', 'division', 'unknown'].includes(String(target.type))) return invalid();
  const known = Object.hasOwn(actions, x.action);
  const changes: Changes = {};
  if (x.action === 'division.settings_changed' && x.changes && typeof x.changes === 'object' && !Array.isArray(x.changes)) {
    for (const key of ['kinerja_enabled', 'pelimpahan_enabled'] as const) {
      const entry = (x.changes as Record<string, unknown>)[key];
      if (entry && typeof entry === 'object' && !Array.isArray(entry)) {
        const diff = entry as Record<string, unknown>;
        if (typeof diff.old === 'boolean' && typeof diff.new === 'boolean') changes[key] = { old: diff.old, new: diff.new };
      }
    }
  }
  return { id: x.id, created_at: x.created_at, actor: { id: actor.id, email: actor.email },
    action: x.action, action_label: known ? actions[x.action as keyof typeof actions] : 'Aktivitas lain',
    target: { id: target.id, type: known ? target.type as AuditEvent['target']['type'] : 'unknown', label: known ? target.label : null }, changes };
}
export function decodeAuditPage(value: unknown): AuditPage {
  const x = object(value);
  if (typeof x.count !== 'number' || !Number.isSafeInteger(x.count) || x.count < 0 ||
      !Array.isArray(x.results) || x.results.length > 50 || x.results.length > x.count ||
      (x.next !== null && typeof x.next !== 'string') || (x.previous !== null && typeof x.previous !== 'string')) return invalid();
  return { count: x.count, next: x.next, previous: x.previous, results: x.results.map(decodeEvent) };
}
export function auditPath(filters: AuditFilters, page: number): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) if (value.trim()) params.set(key, value.trim());
  params.set('page', String(page));
  return '/api/audit-events/?' + params;
}
