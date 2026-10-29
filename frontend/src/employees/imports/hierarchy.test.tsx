import userEvent from '@testing-library/user-event';
import { render, screen, within } from '@testing-library/react';
import { expect, test } from 'vitest';
import { ImportComparison } from './ImportComparison';
import type { ImportRow } from './api';

const row: ImportRow = {
  row: 2, employee_code: '0010', full_name: 'Karyawan Hierarki', status: 'update',
  current: { employee_code: '0010', full_name: 'Karyawan Hierarki', branch: '11111111-1111-1111-1111-111111111111', branch_name: 'Cabang Lama', division: '22222222-2222-2222-2222-222222222222', division_name: 'Pelayanan Lama' },
  incoming: { employee_code: '0010', full_name: 'Karyawan Hierarki', branch: '33333333-3333-3333-3333-333333333333', branch_name: 'Cabang Baru', division: '44444444-4444-4444-4444-444444444444', division_name: 'Pelayanan Baru' },
  changes: ['branch', 'division'], errors: {},
};

test('hierarchy changes compare Cabang and Divisi names instead of identifiers', async () => {
  const user = userEvent.setup();
  render(<ul><ImportComparison row={row} /></ul>);
  expect(screen.getByText('2 perubahan: Cabang, Divisi')).toBeInTheDocument();
  await user.click(screen.getByText('Lihat perubahan'));
  const branch = screen.getByRole('rowheader', { name: 'Cabang' }).closest('tr')!;
  expect(within(branch).getByText('Cabang Lama')).toBeVisible();
  expect(within(branch).getByText('Cabang Baru')).toBeVisible();
  const division = screen.getByRole('rowheader', { name: 'Divisi' }).closest('tr')!;
  expect(within(division).getByText('Pelayanan Lama')).toBeVisible();
  expect(within(division).getByText('Pelayanan Baru')).toBeVisible();
  expect(screen.queryByText(row.incoming.branch!)).not.toBeInTheDocument();
  expect(screen.queryByRole('rowheader', { name: 'ID Karyawan' })).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Lihat semua kolom' }));
  expect(screen.getByRole('rowheader', { name: 'ID Karyawan' })).toBeVisible();
});

test('invalid names and hierarchy errors stay visible and escaped in the CSV preview', () => {
  const invalid = { ...row, status: 'error' as const, current: null, incoming: { ...row.incoming, branch_name: '<img src=x>', division_name: 'Tidak Ada' }, errors: { branch: ['Cabang belum terdaftar.'], division: ['Divisi belum terdaftar di cabang ini.'] } };
  const { container } = render(<ul><ImportComparison row={invalid} /></ul>);
  expect(screen.getByText('Cabang: Cabang belum terdaftar.')).toBeVisible();
  expect(screen.getByText('Divisi: Divisi belum terdaftar di cabang ini.')).toBeVisible();
  expect(screen.getByText('<img src=x>')).toBeVisible();
  expect(screen.getByText('Tidak Ada')).toBeVisible();
  expect(container.querySelector('img')).toBeNull();
});
