import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';

const branch = { id: '10000000-0000-0000-0000-000000000001', name: 'Synthetic Branch' };
const division = { id: '20000000-0000-0000-0000-000000000001', name: 'Synthetic Division', branch: branch.id, branch_name: branch.name, kinerja_enabled: false, pelimpahan_enabled: true };

beforeEach(() => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value: function (this: HTMLDialogElement) { this.setAttribute('open', ''); } });
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value: function (this: HTMLDialogElement) { this.removeAttribute('open'); } });
});
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

function setup(loseResponse = false, persist = true) {
  let current = { ...division };
  const writes: Record<string, unknown>[] = [];
  const fetcher = vi.fn(async (path: string, init?: RequestInit) => {
    if (path.endsWith('/me/')) return Response.json({ id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: true } });
    if (path.endsWith('/csrf/')) return Response.json({ csrfToken: 'valid' });
    if (path.endsWith('/deletion-impact/')) return Response.json({ employee_count: 0 });
    if (init?.method === 'PATCH') {
      const payload = JSON.parse(String(init.body)); writes.push(payload);
      if (persist) current = { ...current, ...payload.divisions[0] };
      if (loseResponse) throw new TypeError('Synthetic response lost');
      return Response.json({ branch, divisions: [current] });
    }
    return Response.json(path.endsWith('/branches/') ? [branch] : path.endsWith('/divisions/') ? [current] : branch);
  });
  vi.stubGlobal('fetch', fetcher);
  render(<App initialEntries={['/employees/groups']} />);
  return { user: userEvent.setup(), writes, fetcher };
}

test('HR edits independent Divisi switches and includes reviewed settings in the combined save', async () => {
  const { user, writes } = setup();
  await user.click(await screen.findByRole('button', { name: 'Edit cabang Synthetic Branch' }));
  const group = within(screen.getByRole('group', { name: 'Pengaturan divisi Synthetic Division' }));
  const kinerja = group.getByRole('switch', { name: 'Kinerja' });
  const pelimpahan = group.getByRole('switch', { name: 'Pelimpahan' });
  expect(kinerja).not.toBeChecked();
  expect(pelimpahan).toBeChecked();
  expect(screen.getByRole('button', { name: 'Simpan perubahan' })).toBeDisabled();
  await user.click(kinerja);
  expect(pelimpahan).toBeChecked();
  await user.click(pelimpahan);
  expect(kinerja).toBeChecked();
  await user.click(screen.getByRole('button', { name: 'Simpan perubahan' }));
  await screen.findByText('Cabang tersimpan.');
  expect(writes).toEqual([{
    name: branch.name, deleted: [],
    divisions: [{ id: division.id, name: division.name, kinerja_enabled: true, pelimpahan_enabled: false }],
    expected: { name: branch.name, divisions: { [division.id]: division.name }, settings: { [division.id]: { kinerja_enabled: false, pelimpahan_enabled: true } } },
  }]);
  await user.click(screen.getByRole('button', { name: 'Edit cabang Synthetic Branch' }));
  expect(screen.getByRole('switch', { name: 'Kinerja' })).toBeChecked();
  expect(screen.getByRole('switch', { name: 'Pelimpahan' })).not.toBeChecked();
});

test('switch-only edits participate in dirty Cancel and restoring values avoids a write', async () => {
  const { user, writes } = setup();
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
  await user.click(await screen.findByRole('button', { name: 'Edit cabang Synthetic Branch' }));
  const kinerja = screen.getByRole('switch', { name: 'Kinerja' });
  kinerja.focus(); await user.keyboard(' ');
  expect(kinerja).toBeChecked();
  await user.click(screen.getByRole('button', { name: 'Batal' }));
  expect(confirm).toHaveBeenCalledOnce();
  expect(screen.getByRole('dialog')).toBeInTheDocument();
  await user.click(kinerja);
  expect(screen.getByRole('button', { name: 'Simpan perubahan' })).toBeDisabled();
  await user.click(kinerja);
  confirm.mockReturnValue(true);
  await user.click(screen.getByRole('button', { name: 'Batal' }));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(writes).toHaveLength(0);
  await user.click(screen.getByRole('button', { name: 'Edit cabang Synthetic Branch' }));
  expect(screen.getByRole('switch', { name: 'Kinerja' })).not.toBeChecked();
  expect(screen.getByRole('switch', { name: 'Pelimpahan' })).toBeChecked();
});

