import { useLocation, useParams } from 'react-router';
import { PageTitle } from '../app/PageTitle';
import { useSession } from '../auth/SessionProvider';
import { ApiError, errorText } from '../api/client';
import { decodeEmployee } from './types';
import { useEmployeeRead } from './useEmployeeRead';
import { EmployeeDetailView } from './EmployeeDetailView';
import { Link } from 'react-router';
import { ContractHistory } from '../contracts/ContractHistory';
import '../contracts/contracts.css';
export function EmployeeDetailPage() {
  const { identity } = useSession(); const location = useLocation();
  const { id } = useParams(); const resource = useEmployeeRead('/api/employees/' + id + '/', decodeEmployee);
  return <>
    {resource.loading && <p role="status">Memuat data pegawai…</p>}
    {Boolean(resource.error) && <div role="alert"><PageTitle>{resource.error instanceof ApiError && resource.error.status === 404 ? 'Data pegawai tidak tersedia' : 'Data belum dapat dimuat'}</PageTitle><p>{resource.error instanceof ApiError && resource.error.status === 404 ? 'Data tidak ditemukan atau tidak tersedia bagi akun ini.' : errorText(resource.error)}</p><button onClick={resource.retry}>Coba lagi</button></div>}
    {resource.data && <>{location.state?.saved && <p className="success" role="status">Data pegawai tersimpan.</p>}<EmployeeDetailView employee={resource.data} writable={Boolean(identity?.capabilities.employees_write)} />{identity?.capabilities.employees_write && <section className="record contract-documents" aria-labelledby="employee-contract"><h2 id="employee-contract">Kontrak</h2>{resource.data.employment_status === 'kontrak' || resource.data.employment_status === 'magang' ? <Link to={'/employees/' + resource.data.id + '/contracts/new'}>Buat draf perpanjangan</Link> : <p>Lengkapi klasifikasi kontrak pada <Link to={'/employees/' + resource.data.id + '/edit'}>data pegawai</Link>.</p>}<ContractHistory employeeId={resource.data.id} /></section>}</>}
  </>;
}
