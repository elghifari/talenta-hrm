import { useParams } from 'react-router';
import { useSession } from '../auth/SessionProvider';
import { ApiError, errorText } from '../api/client';
import { EmployeeForm } from './EmployeeForm';
import { decodeEmployee } from './types';
import { useEmployeeRead } from './useEmployeeRead';
function Editor() {
  const { id } = useParams(); const resource = useEmployeeRead('/api/employees/' + id + '/', decodeEmployee);
  if (resource.loading) return <p role="status">Memuat data pegawai…</p>;
  if (resource.error) return <div role="alert"><h1>{resource.error instanceof ApiError && resource.error.status === 404 ? 'Data pegawai tidak tersedia' : 'Data belum dapat dimuat'}</h1><p>{errorText(resource.error)}</p><button onClick={resource.retry}>Coba lagi</button></div>;
  return <EmployeeForm key={resource.data!.id} employee={resource.data} />;
}
export function EmployeeEditPage() {
  const { identity } = useSession();
  return identity?.capabilities.employees_write ? <Editor /> : <h1>Akses tidak tersedia</h1>;
}
