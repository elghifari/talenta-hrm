import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from '../app/App';
import { changedFields } from './api';
import { decodeEmployee } from './types';


const identity = { id: '00000000-0000-0000-0000-000000000019', employee_code: '0019', full_name: 'Synthetic Classification' };
afterEach(() => vi.unstubAllGlobals());
function setup(options: { create?: boolean; restricted?: boolean; classification?: Record<string, string>; error?: Record<string, string[]> } = {}) {
  let record = { ...identity, ...options.classification };
  const writes: Record<string, unknown>[] = [];
  vi.stubGlobal('fetch', vi.fn(async (path: string, init?: RequestInit) => {
    if (path.endsWith('/me/')) return Response.json({ id: 1, email: 'classification@example.test', capabilities: { employees_read: true, employees_write: !options.restricted } });
    if (path.endsWith('/csrf/')) return Response.json({ csrfToken: 'valid' });
    if (path.startsWith('/api/organization/')) return Response.json([]);
    if (init?.method === 'POST' || init?.method === 'PATCH') {
      const body = JSON.parse(String(init.body)); writes.push(body);
      if (options.error) return Response.json(options.error, { status: 400 });
      record = { ...record, ...body };
    }
    return Response.json(record);
  }));
  render(<App initialEntries={[options.create ? '/employees/new' : '/employees/' + identity.id + (options.restricted ? '' : '/edit')]} />);
  return { writes, user: userEvent.setup() };
}

test('create requires a PKWT choice only for Kontrak and submits the selected codes', async () => {
  const { writes, user } = setup({ create: true });
  await screen.findByRole('heading', { name: 'Tambah pegawai' });
  await user.type(screen.getByLabelText('Kode pegawai'), '0019');
  await user.type(screen.getByLabelText('Nama lengkap'), identity.full_name);
  const status = screen.getByRole('combobox', { name: 'Status Kepegawaian' });
  expect(within(status).getAllByRole('option').map(option => option.textContent)).toEqual(['Belum diisi', 'Kontrak', 'Freelance', 'Magang', 'Permanen']);
  expect(screen.queryByRole('combobox', { name: 'Tipe PKWT' })).not.toBeInTheDocument();
  await user.selectOptions(status, 'kontrak');
  const type = screen.getByRole('combobox', { name: 'Tipe PKWT' });
  await user.click(screen.getByRole('button', { name: 'Simpan pegawai' }));
  await waitFor(() => expect(type).toHaveFocus());
  expect(type).toHaveAttribute('aria-invalid', 'true');
  expect(type).toHaveAccessibleDescription('Tipe PKWT wajib diisi untuk status Kontrak.');
  expect(writes).toEqual([]);
  await user.selectOptions(type, 'klinik_umum');
  await user.click(screen.getByRole('button', { name: 'Simpan pegawai' }));
  await screen.findByRole('heading', { name: identity.full_name });
  expect(writes).toEqual([{ employee_code: '0019', full_name: identity.full_name, employment_status: 'kontrak', pkwt_type: 'klinik_umum' }]);
  expect(screen.getByText('Klinik Umum')).toBeVisible();
});

test('PKWT edit sends only the changed type and renders its human label', async () => {
  const { writes, user } = setup({ classification: { employment_status: 'kontrak', pkwt_type: 'guru' } });
  await screen.findByRole('heading', { name: 'Ubah data pegawai' });
  expect(screen.getByRole('button', { name: 'Simpan perubahan' })).toBeDisabled();
  expect(screen.getByLabelText('Status Kepegawaian')).toHaveValue('kontrak');
  await user.selectOptions(screen.getByLabelText('Tipe PKWT'), 'yayasan');
  await user.click(screen.getByRole('button', { name: 'Simpan perubahan' }));
  await screen.findByRole('heading', { name: identity.full_name });
  expect(writes).toEqual([{ pkwt_type: 'yayasan' }]);
  expect(screen.getByText('Yayasan')).toBeVisible();
});

