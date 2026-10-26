import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';

beforeEach(() => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value: function (this: HTMLDialogElement) { this.setAttribute('open', ''); } });
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value: function (this: HTMLDialogElement) { this.removeAttribute('open'); } });
});
afterEach(() => vi.unstubAllGlobals());
test('HR creates and renames choices then assigns the primary groups without changing identity fields', async () => {
  type Choice = { id: string; name: string; branch?: string; branch_name?: string };
  const branches: Choice[] = []; const divisions: Choice[] = [];
  let record: Record<string, unknown> = { id: '00000000-0000-0000-0000-000000000001', employee_code: '0001', full_name: 'Karyawan Contoh', branch: null, branch_name: null, division: null, division_name: null };
  const fetcher = vi.fn(async (path: string, init?: RequestInit) => {
    if (path.endsWith('/me/')) return Response.json({ id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: true } });
    if (path.endsWith('/csrf/')) return Response.json({ csrfToken: 'valid' });
    if (path.startsWith('/api/organization/')) {
      const choices = path.includes('/branches/') ? branches : divisions;
      if (init?.method === 'POST') { const input = JSON.parse(String(init.body)); const item = { id: path.includes('/branches/') ? '10000000-0000-0000-0000-000000000001' : '20000000-0000-0000-0000-000000000001', name: input.name, ...(choices === divisions ? { branch: input.branch, branch_name: branches.find(choice => choice.id === input.branch)?.name } : {}) }; choices.push(item); return Response.json(item, { status: 201 }); }
      if (init?.method === 'PATCH') { const input = JSON.parse(String(init.body)); branches[0].name = input.name; divisions.splice(0, divisions.length, ...input.divisions.map((row: Choice) => ({ ...row, id: row.id ?? '20000000-0000-0000-0000-000000000001', branch: branches[0].id, branch_name: branches[0].name }))); return Response.json({ branch: branches[0], divisions }); }
      return Response.json(choices);
    }
    if (init?.method === 'PATCH') { record = { ...record, ...JSON.parse(String(init.body)) }; record.branch_name = branches.find(item => item.id === record.branch)?.name ?? null; record.division_name = divisions.find(item => item.id === record.division)?.name ?? null; }
    return Response.json(path === '/api/employees/' ? [record] : record);
  });
  vi.stubGlobal('fetch', fetcher); const user = userEvent.setup();
  render(<App initialEntries={['/employees']} />);
  await user.click(await screen.findByRole('link', { name: 'Cabang & Divisi' }));
  expect(await screen.findByRole('heading', { name: 'Cabang dan Divisi' })).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Tambah cabang' }));
  await user.type(screen.getByLabelText('Nama cabang'), 'Cabang Contoh');
  await user.click(screen.getByRole('button', { name: 'Simpan cabang' }));
  expect(await screen.findByText('Cabang Contoh')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Edit cabang Cabang Contoh' }));
  await user.click(screen.getByRole('button', { name: 'Tambah divisi' }));
  await user.type(screen.getByLabelText('Nama divisi 1'), 'Pelayanan');
  await user.click(screen.getByRole('button', { name: 'Simpan perubahan' }));
  expect(await screen.findByText('Pelayanan')).toBeInTheDocument();
  const divisionWrite = fetcher.mock.calls.find(([path, init]) => path.endsWith('/structure/') && init?.method === 'PATCH')!;
  expect(JSON.parse(String(divisionWrite[1]?.body))).toMatchObject({ name: 'Cabang Contoh', divisions: [{ name: 'Pelayanan' }], deleted: [] });
  await user.click(screen.getByRole('button', { name: 'Edit cabang Cabang Contoh' }));
  const rename = screen.getByLabelText('Nama cabang');
  await user.clear(rename); await user.type(rename, 'Cabang Baru');
  await user.click(screen.getByRole('button', { name: 'Simpan perubahan' }));
  expect(await screen.findByText('Cabang Baru')).toBeInTheDocument();
  await user.click(screen.getByRole('link', { name: 'Data pegawai' }));
  await user.click(await screen.findByRole('link', { name: 'Karyawan Contoh' }));
  await user.click(await screen.findByRole('link', { name: 'Ubah data' }));
  await user.selectOptions(await screen.findByRole('combobox', { name: 'Cabang' }), branches[0].id);
  await user.selectOptions(screen.getByRole('combobox', { name: 'Divisi' }), divisions[0].id);
  await user.click(screen.getByRole('button', { name: 'Simpan perubahan' }));
  expect(await screen.findByRole('heading', { name: 'Karyawan Contoh' })).toBeInTheDocument();
  expect(screen.getByText('Cabang Baru')).toBeInTheDocument();
  expect(screen.getByText('Pelayanan')).toBeInTheDocument();
  const employeeWrite = fetcher.mock.calls.find(([path, init]) => path.startsWith('/api/employees/') && init?.method === 'PATCH')!;
  expect(JSON.parse(String(employeeWrite[1]?.body))).toEqual({ branch: branches[0].id, division: divisions[0].id });
});
