import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { afterEach, expect, test, vi } from 'vitest';
import { SessionProvider, useSession } from './SessionProvider';
const identity = { id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: true } };
afterEach(() => vi.unstubAllGlobals());
function Probe() {
  const session = useSession(); const [data, setData] = useState(''); const [error, setError] = useState('');
  return <><p>{session.status}</p><p>{session.identity?.email}</p><p>{data}</p><p>{error}</p>
    <button onClick={() => { session.request<string>('/api/employees/').then(setData).catch(e => { if(e.name !== 'AbortError') setError('Request denied'); }); }}>Load</button>
    <button onClick={() => { session.logout().catch(() => setError('Logout failed')); }}>Logout</button></>;
}
test('late old-session response cannot resolve protected data after logout', async () => {
  let resolve!: (value: Response) => void;
  vi.stubGlobal('fetch', vi.fn(async (path: string) => {
    if(path.endsWith('/csrf/')) return Response.json({ csrfToken: 'valid' });
    if(path.endsWith('/logout/')) return new Response(null, { status: 204 });
    if(path === '/api/employees/') return new Promise<Response>(r => { resolve = r; });
    return Response.json(identity);
  }));
  const user = userEvent.setup(); render(<SessionProvider><Probe /></SessionProvider>);
  await screen.findByText('authenticated'); await user.click(screen.getByText('Load'));
  await user.click(screen.getByText('Logout')); await screen.findByText('anonymous');
  await act(async () => resolve(Response.json('Synthetic previous-account secret')));
  expect(screen.queryByText('Synthetic previous-account secret')).not.toBeInTheDocument();
});
test('403 plus identity-network failure does not invent session expiry', async () => {
  let meCalls = 0;
  vi.stubGlobal('fetch', vi.fn(async (path: string) => {
    if(path.endsWith('/me/')) { if(meCalls++) throw new TypeError('Network lost'); return Response.json(identity); }
    return new Response('<html>Denied</html>', { status: 403 });
  }));
  const user = userEvent.setup(); render(<SessionProvider><Probe /></SessionProvider>);
  await screen.findByText('authenticated'); await user.click(screen.getByText('Load'));
  await screen.findByText('Request denied');
  expect(screen.getByText('authenticated')).toBeInTheDocument();
  expect(screen.getByText('hr@example.test')).toBeInTheDocument();
});
