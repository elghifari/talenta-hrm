import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';
import type { Draft, References } from './types';

export const employeeId = '10000000-0000-0000-0000-000000000001';
export const hash = 'a'.repeat(64);
const field = (key: string, label: string) => ({ key, label, group: 'Identitas', kind: 'text' as const, choices: [], max_length: 1000, required_for_generation: true });
export const refs: References = { available: true, version: 'synthetic-v1', templates: Object.fromEntries(['yayasan', 'guru', 'klinik_umum'].map(k => [k, { sha256: hash }])), units: [], jobs: [], fields: { yayasan: [field('nama', 'Nama Lengkap Karyawan'), field('nip', 'NIP')], guru: [], klinik_umum: [] } };
export function renderContractEditor(options: { loseCreate?: boolean; route?: string } = {}) {
  let stored: Draft | undefined;
  let readAvailable = !options.loseCreate;
  const fetcher = vi.fn(async (path: string, init?: RequestInit) => {
    if (path.endsWith('/me/')) return Response.json({ id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: true } });
    if (path.endsWith('/csrf/')) return Response.json({ csrfToken: 'valid' });
    if (path === '/api/employees/' + employeeId + '/') return Response.json({ id: employeeId, employee_code: '00042', full_name: 'Synthetic Employee', employment_status: 'kontrak', pkwt_type: 'yayasan' });
    if (path.startsWith('/api/contract-references/')) return Response.json(refs);
    if (path.startsWith('/api/contract-drafts/?')) return Response.json({ results: [], count: 0, page: 1 });
    if (path === '/api/contract-drafts/' && init?.method === 'POST') {
      const body = JSON.parse(String(init.body));
      stored = { ...body, pkwt_type: 'yayasan', revision: 1, reference_version: 'synthetic-v1', template_sha256: hash, employee_snapshot: { employee_code: '00042' }, source_unit: body.source_unit ?? null, job_default_key: body.job_default_key ?? null, created_at: '2026-11-05', updated_at: '2026-11-05' };
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
  expect(fetcher.mock.calls.filter(([, init]) => ['POST', 'PATCH'].includes(init?.method ?? 'GET'))).toHaveLength(0);
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
