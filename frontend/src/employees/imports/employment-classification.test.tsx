import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test } from 'vitest';
import { ImportComparison } from './ImportComparison';
import { decodeBatch, type ImportRow, type ImportValues } from './api';

const row: ImportRow = { row: 2, employee_code: '0019', full_name: 'Synthetic Classification', status: 'update', current: { employment_status: 'kontrak', pkwt_type: 'klinik_umum' }, incoming: { employment_status: 'permanen', pkwt_type: '' }, changes: ['employment_status', 'pkwt_type'], errors: {} };
const batch = (item: ImportRow) => ({ id: 'batch', state: 'pending', expires_at: '2026-11-01T00:00:00Z', rows: [item], summary: { new: 0, update: 1, unchanged: 0, error: 0 } });

test('import comparison labels changed and cleared classification rather than wire codes', async () => {
  render(<ul><ImportComparison row={row} /></ul>);
  await userEvent.setup().click(screen.getByText('Lihat perubahan'));
  const status = screen.getByRole('rowheader', { name: 'Status Kepegawaian' }).closest('tr')!;
  expect(within(status).getByText('Kontrak')).toBeVisible();
  expect(within(status).getByText('Permanen')).toBeVisible();
  const type = screen.getByRole('rowheader', { name: 'Tipe PKWT' }).closest('tr')!;
  expect(within(type).getByText('Klinik Umum')).toBeVisible();
  expect(within(type).getByText('Belum diisi')).toBeVisible();
  expect(screen.queryByText('klinik_umum')).not.toBeInTheDocument();
});

test('new rows render classification labels and old receipts omit unavailable classification rows', async () => {
  const { rerender } = render(<ul><ImportComparison row={{ ...row, status: 'new', current: null, incoming: { employment_status: 'kontrak', pkwt_type: 'guru' } }} /></ul>);
  await userEvent.setup().click(screen.getByText('Lihat data'));
  expect(screen.getByText('Guru')).toBeVisible();
  rerender(<ul><ImportComparison row={{ ...row, status: 'unchanged', current: {}, incoming: {}, changes: [] }} /></ul>);
  expect(screen.queryByRole('rowheader', { name: 'Status Kepegawaian' })).not.toBeInTheDocument();
  expect(screen.queryByRole('rowheader', { name: 'Tipe PKWT' })).not.toBeInTheDocument();
});

test.each<ImportValues>([{ employment_status: 'invalid' }, { employment_status: null }, { pkwt_type: 'invalid' }, { pkwt_type: null }])('import decoder rejects malformed known classification %j', incoming => {
  expect(() => decodeBatch(batch({ ...row, incoming }))).toThrow();
  expect(() => decodeBatch(batch({ ...row, current: incoming }))).toThrow();
});

test('invalid CSV enum text remains visible with its field error rather than breaking preview decoding', () => {
  const invalid = { ...row, status: 'error' as const, incoming: { employment_status: '<img src=x>', pkwt_type: 'guru' }, errors: { employment_status: ['Status tidak valid.'] } };
  const decoded = decodeBatch({ ...batch(invalid), summary: { new: 0, update: 0, unchanged: 0, error: 1 } });
  const { container } = render(<ul><ImportComparison row={decoded.rows[0]} /></ul>);
  expect(screen.getByText('Status Kepegawaian: Status tidak valid.')).toBeVisible();
  expect(screen.getByText('<img src=x>')).toBeVisible();
  expect(container.querySelector('img')).toBeNull();
});

test('import decoder accepts old receipts and valid classification codes', () => {
  expect(decodeBatch(batch({ ...row, current: {}, incoming: {} })).rows[0].incoming).toEqual({});
  expect(decodeBatch(batch(row)).rows[0].incoming).toEqual({ employment_status: 'permanen', pkwt_type: '' });
});
