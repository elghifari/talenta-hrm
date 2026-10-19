import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';
afterEach(() => vi.unstubAllGlobals());
test('a denial verified as another account clears old identity and draft without replay', async () => {
  let account = 1;
  const fetcher = vi.fn(async (path: string, init?: RequestInit) => {
    if(path.endsWith('/me/')) return Response.json({ id: account, email: account === 1 ? 'first@example.test' : 'second@example.test', capabilities: { employees_read: true, employees_write: true } });
    if(path.endsWith('/csrf/')) return Response.json({ csrfToken: 'valid' });
    if(init?.method === 'POST') { account = 2; return Response.json({ detail: 'Denied' }, { status: 403 }); }
    return Response.json([]);
  });
  vi.stubGlobal('fetch', fetcher);
  render(<App initialEntries={['/employees/new']} />); const user = userEvent.setup();
  await user.type(await screen.findByLabelText('Kode pegawai'), '0099');
  await user.type(screen.getByLabelText('Nama lengkap'), 'Synthetic first-account private draft');
  await user.click(screen.getByRole('button', { name: 'Simpan pegawai' }));
  expect(await screen.findByText('second@example.test')).toBeInTheDocument();
  expect(screen.queryByText('first@example.test')).not.toBeInTheDocument();
  expect(screen.getByLabelText('Nama lengkap')).toHaveValue('');
  expect(screen.getByLabelText('Kode pegawai')).toHaveValue('');
  expect(fetcher.mock.calls.filter(c => c[1]?.method === 'POST')).toHaveLength(1);
});