test.each(['', 'freelance', 'magang', 'permanen'])('leaving Kontrak for %s explicitly clears PKWT without writing other fields', async status => {
  const { writes, user } = setup({ classification: { employment_status: 'kontrak', pkwt_type: 'guru' } });
  await screen.findByRole('heading', { name: 'Ubah data pegawai' });
  await user.selectOptions(screen.getByLabelText('Status Kepegawaian'), status);
  expect(screen.queryByLabelText('Tipe PKWT')).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Simpan perubahan' }));
  await screen.findByRole('heading', { name: identity.full_name });
  expect(writes).toEqual([{ employment_status: status, pkwt_type: '' }]);
});

test('legacy missing classification stays blank, clean and unwritten on cancel', async () => {
  const { writes, user } = setup();
  await screen.findByRole('heading', { name: 'Ubah data pegawai' });
  expect(screen.getByLabelText('Status Kepegawaian')).toHaveValue('');
  expect(screen.getByRole('button', { name: 'Simpan perubahan' })).toBeDisabled();
  await user.click(screen.getByRole('button', { name: 'Batal' }));
  await screen.findByRole('heading', { name: identity.full_name });
  expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  expect(writes).toEqual([]);
});

test('editing an unrelated field keeps omitted classification out of PATCH', async () => {
  const { writes, user } = setup();
  await screen.findByRole('heading', { name: 'Ubah data pegawai' });
  await user.type(screen.getByLabelText('Jabatan'), 'Terapis');
  await user.click(screen.getByRole('button', { name: 'Simpan perubahan' }));
  await screen.findByRole('heading', { name: identity.full_name });
  expect(writes).toEqual([{ job_title: 'Terapis' }]);
});

test('selecting a non-contract status explicitly sends an empty PKWT even from a legacy blank', async () => {
  const { writes, user } = setup();
  await screen.findByRole('heading', { name: 'Ubah data pegawai' });
  await user.selectOptions(screen.getByLabelText('Status Kepegawaian'), 'permanen');
  await user.click(screen.getByRole('button', { name: 'Simpan perubahan' }));
  await screen.findByRole('heading', { name: identity.full_name });
  expect(writes).toEqual([{ employment_status: 'permanen', pkwt_type: '' }]);
});

test('create of a non-contract employee explicitly sends an empty PKWT', async () => {
  const { writes, user } = setup({ create: true });
  await screen.findByRole('heading', { name: 'Tambah pegawai' });
  await user.type(screen.getByLabelText('Kode pegawai'), '0019');
  await user.type(screen.getByLabelText('Nama lengkap'), identity.full_name);
  await user.selectOptions(screen.getByLabelText('Status Kepegawaian'), 'magang');
  await user.click(screen.getByRole('button', { name: 'Simpan pegawai' }));
  await screen.findByRole('heading', { name: identity.full_name });
  expect(writes).toEqual([{ employee_code: '0019', full_name: identity.full_name, employment_status: 'magang', pkwt_type: '' }]);
});

test('reverting the classification draft returns to a clean no-op without inferring a PKWT', async () => {
  const { writes, user } = setup();
  await screen.findByRole('heading', { name: 'Ubah data pegawai' });
  await user.selectOptions(screen.getByLabelText('Status Kepegawaian'), 'kontrak');
  await user.selectOptions(screen.getByLabelText('Tipe PKWT'), 'guru');
  await user.selectOptions(screen.getByLabelText('Status Kepegawaian'), '');
  expect(screen.getByRole('button', { name: 'Simpan perubahan' })).toBeDisabled();
  expect(screen.queryByLabelText('Tipe PKWT')).not.toBeInTheDocument();
  expect(writes).toEqual([]);
});

