import { ApiError, type apiRequest } from '../api/client';
import { decodeEmployee, type EmployeeInput } from './types';
export function changedFields(original: EmployeeInput, current: EmployeeInput): Partial<EmployeeInput> {
  const changes: Partial<EmployeeInput> = {};
  if (original.employee_code !== current.employee_code) changes.employee_code = current.employee_code;
  if (original.full_name !== current.full_name) changes.full_name = current.full_name;
  return changes;
}
export async function saveEmployee(request: typeof apiRequest, input: Partial<EmployeeInput>, id?: string, signal?: AbortSignal) {
  const value = await request<unknown>(id ? '/api/employees/' + encodeURIComponent(id) + '/' : '/api/employees/', {
    method: id ? 'PATCH' : 'POST', signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
  });
  try { return decodeEmployee(value); }
  catch { throw new ApiError('protocol', id ? 200 : 201, null, 'uncertain'); }
}
