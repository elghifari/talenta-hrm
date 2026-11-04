import './imports.css';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate, useOutletContext, useParams } from 'react-router';
import { ApiError, isAbort } from '../../api/client';
import { PageTitle } from '../../app/PageTitle';
import { useSession } from '../../auth/SessionProvider';
import { useEmployeeRead } from '../useEmployeeRead';
import { useUnsavedChanges } from '../useUnsavedChanges';
import { confirmBatch, decodeBatch, importError, previewCsv, type ImportBatch } from './api';
import { ImportComparison } from './ImportComparison';
import { ImportReferenceFixes } from './ImportReferenceFixes';
import type { ImportSource } from './source';

function Preview({ batchId }: { batchId: string }) {
  const resource = useEmployeeRead('/api/employees/imports/' + encodeURIComponent(batchId) + '/', decodeBatch);
  const { request } = useSession(); const navigate = useNavigate();
  const { setDirty, importFile, setImportFile } = useOutletContext<ImportSource & { setDirty(value: boolean): void }>();
  const sourceFile = importFile?.batchId === batchId ? importFile.file : null;
  const [receipt, setReceipt] = useState<ImportBatch | null>(null);
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const [uncertain, setUncertain] = useState(false); const [blocked, setBlocked] = useState(false);
  const [fixBusy, setFixBusy] = useState(false);
  const [replacementFile, setReplacementFile] = useState<File | null>(null);
  const controller = useRef(new AbortController()); const allowLeave = useRef(false);
  const blocker = useUnsavedChanges(busy || uncertain || fixBusy, allowLeave);
  useEffect(() => { setDirty(busy || uncertain || fixBusy); return () => setDirty(false); }, [setDirty, busy, uncertain, fixBusy]);
  useEffect(() => { const control = new AbortController(); controller.current = control; return () => control.abort(); }, []);
  const batch = receipt ?? resource.data;
  async function confirm() {
    if (!batch || busy || fixBusy || uncertain || blocked || batch.state === 'committed' || batch.summary.error) return;
    setBusy(true); setError('');
    try { const result = await confirmBatch(request, batch.id, controller.current.signal); if (!controller.current.signal.aborted) { setReceipt(result); setImportFile(null); } }
    catch (failure) {
      if (!controller.current.signal.aborted && !isAbort(failure)) {
        setError(importError(failure));
        if (failure instanceof ApiError && failure.writeOutcome === 'uncertain') setUncertain(true);
        if (failure instanceof ApiError && [404, 409, 410].includes(failure.status ?? 0)) setBlocked(true);
      }
    }
    finally { if (!controller.current.signal.aborted) setBusy(false); }
  }
  async function repreview(event: FormEvent) {
    event.preventDefault();
    const file = replacementFile ?? sourceFile;
    if (!file || busy || fixBusy || uncertain) return;
    if (file.size > 1024 * 1024) { setError('Ukuran CSV maksimal 1 MiB.'); return; }
    setBusy(true); setError('');
    try {
      const next = await previewCsv(request, file, controller.current.signal);
      if (controller.current.signal.aborted) return;
      setImportFile({ batchId: next.id, file }); allowLeave.current = true;
      navigate('/employees/imports/' + next.id, { replace: true });
    } catch (failure) {
      if (!controller.current.signal.aborted && !isAbort(failure)) setError(importError(failure));
    } finally { if (!controller.current.signal.aborted) setBusy(false); }
  }
  async function readReceipt() {
    if (busy) return;
    setBusy(true);
    try {
      const result = decodeBatch(await request('/api/employees/imports/' + encodeURIComponent(batchId) + '/', { signal: controller.current.signal }));
      if (controller.current.signal.aborted) return;
      if (result.state === 'committed') { setReceipt(result); setUncertain(false); setError(''); }
      else setError('Hasil impor belum bisa dikonfirmasi. Coba periksa lagi.');
    } catch (failure) {
      if (!controller.current.signal.aborted && !isAbort(failure)) setError('Hasil impor belum bisa dikonfirmasi. Periksa data pegawai.');
    } finally { if (!controller.current.signal.aborted) setBusy(false); }
  }
  const committed = batch?.state === 'committed';
  return <><Link className="back" to={committed ? '/employees' : '/employees/import'}>{committed ? 'Kembali ke data pegawai' : 'Pilih CSV lain'}</Link>
    <div className="page-heading"><div><PageTitle key={String(committed)}>{committed ? 'Batch Upload tersimpan' : 'Preview Batch Upload'}</PageTitle>{batch && <p>{committed ? 'Data pegawai berhasil diimpor.' : uncertain ? 'Periksa hasil impor.' : 'Periksa data dari CSV sebelum menyimpan.'}</p>}</div></div>
    {blocker.state === 'blocked' && <section className="notice" role="alertdialog" aria-label="Permintaan masih berjalan"><p>Permintaan masih berjalan. Tinggalkan halaman?</p><div className="form-actions"><button autoFocus onClick={() => blocker.reset()}>Tetap di preview</button><button onClick={() => blocker.proceed()}>Tinggalkan halaman</button></div></section>}
    {resource.loading && !receipt && <p role="status">Memuat preview CSV…</p>}
    {Boolean(resource.error) && !receipt && <div role="alert"><p className="error">{importError(resource.error)}</p><button onClick={resource.retry}>Coba lagi</button></div>}
    {batch && <>
      <p className={committed ? 'success' : 'import-totals'} role={committed ? 'status' : undefined}>{batch.summary.new} baru, {batch.summary.update} diperbarui, {batch.summary.unchanged} tidak berubah, {batch.summary.error} bermasalah.</p>
      {!committed && <>
        {batch.rows.some(row => row.missing_hierarchy?.length) && <ImportReferenceFixes rows={batch.rows} reportBusy={setFixBusy} />}
        {batch.summary.error > 0 && <form className="record import-repreview" onSubmit={repreview}>
          <h2>Perbarui preview</h2>
          <p>Setelah Unit/Divisi ditambahkan, periksa CSV lagi. Untuk kesalahan nama atau data lain, pilih file yang sudah diperbaiki.</p>
          {sourceFile && <p>File saat ini: <strong>{sourceFile.name}</strong></p>}
          <div className="form-field"><label htmlFor="replacement-csv">File CSV untuk preview ulang</label><input id="replacement-csv" type="file" accept=".csv,text/csv" disabled={busy || fixBusy || uncertain} onChange={event => setReplacementFile(event.target.files?.[0] ?? null)} /></div>
          {!sourceFile && !replacementFile && <p className="hint">Pilih kembali CSV untuk melanjutkan preview.</p>}
          <button className="primary" type="submit" disabled={busy || fixBusy || uncertain || (!replacementFile && !sourceFile)}>{busy ? 'Memuat preview…' : 'Perbarui preview'}</button>
        </form>}
        {batch.rows.some(row => row.current) && <section className="notice"><p>Beberapa ID Karyawan sudah terdaftar. Periksa perubahan berikut.</p><ul>{batch.rows.filter(row => row.current).map(row => <li key={row.row}>{row.employee_code} - {row.current!.full_name}</li>)}</ul><p>Hanya kolom yang berubah pada baris Upd yang diperbarui.</p></section>}
        <p className="hint">New: baru. Upd: diperbarui. -: tidak berubah. !: perlu diperbaiki. Buka baris untuk membandingkan kolom.</p>
        <div className="import-head" aria-hidden="true"><span>Baris CSV</span><span>ID Karyawan</span><span>Nama lengkap</span><span>Ringkasan perubahan</span></div>
        <ul className="import-rows" aria-label="Baris CSV">{batch.rows.map(row => <ImportComparison key={row.row} row={row} />)}</ul>
        {batch.summary.error > 0 && <p className="error" role="alert">Perbaiki baris bermasalah, lalu upload ulang CSV.</p>}
        {error && <p className="error" role="alert">{error}</p>}
        {uncertain && <button disabled={busy} onClick={readReceipt}>Periksa hasil</button>}
        <div className="form-actions"><button className="primary" disabled={busy || fixBusy || uncertain || blocked || batch.summary.error > 0} onClick={confirm}>{busy ? 'Menyimpan batch…' : 'Konfirmasi upload'}</button><button disabled={busy || fixBusy} onClick={() => { allowLeave.current = !uncertain; navigate('/employees'); }}>Batal</button></div>
      </>}
    </>}
  </>;
}
export function ImportPreviewPage() {
  const { batchId } = useParams(); const { identity } = useSession();
  return identity?.capabilities.employees_write ? <Preview key={batchId} batchId={batchId ?? ''} /> : <PageTitle>Akses tidak diizinkan</PageTitle>;
}
