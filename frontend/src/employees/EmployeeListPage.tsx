import { Link } from 'react-router';
import { errorText } from '../api/client';
import { useSession } from '../auth/SessionProvider';
import { decodeEmployees } from './types';
import { useEmployeeRead } from './useEmployeeRead';
export function EmployeeListPage() {
  const { identity } = useSession(); const writable = identity!.capabilities.employees_write;
  const resource = useEmployeeRead('/api/employees/', decodeEmployees);
  return <><div className="page-heading"><div><h1>Data pegawai</h1><p>{writable ? 'Kelola kode dan nama pegawai.' : 'Lihat identitas pegawai dalam lingkup unit Anda.'}</p></div>{writable && <Link className="primary" to="/employees/new">Tambah pegawai</Link>}</div>
    {!writable && <p className="notice">Akses baca saja. Data yang terlihat mengikuti hak akses unit Anda.</p>}
    {resource.loading && <p role="status">Memuat data pegawai…</p>}
    {Boolean(resource.error) && <div role="alert"><p>{errorText(resource.error)}</p><button onClick={resource.retry}>Coba lagi</button></div>}
    {resource.data && (resource.data.length ? <div className="record-table"><table><thead><tr><th>Kode pegawai</th><th>Nama lengkap</th></tr></thead><tbody>{resource.data.map(employee => <tr key={employee.id}><td className="employee-code"><span className="mobile-label">Kode pegawai</span>{employee.employee_code}</td><td><Link to={'/employees/' + employee.id}>{employee.full_name}</Link></td></tr>)}</tbody></table></div> : <section className="empty"><h2>Belum ada pegawai</h2><p>{writable ? 'Tambahkan identitas pegawai pertama. Penugasan unit dikelola terpisah.' : 'Belum ada pegawai yang tersedia dalam lingkup akses Anda. Hubungi HR bila akses perlu diperiksa.'}</p></section>)}
    <p className="footnote">Kode pegawai disimpan sebagai teks, termasuk nol di depan.</p>
  </>;
}
