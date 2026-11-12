import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';
import type { Draft, References } from './types';

export const employeeId = '10000000-0000-0000-0000-000000000001';
export const hash = 'a'.repeat(64);
const field = (key: string, label: string) => ({ key, label, group: 'Identitas', kind: 'text' as const, choices: [], max_length: 1000, required_for_generation: true });
export const refs: References = { available: true, version: 'synthetic-v1', templates: Object.fromEntries(['yayasan', 'guru', 'klinik_umum'].map(k => [k, { sha256: hash }])), units: [], jobs: [], fields: { yayasan: [field('nama', 'Nama Lengkap Karyawan'), field('nip', 'NIP')], guru: [], klinik_umum: [] } };
export function renderContractEditor(options: { loseCreate?: boolean; route?: string; status?: 'kontrak' | 'magang' } = {}) {
  let stored: Draft | undefined;
  let readAvailable = !options.loseCreate;
  const fetcher = vi.fn(async (path: string, init?: RequestInit) => {
    if (path.endsWith('/me/')) return Response.json({ id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: true } });
    if (path.endsWith('/csrf/')) return Response.json({ csrfToken: 'valid' });
    if (path === '/api/employees/' + employeeId + '/') return Response.json({ id: employeeId, employee_code: '00042', full_name: 'Synthetic Employee', employment_status: options.status ?? 'kontrak', pkwt_type: 'yayasan' });
    if (path.startsWith('/api/contract-references/')) return Response.json(refs);
    if (path.startsWith('/api/contract-drafts/?')) return Response.json({ results: [], count: 0, page: 1 });
    if (path === '/api/contract-drafts/' && init?.method === 'POST') {
      const body = JSON.parse(String(init.body));
      stored = { ...body, pkwt_type: body.pkwt_type, revision: 1, reference_version: 'synthetic-v1', template_sha256: hash, employee_snapshot: { employee_code: '00042' }, source_unit: body.source_unit ?? null, job_default_key: body.job_default_key ?? null, created_at: '2026-11-05', updated_at: '2026-11-05' };
      if (options.loseCreate) throw new TypeError('Lost response');
      return Response.json(stored, { status: 201 });
    }
    if (path.endsWith('/documents/')) return Response.json({ results: [] });
    if (stored && path === `/api/contract-drafts/${stored.id}/`) return readAvailable ? Response.json(stored) : Response.json({}, { status: 404 });
    throw new Error('Unexpected request ' + path);
  });
  vi.stubGlobal('fetch', fetcher);
  render(<App initialEntries={[options.route ?? `/employees/${employeeId}/contracts/new`]} />);
  return { fetcher, user: userEvent.setup(), allowRead: () => { readAvailable = true; } };
}
afterEach(() => vi.unstubAllGlobals());

test('new renewal keeps NIP separate and does not write before Save', async () => {
  const { fetcher } = renderContractEditor();
  expect(await screen.findByLabelText('NIP')).toHaveValue('');
  expect(screen.getByText('00042')).toBeVisible();
  expect(screen.getByRole('heading', { name: 'Template' })).toBeVisible();
  expect(screen.getByLabelText('Unit', { exact: true })).toBeVisible();
  expect(screen.getByLabelText('Jabatan', { exact: true })).toBeDisabled();
  expect(screen.getByRole('navigation', { name: 'Bagian form kontrak' })).toBeInTheDocument();
  expect(screen.queryByText('Klik bagian untuk berpindah.')).not.toBeInTheDocument();
  expect(screen.queryByText('Sorotan mengikuti posisi scroll.')).not.toBeInTheDocument();
  expect(fetcher.mock.calls.filter(([, init]) => ['POST', 'PATCH'].includes(init?.method ?? 'GET'))).toHaveLength(0);
});

test.each(['kontrak', 'magang'] as const)('%s can select a target type independently before saving', async status => {
  const { fetcher, user } = renderContractEditor({ status });
  const type = await screen.findByRole('combobox', { name: 'Tipe PKWT' });
  expect(type).toHaveValue('yayasan');
  await user.selectOptions(type, 'guru');
  await user.click(screen.getByRole('button', { name: 'Simpan draf' }));
  await screen.findByText('Draf tersimpan.');
  const writes = fetcher.mock.calls.filter(([, init]) => init?.method === 'POST');
  expect(writes).toHaveLength(1);
  expect(JSON.parse(String(writes[0][1]?.body))).toMatchObject({ employee: employeeId, pkwt_type: 'guru' });
  const savedType = await screen.findByRole('textbox', { name: 'Tipe PKWT' });
  expect(savedType).toHaveValue('Guru');
  expect(savedType).toHaveAttribute('readonly');
});

test('changing type requires confirmation before discarding edited values', async () => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value: function(this: HTMLDialogElement) { this.setAttribute('open', ''); } });
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value: function(this: HTMLDialogElement) { this.removeAttribute('open'); } });
  const { fetcher, user } = renderContractEditor();
  await user.type(await screen.findByLabelText('NIP'), '0099');
  await user.selectOptions(screen.getByRole('combobox', { name: 'Tipe PKWT' }), 'guru');
  await screen.findByRole('dialog');
  expect(screen.getByRole('combobox', { name: 'Tipe PKWT' })).toHaveValue('yayasan');
  await user.click(screen.getByRole('button', { name: 'Batal' }));
  expect(screen.getByLabelText('NIP')).toHaveValue('0099');
  await user.selectOptions(screen.getByRole('combobox', { name: 'Tipe PKWT' }), 'guru');
  await user.click(await screen.findByRole('button', { name: 'Gunakan default' }));
  expect(screen.getByRole('combobox', { name: 'Tipe PKWT' })).toHaveValue('guru');
  expect(fetcher.mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(0);
});

test('lost create response recovers by GET without repeating POST', async () => {
  const { fetcher, user, allowRead } = renderContractEditor({ loseCreate: true });
  await user.click(await screen.findByRole('button', { name: 'Simpan draf' }));
  await screen.findByRole('button', { name: 'Periksa hasil' });
  await user.click(screen.getByRole('button', { name: 'Periksa hasil' }));
  expect(screen.getByRole('button', { name: 'Simpan draf' })).toBeDisabled();
  allowRead();
  await user.click(screen.getByRole('button', { name: 'Periksa hasil' }));
  await screen.findByText('Draf tersimpan.');
  expect(fetcher.mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(1);
});
