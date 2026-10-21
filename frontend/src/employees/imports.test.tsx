import userEvent from '@testing-library/user-event';
import { render, screen } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';

afterEach(() => vi.unstubAllGlobals());
const employee = { id: '00000000-0000-0000-0000-000000000001', employee_code: '0001', full_name: 'Karyawan A' };

function auth(path: string) {
  if (path.endsWith('/me/')) return Response.json({ id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: true } });
  if (path.endsWith('/csrf/')) return Response.json({ csrfToken: 'valid' });
  return Response.json([employee]);
}

test('HR has adjacent add and batch upload actions with ID Karyawan naming', async () => {
  vi.stubGlobal('fetch', vi.fn(async (path: string) => auth(path)));
  render(<App initialEntries={['/employees']} />);
  const upload = await screen.findByRole('link', { name: 'batch upload' });
  expect(upload).toHaveAttribute('href', '/employees/import');
  expect(upload.parentElement).toBe(screen.getByRole('link', { name: 'Tambah pegawai' }).parentElement);
  expect(await screen.findByRole('columnheader', { name: 'ID Karyawan' })).toBeInTheDocument();
});

const incoming = { employee_code: '0002', full_name: 'Karyawan B', date_of_birth: '1998-03-21', job_title: 'Terapis', level: '1', start_date: '2024-01-01', contract_expiry: '2027-12-31' };
const draft = { id: '10000000-0000-0000-0000-000000000001', state: 'pending', expires_at: '2026-12-01T00:00:00Z', summary: { new: 1, update: 0, unchanged: 0, error: 0 }, rows: [{ row: 2, employee_code: '0002', full_name: 'Karyawan B', status: 'new', current: null, incoming, changes: Object.keys(incoming), errors: {} }] };

test('CSV stays in memory and is uploaded as multipart before an incoming-only server preview', async () => {
  const fetcher = vi.fn(async (path: string) => path.includes('import-preview') || path.includes('/imports/') ? Response.json(draft, { status: path.includes('import-preview') ? 201 : 200 }) : auth(path));
  vi.stubGlobal('fetch', fetcher);
  const user = userEvent.setup();
  render(<App initialEntries={['/employees/import']} />);
  const input = await screen.findByLabelText('File CSV');
  expect(screen.getByRole('button', { name: 'Pratinjau CSV' })).toBeDisabled();
  await user.upload(input, new File(['Nama Lengkap,ID Karyawan\nKaryawan B,0002\n'], 'karyawan.csv', { type: 'text/csv' }));
  await user.click(screen.getByRole('button', { name: 'Pratinjau CSV' }));
  expect(await screen.findByRole('heading', { name: 'Pratinjau batch upload' })).toBeInTheDocument();
  expect(await screen.findByText('Karyawan B')).toBeInTheDocument();
  expect(screen.getByText('New')).toBeInTheDocument();
  expect(screen.queryByText('Karyawan A')).not.toBeInTheDocument();
  const writes = fetcher.mock.calls.filter(([path]) => path.includes('import-preview'));
  expect(writes).toHaveLength(1);
  const options = (fetcher.mock.calls as unknown as [string, RequestInit][]).find(([path]) => path.includes('import-preview'))![1];
  expect(options.body).toBeInstanceOf(FormData);
  expect(new Headers(options.headers).has('Content-Type')).toBe(false);
  expect(fetcher.mock.calls.some(([path]) => path.endsWith('/confirm/'))).toBe(false);
});
