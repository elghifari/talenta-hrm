import { expect, test } from 'vitest';
import { unitDefaults } from './api';
import { decodeReferences, type References } from './types';
const fields = ['pihak1_nama', 'nama', 'nip', 'gaji_pokok'].map(key => ({ key, label: key, group: 'Group', kind: 'text' as const, choices: [], max_length: 1000, required_for_generation: true }));
const refs: References = { available: false, version: null, templates: {}, jobs: [], units: [{ key: 'School', unit: 'School', pihak1_nama: 'Foundation', nama: 'Catalog Name', nip: '001234', gaji_pokok: '9000000' }], fields: { yayasan: fields, guru: [], klinik_umum: [] } };
test('Unit defaults never populate identity, NIP or money even with extra editable fields', () => {
  const values = unitDefaults(refs, 'School', 'yayasan');
  expect(values).not.toHaveProperty('nama');
  expect(values).not.toHaveProperty('nip');
  expect(values).not.toHaveProperty('gaji_pokok');
  expect(values.pihak1_nama).toBe('Foundation');
});
test('reference decoder rejects unknown Unit-owned fields', () => {
  expect(() => decodeReferences(refs)).toThrow();
});
