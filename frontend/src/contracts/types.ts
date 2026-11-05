import { ApiError } from '../api/client';
export type Kind = 'yayasan' | 'guru' | 'klinik_umum';
export type Values = Record<string, string>;
export type Field = { key: string; label: string; group: string; kind: 'text' | 'textarea' | 'date' | 'number' | 'choice'; choices: string[]; max_length: number; required_for_generation: boolean };
export type References = { available: boolean; version: string | null; templates: Record<string, { sha256: string }>; units: Values[]; jobs: Values[]; fields: Record<Kind, Field[]> };
export type Metadata = { id: string; employee: string; pkwt_type: Kind; revision: number; reference_version: string; template_sha256: string; created_at: string; updated_at: string };
export type Draft = Metadata & { values: Values; employee_snapshot: Record<string, string | null>; source_unit: string | null; job_default_key: string | null };
export type Receipt = { id: string; draft: string; revision: number; template_sha256: string; filename: string; content_sha256: string; generated_at: string; download_url: string };
export const unitDefaultKeys = ['pihak1_nama', 'alamat_unit', 'unit_kelurahan', 'unit_kecamatan', 'unit_kota', 'unit_provinsi', 'unit_kodepos', 'hari_kerja_jml', 'hari_kerja_rentang', 'jam_sen_jum', 'jam_sabtu_jam', 'jam_ist', 'jam_ist_jumat'];
const unitCatalogKeys = new Set([...unitDefaultKeys, 'key', 'unit', 'jam_minggu_jml__usang']);
const jobCatalogKeys = new Set(['key', 'unit', 'division', 'title', 'pkwt_type', 'jobdesk', 'source_row']);
export const kinds: Kind[] = ['yayasan', 'guru', 'klinik_umum'];
export const mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const hash = /^[0-9a-f]{64}$/;
function invalid(write = false): never { throw new ApiError('protocol', 200, null, write ? 'uncertain' : null); }
function object(value: unknown): value is Record<string, unknown> { return !!value && typeof value === 'object' && !Array.isArray(value); }
function strings(value: unknown): value is Values { return object(value) && Object.values(value).every(x => typeof x === 'string'); }
function nullable(value: unknown): value is string | null { return value === null || typeof value === 'string'; }
function metadata(value: unknown): value is Metadata {
  if (!object(value)) return false;
  return typeof value.id === 'string' && uuid.test(value.id) && typeof value.employee === 'string' && uuid.test(value.employee) && kinds.includes(value.pkwt_type as Kind) && Number.isInteger(value.revision) && Number(value.revision) > 0 && typeof value.reference_version === 'string' && typeof value.template_sha256 === 'string' && hash.test(value.template_sha256) && typeof value.created_at === 'string' && typeof value.updated_at === 'string';
}
export function decodeDraft(value: unknown, write = false): Draft {
  if (!metadata(value)) return invalid(write);
  const x = value as Draft;
  if (!strings(x.values) || !nullable(x.source_unit) || !nullable(x.job_default_key) || !object(x.employee_snapshot) || !Object.values(x.employee_snapshot).every(nullable)) return invalid(write);
  return x;
}
export function decodeReceipt(value: unknown, write = false): Receipt {
  if (!object(value)) return invalid(write);
  const x = value as Receipt;
  if (typeof x.id !== 'string' || !uuid.test(x.id) || typeof x.draft !== 'string' || !uuid.test(x.draft) || !Number.isInteger(x.revision) || x.revision < 1 || typeof x.template_sha256 !== 'string' || !hash.test(x.template_sha256) || typeof x.content_sha256 !== 'string' || !hash.test(x.content_sha256) || typeof x.filename !== 'string' || typeof x.generated_at !== 'string' || x.download_url !== `/api/contract-documents/${x.id}/download/`) return invalid(write);
  return x;
}
export function decodeDocuments(value: unknown): Receipt[] {
  if (!object(value) || !Array.isArray(value.results)) return invalid();
  return value.results.map(x => decodeReceipt(x));
}
export function decodeDraftList(value: unknown): { results: Metadata[]; count: number; page: number } {
  if (!object(value) || !Array.isArray(value.results) || !value.results.every(metadata) || !Number.isInteger(value.count) || Number(value.count) < 0 || !Number.isInteger(value.page) || Number(value.page) < 1) return invalid();
  return value as { results: Metadata[]; count: number; page: number };
}
export function decodeReferences(value: unknown): References {
  if (!object(value)) return invalid();
  const x = value as References;
  if (typeof x.available !== 'boolean' || !nullable(x.version) || !object(x.templates) || !Array.isArray(x.units) || !x.units.every(strings) || !Array.isArray(x.jobs) || !x.jobs.every(strings) || !object(x.fields)) return invalid();
  if (x.units.some(row => !row.key || !row.unit || Object.keys(row).some(key => !unitCatalogKeys.has(key))) || x.jobs.some(row => Object.keys(row).some(key => !jobCatalogKeys.has(key)) || !row.key || !row.unit || !row.title || !row.jobdesk || !kinds.includes(row.pkwt_type as Kind))) return invalid();
  for (const kind of kinds) {
    if (!Array.isArray(x.fields[kind]) || !x.fields[kind].every(f => object(f) && typeof f.key === 'string' && typeof f.label === 'string' && typeof f.group === 'string' && ['text', 'textarea', 'date', 'number', 'choice'].includes(f.kind) && Number.isInteger(f.max_length) && f.max_length > 0 && Array.isArray(f.choices) && f.choices.every(c => typeof c === 'string') && typeof f.required_for_generation === 'boolean')) return invalid();
    if (x.available && (!x.version || !x.templates[kind] || !hash.test(x.templates[kind].sha256))) return invalid();
  }
  return x;
}
