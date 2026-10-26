import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';
const employee = { id: '00000000-0000-0000-0000-000000000001', employee_code: '0001', full_name: 'Pegawai Contoh A' };
afterEach(() => { vi.unstubAllGlobals(); window.history.replaceState({}, '', '/'); });
test('selected sidebar exposes Personnel and code-first employees with real detail navigation', async () => {
  vi.stubGlobal('fetch', vi.fn(async (path: string) => {
    if(path.endsWith('/me/')) return Response.json({ id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: true } });
    return Response.json(path === '/api/employees/' ? [employee] : employee);
  }));
  render(<App initialEntries={['/employees']} />); const user = userEvent.setup();
  expect(within(await screen.findByRole('navigation', { name: 'Modul' })).getByRole('link', { name: 'Personnel' })).toHaveAttribute('href', '/personnel');
  expect(screen.queryByRole('link', { name: 'Payroll' })).not.toBeInTheDocument();
  await user.click(await screen.findByRole('link', { name: employee.full_name }));
  expect(await screen.findByRole('heading', { name: employee.full_name })).toBeInTheDocument();
  expect(screen.getByText('0001', { exact: true })).toBeInTheDocument();
  await user.click(within(screen.getByRole('navigation', { name: 'Breadcrumb' })).getByRole('link', { name: 'Data pegawai' }));
  expect(await screen.findByRole('heading', { name: 'Data pegawai' })).toBeInTheDocument();
});
test('manager sees read-only and scoped empty state, not HR creation instructions', async () => {
  vi.stubGlobal('fetch', vi.fn(async (path: string) => Response.json(path.endsWith('/me/') ? { id: 2, email: 'manager@example.test', capabilities: { employees_read: true, employees_write: false } } : [])));
  render(<App initialEntries={['/employees']} />);
  expect(await screen.findByText(/Akses baca saja/)).toBeInTheDocument();
  expect(await screen.findByText(/Belum ada pegawai yang tersedia/)).toBeInTheDocument();
  expect(screen.queryByRole('link', { name: 'Tambah pegawai' })).not.toBeInTheDocument();
});
