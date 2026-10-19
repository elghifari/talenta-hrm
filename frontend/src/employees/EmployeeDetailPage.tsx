import { Link, useLocation, useParams } from 'react-router';
import { PageTitle } from '../app/PageTitle';
import { useSession } from '../auth/SessionProvider';
import { ApiError, errorText } from '../api/client';
import { decodeEmployee } from './types';
import { useEmployeeRead } from './useEmployeeRead';
export function EmployeeDetailPage() {
  const { identity } = useSession(); const location = useLocation();
  const { id } = useParams(); const resource = useEmployeeRead('/api/employees/' + id + '/', decodeEmployee);
  return <><Link className="back" to="/employees">Kembali ke data pegawai</Link>
    {resource.loading && <p role="status">Memuat data pegawai…</p>}
    {Boolean(resource.error) && <div role="alert"><PageTitle>{resource.error instanceof ApiError && resource.error.status === 404 ? 'Data pegawai tidak tersedia' : 'Data belum dapat dimuat'}</PageTitle><p>{resource.error instanceof ApiError && resource.error.status === 404 ? 'Data tidak ditemukan atau tidak tersedia bagi akun ini.' : errorText(resource.error)}</p><button onClick={resource.retry}>Coba lagi</button></div>}
    {resource.data && <><div className="page-heading"><div><PageTitle>{resource.data.full_name}</PageTitle><p>Identitas pegawai</p></div>{identity?.capabilities.employees_write && <Link className="primary" to={'/employees/' + id + '/edit'}>Ubah data</Link>}</div>{location.state?.saved && <p className="success" role="status">Data pegawai tersimpan.</p>}<section className="record"><dl><dt>Kode pegawai</dt><dd>{resource.data.employee_code}</dd><dt>Nama lengkap</dt><dd>{resource.data.full_name}</dd></dl></section></>}
  </>;
}
