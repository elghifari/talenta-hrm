import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ApiError, isAbort } from '../api/client';
import { useSession } from '../auth/SessionProvider';
import { choiceError, decodeChoice, decodeDivisionChoices, divisionSettings, type DivisionChoice, type DivisionSettings, type GroupChoice } from './group-api';
import './branch-dialog.css';

type Props = { branch: GroupChoice; divisions: DivisionChoice[]; reportDirty(value: boolean): void; saved(): void; cancel(): void; refresh(): void };
export function BranchDialog({ branch, divisions, reportDirty, saved, cancel, refresh }: Props) {
  const { request } = useSession();
  const dialog = useRef<HTMLDialogElement>(null);
  const controller = useRef(new AbortController());
  const [name, setName] = useState(branch.name);
  const [originalDivisions] = useState(divisions);
  const [deleted, setDeleted] = useState<({ id: string; employee_count: number; name: string } & DivisionSettings)[]>([]);
  const [deleting, setDeleting] = useState<{ key: string; name: string; count?: number; error?: string } | null>(null);
  const [rows, setRows] = useState(() => divisions.map(item => ({ key: item.id, id: item.id as string | undefined, name: item.name, ...divisionSettings(item) })));
  const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [error, setError] = useState('');
  const [checking, setChecking] = useState(false);
  const dirty = name !== branch.name || deleted.length > 0 || rows.length !== originalDivisions.length || rows.some(row => {
    const original = originalDivisions.find(item => item.id === row.id);
    return !original || row.name !== original.name || row.kinerja_enabled !== original.kinerja_enabled || row.pelimpahan_enabled !== original.pelimpahan_enabled;
  }) || busy || uncertain;
  useEffect(() => { reportDirty(dirty); return () => reportDirty(false); }, [dirty, reportDirty]);
  useEffect(() => {
    const control = new AbortController(); controller.current = control;
    const element = dialog.current; element?.showModal();
    element?.querySelector<HTMLInputElement>('#branch-name')?.focus();
    return () => { control.abort(); element?.close(); };
  }, []);
  async function askDelete(row: { key: string; id?: string; name: string }) {
    if (!row.id) { setRows(previous => previous.filter(item => item.key !== row.key)); return; }
    setDeleting({ key: row.key, name: row.name });
    requestAnimationFrame(() => document.getElementById('cancel-division-delete')?.focus());
    try {
      const impact = await request<{ employee_count: number }>('/api/organization/divisions/' + row.id + '/deletion-impact/', { signal: controller.current.signal });
      if (!Number.isSafeInteger(impact.employee_count) || impact.employee_count < 0) throw new ApiError('protocol', 200, null, null);
      setDeleting(current => current?.key === row.key ? { ...current, count: impact.employee_count } : current);
    } catch (failure) { if (!isAbort(failure)) setDeleting(current => current?.key === row.key ? { ...current, error: choiceError(failure) } : current); }
  }
  function confirmDelete() {
    if (!deleting || deleting.count === undefined) return;
    const row = rows.find(item => item.key === deleting.key);
    if (!row?.id) return;
    setDeleted(previous => [...previous, { id: row.id!, employee_count: deleting.count!, name: row.name, ...divisionSettings(row) }]);
    setRows(previous => previous.filter(item => item.key !== row.key)); setDeleting(null);
    requestAnimationFrame(() => document.getElementById('branch-name')?.focus());
  }
  function close() {
    if (deleting) { setDeleting(null); return; }
    if (busy || checking) return;
    if (!dirty || window.confirm(uncertain ? 'Hasil penyimpanan belum pasti. Tutup editor dan periksa daftar terbaru?' : 'Batalkan perubahan yang belum disimpan?')) { if (uncertain) refresh(); cancel(); }
  }
  async function submit(event: FormEvent) {
    event.preventDefault(); if (busy || uncertain || deleting) return;
    setBusy(true); setError('');
    try {
      const response = await request<{ branch: unknown; divisions: unknown }>('/api/organization/branches/' + branch.id + '/structure/', {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' }, signal: controller.current.signal,
        body: JSON.stringify({ name, deleted: deleted.map(({ id, employee_count }) => ({ id, employee_count })), divisions: rows.map(row => ({ ...(row.id ? { id: row.id } : {}), name: row.name, ...divisionSettings(row) })), expected: { name: branch.name, divisions: Object.fromEntries(originalDivisions.map(row => [row.id, row.name])), settings: Object.fromEntries(originalDivisions.map(row => [row.id, divisionSettings(row)])) } }),
      });
      try { decodeChoice(response.branch); decodeDivisionChoices(response.divisions); } catch { throw new ApiError('protocol', 200, null, 'uncertain'); }
      if (!controller.current.signal.aborted) saved();
    } catch (failure) {
      if (!controller.current.signal.aborted && !isAbort(failure)) { setError(choiceError(failure)); if (failure instanceof ApiError && failure.writeOutcome === 'uncertain') setUncertain(true); }
    } finally { if (!controller.current.signal.aborted) setBusy(false); }
  }
  async function checkSaved() {
    if (checking) return; setChecking(true); setError('');
    try {
      const currentBranch = decodeChoice(await request('/api/organization/branches/' + branch.id + '/', { signal: controller.current.signal }));
      const currentDivisions = decodeDivisionChoices(await request('/api/organization/divisions/', { signal: controller.current.signal })).filter(item => item.branch === branch.id);
      const normalize = (value: string) => value.trim().replace(/\s+/g, ' ');
      const matches = currentBranch.name === normalize(name) && currentDivisions.length === rows.length && deleted.every(row => !currentDivisions.some(item => item.id === row.id)) && rows.every(row => currentDivisions.some(item => (!row.id || row.id === item.id) && item.name === normalize(row.name) && item.kinerja_enabled === row.kinerja_enabled && item.pelimpahan_enabled === row.pelimpahan_enabled));
      if (matches) saved(); else { refresh(); setError('Data tersimpan belum cocok dengan perubahan ini. Tutup editor dan periksa daftar terbaru.'); }
    } catch (failure) { if (!isAbort(failure)) setError(choiceError(failure)); }
    finally { if (!controller.current.signal.aborted) setChecking(false); }
  }
  return <dialog ref={dialog} className="branch-dialog" aria-labelledby="branch-dialog-title" onCancel={event => { event.preventDefault(); close(); }}>
    <form onSubmit={submit}>
      <header className="branch-dialog-header"><h2 id="branch-dialog-title">{deleting ? 'Hapus divisi?' : 'Edit cabang'}</h2><button type="button" onClick={close} disabled={busy || checking} aria-label="Tutup editor"><svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path d="m4 4 10 10M14 4 4 14" stroke="currentColor" strokeWidth="1.5" /></svg></button></header>
      {deleting ? <><div className="branch-dialog-body" role="alert"><p>Hapus divisi <strong>{deleting.name}</strong>?</p>{deleting.error ? <p className="error">{deleting.error}</p> : deleting.count === undefined ? <p role="status">Memeriksa karyawan…</p> : <p>{deleting.count > 0 ? `${deleting.count} karyawan akan tetap di cabang masing-masing, dengan Divisi dikosongkan. Data karyawan tidak dihapus.` : 'Divisi ini belum memiliki karyawan.'}</p>}<p>Penghapusan diterapkan saat Anda menyimpan perubahan.</p></div><footer className="branch-dialog-footer"><button id="cancel-division-delete" type="button" onClick={() => { setDeleting(null); requestAnimationFrame(() => document.getElementById('division-' + deleting.key)?.focus()); }}>Batal</button><button type="button" className="danger" disabled={deleting.count === undefined || Boolean(deleting.error)} onClick={event => { event.preventDefault(); confirmDelete(); }}>Hapus divisi</button></footer></> : <>
      <div className="branch-dialog-body">
        {error && <p role="alert" className="error">{error}</p>}
        {uncertain && <div className="notice"><p>Hasil penyimpanan belum pasti. Periksa sebelum mencoba lagi.</p><button type="button" disabled={checking} onClick={checkSaved}>{checking ? 'Memeriksa…' : 'Periksa data tersimpan'}</button></div>}
        <div className="form-field"><label htmlFor="branch-name">Nama cabang</label><input autoFocus id="branch-name" value={name} maxLength={150} required disabled={busy || uncertain} onChange={event => setName(event.target.value)} /></div>
        <fieldset disabled={busy || uncertain} className="branch-dialog-divisions"><legend>Divisi</legend>
          {rows.map((row, index) => <fieldset className="branch-division" key={row.key} aria-label={'Pengaturan divisi ' + (row.name || (index + 1))}>
            <div className="branch-dialog-row">
              <span className="branch-division-number" aria-hidden="true">{index + 1}.</span>
              <label className="sr-only" htmlFor={'division-' + row.key}>Nama divisi {index + 1}</label>
              <input id={'division-' + row.key} value={row.name} required maxLength={150} onChange={event => setRows(previous => previous.map(item => item.key === row.key ? { ...item, name: event.target.value } : item))} />
              <button type="button" aria-label={'Hapus divisi ' + (row.name || (index + 1))} onClick={() => askDelete(row)}>Hapus</button>
            </div>
            <div className="division-settings">
              <label><input type="checkbox" role="switch" checked={row.kinerja_enabled} onChange={event => setRows(previous => previous.map(item => item.key === row.key ? { ...item, kinerja_enabled: event.target.checked } : item))} />Kinerja</label>
              <label><input type="checkbox" role="switch" checked={row.pelimpahan_enabled} onChange={event => setRows(previous => previous.map(item => item.key === row.key ? { ...item, pelimpahan_enabled: event.target.checked } : item))} />Pelimpahan</label>
            </div>
          </fieldset>)}
          <button type="button" className="branch-add-division" onClick={() => { const key = crypto.randomUUID(); setRows(previous => [...previous, { key, id: undefined, name: '', kinerja_enabled: false, pelimpahan_enabled: false }]); requestAnimationFrame(() => document.getElementById('division-' + key)?.focus()); }}>Tambah divisi</button>
        </fieldset>
        {deleted.length > 0 && <section className="branch-pending-deletions" aria-label="Divisi yang akan dihapus"><h3>Akan dihapus</h3>{deleted.map(item => <div key={item.id}><span>{item.name}</span><button type="button" disabled={busy || uncertain} onClick={() => { setDeleted(previous => previous.filter(entry => entry.id !== item.id)); setRows(previous => [...previous, { key: item.id, id: item.id, name: item.name, ...divisionSettings(item) }]); }}>Batalkan</button></div>)}</section>}
      </div>
      <footer className="branch-dialog-footer"><button type="button" onClick={close} disabled={busy || checking}>{uncertain ? 'Tutup' : 'Batal'}</button><button type="submit" className="primary" disabled={!dirty || busy || uncertain}>{busy ? 'Menyimpan…' : 'Simpan perubahan'}</button></footer>
      </>}
    </form>
  </dialog>;
}
