import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';
import type { Draft, Receipt, References } from './types';
const employee = '10000000-0000-0000-0000-000000000001';
const id = '20000000-0000-0000-0000-000000000001';
const docId = '30000000-0000-0000-0000-000000000001';
const hash = 'a'.repeat(64);
const saved: Draft = { id, employee, pkwt_type: 'yayasan', revision: 1, reference_version: 'v1', template_sha256: hash, values: { nama: 'Private Contract Name' }, employee_snapshot: {}, source_unit: null, job_default_key: null, created_at: '2026-11-05', updated_at: '2026-11-05' };
const receipt: Receipt = { id: docId, draft: id, revision: 1, template_sha256: hash, content_sha256: hash, filename: 'private.docx', generated_at: '2026-11-05T00:00:00Z', download_url: `/api/contract-documents/${docId}/download/` };
const refs: References = { available: true, version: 'v1', templates: Object.fromEntries(['yayasan', 'guru', 'klinik_umum'].map(k => [k, { sha256: hash }])), units: [], jobs: [], fields: { yayasan: [{ key: 'nama', label: 'Nama', group: 'Identitas', kind: 'text', choices: [], max_length: 1000, required_for_generation: true }], guru: [], klinik_umum: [] } };
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(r => { resolve = r; }); return { promise, resolve }; }
function setup(mode: 'generate' | 'blob' | 'denied') {
  let writable = true, authenticated = true;
  const pending = deferred<Response>(), blob = deferred<Blob>();
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  vi.stubGlobal('fetch', vi.fn(async (path: string) => {
    if (path.endsWith('/me/')) return authenticated ? Response.json({ id: writable ? 1 : 2, email: writable ? 'hr@example.test' : 'manager@example.test', capabilities: { employees_read: true, employees_write: writable } }) : Response.json({}, { status: 403 });
    if (path.endsWith('/csrf/')) return Response.json({ csrfToken: 'valid' });
    if (path.endsWith('/logout/')) { authenticated = false; return Response.json({}); }
    if (path === `/api/employees/${employee}/`) return Response.json({ id: employee, employee_code: '00042', full_name: 'Employee', employment_status: 'kontrak', pkwt_type: 'yayasan' });
    if (path.startsWith('/api/contract-references/')) return Response.json(refs);
    if (path === `/api/contract-drafts/${id}/`) return Response.json(saved);
    if (path.endsWith('/documents/')) return Response.json({ results: mode === 'generate' ? [] : [receipt] });
    if (path.endsWith('/generate/')) return pending.promise;
    if (path.endsWith('/download/')) {
      if (mode === 'denied') { writable = false; return Response.json({}, { status: 403 }); }
      const response = new Response(null, { headers: { 'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' } });
      response.blob = () => blob.promise;
      return response;
    }
    throw new Error('Unexpected request ' + path);
  }));
  render(<App initialEntries={[`/employees/${employee}/contracts/${id}`]} />);
  return { click, pending, blob, switchAccount: () => { writable = false; }, user: userEvent.setup() };
}
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

test('generation reply after logout cannot restore private fields or start download', async () => {
  const fixture = setup('generate');
  await fixture.user.click(await screen.findByRole('button', { name: 'Buat DOCX' }));
  await fixture.user.click(screen.getByRole('button', { name: 'Keluar' }));
  await screen.findByLabelText('Email');
  await act(async () => fixture.pending.resolve(Response.json(receipt)));
  expect(screen.queryByDisplayValue('Private Contract Name')).not.toBeInTheDocument();
  expect(fixture.click).not.toHaveBeenCalled();
});

test('HR to manager switch clears pending generation data', async () => {
  const fixture = setup('generate');
  await fixture.user.click(await screen.findByRole('button', { name: 'Buat DOCX' }));
  fixture.switchAccount();
  await act(async () => window.dispatchEvent(new Event('focus')));
  await screen.findByRole('heading', { name: 'Akses tidak tersedia' });
  await act(async () => fixture.pending.resolve(Response.json(receipt)));
  expect(screen.queryByDisplayValue('Private Contract Name')).not.toBeInTheDocument();
  expect(fixture.click).not.toHaveBeenCalled();
});

test('permission loss while Blob is pending prevents a download and clears fields', async () => {
  const fixture = setup('blob');
  await fixture.user.click(await screen.findByRole('button', { name: 'Download DOCX' }));
  fixture.switchAccount();
  await act(async () => fixture.blob.resolve(new Blob(['private'])));
  await screen.findByRole('heading', { name: 'Akses tidak tersedia' });
  expect(screen.queryByDisplayValue('Private Contract Name')).not.toBeInTheDocument();
  expect(fixture.click).not.toHaveBeenCalled();
});

test('download denial verifies changed identity and clears private fields', async () => {
  const fixture = setup('denied');
  await fixture.user.click(await screen.findByRole('button', { name: 'Download DOCX' }));
  await waitFor(() => expect(screen.queryByDisplayValue('Private Contract Name')).not.toBeInTheDocument());
  expect(fixture.click).not.toHaveBeenCalled();
});
