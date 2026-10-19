import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate, useOutletContext } from 'react-router';
import { ApiError, errorText, isAbort } from '../api/client';
import { useSession } from '../auth/SessionProvider';
import { changedFields, saveEmployee } from './api';
import { decodeEmployee, type Employee, type EmployeeInput } from './types';
import { useUnsavedChanges } from './useUnsavedChanges';
type Errors = Partial<Record<keyof EmployeeInput, string>>;
export function EmployeeForm({ employee }: { employee?: Employee }) {
  const original = employee ?? { employee_code: '', full_name: '' };
  const [values, setValues] = useState<EmployeeInput>({ employee_code: original.employee_code, full_name: original.full_name });
  const [errors, setErrors] = useState<Errors>({}); const [summary, setSummary] = useState('');
  const [busy, setBusy] = useState(false); const [confirmed, setConfirmed] = useState(false); const [uncertain, setUncertain] = useState(false);
  const { request } = useSession(); const navigate = useNavigate();
  const { setDirty } = useOutletContext<{ setDirty(value: boolean): void }>();
  const alive = useRef(true); const controller = useRef(new AbortController()); const allowLeave = useRef(false);
  const changes = changedFields(original, values); const dirty = !confirmed && Object.keys(changes).length > 0;
  const blocker = useUnsavedChanges(dirty || busy, allowLeave);
  const form = useRef<HTMLFormElement>(null);
  useEffect(() => { setDirty(dirty); return () => setDirty(false); }, [setDirty, dirty]);
  useEffect(() => () => { alive.current = false; controller.current.abort(); }, []);
  function showErrors(next: Errors) {
    setErrors(next);
    requestAnimationFrame(() => { const field = Object.keys(next)[0]; if (field) (form.current?.elements.namedItem(field) as HTMLElement | null)?.focus(); });
  }
  async function submit(event: FormEvent) {
    event.preventDefault(); if (busy || confirmed || uncertain) return;
    const next: Errors = {};
    const input = { employee_code: values.employee_code.trim(), full_name: values.full_name.trim() };
    if (!input.employee_code) next.employee_code = 'Kode pegawai wajib diisi.';
    else if (input.employee_code.length > 64) next.employee_code = 'Kode pegawai maksimal 64 karakter.';
    if (!input.full_name) next.full_name = 'Nama lengkap wajib diisi.';
    else if (input.full_name.length > 200) next.full_name = 'Nama lengkap maksimal 200 karakter.';
    if (Object.keys(next).length) { showErrors(next); return; }
    const payload = employee ? changedFields(original, input) : input;
    if (employee && !Object.keys(payload).length) return;
    setBusy(true); setErrors({}); setSummary('');
    try {
      const saved = await saveEmployee(request, payload, employee?.id, controller.current.signal);
      if (!alive.current) return;
      allowLeave.current = true; setConfirmed(true); setDirty(false);
      try {
        decodeEmployee(await request('/api/employees/' + saved.id + '/', { signal: controller.current.signal }));
      } catch (e) {
        if (isAbort(e) || !alive.current) return;
        setSummary('Data tersimpan, tetapi belum dapat dimuat ulang. Buka detail untuk memeriksa data terbaru.');
        return;
      }
      if (alive.current) navigate('/employees/' + saved.id, { replace: true, state: { saved: true } });
    } catch (error) {
      if (!alive.current || isAbort(error)) return;
      if (error instanceof ApiError && error.status === 400 && error.body && typeof error.body === 'object') {
        const fields: Errors = {}; const other: string[] = [];
        for (const [key, value] of Object.entries(error.body)) {
          const text = Array.isArray(value) && value.every(x => typeof x === 'string') ? value.join(' ') : typeof value === 'string' ? value : 'Data tidak valid.';
          if (key === 'employee_code' || key === 'full_name') fields[key] = text; else other.push(text);
        }
        showErrors(fields); setSummary(other.join(' '));
      } else { setSummary(errorText(error)); if (error instanceof ApiError && error.writeOutcome === 'uncertain') setUncertain(true); }
    } finally { if (alive.current) setBusy(false); }
  }
  return <><Link className="back" to={employee ? '/employees/' + employee.id : '/employees'}>Kembali ke {employee ? 'detail pegawai' : 'data pegawai'}</Link>
    <div className="page-heading"><div><h1>{employee ? 'Ubah data pegawai' : 'Tambah pegawai'}</h1><p>{employee ? 'Perbarui identitas pegawai.' : 'Buat identitas pegawai. Penugasan unit dilakukan terpisah.'}</p></div></div>
    {blocker.state === 'blocked' && <section className="notice" role="alertdialog" aria-label="Perubahan belum disimpan"><p>Perubahan belum disimpan. Tinggalkan halaman ini?</p><div className="form-actions"><button autoFocus onClick={() => blocker.reset()}>Tetap mengedit</button><button onClick={() => blocker.proceed()}>Tinggalkan halaman</button></div></section>}
    {summary && <div className={confirmed ? 'notice' : 'error'} role="alert"><p>{summary}</p>{(confirmed || uncertain) && <Link to={employee ? '/employees/' + employee.id : '/employees'}>Periksa data tersimpan</Link>}</div>}
    {confirmed ? <Link to={employee ? '/employees/' + employee.id : '/employees'}>Buka data pegawai</Link> : <form ref={form} className="record" onSubmit={submit} noValidate>
      <div className="form-field"><label htmlFor="employee-code">Kode pegawai</label><input id="employee-code" name="employee_code" value={values.employee_code} maxLength={64} required aria-invalid={Boolean(errors.employee_code)} aria-describedby="code-hint code-error" disabled={busy || uncertain} onChange={e => setValues(v => ({ ...v, employee_code: e.target.value }))} /><p className="hint" id="code-hint">Gunakan kode unik. Nol di depan tetap disimpan.</p>{errors.employee_code && <p className="error" id="code-error">{errors.employee_code}</p>}</div>
      <div className="form-field"><label htmlFor="employee-name">Nama lengkap</label><input id="employee-name" name="full_name" value={values.full_name} maxLength={200} required aria-invalid={Boolean(errors.full_name)} aria-describedby={errors.full_name ? 'name-error' : undefined} disabled={busy || uncertain} onChange={e => setValues(v => ({ ...v, full_name: e.target.value }))} />{errors.full_name && <p className="error" id="name-error">{errors.full_name}</p>}</div>
      <div className="form-actions"><button className="primary" disabled={busy || uncertain || (Boolean(employee) && !dirty)} type="submit">{busy ? 'Menyimpan…' : employee ? 'Simpan perubahan' : 'Simpan pegawai'}</button><button type="button" disabled={busy} onClick={() => navigate(employee ? '/employees/' + employee.id : '/employees')}>Batal</button></div>
    </form>}
  </>;
}
