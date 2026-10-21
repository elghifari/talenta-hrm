import { render, screen } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';
afterEach(() => vi.unstubAllGlobals());

test('invalid incoming rows open their errors and block batch confirmation', async () => {
  const row = { row: 2, employee_code: '0001', full_name: '', status: 'error', current: null, incoming: { employee_code: '0001', full_name: '' }, changes: [], errors: { full_name: ['Nama lengkap wajib diisi.'] } };
  const draft = { id: '10000000-0000-0000-0000-000000000002', state: 'pending', expires_at: '2026-12-01T00:00:00Z', summary: { new: 0, update: 0, unchanged: 0, error: 1 }, rows: [row] };
  vi.stubGlobal('fetch', vi.fn(async (path: string) => Response.json(path.endsWith('/me/') ? { id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: true } } : draft)));
  render(<App initialEntries={['/employees/imports/' + draft.id]} />);
  const marker = await screen.findByText('!');
  expect(marker.parentElement?.querySelector('details')).toHaveAttribute('open');
  expect(screen.getByText('Nama lengkap: Nama lengkap wajib diisi.')).toBeVisible();
  expect(screen.getByRole('button', { name: 'Konfirmasi upload' })).toBeDisabled();
});
