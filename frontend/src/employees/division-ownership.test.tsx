import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';

const branches = [
  { id: '10000000-0000-0000-0000-000000000001', name: 'KURI' },
  { id: '10000000-0000-0000-0000-000000000002', name: 'Sekolah' },
];
const divisions = [
  { id: '20000000-0000-0000-0000-000000000001', name: 'Marketing', branch: branches[0].id, branch_name: branches[0].name, kinerja_enabled: false, pelimpahan_enabled: false },
  { id: '20000000-0000-0000-0000-000000000002', name: 'Marketing', branch: branches[1].id, branch_name: branches[1].name, kinerja_enabled: false, pelimpahan_enabled: false },
  { id: '20000000-0000-0000-0000-000000000003', name: 'Terapi', branch: branches[0].id, branch_name: branches[0].name, kinerja_enabled: false, pelimpahan_enabled: false },
];
afterEach(() => vi.unstubAllGlobals());
function setup() {
  let employee = { id: '00000000-0000-0000-0000-000000000001', employee_code: '0009', full_name: 'Synthetic Employee', branch: branches[0].id, branch_name: branches[0].name, division: divisions[0].id, division_name: 'Marketing' };
  const writes: unknown[] = [];
  vi.stubGlobal('fetch', vi.fn(async (path: string, init?: RequestInit) => {
    if (path.endsWith('/me/')) return Response.json({ id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: true } });
    if (path.endsWith('/csrf/')) return Response.json({ csrfToken: 'valid' });
    if (path === '/api/organization/branches/') return Response.json(branches);
    if (path === '/api/organization/divisions/') return Response.json(divisions);
    if (init?.method === 'PATCH') { const input = JSON.parse(String(init.body)); writes.push(input); employee = { ...employee, ...input }; }
    return Response.json(employee);
  }));
  render(<App initialEntries={['/employees/' + employee.id + '/edit']} />);
  return { user: userEvent.setup(), writes };
}

test('changing Cabang resets Divisi and offers only divisions owned by the selected Cabang', async () => {
  const { user, writes } = setup();
  await screen.findByRole('heading', { name: 'Ubah data pegawai' });
  const division = screen.getByRole('combobox', { name: 'Divisi' });
  await waitFor(() => expect(division).toBeEnabled());
  expect(within(division).getAllByRole('option').map(option => (option as HTMLOptionElement).value)).toEqual(['', divisions[0].id, divisions[2].id]);
  await user.selectOptions(screen.getByRole('combobox', { name: 'Cabang' }), branches[1].id);
  expect(division).toHaveValue('');
  expect(within(division).getAllByRole('option').map(option => (option as HTMLOptionElement).value)).toEqual(['', divisions[1].id]);
  await user.selectOptions(division, divisions[1].id);
  await user.click(screen.getByRole('button', { name: 'Simpan perubahan' }));
  await screen.findByRole('heading', { name: 'Synthetic Employee' });
  expect(writes).toEqual([{ branch: branches[1].id, division: divisions[1].id }]);
});

test('clearing Cabang also clears Divisi in the same employee update', async () => {
  const { user, writes } = setup();
  await screen.findByRole('heading', { name: 'Ubah data pegawai' });
  const branch = screen.getByRole('combobox', { name: 'Cabang' });
  await waitFor(() => expect(branch).toBeEnabled());
  await user.selectOptions(branch, '');
  expect(screen.getByRole('combobox', { name: 'Divisi' })).toBeDisabled();
  expect(screen.getByRole('combobox', { name: 'Divisi' })).toHaveValue('');
  await user.click(screen.getByRole('button', { name: 'Simpan perubahan' }));
  await screen.findByRole('heading', { name: 'Synthetic Employee' });
  expect(writes).toEqual([{ branch: null, division: null }]);
});
