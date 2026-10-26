import { Link } from 'react-router';
import { errorText } from '../api/client';
import { useSession } from '../auth/SessionProvider';
import { PageTitle } from '../app/PageTitle';
import { decodeChoices, decodeDivisionChoices } from './group-api';
import { decodeEmployees, type Employee } from './types';
import { useEmployeeRead } from './useEmployeeRead';
import './personnel.css';

function Metric({ label, value, to }: { label: string; value: number; to: string }) {
  return <Link className="personnel-metric" to={to}><span>{label}</span><strong>{value.toLocaleString('id-ID')}</strong><span className="personnel-metric-link">Lihat detail <span aria-hidden="true">→</span></span></Link>;
}
function OrganizationMetrics() {
  const branches = useEmployeeRead('/api/organization/branches/', decodeChoices);
  const divisions = useEmployeeRead('/api/organization/divisions/', decodeDivisionChoices);
  return <>{[{ label: 'Cabang', resource: branches }, { label: 'Divisi', resource: divisions }].map(({ label, resource }) => resource.data ? <Metric key={label} label={label} value={resource.data.length} to="/employees/groups" /> : <div key={label} className="personnel-metric"><span>{label}</span>{resource.error ? <div role="alert"><p>{errorText(resource.error)}</p><button onClick={resource.retry}>Coba lagi</button></div> : <p role="status">Memuat…</p>}</div>)}</>;
}
function ContractList({ employees }: { employees: Employee[] }) {
  const dateFormat = new Intl.DateTimeFormat('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
  return <section className="personnel-contracts" id="contract-expiries" aria-labelledby="contract-heading"><header><h2 id="contract-heading">Kontrak segera berakhir</h2><p>Hari ini hingga 30 hari ke depan</p></header>{employees.length ? <div className="personnel-contract-table" role="region" aria-label="Kontrak segera berakhir" tabIndex={0}><table><thead><tr><th scope="col">Karyawan</th><th scope="col">Cabang / Divisi</th><th scope="col">Kontrak berakhir</th></tr></thead><tbody>{employees.map(employee => <tr key={employee.id}><td><Link to={'/employees/' + employee.id}>{employee.full_name}</Link><span className="personnel-contract-id">{employee.employee_code}</span></td><td>{[employee.branch_name, employee.division_name].filter(Boolean).join(' / ') || '—'}</td><td><time dateTime={employee.contract_expiry!}>{dateFormat.format(new Date(employee.contract_expiry! + 'T12:00:00'))}</time></td></tr>)}</tbody></table></div> : <p className="personnel-contract-empty">Tidak ada kontrak yang berakhir dalam 30 hari ke depan.</p>}</section>;
}
export function PersonnelPage() {
  const { identity } = useSession();
  const writable = Boolean(identity?.capabilities.employees_write);
  const employees = useEmployeeRead('/api/employees/', decodeEmployees);
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const end = new Date(today); end.setDate(end.getDate() + 30);
  const expiring = writable ? (employees.data ?? []).filter(employee => {
    if (!employee.contract_expiry) return false;
    const date = new Date(employee.contract_expiry + 'T00:00:00');
    return date >= today && date <= end;
  }).sort((a, b) => a.contract_expiry!.localeCompare(b.contract_expiry!) || a.employee_code.localeCompare(b.employee_code, 'id', { numeric: true })) : [];
  return <><div className="page-heading"><div><PageTitle>Personnel</PageTitle><p>Ringkasan kepegawaian</p></div><Link className="primary" to="/employees">Data pegawai</Link></div>
    {!writable && <p className="notice">Ringkasan mengikuti hak akses unit Anda.</p>}
    {employees.loading && <p role="status">Memuat ringkasan pegawai…</p>}
    {Boolean(employees.error) && <div role="alert"><p>{errorText(employees.error)}</p><button onClick={employees.retry}>Coba lagi</button></div>}
    <div className="personnel-metrics">{employees.data && <Metric label="Karyawan" value={employees.data.length} to="/employees" />}{writable && <OrganizationMetrics />}{writable && employees.data && <a className="personnel-metric" href="#contract-expiries"><span>Kontrak segera berakhir</span><strong>{expiring.length.toLocaleString('id-ID')}</strong><span className="personnel-metric-link">Dalam 30 hari <span aria-hidden="true">↓</span></span></a>}</div>
    {writable && employees.data && <ContractList employees={expiring} />}
  </>;
}
