import { ApiError } from '../api/client';
export type Employee = { id: string; employee_code: string; full_name: string };
export type EmployeeInput = Pick<Employee, 'employee_code' | 'full_name'>;
export function decodeEmployee(value: unknown): Employee {
  const x = value as Employee | null;
  if (!x || typeof x.id !== 'string' || typeof x.employee_code !== 'string' || typeof x.full_name !== 'string') throw new ApiError('protocol', 200, null, null);
  return x;
}
export function decodeEmployees(value: unknown): Employee[] {
  if (!Array.isArray(value)) throw new ApiError('protocol', 200, null, null);
  return value.map(decodeEmployee);
}
