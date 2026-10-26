import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { expect, test } from 'vitest';
import { EmployeeTable } from './EmployeeTable';

const employees = [
  { id: 'z', employee_code: '0010', full_name: 'Zulu', branch: 'a', branch_name: 'Cabang A', division: 'd', division_name: 'Marketing', date_of_birth: '1995-01-01' },
  { id: 'a', employee_code: '0002', full_name: 'Alpha', branch: 'a', branch_name: 'Cabang A', division: 'd', division_name: 'Marketing', date_of_birth: null },
  { id: 'b', employee_code: '0001', full_name: 'Beta', branch: 'b', branch_name: 'Cabang B', division: null, division_name: null, date_of_birth: '2000-01-01' },
];
const names = () => screen.getAllByRole('link').map(link => link.textContent);

test('sorts naturally in All and within groups, leaving blanks last in either direction', async () => {
  render(<MemoryRouter><EmployeeTable employees={employees} showPrivate /></MemoryRouter>);
  const user = userEvent.setup();
  const grouping = screen.getByRole('combobox', { name: 'Grouping' });
  expect(within(grouping).getAllByRole('option').map(option => option.textContent)).toEqual(['Cabang/Divisi', 'Cabang', 'Divisi', 'All']);
  expect(grouping).toHaveValue('both');
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
  await user.selectOptions(grouping, 'none');
  expect(names()).toEqual(['Beta', 'Alpha', 'Zulu']);
  const sort = screen.getByRole('combobox', { name: 'Sort by' });
  await user.selectOptions(sort, 'full_name');
  expect(names()).toEqual(['Alpha', 'Beta', 'Zulu']);
  await user.click(screen.getByRole('button', { name: 'Asc: urutan menaik' }));
  expect(names()).toEqual(['Zulu', 'Beta', 'Alpha']);
  await user.selectOptions(grouping, 'both');
  expect(names()).toEqual(['Zulu', 'Alpha', 'Beta']);
  await user.selectOptions(grouping, 'none');
  await user.selectOptions(sort, 'date_of_birth');
  expect(names()).toEqual(['Beta', 'Zulu', 'Alpha']);
  await user.click(screen.getByRole('button', { name: 'Desc: urutan menurun' }));
  expect(names()).toEqual(['Zulu', 'Beta', 'Alpha']);
  expect(employees.map(employee => employee.full_name)).toEqual(['Zulu', 'Alpha', 'Beta']);
});

test('manager sorting only exposes identity fields', () => {
  render(<MemoryRouter><EmployeeTable employees={employees} showPrivate={false} /></MemoryRouter>);
  expect(within(screen.getByRole('combobox', { name: 'Sort by' })).getAllByRole('option').map(option => option.textContent)).toEqual(['ID Karyawan', 'Nama lengkap']);
});
