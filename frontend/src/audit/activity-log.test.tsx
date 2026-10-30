import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';

const event = { id: 1, created_at: '2026-10-27T00:00:00+00:00', actor: { id: 1, email: 'actor@example.test' }, action: 'division.settings_changed', action_label: 'Pengaturan divisi diubah', target: { type: 'division', id: '20000000-0000-0000-0000-000000000001', label: 'Synthetic Division' }, changes: { kinerja_enabled: { old: false, new: true } } };
const page = { count: 1, next: null, previous: null, results: [event] };
function setup(allowed = true, handler: (path: string) => Promise<Response> = async () => Response.json(page)) {
  const state = { allowed };
  const fetcher = vi.fn(async (path: string) => {
    if (path.endsWith('/me/')) return Response.json({ id: 1, email: 'manager@example.test', capabilities: { employees_read: true, employees_write: true, audit_read: state.allowed } });
    if (path.startsWith('/api/audit-events/')) return handler(path);
    return Response.json([]);
  });
  vi.stubGlobal('fetch', fetcher);
  render(<App initialEntries={['/personnel/activity']} />);
  return { state, fetcher, user: userEvent.setup() };
}
afterEach(() => { vi.unstubAllGlobals(); });

test('HR Staff direct route denies without fetching log rows or exposing navigation', async () => {
  const { fetcher } = setup(false);
  expect(await screen.findByRole('alert')).toHaveTextContent('Akses log aktivitas tidak tersedia.');
  expect(screen.queryByRole('link', { name: 'Log aktivitas' })).not.toBeInTheDocument();
  expect(fetcher.mock.calls.some(([path]) => path.startsWith('/api/audit-events/'))).toBe(false);
});

test('HR Manager sees translated events, WIB, safe details and working filters and paging', async () => {
  const { fetcher, user } = setup(true, async path => {
    const query = new URL(path, 'http://test').searchParams;
    if (query.get('actor') === 'absent') return Response.json({ count: 0, next: null, previous: null, results: [] });
    return Response.json({ ...page, count: 51, next: query.get('page') === '2' ? null : '/api/audit-events/?page=2', previous: query.get('page') === '2' ? '/api/audit-events/?page=1' : null });
  });
  expect(await screen.findByText('Synthetic Division')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Log aktivitas' })).toHaveAttribute('href', '/personnel/activity');
  expect(within(screen.getByRole('navigation', { name: 'Breadcrumb' })).queryByText('Data pegawai')).not.toBeInTheDocument();
  expect(screen.getByText(/07\.00.*WIB/)).toHaveAttribute('datetime', event.created_at);
  expect(screen.getByText('Kinerja: Nonaktif → Aktif')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Berikutnya' }));
  await waitFor(() => expect(screen.getByText('Halaman 2')).toBeInTheDocument());
  await user.click(screen.getByRole('button', { name: 'Sebelumnya' }));
  await user.type(screen.getByLabelText('Pelaku (email)'), 'absent');
  await user.click(screen.getByRole('button', { name: 'Terapkan filter' }));
  expect(await screen.findByText('Tidak ada aktivitas yang cocok dengan filter.')).toBeInTheDocument();
  expect(fetcher.mock.calls.some(([path]) => path.includes('actor=absent&page=1'))).toBe(true);
  await user.click(screen.getByRole('button', { name: 'Reset' }));
  expect(await screen.findByText('Synthetic Division')).toBeInTheDocument();
});

test('empty, failure/retry, invalid filters and unavailable page stay distinct', async () => {
  let mode = 'failure';
  const { user } = setup(true, async () => {
    if (mode === 'failure') return Response.json({}, { status: 500 });
    if (mode === 'unavailable') return Response.json({}, { status: 404 });
    if (mode === 'invalid') return Response.json({}, { status: 400 });
    return Response.json({ count: 0, results: [], next: null, previous: null });
  });
  await screen.findByRole('alert');
  mode = 'empty';
  await user.click(screen.getByRole('button', { name: 'Coba lagi' }));
  expect(await screen.findByText('Belum ada aktivitas tercatat.')).toBeInTheDocument();
  mode = 'invalid';
  await user.click(screen.getByRole('button', { name: 'Terapkan filter' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Filter tidak valid.');
  mode = 'unavailable';
  await user.click(screen.getByRole('button', { name: 'Reset' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Halaman log ini tidak tersedia.');
  mode = 'empty';
  await user.click(screen.getByRole('button', { name: 'Halaman pertama' }));
  expect(await screen.findByText('Belum ada aktivitas tercatat.')).toBeInTheDocument();
});

test('stale filter responses cannot overwrite newer results', async () => {
  let resolveOld!: (response: Response) => void;
  const { user } = setup(true, path => path.includes('actor=old') ? new Promise(resolve => { resolveOld = resolve; }) : Promise.resolve(Response.json(page)));
  await screen.findByText('Synthetic Division');
  await user.type(screen.getByLabelText('Pelaku (email)'), 'old');
  await user.click(screen.getByRole('button', { name: 'Terapkan filter' }));
  expect(screen.queryByText('Synthetic Division')).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Reset' }));
  await screen.findByText('Synthetic Division');
  await act(async () => resolveOld(Response.json({ ...page, results: [{ ...event, target: { ...event.target, label: 'Stale Secret' } }] })));
  expect(screen.queryByText('Stale Secret')).not.toBeInTheDocument();
});

test('audit-only permission revocation clears rows and ignores delayed response', async () => {
  let resolveOld!: (response: Response) => void;
  const { user, state } = setup(true, path => path.includes('actor=delayed') ? new Promise(resolve => { resolveOld = resolve; }) : Promise.resolve(Response.json(page)));
  await screen.findByText('Synthetic Division');
  await user.type(screen.getByLabelText('Pelaku (email)'), 'delayed');
  await user.click(screen.getByRole('button', { name: 'Terapkan filter' }));
  state.allowed = false;
  await act(async () => window.dispatchEvent(new Event('focus')));
  expect(await screen.findByRole('alert')).toHaveTextContent('Akses log aktivitas tidak tersedia.');
  await act(async () => resolveOld(Response.json(page)));
  expect(screen.queryByText('Synthetic Division')).not.toBeInTheDocument();
  expect(screen.queryByRole('link', { name: 'Log aktivitas' })).not.toBeInTheDocument();
});

test('target labels render as text and deleted targets never link', async () => {
  setup(true, async () => Response.json({ ...page, count: 2, results: [
    { ...event, target: { ...event.target, label: '<img src=x onerror=alert(1)>' } },
    { ...event, id: 2, target: { ...event.target, label: null }, changes: {} },
  ] }));
  expect(await screen.findByText('<img src=x onerror=alert(1)>')).toBeInTheDocument();
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  expect(screen.getByText(event.target.id).closest('a')).toBeNull();
  expect(screen.getByText('Rincian perubahan tidak tercatat.')).toBeInTheDocument();
});