test('dirty cancel retains classification draft when departure is declined', async () => {
  const { writes, user } = setup();
  await screen.findByRole('heading', { name: 'Ubah data pegawai' });
  await user.selectOptions(screen.getByLabelText('Status Kepegawaian'), 'kontrak');
  await user.selectOptions(screen.getByLabelText('Tipe PKWT'), 'guru');
  await user.click(screen.getByRole('button', { name: 'Batal' }));
  await user.click(await screen.findByRole('button', { name: 'Tetap mengedit' }));
  expect(screen.getByLabelText('Tipe PKWT')).toHaveValue('guru');
  expect(writes).toEqual([]);
});

test.each(['employment_status', 'pkwt_type'])('API %s errors stay associated and focus the field', async field => {
  const { writes, user } = setup({ classification: { employment_status: 'kontrak', pkwt_type: 'guru' }, error: { [field]: ['Pilihan tidak tersedia.'] } });
  await screen.findByRole('heading', { name: 'Ubah data pegawai' });
  await user.selectOptions(screen.getByLabelText('Tipe PKWT'), 'yayasan');
  await user.click(screen.getByRole('button', { name: 'Simpan perubahan' }));
  const control = screen.getByLabelText(field === 'pkwt_type' ? 'Tipe PKWT' : 'Status Kepegawaian');
  await waitFor(() => expect(control).toHaveFocus());
  expect(control).toHaveAccessibleDescription('Pilihan tidak tersedia.');
  expect(writes).toEqual([{ pkwt_type: 'yayasan' }]);
  expect(screen.getByLabelText('Tipe PKWT')).toHaveValue('yayasan');
});

test('restricted detail never renders classification labels or values even if supplied', async () => {
  setup({ restricted: true, classification: { employment_status: 'kontrak', pkwt_type: 'klinik_umum' } });
  await screen.findByRole('heading', { name: identity.full_name });
  for (const text of ['Status Kepegawaian', 'Tipe PKWT', 'Kontrak', 'Klinik Umum']) expect(screen.queryByText(text)).not.toBeInTheDocument();
});

test('classification diff normalizes omitted legacy fields and preserves unaffected data', () => {
  expect(changedFields(identity, { ...identity, employment_status: '', pkwt_type: '' } as Parameters<typeof changedFields>[1])).toEqual({});
  expect(changedFields({ ...identity, employment_status: 'kontrak', pkwt_type: 'guru' } as Parameters<typeof changedFields>[0], { ...identity, full_name: 'Changed', employment_status: 'kontrak', pkwt_type: 'guru' } as Parameters<typeof changedFields>[1])).toEqual({ full_name: 'Changed' });
  expect(changedFields({ ...identity, employment_status: 'kontrak', pkwt_type: 'guru' } as Parameters<typeof changedFields>[0], { ...identity, employment_status: '', pkwt_type: '' } as Parameters<typeof changedFields>[1])).toEqual({ employment_status: '', pkwt_type: '' });
});

test.each([
  { employment_status: 'unknown' }, { employment_status: null }, { employment_status: [] },
  { pkwt_type: 'unknown' }, { pkwt_type: null }, { pkwt_type: {} },
])('employee decoder rejects malformed present classification %j', classification => {
  expect(() => decodeEmployee({ ...identity, ...classification })).toThrow();
});

test.each(['', 'kontrak', 'freelance', 'magang', 'permanen'])('employee decoder retains valid status %s and permits omitted restricted fields', employment_status => {
  expect(decodeEmployee({ ...identity, employment_status })).toMatchObject({ employment_status });
  expect(decodeEmployee(identity)).toEqual(identity);
});

test('HR detail renders blank classification without inference', async () => {
  const { user } = setup();
  await screen.findByRole('heading', { name: 'Ubah data pegawai' });
  await user.click(screen.getByRole('button', { name: 'Batal' }));
  await screen.findByRole('heading', { name: identity.full_name });
  for (const label of ['Status Kepegawaian', 'Tipe PKWT']) {
    const fact = screen.getByText(label).closest('.employee-fact')!;
    expect(within(fact as HTMLElement).getByText('Belum diisi')).toBeVisible();
  }
});
