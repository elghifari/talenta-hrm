import { Link, useParams } from 'react-router';
import { ApiError, errorText } from '../api/client';
import { decodeEmployee } from './types';
import { useEmployeeRead } from './useEmployeeRead';
export function EmployeeDetailPage() {
  const { id } = useParams(); const resource = useEmployeeRead('/api/employees/' + id + '/', decodeEmployee);
  return <><Link className="back" to="/employees">Kembali ke data pegawai</Link>
    {resource.loading && <p role="status">Memuat data pegawai…</p>}
    {Boolean(resource.error) && <div role="alert"><h1>{resource.error instanceof ApiError && resource.error.status === 404 ? 'Data pegawai tidak tersedia' : 'Data belum dapat dimuat'}</h1><p>{resource.error instanceof ApiError && resource.error.status === 404 ? 'Data tidak ditemukan atau tidak tersedia bagi akun ini.' : errorText(resource.error)}</p><button onClick={resource.retry}>Coba lagi</button></div>}
    {resource.data && <><div className="page-heading"><div><h1>{resource.data.full_name}</h1><p>Identitas pegawai</p></div></div><section className="record"><dl><dt>Kode pegawai</dt><dd>{resource.data.employee_code}</dd><dt>Nama lengkap</dt><dd>{resource.data.full_name}</dd></dl></section></>}
  </>;
}
