import type { Field } from './types';

export function contractFieldGroups(fields: Field[]) {
  const labels = [...new Set(fields.map(field => field.group))];
  return labels.map(label => {
    const entries = fields.filter(field => field.group === label);
    return { id: 'contract-section-' + entries[0].key, label, fields: entries };
  });
}

export type ContractSection = { id: string; label: string; filled: number; total: number; errors: number };
