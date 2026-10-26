import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ApiError, isAbort } from '../api/client';
import { useSession } from '../auth/SessionProvider';
import { choiceError, saveChoice, type GroupChoice, type GroupKind } from './group-api';

export type GroupEdit = { kind: GroupKind; record?: GroupChoice };
type Props = { edit: GroupEdit; branches: GroupChoice[]; reportDirty(value: boolean): void; saved(owner?: string): void; cancel(): void; refresh(): void };
export function GroupEditor({ edit, branches, reportDirty, saved, cancel, refresh }: Props) {
  const label = edit.kind === 'branches' ? 'cabang' : 'divisi';
  const [name, setName] = useState(edit.record?.name ?? '');
  const [branch, setBranch] = useState(edit.record?.branch ?? '');
  const [busy, setBusy] = useState(false); const [uncertain, setUncertain] = useState(false); const [error, setError] = useState('');
  const { request } = useSession(); const input = useRef<HTMLInputElement>(null); const controller = useRef(new AbortController());
  const dirty = name !== (edit.record?.name ?? '') || Boolean(!edit.record && branch) || busy || uncertain;
  useEffect(() => { reportDirty(dirty); return () => reportDirty(false); }, [dirty, reportDirty]);
  useEffect(() => { input.current?.focus(); const control = new AbortController(); controller.current = control; return () => control.abort(); }, []);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (busy || uncertain) return;
    if (!name.trim()) { setError('Nama wajib diisi.'); input.current?.focus(); return; }
    if (edit.kind === 'divisions' && !edit.record && !branch) { setError('Cabang wajib dipilih.'); return; }
    setBusy(true); setError('');
    try {
      await saveChoice(request, edit.kind, { name: name.trim(), ...(edit.kind === 'divisions' && !edit.record ? { branch } : {}) }, edit.record?.id, controller.current.signal);
      if (!controller.current.signal.aborted) saved(branch || undefined);
    } catch (failure) {
      if (!controller.current.signal.aborted && !isAbort(failure)) {
        setError(choiceError(failure));
        if (failure instanceof ApiError && failure.writeOutcome === 'uncertain') setUncertain(true);
        else input.current?.focus();
      }
    } finally { if (!controller.current.signal.aborted) setBusy(false); }
  }
  return <form className="record organization-editor" aria-label={(edit.record ? 'Ubah nama ' : 'Tambah ') + label} onSubmit={submit}>
    <h2>{edit.record ? 'Ubah nama ' : 'Tambah '}{label}</h2>
    {error && <p id="group-editor-error" className="error" role="alert">{error}</p>}
    {uncertain && <p className="notice">Hasil penyimpanan belum pasti. Jangan kirim ulang. <button type="button" onClick={refresh}>Periksa daftar terbaru</button></p>}
    {edit.kind === 'divisions' && (edit.record ? <p className="hint">Cabang: {branches.find(item => item.id === branch)?.name ?? edit.record.branch_name}</p> : <div className="form-field"><label htmlFor="division-owner">Cabang pemilik divisi</label><select id="division-owner" value={branch} required disabled={busy || uncertain} onChange={event => { setBranch(event.target.value); setError(''); }}><option value="">Pilih cabang</option>{branches.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div>)}
    <div className="form-field"><label htmlFor="group-editor-name">Nama {label}{edit.record ? ' baru' : ''}</label><input ref={input} id="group-editor-name" value={name} maxLength={150} disabled={busy || uncertain} aria-invalid={Boolean(error)} aria-describedby={error ? 'group-editor-error' : undefined} onChange={event => { setName(event.target.value); setError(''); }} /></div>
    <div className="form-actions"><button className="primary" type="submit" disabled={busy || uncertain || Boolean(edit.record && name.trim() === edit.record.name) || (edit.kind === 'divisions' && !edit.record && !branch)}>{busy ? 'Menyimpan…' : edit.record ? 'Simpan nama' : 'Simpan ' + label}</button><button type="button" disabled={busy || uncertain} onClick={() => { if (!dirty || window.confirm('Batalkan perubahan yang belum disimpan?')) cancel(); }}>Batal</button></div>
  </form>;
}