test('a committed save with a lost response is confirmed by reads without replaying writes', async () => {
  const { user, writes } = setup(true);
  await user.click(await screen.findByRole('button', { name: 'Edit cabang Synthetic Branch' }));
  await user.click(screen.getByRole('switch', { name: 'Kinerja' }));
  await user.click(screen.getByRole('button', { name: 'Simpan perubahan' }));
  await screen.findByRole('button', { name: 'Periksa data tersimpan' });
  expect(screen.getByRole('button', { name: 'Simpan perubahan' })).toBeDisabled();
  expect(screen.getByRole('switch', { name: 'Kinerja' })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Periksa data tersimpan' }));
  await screen.findByText('Cabang tersimpan.');
  expect(writes).toHaveLength(1);
});

test('Divisi rows show sequential numbers after adding, removing and restoring rows', async () => {
  const { user, writes } = setup();
  await user.click(await screen.findByRole('button', { name: 'Edit cabang Synthetic Branch' }));
  const numbers = () => [...screen.getByRole('dialog').querySelectorAll('.branch-division-number')].map(item => item.textContent);
  expect(numbers()).toEqual(['1.']);
  await user.click(screen.getByRole('button', { name: 'Tambah divisi' }));
  expect(numbers()).toEqual(['1.', '2.']);
  await user.click(screen.getByRole('button', { name: 'Hapus divisi Synthetic Division' }));
  await user.click(await screen.findByRole('button', { name: 'Hapus divisi' }));
  expect(numbers()).toEqual(['1.']);
  await user.click(screen.getByRole('button', { name: 'Batalkan' }));
  expect(numbers()).toEqual(['1.', '2.']);
  await user.click(screen.getByRole('button', { name: 'Hapus divisi 1' }));
  expect(numbers()).toEqual(['1.']);
  expect(screen.getByLabelText('Nama divisi 1')).toHaveValue(division.name);
  expect(writes).toHaveLength(0);
});

test('new Divisi switches default off and are included in the combined save', async () => {
  const { user, writes } = setup();
  await user.click(await screen.findByRole('button', { name: 'Edit cabang Synthetic Branch' }));
  await user.click(screen.getByRole('button', { name: 'Tambah divisi' }));
  const group = within(screen.getByRole('group', { name: 'Pengaturan divisi 2' }));
  expect(group.getByRole('switch', { name: 'Kinerja' })).not.toBeChecked();
  expect(group.getByRole('switch', { name: 'Pelimpahan' })).not.toBeChecked();
  await user.type(screen.getByLabelText('Nama divisi 2'), 'Synthetic New');
  await user.click(group.getByRole('switch', { name: 'Pelimpahan' }));
  await user.click(screen.getByRole('button', { name: 'Simpan perubahan' }));
  await waitFor(() => expect(writes).toHaveLength(1));
  expect(writes[0]).toMatchObject({ divisions: [
    { id: division.id, kinerja_enabled: false, pelimpahan_enabled: true },
    { name: 'Synthetic New', kinerja_enabled: false, pelimpahan_enabled: true },
  ] });
});

test('undoing staged deletion preserves the Divisi draft switches', async () => {
  const { user, writes } = setup();
  await user.click(await screen.findByRole('button', { name: 'Edit cabang Synthetic Branch' }));
  await user.click(screen.getByRole('switch', { name: 'Kinerja' }));
  await user.click(screen.getByRole('button', { name: 'Hapus divisi Synthetic Division' }));
  await user.click(await screen.findByRole('button', { name: 'Hapus divisi' }));
  await user.click(screen.getByRole('button', { name: 'Batalkan' }));
  expect(screen.getByRole('switch', { name: 'Kinerja' })).toBeChecked();
  expect(screen.getByRole('switch', { name: 'Pelimpahan' })).toBeChecked();
  expect(writes).toHaveLength(0);
});

test('read-back cannot confirm an uncertain save when names match but settings do not', async () => {
  const { user, writes } = setup(true, false);
  await user.click(await screen.findByRole('button', { name: 'Edit cabang Synthetic Branch' }));
  await user.click(screen.getByRole('switch', { name: 'Kinerja' }));
  await user.click(screen.getByRole('button', { name: 'Simpan perubahan' }));
  await user.click(await screen.findByRole('button', { name: 'Periksa data tersimpan' }));
  await screen.findByText('Data tersimpan belum cocok dengan perubahan ini. Tutup editor dan periksa daftar terbaru.');
  expect(screen.getByRole('dialog')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Simpan perubahan' })).toBeDisabled();
  expect(writes).toHaveLength(1);
});
