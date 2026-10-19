import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';
const existing = { id: '00000000-0000-0000-0000-000000000001', employee_code: '0001', full_name: 'Pegawai Contoh A' };
afterEach(() => vi.unstubAllGlobals());
function mockServer(mode: 'success' | 'duplicate' | 'refetch-failed' = 'success') {
  let saved = false; let record = { ...existing };
  const fetcher = vi.fn(async (path: string, init?: RequestInit) => {
    if(path.endsWith('/me/')) return Response.json({ id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: true } });
    if(path.endsWith('/csrf/')) return Response.json({ csrfToken: 'valid' });
    if(init?.method === 'POST' || init?.method === 'PATCH') {
      if(mode === 'duplicate') return Response.json({ employee_code: ['Kode sudah digunakan.'] }, { status: 400 });
      record = { ...record, ...JSON.parse(String(init.body)) }; saved = true;
      return Response.json(record, { status: init.method === 'POST' ? 201 : 200 });
    }
    if(saved && mode === 'refetch-failed') return Response.json({}, { status: 503 });
    return Response.json(path === '/api/employees/' ? [record] : record);
  });
  vi.stubGlobal('fetch', fetcher); return fetcher;
}
test('HR creates a text code from list and reaches persisted detail', async () => {
  const server = mockServer(); const user = userEvent.setup(); render(<App initialEntries={['/employees']} />);
  await user.click(await screen.findByRole('link', { name: 'Tambah pegawai' }));
  await user.click(screen.getByRole('button', { name: 'Simpan pegawai' }));
  expect(await screen.findByText('Kode pegawai wajib diisi.')).toBeInTheDocument();
  await user.type(screen.getByLabelText('Kode pegawai'), '0099');
  await user.type(screen.getByLabelText('Nama lengkap'), 'Pegawai Contoh Baru');
  await user.click(screen.getByRole('button', { name: 'Simpan pegawai' }));
  expect(await screen.findByRole('heading', { name: 'Pegawai Contoh Baru' })).toBeInTheDocument();
  const post = server.mock.calls.find(c => c[1]?.method === 'POST')!;
  expect(JSON.parse(String(post[1]?.body))).toEqual({ employee_code: '0099', full_name: 'Pegawai Contoh Baru' });
});
test('edit sends only changed fields and untouched form cannot create an audit write', async () => {
  const server = mockServer(); const user = userEvent.setup(); render(<App initialEntries={['/employees/' + existing.id + '/edit']} />);
  const input = await screen.findByLabelText('Nama lengkap');
  expect(screen.getByRole('button', { name: 'Simpan perubahan' })).toBeDisabled();
  await user.clear(input); await user.type(input, 'Pegawai Contoh Diubah');
  await user.click(screen.getByRole('button', { name: 'Simpan perubahan' }));
  expect(await screen.findByRole('heading', { name: 'Pegawai Contoh Diubah' })).toBeInTheDocument();
  const patch = server.mock.calls.find(c => c[1]?.method === 'PATCH')!;
  expect(JSON.parse(String(patch[1]?.body))).toEqual({ full_name: 'Pegawai Contoh Diubah' });
});
test('server field errors preserve entered values', async () => {
  mockServer('duplicate'); const user = userEvent.setup(); render(<App initialEntries={['/employees/new']} />);
  await user.type(await screen.findByLabelText('Kode pegawai'), '0001');
  await user.type(screen.getByLabelText('Nama lengkap'), 'Pegawai Contoh Baru');
  await user.click(screen.getByRole('button', { name: 'Simpan pegawai' }));
  expect(await screen.findByText('Kode sudah digunakan.')).toBeInTheDocument();
  expect(screen.getByLabelText('Kode pegawai')).toHaveValue('0001');
  expect(screen.getByLabelText('Nama lengkap')).toHaveValue('Pegawai Contoh Baru');
});
test('confirmed PATCH followed by failed GET reports saved state without inviting mutation replay', async () => {
  const server = mockServer('refetch-failed'); const user = userEvent.setup(); render(<App initialEntries={['/employees/' + existing.id + '/edit']} />);
  const input = await screen.findByLabelText('Nama lengkap'); await user.clear(input); await user.type(input, 'Pegawai Contoh Diubah');
  await user.click(screen.getByRole('button', { name: 'Simpan perubahan' }));
  expect(await screen.findByText(/Data tersimpan, tetapi belum dapat dimuat ulang/)).toBeInTheDocument();
  expect(server.mock.calls.filter(c => c[1]?.method === 'PATCH')).toHaveLength(1);
  expect(screen.queryByRole('button', { name: 'Simpan perubahan' })).not.toBeInTheDocument();
});
