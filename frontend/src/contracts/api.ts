import type { Employee } from '../employees/types';
import { unitDefaultKeys, type Draft, type Field, type Kind, type References, type Values } from './types';
export type Editable = { source_unit: string | null; job_default_key: string | null; values: Values };
export function canonical(values: Values, fields: Field[]): Values {
  return Object.fromEntries(Object.entries(values).map(([key, value]) => [key, fields.find(f => f.key === key)?.kind === 'textarea' ? value : value.trim()]));
}
export function same(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (!a || !b || typeof a !== 'object' || typeof b !== 'object') return false;
  const x = a as Record<string, unknown>, y = b as Record<string, unknown>;
  return Object.keys(x).length === Object.keys(y).length && Object.keys(x).every(key => same(x[key], y[key]));
}
export function editable(draft: Draft): Editable { return { source_unit: draft.source_unit, job_default_key: draft.job_default_key, values: draft.values }; }
export function unitDefaults(refs: References, key: string, kind: Kind): Values {
  const row = refs.units.find(x => x.key === key);
  if (!row) return {};
  const keys = new Set(unitDefaultKeys);
  return { ...Object.fromEntries(Object.entries(row).filter(([field]) => keys.has(field))), nama_unit: row.unit, kota_ttd: /bogor|tcb/i.test(row.unit) ? 'Bogor' : 'Bekasi', saksi2_jabatan: kind === 'guru' ? `Kepala ${row.unit}` : 'HR Manager Yayasan Bina Talenta Tunas Bangsa Karya Mandiri' };
}
export function initialValues(employee: Employee, refs: References): Editable {
  const kind = employee.pkwt_type as Kind;
  const values: Values = { nama: employee.full_name, nip: '', jabatan: employee.job_title ?? '', tgl_lahir: employee.date_of_birth ?? '', tambahan_mode: 'tambah' };
  const unit = refs.units.find(x => x.unit.trim().toLowerCase() === employee.branch_name?.trim().toLowerCase());
  const result: Editable = { values, source_unit: unit?.key ?? null, job_default_key: null };
  if (unit) {
    Object.assign(values, unitDefaults(refs, unit.key, kind));
    const matches = refs.jobs.filter(x => x.unit.trim().toLowerCase() === unit.unit.trim().toLowerCase() && (x.division || '(Umum)').trim().toLowerCase() === (employee.division_name || '(Umum)').trim().toLowerCase() && x.title.trim().toLowerCase() === employee.job_title?.trim().toLowerCase() && x.pkwt_type === kind);
    if (matches.length === 1) { result.job_default_key = matches[0].key; Object.assign(values, { jabatan: matches[0].title, jobdesk: matches[0].jobdesk }); }
  }
  return result;
}
