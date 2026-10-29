import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';

const branch = { id: '10000000-0000-0000-0000-000000000001', name: 'Synthetic Branch' };
const division = { id: '20000000-0000-0000-0000-000000000001', name: 'Synthetic Division', branch: branch.id, branch_name: branch.name, kinerja_enabled: false, pelimpahan_enabled: false };
afterEach(() => vi.unstubAllGlobals());
function identity(writable: boolean) { return { id: 1, email: 'test@example.test', capabilities: { employees_read: true, employees_write: writable } }; }
function dateAfter(days: number) {
  const date = new Date(); date.setDate(date.getDate() + days);
  return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-');
}
function dashboard(writable = true, fail = false) {
  const records = [-1, 0, 30, 31, null].map((days, index) => ({ id: 'employee-' + index, employee_code: '000' + index, full_name: 'Synthetic ' + index, contract_expiry: days === null ? null : dateAfter(days) }));
  const fetcher = vi.fn(async (path: string) => {
    if (path.endsWith('/me/')) return Response.json(identity(writable));
    if (path === '/api/employees/') return fail ? Response.json({}, { status: 503 }) : Response.json(records);
    if (path.includes('/branches/')) return Response.json([branch]);
    if (path.includes('/divisions/')) return Response.json([division]);
    throw new Error('Unexpected request ' + path);
  });
  vi.stubGlobal('fetch', fetcher);
  render(<App initialEntries={['/personnel']} />);
  return fetcher;
}

test('Personnel shows complete totals and inclusive 30-day expiries without a root breadcrumb', async () => {
  dashboard();
  const employeeCard = await screen.findByRole('link', { name: /Karyawan\s*5/ });
  expect(employeeCard).toHaveAttribute('href', '/employees');
  expect(await screen.findByRole('link', { name: /Cabang\s*1/ })).toHaveAttribute('href', '/employees/groups');
  expect(await screen.findByRole('link', { name: /Divisi\s*1/ })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /Kontrak segera berakhir\s*2/ })).toHaveAttribute('href', '#contract-expiries');
  const table = screen.getByRole('table');
  expect(within(table).getAllByRole('link').map(link => link.textContent)).toEqual(['Synthetic 1', 'Synthetic 2']);
  expect(screen.queryByRole('navigation', { name: 'Breadcrumb' })).not.toBeInTheDocument();
});

test('manager overview omits private metrics and never requests organization totals', async () => {
  const fetcher = dashboard(false);
  await screen.findByRole('link', { name: /Karyawan\s*5/ });
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
  expect(screen.queryByText('Kontrak segera berakhir')).not.toBeInTheDocument();
  expect(fetcher.mock.calls.some(([path]) => path.includes('/organization/'))).toBe(false);
});

test('failed employee read is not displayed as zero employees', async () => {
  dashboard(true, true);
  expect(await screen.findByRole('alert')).toBeInTheDocument();
  expect(screen.queryByRole('link', { name: /Karyawan\s*\d/ })).not.toBeInTheDocument();
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
});

test('populated division deletion confirms impact and sends no write until Save', async () => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value: function (this: HTMLDialogElement) { this.setAttribute('open', ''); } });
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value: function (this: HTMLDialogElement) { this.removeAttribute('open'); } });
  const writes: Record<string, unknown>[] = [];
  let divisions = [division];
  vi.stubGlobal('fetch', vi.fn(async (path: string, init?: RequestInit) => {
    if (path.endsWith('/me/')) return Response.json(identity(true));
    if (path.endsWith('/csrf/')) return Response.json({ csrfToken: 'valid' });
    if (path.endsWith('/deletion-impact/')) return Response.json({ employee_count: 2 });
    if (init?.method === 'PATCH') { writes.push(JSON.parse(String(init.body))); divisions = []; return Response.json({ branch, divisions }); }
    return Response.json(path.includes('/branches/') ? [branch] : divisions);
  }));
  const user = userEvent.setup();
  render(<App initialEntries={['/employees/groups']} />);
  await user.click(await screen.findByRole('button', { name: 'Edit cabang Synthetic Branch' }));
  await user.click(screen.getByRole('button', { name: 'Hapus divisi Synthetic Division' }));
  await screen.findByText(/2 karyawan akan tetap di cabang/);
  await user.click(screen.getByRole('button', { name: 'Batal' }));
  expect(screen.getByLabelText('Nama divisi 1')).toHaveValue(division.name);
  expect(writes).toHaveLength(0);
  await user.click(screen.getByRole('button', { name: 'Hapus divisi Synthetic Division' }));
  await screen.findByText(/2 karyawan akan tetap di cabang/);
  expect(screen.getByRole('button', { name: 'Hapus divisi' })).toHaveClass('danger');
  await user.click(screen.getByRole('button', { name: 'Hapus divisi' }));
  expect(writes).toHaveLength(0);
  await user.click(screen.getByRole('button', { name: 'Simpan perubahan' }));
  await screen.findByText('Cabang tersimpan.');
  expect(writes).toHaveLength(1);
  expect(writes[0]).toMatchObject({ divisions: [], deleted: [{ id: division.id, employee_count: 2 }] });
});
