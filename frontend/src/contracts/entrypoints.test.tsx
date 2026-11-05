import { render, screen, within } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';
const id = '10000000-0000-0000-0000-000000000001';
function setup(writable: boolean, route: string) {
  const date = new Date();
  const today = [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-');
  const employee = { id, employee_code: '00042', full_name: 'Synthetic Name', employment_status: 'kontrak', pkwt_type: 'yayasan', contract_expiry: today };
  vi.stubGlobal('fetch', vi.fn(async (path: string) => {
    if (path.endsWith('/me/')) return Response.json({ id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: writable } });
    if (path === '/api/employees/') return Response.json([employee]);
    if (path === `/api/employees/${id}/`) return Response.json(employee);
    if (path.startsWith('/api/contract-drafts/?')) return Response.json({ results: [], count: 0, page: 1 });
    if (path.includes('/organization/')) return Response.json([]);
    throw new Error('Unexpected request ' + path);
  }));
  render(<App initialEntries={[route]} />);
}
afterEach(() => vi.unstubAllGlobals());
test('HR employee detail offers the shared renewal route and empty history', async () => {
  setup(true, '/employees/' + id);
  const region = await screen.findByRole('region', { name: 'Kontrak' });
  expect(within(region).getByRole('link', { name: 'Buat draf perpanjangan' })).toHaveAttribute('href', `/employees/${id}/contracts/new`);
  expect(await within(region).findByText('Belum ada draf perpanjangan.')).toBeVisible();
});
test('manager detail omits private contract history and action', async () => {
  setup(false, '/employees/' + id);
  await screen.findByRole('heading', { name: 'Synthetic Name' });
  expect(screen.queryByRole('region', { name: 'Kontrak' })).not.toBeInTheDocument();
});
test('expiry shortcut retains the employee link and opens the same editor', async () => {
  setup(true, '/personnel');
  const table = await screen.findByRole('table');
  expect(within(table).getByRole('link', { name: 'Synthetic Name' })).toHaveAttribute('href', '/employees/' + id);
  expect(within(table).getByRole('link', { name: 'Buat draf perpanjangan' })).toHaveAttribute('href', `/employees/${id}/contracts/new`);
});
