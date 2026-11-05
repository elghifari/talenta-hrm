import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';
import type { Draft, Receipt, References } from './types';
const employee = '10000000-0000-0000-0000-000000000001', id = '20000000-0000-0000-0000-000000000001', docId = '30000000-0000-0000-0000-000000000001', hash = 'a'.repeat(64);
const refs: References = { available: true, version: 'v1', templates: Object.fromEntries(['yayasan', 'guru', 'klinik_umum'].map(k => [k, { sha256: hash }])), units: [], jobs: [], fields: { yayasan: [{ key: 'nip', label: 'NIP', group: 'Identitas', kind: 'text', choices: [], max_length: 1000, required_for_generation: true }], guru: [], klinik_umum: [] } };
function setup(mode: 'save' | 'generate' | 'conflict' | 'malformed' | 'mismatch' | 'noop' | 'noop-concurrent') {
  let draft: Draft = { id, employee, pkwt_type: 'yayasan', revision: 1, reference_version: 'v1', template_sha256: hash, values: { nip: '0001' }, employee_snapshot: {}, source_unit: null, job_default_key: null, created_at: '2026-11-05', updated_at: '2026-11-05' };
  let documents: Receipt[] = [];
  const fetcher = vi.fn(async (path: string, init?: RequestInit) => {
    if (path.endsWith('/me/')) return Response.json({ id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: true } });
    if (path.endsWith('/csrf/')) return Response.json({ csrfToken: 'valid' });
    if (path === `/api/employees/${employee}/`) return Response.json({ id: employee, employee_code: '00042', full_name: 'Employee', employment_status: 'kontrak', pkwt_type: 'yayasan' });
    if (path.startsWith('/api/contract-references/')) return Response.json(refs);
    if (path === `/api/contract-drafts/${id}/` && init?.method === 'PATCH') {
      if (mode === 'conflict') return Response.json({ code: 'revision_conflict', revision: 2 }, { status: 409 });
      const payload = JSON.parse(String(init.body));
      draft = { ...draft, revision: mode === 'noop' ? 1 : mode === 'noop-concurrent' ? 3 : 2, values: mode === 'mismatch' ? { nip: 'other-user' } : payload.values };
      if (mode === 'malformed') return Response.json({ accepted: true });
      throw new TypeError('Lost response');
    }
    if (path === `/api/contract-drafts/${id}/`) return Response.json(draft);
    if (path.endsWith('/documents/')) return Response.json({ results: documents });
    if (path.endsWith('/generate/')) {
      documents = [{ id: docId, draft: id, revision: 1, template_sha256: hash, content_sha256: hash, filename: 'generated.docx', generated_at: '2026-11-05', download_url: `/api/contract-documents/${docId}/download/` }];
      throw new TypeError('Lost response');
    }
    throw new Error('Unexpected request ' + path);
  });
  vi.stubGlobal('fetch', fetcher);
  render(<App initialEntries={[`/employees/${employee}/contracts/${id}`]} />);
  return { user: userEvent.setup(), fetcher };
}
afterEach(() => vi.unstubAllGlobals());

test.each(['save', 'malformed'] as const)('lost or malformed PATCH receipt recovers exact revision by GET (%s)', async mode => {
  const { user, fetcher } = setup(mode);
  const nip = await screen.findByLabelText('NIP');
  await user.clear(nip); await user.type(nip, '0009');
  await user.click(screen.getByRole('button', { name: 'Simpan draf' }));
  await user.click(await screen.findByRole('button', { name: 'Periksa hasil' }));
  await screen.findByText('Draf tersimpan.');
  expect(screen.getByLabelText('NIP')).toHaveValue('0009');
  expect(fetcher.mock.calls.filter(([, init]) => init?.method === 'PATCH')).toHaveLength(1);
});

test('lost canonical no-op save recovers at the unchanged revision', async () => {
  const { user, fetcher } = setup('noop');
  await user.type(await screen.findByLabelText('NIP'), ' ');
  await user.click(screen.getByRole('button', { name: 'Simpan draf' }));
  await user.click(await screen.findByRole('button', { name: 'Periksa hasil' }));
  await screen.findByText('Draf tersimpan.');
  expect(screen.getByLabelText('NIP')).toHaveValue('0001');
  expect(screen.queryByRole('button', { name: 'Periksa hasil' })).not.toBeInTheDocument();
  expect(fetcher.mock.calls.filter(([, init]) => init?.method === 'PATCH')).toHaveLength(1);
});

test('no-op recovery does not accept matching values from a later concurrent revision', async () => {
  const { user } = setup('noop-concurrent');
  await user.type(await screen.findByLabelText('NIP'), ' ');
  await user.click(screen.getByRole('button', { name: 'Simpan draf' }));
  await user.click(await screen.findByRole('button', { name: 'Periksa hasil' }));
  await screen.findByText(/Hasil berbeda dari isian/);
  expect(screen.getByRole('button', { name: 'Simpan draf' })).toBeDisabled();
  expect(screen.getByLabelText('NIP')).toHaveValue('0001 ');
});

test('generation receipt is recovered without repeating POST' , async () => {
  const { user, fetcher } = setup('generate');
  await user.dblClick(await screen.findByRole('button', { name: 'Buat DOCX' }));
  await user.click(await screen.findByRole('button', { name: 'Periksa hasil' }));
  await screen.findByText('DOCX dibuat.');
  expect(screen.getByText('generated.docx')).toBeVisible();
  expect(fetcher.mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(1);
});

test.each(['conflict', 'mismatch'] as const)('conflict recovery preserves unsaved local fields (%s)', async mode => {
  const { user, fetcher } = setup(mode);
  const nip = await screen.findByLabelText('NIP');
  await user.clear(nip); await user.type(nip, '0009');
  await user.click(screen.getByRole('button', { name: 'Simpan draf' }));
  if (mode === 'mismatch') {
    await user.click(await screen.findByRole('button', { name: 'Periksa hasil' }));
    expect(screen.getByRole('button', { name: 'Simpan draf' })).toBeDisabled();
  } else await screen.findByText(/Draf telah berubah/);
  expect(screen.getByLabelText('NIP')).toHaveValue('0009');
  expect(fetcher.mock.calls.filter(([, init]) => init?.method === 'PATCH')).toHaveLength(1);
});
