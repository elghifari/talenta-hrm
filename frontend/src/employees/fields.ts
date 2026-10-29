import { classificationFields } from './classification';
export const employeeFields = [
  { key: 'employee_code', label: 'ID Karyawan', type: 'text', maxLength: 64, required: true },
  { key: 'full_name', label: 'Nama lengkap', type: 'text', maxLength: 200, required: true },
  { key: 'date_of_birth', label: 'Tanggal lahir', type: 'date' },
  { key: 'job_title', label: 'Jabatan', type: 'text', maxLength: 200 },
  { key: 'level', label: 'Level', type: 'text', maxLength: 100 },
  { key: 'start_date', label: 'Tanggal masuk', type: 'date' },
  { key: 'contract_expiry', label: 'Kontrak berakhir', type: 'date' },
] as const;
export type EmployeeField = typeof employeeFields[number]['key'];
export function fieldLabel(key: string) { return [...employeeFields, ...classificationFields].find(field => field.key === key)?.label ?? 'Data karyawan'; }
export function fieldValue(value: string | null | undefined, key?: string) {
  const classification = classificationFields.find(field => field.key === key);
  if (classification) return classification.options.find(option => option.value === value)?.label ?? (value || 'Belum diisi');
  return value || 'Belum diisi';
}
