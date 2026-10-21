import './imports.css';
import { Link, useParams } from 'react-router';
import { PageTitle } from '../../app/PageTitle';
import { useSession } from '../../auth/SessionProvider';
import { fieldLabel } from '../fields';
import { useEmployeeRead } from '../useEmployeeRead';
import { decodeBatch, importError } from './api';

const marker = { new: 'New', update: 'Upd', unchanged: '-', error: '!' };
const statusLabel = { new: 'Karyawan baru', update: 'Diperbarui', unchanged: 'Tidak berubah', error: 'Perlu diperbaiki' };
function Preview({ batchId }: { batchId: string }) {
  const resource = useEmployeeRead('/api/employees/imports/' + encodeURIComponent(batchId) + '/', decodeBatch);
  return <><Link className="back" to="/employees/import">Pilih CSV lain</Link>
    <div className="page-heading"><div><PageTitle>Pratinjau batch upload</PageTitle><p>Hanya karyawan dari CSV ini yang ditampilkan. Belum ada data pegawai yang disimpan.</p></div></div>
    {resource.loading && <p role="status">Memuat pratinjau CSV…</p>}
    {Boolean(resource.error) && <div role="alert"><p className="error">{importError(resource.error)}</p><button onClick={resource.retry}>Coba lagi</button></div>}
    {resource.data && <ul className="import-rows" aria-label="Baris CSV">{resource.data.rows.map(row => <li className="import-line" key={row.row}>
      <span className={'import-marker ' + (row.status === 'error' ? 'error' : '')} aria-label={statusLabel[row.status]}>{marker[row.status]}</span>
      <div className="import-summary"><span>{row.employee_code}</span><strong>{row.full_name}</strong><span>{row.changes.map(fieldLabel).join(', ') || 'Tidak ada perubahan'}</span></div>
    </li>)}</ul>}
  </>;
}
export function ImportPreviewPage() {
  const { batchId } = useParams(); const { identity } = useSession();
  return identity?.capabilities.employees_write ? <Preview key={batchId} batchId={batchId ?? ''} /> : <PageTitle>Akses tidak diizinkan</PageTitle>;
}
