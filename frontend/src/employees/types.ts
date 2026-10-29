import { ApiError } from '../api/client';
import { validClassification, type EmploymentStatus, type PkwtType } from './classification';
export type Employee = {
  id: string; employee_code: string; full_name: string;
  branch?: string | null; branch_name?: string | null;
  division?: string | null; division_name?: string | null;
  date_of_birth?: string | null; job_title?: string; level?: string;
  start_date?: string | null; contract_expiry?: string | null;
  employment_status?: EmploymentStatus; pkwt_type?: PkwtType;
};
export type EmployeeInput = Pick<Employee, 'employee_code' | 'full_name' | 'branch' | 'division' | 'date_of_birth' | 'job_title' | 'level' | 'start_date' | 'contract_expiry' | 'employment_status' | 'pkwt_type'>;
export function decodeEmployee(value: unknown): Employee {
  const x = value as Employee | null;
  if (!x || typeof x.id !== 'string' || typeof x.employee_code !== 'string' || typeof x.full_name !== 'string') throw new ApiError('protocol', 200, null, null);
  for (const field of ['branch', 'branch_name', 'division', 'division_name', 'date_of_birth', 'job_title', 'level', 'start_date', 'contract_expiry'] as const) {
    if (x[field] !== undefined && x[field] !== null && typeof x[field] !== 'string') throw new ApiError('protocol', 200, null, null);
  }
  if (!validClassification(x)) throw new ApiError('protocol', 200, null, null);
  return x;
}
export function decodeEmployees(value: unknown): Employee[] {
  if (!Array.isArray(value)) throw new ApiError('protocol', 200, null, null);
  return value.map(decodeEmployee);
}
