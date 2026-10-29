export const employmentStatuses = [
  { value: '', label: 'Belum diisi' },
  { value: 'kontrak', label: 'Kontrak' },
  { value: 'freelance', label: 'Freelance' },
  { value: 'magang', label: 'Magang' },
  { value: 'permanen', label: 'Permanen' },
] as const;
export const pkwtTypes = [
  { value: '', label: 'Belum diisi' },
  { value: 'klinik_umum', label: 'Klinik Umum' },
  { value: 'guru', label: 'Guru' },
  { value: 'yayasan', label: 'Yayasan' },
] as const;
export type EmploymentStatus = typeof employmentStatuses[number]['value'];
export type PkwtType = typeof pkwtTypes[number]['value'];
export const classificationFields = [
  { key: 'employment_status', label: 'Status Kepegawaian', options: employmentStatuses },
  { key: 'pkwt_type', label: 'Tipe PKWT', options: pkwtTypes },
] as const;
export function validClassification(value: object, invalidFields: readonly string[] = []) {
  return classificationFields.every(field => {
    if (!(field.key in value)) return true;
    const code = (value as Record<string, unknown>)[field.key];
    return field.options.some(option => option.value === code) || (invalidFields.includes(field.key) && typeof code === 'string');
  });
}
