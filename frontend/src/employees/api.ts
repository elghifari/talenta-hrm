import { ApiError, type apiRequest } from '../api/client';
import { decodeEmployee, type EmployeeInput } from './types';
export function changedFields(original: EmployeeInput, current: EmployeeInput): Partial<EmployeeInput> {
  const changes: Partial<EmployeeInput> = {};
  if (original.employee_code !== current.employee_code) changes.employee_code = current.employee_code;
  if (original.full_name !== current.full_name) changes.full_name = current.full_name;
  if ('branch' in current && (original.branch ?? null) !== (current.branch ?? null)) changes.branch = current.branch ?? null;
  if ('division' in current && (original.division ?? null) !== (current.division ?? null)) changes.division = current.division ?? null;
  for (const field of ['date_of_birth', 'start_date', 'contract_expiry'] as const) if (field in current && (original[field] ?? null) !== (current[field] ?? null)) changes[field] = current[field] ?? null;
  for (const field of ['job_title', 'level'] as const) if (field in current && (original[field] ?? '') !== (current[field] ?? '')) changes[field] = current[field] ?? '';
  if ('employment_status' in current && (original.employment_status ?? '') !== (current.employment_status ?? '')) changes.employment_status = current.employment_status ?? '';
  if ('pkwt_type' in current && (original.pkwt_type ?? '') !== (current.pkwt_type ?? '')) changes.pkwt_type = current.pkwt_type ?? '';
  return changes;
}
export async function saveEmployee(request: typeof apiRequest, input: Partial<EmployeeInput>, id?: string, signal?: AbortSignal) {
  const value = await request<unknown>(id ? '/api/employees/' + encodeURIComponent(id) + '/' : '/api/employees/', {
    method: id ? 'PATCH' : 'POST', signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
  });
  try { return decodeEmployee(value); }
  catch { throw new ApiError('protocol', id ? 200 : 201, null, 'uncertain'); }
}
