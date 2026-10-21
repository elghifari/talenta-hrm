import { ApiError, errorText, type apiRequest } from '../../api/client';

export type ImportStatus = 'new' | 'update' | 'unchanged' | 'error';
export type ImportValues = Record<string, string | null>;
export type ImportRow = {
  row: number; employee_code: string; full_name: string; status: ImportStatus;
  current: ImportValues | null; incoming: ImportValues; changes: string[];
  errors: Record<string, string[]>;
};
export type ImportBatch = {
  id: string; state: 'pending' | 'committed'; expires_at: string;
  rows: ImportRow[]; summary: Record<ImportStatus, number>;
};
const statuses: ImportStatus[] = ['new', 'update', 'unchanged', 'error'];
function values(value: unknown) {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value) && Object.values(value).every(item => item === null || typeof item === 'string'));
}
export function decodeBatch(value: unknown): ImportBatch {
  const batch = value as ImportBatch | null;
  if (!batch || typeof batch.id !== 'string' || !['pending', 'committed'].includes(batch.state) || typeof batch.expires_at !== 'string' || !batch.summary || !statuses.every(status => Number.isInteger(batch.summary[status]) && batch.summary[status] >= 0) || !Array.isArray(batch.rows) || batch.rows.length > 500) throw new ApiError('protocol', 200, null, null);
  for (const row of batch.rows) {
    if (!row || !Number.isInteger(row.row) || typeof row.employee_code !== 'string' || typeof row.full_name !== 'string' || !statuses.includes(row.status) || (row.current !== null && !values(row.current)) || !values(row.incoming) || !Array.isArray(row.changes) || !row.changes.every(key => typeof key === 'string') || !row.errors || !Object.values(row.errors).every(error => Array.isArray(error) && error.every(text => typeof text === 'string'))) throw new ApiError('protocol', 200, null, null);
  }
  if (batch.state === 'pending' && Object.values(batch.summary).reduce((sum, count) => sum + count, 0) !== batch.rows.length) throw new ApiError('protocol', 200, null, null);
  return batch;
}
export async function previewCsv(request: typeof apiRequest, file: File, signal: AbortSignal) {
  const body = new FormData(); body.append('file', file);
  return decodeBatch(await request('/api/employees/import-preview/', { method: 'POST', body, signal }));
}
export async function confirmBatch(request: typeof apiRequest, id: string, signal: AbortSignal) {
  const value = await request('/api/employees/imports/' + encodeURIComponent(id) + '/confirm/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}', signal });
  try { const batch = decodeBatch(value); if (batch.state !== 'committed') throw new Error('Receipt missing'); return batch; }
  catch { throw new ApiError('protocol', 200, null, 'uncertain'); }
}
export function importError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 404 || error.status === 410) return 'Pratinjau tidak tersedia atau kedaluwarsa. Unggah CSV kembali.';
    if (error.status === 409) return 'Data berubah sejak pratinjau. Unggah CSV kembali untuk memeriksa perubahan terbaru.';
    if (error.status === 400 && error.body && typeof error.body === 'object') return Object.values(error.body).flat().filter(value => typeof value === 'string').join(' ') || 'CSV tidak valid. Periksa file lalu unggah kembali.';
  }
  return errorText(error);
}
