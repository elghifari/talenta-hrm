import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';

const fields = { date_of_birth: '1996-04-12', job_title: 'Terapis', level: 'Level 1', start_date: '2024-01-01', contract_expiry: '2027-12-31' };
const labels = { date_of_birth: 'Tanggal lahir', job_title: 'Jabatan', level: 'Level', start_date: 'Tanggal masuk', contract_expiry: 'Kontrak berakhir' };
afterEach(() => vi.unstubAllGlobals());
function setup(route: 'new' | 'edit' | 'detail' = 'edit', writable = true) {
  let record = { id: '00000000-0000-0000-0000-000000000009', employee_code: '0009', full_name: 'Synthetic Employee', ...fields };
  const writes: Record<string, unknown>[] = [];
  vi.stubGlobal('fetch', vi.fn(async (path: string, init?: RequestInit) => {
    if (path.endsWith('/me/')) return Response.json({ id: 1, email: 'synthetic@example.test', capabilities: { employees_read: true, employees_write: writable } });
    if (path.endsWith('/csrf/')) return Response.json({ csrfToken: 'valid' });
    if (path.startsWith('/api/organization/')) return Response.json([]);
    if (init?.method === 'POST' || init?.method === 'PATCH') { const body = JSON.parse(String(init.body)); writes.push(body); record = { ...record, ...body }; }
    return Response.json(record);
  }));
  render(<App initialEntries={[route === 'new' ? '/employees/new' : '/employees/' + record.id + (route === 'edit' ? '/edit' : '')]} />);
  return { writes, user: userEvent.setup() };
}

test('individual edit exposes all profile fields and clears only changed fields', async () => {
  const { writes, user } = setup();
  await screen.findByRole('heading', { name: 'Ubah data pegawai' });
  expect(screen.getByRole('button', { name: 'Simpan perubahan' })).toBeDisabled();
  for (const [key, label] of Object.entries(labels)) {
    expect(screen.getByLabelText(label)).toHaveValue(fields[key as keyof typeof fields]);
    fireEvent.change(screen.getByLabelText(label), { target: { value: '' } });
  }
  await user.click(screen.getByRole('button', { name: 'Simpan perubahan' }));
  await screen.findByRole('heading', { name: 'Synthetic Employee' });
  expect(writes).toEqual([{ date_of_birth: null, job_title: '', level: '', start_date: null, contract_expiry: null }]);
  expect(screen.getByText('Tanggal lahir')).toBeInTheDocument();
  const crumbs = screen.getByRole('navigation', { name: 'Breadcrumb' });
  expect(within(crumbs).getByRole('link', { name: 'Data pegawai' })).toHaveAttribute('href', '/employees');
});

test('individual create sends entered profile fields', async () => {
  const { writes, user } = setup('new');
  await screen.findByRole('heading', { name: 'Tambah pegawai' });
  await user.type(screen.getByLabelText('Kode pegawai'), '0009');
  await user.type(screen.getByLabelText('Nama lengkap'), 'Synthetic Employee');
  for (const [key, label] of Object.entries(labels)) fireEvent.change(screen.getByLabelText(label), { target: { value: fields[key as keyof typeof fields] } });
  await user.click(screen.getByRole('button', { name: 'Simpan pegawai' }));
  await screen.findByRole('heading', { name: 'Synthetic Employee' });
  expect(writes).toEqual([{ employee_code: '0009', full_name: 'Synthetic Employee', ...fields }]);
});

test('manager detail does not render private profile fields or organization management navigation', async () => {
  setup('detail', false);
  await screen.findByRole('heading', { name: 'Synthetic Employee' });
  for (const label of Object.values(labels)) expect(screen.queryByText(label)).not.toBeInTheDocument();
  expect(screen.queryByRole('link', { name: 'Cabang & Divisi' })).not.toBeInTheDocument();
});
