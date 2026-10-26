import { Link } from 'react-router';
import { errorText } from '../api/client';
import { useSession } from '../auth/SessionProvider';
import { decodeEmployees } from './types';
import { useEmployeeRead } from './useEmployeeRead';
import { EmployeeTable } from './EmployeeTable';
export function EmployeeListPage() {
  const { identity } = useSession(); const writable = identity!.capabilities.employees_write;
  const resource = useEmployeeRead('/api/employees/', decodeEmployees);
  return <><div className="page-heading"><div><h1>Data pegawai</h1><p>{writable ? 'Kelola identitas dan data kepegawaian.' : 'Lihat identitas pegawai dalam lingkup unit Anda.'}</p></div>{writable && <div className="form-actions"><Link className="primary" to="/employees/new">Tambah pegawai</Link><Link className="primary secondary" to="/employees/import">Batch Upload</Link></div>}</div>

    {!writable && <p className="notice">Akses baca saja. Data yang terlihat mengikuti hak akses unit Anda.</p>}
    {resource.loading && <p role="status">Memuat data pegawai…</p>}
    {Boolean(resource.error) && <div role="alert"><p>{errorText(resource.error)}</p><button onClick={resource.retry}>Coba lagi</button></div>}
    {resource.data && (resource.data.length ? <EmployeeTable employees={resource.data} showPrivate={writable} /> : <section className="empty"><h2>Belum ada pegawai</h2><p>{writable ? 'Tambahkan identitas pegawai pertama. Penugasan unit dikelola terpisah.' : 'Belum ada pegawai yang tersedia dalam lingkup akses Anda. Hubungi HR bila akses perlu diperiksa.'}</p></section>)}

  </>;
}
