import { useSession } from '../auth/SessionProvider';
import { EmployeeForm } from './EmployeeForm';
export function EmployeeCreatePage() {
  const { identity } = useSession();
  return identity?.capabilities.employees_write ? <EmployeeForm /> : <h1>Akses tidak tersedia</h1>;
}
