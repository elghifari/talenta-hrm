import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { expect, test } from 'vitest';
import { EmployeeTable } from './EmployeeTable';

test('grouping offers the four modes and adjacent dot-separated counts', async () => {
  const employees = ['A', 'B'].map((name, index) => ({ id: String(index), employee_code: '000' + index, full_name: 'Synthetic ' + name, branch: 'branch', branch_name: 'Cabang Contoh', division: 'division', division_name: 'Marketing' }));
  render(<MemoryRouter><EmployeeTable employees={employees} showPrivate /></MemoryRouter>);
  const user = userEvent.setup();
  const grouping = screen.getByRole('combobox', { name: 'Grouping' });
  expect(grouping).toHaveValue('both');
  expect(screen.queryByText('Kelompokkan')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Cabang Contoh · 2 karyawan' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Marketing · 2 karyawan' })).toBeInTheDocument();
  await user.selectOptions(grouping, 'none');
  expect(screen.getByRole('option', { name: 'All' })).toHaveProperty('selected', true);
  expect(screen.queryByRole('button', { name: 'Tutup semua' })).not.toBeInTheDocument();
  expect(screen.getByRole('columnheader', { name: 'Cabang' })).toBeInTheDocument();
  await user.selectOptions(grouping, 'both');
  await user.click(screen.getByRole('button', { name: 'Marketing · 2 karyawan' }));
  expect(screen.queryByRole('link', { name: 'Synthetic A' })).not.toBeInTheDocument();
});
