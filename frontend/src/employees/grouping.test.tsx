import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';

afterEach(() => vi.unstubAllGlobals());
const records = [
  { id: '00000000-0000-0000-0000-000000000001', employee_code: '0001', full_name: 'Karyawan A', branch: '10000000-0000-0000-0000-000000000001', branch_name: 'Unit A', division: '20000000-0000-0000-0000-000000000001', division_name: 'Pelayanan', job_title: 'Terapis', level: 'Level 1', date_of_birth: '1996-04-12', start_date: '2024-01-01', contract_expiry: '2027-12-31' },
  { id: '00000000-0000-0000-0000-000000000002', employee_code: '0002', full_name: 'Karyawan B', branch: '10000000-0000-0000-0000-000000000002', branch_name: 'Unit B', division: '20000000-0000-0000-0000-000000000002', division_name: 'Pelayanan' },
  { id: '00000000-0000-0000-0000-000000000003', employee_code: '0003', full_name: 'Belum dikelompokkan', branch: null, branch_name: null, division: null, division_name: null },
];

test('full table groups by primary Unit and Divisi and filters without duplicating employees', async () => {
  vi.stubGlobal('fetch', vi.fn(async (path: string) => Response.json(path.endsWith('/me/') ? { id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: true } } : records)));
  const user = userEvent.setup(); render(<App initialEntries={['/employees']} />);
  const grouping = await screen.findByRole('combobox', { name: 'Grouping' });
  expect(grouping).toHaveValue('both');
  const unit = await screen.findByRole('button', { name: /Unit A.*1 karyawan/ });
  expect(screen.getByRole('button', { name: /Unit belum ditentukan/ })).toBeInTheDocument();
  await user.click(unit);
  expect(screen.queryByRole('link', { name: 'Karyawan A' })).not.toBeInTheDocument();
  expect(screen.queryByText('3 dari 3 karyawan')).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: /Unit A.*1 karyawan/ }));
  await user.selectOptions(screen.getByLabelText('Unit', { exact: true }), records[0].branch!);
  expect(screen.getByRole('link', { name: 'Karyawan A' })).toBeInTheDocument();
  expect(screen.queryByRole('link', { name: 'Karyawan B' })).not.toBeInTheDocument();
  expect(screen.getByRole('cell', { name: 'Terapis' })).toBeInTheDocument();
  await user.selectOptions(grouping, 'none');
  expect(screen.getByRole('columnheader', { name: 'Unit' })).toBeInTheDocument();
  expect(screen.getByRole('columnheader', { name: 'Divisi' })).toBeInTheDocument();
  await user.type(screen.getByLabelText('Cari pegawai'), 'no-match');
  expect(screen.getByRole('heading', { name: 'Tidak ada pegawai yang cocok' })).toBeInTheDocument();
  await user.click(within(screen.getByRole('region', { name: 'Hasil pencarian kosong' })).getByRole('button', { name: 'Reset filter' }));
  expect(screen.getByRole('link', { name: 'Karyawan B' })).toBeInTheDocument();
});

test('same-named divisions are distinguished by their Unit in global filters and division-only groups', async () => {
  vi.stubGlobal('fetch', vi.fn(async (path: string) => Response.json(path.endsWith('/me/') ? { id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: true } } : records)));
  const user = userEvent.setup(); render(<App initialEntries={['/employees']} />);
  const grouping = await screen.findByRole('combobox', { name: 'Grouping' });
  const division = screen.getByRole('combobox', { name: 'Divisi' });
  expect(within(division).getByRole('option', { name: 'Pelayanan (Unit A)' })).toHaveValue(records[0].division!);
  expect(within(division).getByRole('option', { name: 'Pelayanan (Unit B)' })).toHaveValue(records[1].division!);
  await user.selectOptions(grouping, 'division');
  expect(screen.getByRole('button', { name: /Pelayanan \(Unit A\).*1 karyawan/ })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Pelayanan \(Unit B\).*1 karyawan/ })).toBeInTheDocument();
  await user.selectOptions(division, records[1].division!);
  expect(screen.getByRole('link', { name: 'Karyawan B' })).toBeInTheDocument();
  expect(screen.queryByRole('link', { name: 'Karyawan A' })).not.toBeInTheDocument();
  await user.selectOptions(screen.getByRole('combobox', { name: 'Unit' }), records[0].branch!);
  expect(division).toHaveValue('');
  expect(within(division).queryByRole('option', { name: 'Pelayanan (Unit B)' })).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Karyawan A' })).toBeInTheDocument();
});
