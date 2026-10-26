import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';

test('failed logout with a still-valid identity does not claim the session ended', async () => {
  vi.stubGlobal('fetch', vi.fn(async (path: string) => {
    if(path === '/api/employees/' || path.startsWith('/api/organization/')) return Response.json([]);
    if(path.endsWith('/csrf/')) return Response.json({ csrfToken: 'valid' });
    if(path.endsWith('/logout/')) return new Response('<html>CSRF denied</html>', { status: 403, headers: { 'content-type': 'text/html' } });
    return Response.json({ id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: true } });
  }));
  render(<App />); const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: 'Keluar' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Tindakan ditolak');
  expect(screen.getByText('hr@example.test')).toBeInTheDocument();
  expect(screen.queryByLabelText('Sandi')).not.toBeInTheDocument();
});

afterEach(() => { vi.unstubAllGlobals(); window.history.replaceState({}, '', '/'); });

test('anonymous bootstrap exposes an accessible email login form without expiry messaging', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Authentication required' }), { status: 403 })));
  render(<App />);
  expect(await screen.findByRole('button', { name: 'Masuk' })).toBeEnabled();
  expect(screen.getByLabelText('Email')).toHaveAttribute('autocomplete', 'username');
  expect(screen.getByLabelText('Sandi')).toHaveAttribute('type', 'password');
  expect(screen.queryByText(/Sesi Anda berakhir/)).not.toBeInTheDocument();
});

test('login uses form email, refreshed CSRF and server capabilities; logout clears session', async () => {
  let signedIn = false;
  const calls: { path: string; init?: RequestInit }[] = [];
  vi.stubGlobal('fetch', vi.fn(async (path: string, init?: RequestInit) => {
    calls.push({ path, init });
    if(path === '/api/employees/' || path.startsWith('/api/organization/')) return Response.json([]);
    if(path.endsWith('/csrf/')) return Response.json({ csrfToken: signedIn ? 'rotated' : 'initial' });
    if(path.endsWith('/login/')) { signedIn = true; return Response.json({ detail: 'Signed in' }); }
    if(path.endsWith('/logout/')) { signedIn = false; return new Response(null, { status: 204 }); }
    return signedIn ? Response.json({ id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: true } }) : Response.json({}, { status: 403 });
  }));
  const user = userEvent.setup(); render(<App />);
  await user.type(await screen.findByLabelText('Email'), 'hr@example.test');
  await user.type(screen.getByLabelText('Sandi'), 'Synthetic-test-only');
  await user.click(screen.getByRole('button', { name: 'Masuk' }));
  expect(await screen.findByText('hr@example.test')).toBeInTheDocument();
  const login = calls.find(c => c.path.endsWith('/login/'))!;
  expect(String(login.init?.body)).toContain('username=hr%40example.test');
  expect(login.init?.credentials).toBe('same-origin');
  expect(calls.filter(c => c.path.endsWith('/csrf/'))).toHaveLength(2);
  await user.click(screen.getByRole('button', { name: 'Keluar' }));
  expect(await screen.findByRole('button', { name: 'Masuk' })).toBeInTheDocument();
  expect(screen.queryByText('hr@example.test')).not.toBeInTheDocument();
});
