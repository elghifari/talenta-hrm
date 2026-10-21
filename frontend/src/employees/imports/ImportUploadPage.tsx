import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import { isAbort } from '../../api/client';
import { PageTitle } from '../../app/PageTitle';
import { useSession } from '../../auth/SessionProvider';
import { importError, previewCsv } from './api';

export function ImportUploadPage() {
  const { identity, request } = useSession(); const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const controller = useRef(new AbortController());
  useEffect(() => { const control = new AbortController(); controller.current = control; return () => control.abort(); }, []);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!file || busy) return;
    if (file.size > 1024 * 1024) { setError('Ukuran CSV maksimal 1 MiB.'); return; }
    setBusy(true); setError('');
    try {
      const batch = await previewCsv(request, file, controller.current.signal);
      if (!controller.current.signal.aborted) navigate('/employees/imports/' + batch.id);
    } catch (failure) {
      if (!controller.current.signal.aborted && !isAbort(failure)) setError(importError(failure));
    } finally { if (!controller.current.signal.aborted) setBusy(false); }
  }
  if (!identity?.capabilities.employees_write) return <PageTitle>Akses tidak diizinkan</PageTitle>;
  return <><Link className="back" to="/employees">Kembali ke data pegawai</Link>
    <div className="page-heading"><div><PageTitle>Batch upload</PageTitle><p>Tambahkan atau perbarui karyawan melalui CSV. Periksa perubahan sebelum menyimpan.</p></div></div>
    <form className="record" onSubmit={submit}>
      <p><a className="back" href="/api/employees/import-template/" download>Unduh template CSV</a></p>
      <p className="hint" id="csv-help">CSV UTF-8, maksimal 1 MiB dan 500 baris. Urutan kolom bebas. ID Karyawan dan Nama Lengkap wajib ada. Simpan ID sebagai teks agar nol di depan tetap ada.</p>
      <p className="hint">Tanggal menggunakan YYYY-MM-DD. Kolom atau sel opsional yang kosong tidak menghapus data lama.</p>
      <div className="form-field"><label htmlFor="csv-file">File CSV</label><input id="csv-file" type="file" accept=".csv,text/csv" aria-describedby="csv-help" disabled={busy} onChange={event => { setFile(event.target.files?.[0] ?? null); setError(''); }} /></div>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="form-actions"><button className="primary" disabled={!file || busy}>{busy ? 'Memuat pratinjau…' : 'Pratinjau CSV'}</button><Link className="primary secondary" to="/employees">Batal</Link></div>
    </form></>;
}
