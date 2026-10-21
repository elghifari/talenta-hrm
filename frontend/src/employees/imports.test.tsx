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
  const upload = await screen.findByRole('link', { name: 'batch upload', exact: true });
  expect(upload).toHaveAttribute('href', '/employees/import');
  expect(upload.parentElement).toBe(screen.getByRole('link', { name: 'Tambah pegawai', exact: true }).parentElement);
  expect(screen.getByRole('columnheader', { name: 'ID Karyawan', exact: true })).toBeInTheDocument();
});
