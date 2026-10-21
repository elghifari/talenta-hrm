import './imports.css';
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useOutletContext, useParams } from 'react-router';
import { isAbort } from '../../api/client';
import { PageTitle } from '../../app/PageTitle';
import { useSession } from '../../auth/SessionProvider';
import { useEmployeeRead } from '../useEmployeeRead';
import { useUnsavedChanges } from '../useUnsavedChanges';
import { confirmBatch, decodeBatch, importError, type ImportBatch } from './api';
import { ImportComparison } from './ImportComparison';

function Preview({ batchId }: { batchId: string }) {
  const resource = useEmployeeRead('/api/employees/imports/' + encodeURIComponent(batchId) + '/', decodeBatch);
  const { request } = useSession(); const navigate = useNavigate();
  const { setDirty } = useOutletContext<{ setDirty(value: boolean): void }>();
  const [receipt, setReceipt] = useState<ImportBatch | null>(null);
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const controller = useRef(new AbortController()); const allowLeave = useRef(false);
  const blocker = useUnsavedChanges(busy, allowLeave);
  useEffect(() => { setDirty(busy); return () => setDirty(false); }, [setDirty, busy]);
  useEffect(() => { const control = new AbortController(); controller.current = control; return () => control.abort(); }, []);
  const batch = receipt ?? resource.data;
  async function confirm() {
    if (!batch || busy || batch.state === 'committed' || batch.summary.error) return;
    setBusy(true); setError('');
    try { const result = await confirmBatch(request, batch.id, controller.current.signal); if (!controller.current.signal.aborted) setReceipt(result); }
    catch (failure) { if (!controller.current.signal.aborted && !isAbort(failure)) setError(importError(failure)); }
    finally { if (!controller.current.signal.aborted) setBusy(false); }
  }
  const committed = batch?.state === 'committed';
  return <><Link className="back" to={committed ? '/employees' : '/employees/import'}>{committed ? 'Kembali ke data pegawai' : 'Pilih CSV lain'}</Link>
    <div className="page-heading"><div><PageTitle key={String(committed)}>{committed ? 'Batch upload tersimpan' : 'Pratinjau batch upload'}</PageTitle>{batch && <p>{committed ? 'Data pegawai telah disimpan. Unggah ulang tidak diperlukan.' : 'Hanya karyawan dari CSV ini yang ditampilkan. Belum ada data pegawai yang disimpan.'}</p>}</div></div>
    {blocker.state === 'blocked' && <section className="notice" role="alertdialog" aria-label="Permintaan masih berjalan"><p>Permintaan masih berjalan. Tinggalkan halaman?</p><div className="form-actions"><button autoFocus onClick={() => blocker.reset()}>Tetap di pratinjau</button><button onClick={() => blocker.proceed()}>Tinggalkan halaman</button></div></section>}
    {resource.loading && !receipt && <p role="status">Memuat pratinjau CSV…</p>}
    {Boolean(resource.error) && !receipt && <div role="alert"><p className="error">{importError(resource.error)}</p><button onClick={resource.retry}>Coba lagi</button></div>}
    {batch && <>
      <p className={committed ? 'success' : 'import-totals'} role={committed ? 'status' : undefined}>{batch.summary.new} baru, {batch.summary.update} diperbarui, {batch.summary.unchanged} tidak berubah, {batch.summary.error} bermasalah.</p>
      {!committed && <>
        {batch.rows.some(row => row.current) && <section className="notice"><p>ID Karyawan existing terdeteksi, apakah anda ingin meng-update informasi karyawan berikut?</p><ul>{batch.rows.filter(row => row.current).map(row => <li key={row.row}>{row.employee_code} - {row.current!.full_name}</li>)}</ul><p>Hanya kolom yang berubah pada baris Upd yang diperbarui.</p></section>}
        <p className="hint">New: baru. Upd: diperbarui. -: tidak berubah. !: perlu diperbaiki. Buka baris untuk membandingkan kolom.</p>
        <div className="import-head" aria-hidden="true"><span>ID Karyawan</span><span>Nama lengkap</span><span>Ringkasan perubahan</span></div>
        <ul className="import-rows" aria-label="Baris CSV">{batch.rows.map(row => <ImportComparison key={row.row} row={row} />)}</ul>
        {batch.summary.error > 0 && <p className="error" role="alert">Perbaiki baris bermasalah lalu unggah CSV kembali. Seluruh batch belum dapat disimpan.</p>}
        {error && <p className="error" role="alert">{error}</p>}
        <div className="form-actions"><button className="primary" disabled={busy || batch.summary.error > 0} onClick={confirm}>{busy ? 'Menyimpan batch…' : 'Konfirmasi upload'}</button><button disabled={busy} onClick={() => { allowLeave.current = true; navigate('/employees'); }}>Batal</button></div>
      </>}
    </>}
  </>;
}
export function ImportPreviewPage() {
  const { batchId } = useParams(); const { identity } = useSession();
  return identity?.capabilities.employees_write ? <Preview key={batchId} batchId={batchId ?? ''} /> : <PageTitle>Akses tidak diizinkan</PageTitle>;
}
