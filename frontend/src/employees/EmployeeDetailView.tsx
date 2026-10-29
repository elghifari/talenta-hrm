import { Link } from 'react-router';
import { PageTitle } from '../app/PageTitle';
import type { Employee } from './types';
import { fieldValue } from './fields';
import './detail.css';

function Fact({ label, value }: { label: string; value?: string | null }) {
  return <div className="employee-fact"><dt>{label}</dt><dd className={value ? undefined : 'empty-value'}>{value || '-'}</dd></div>;
}
export function EmployeeDetailView({ employee, writable }: { employee: Employee; writable: boolean }) {
  return <article className="record employee-detail">
    <header className="employee-detail-heading"><div><PageTitle>{employee.full_name}</PageTitle><p className="employee-detail-id"><span>ID Karyawan</span><strong>{employee.employee_code}</strong></p></div>{writable && <Link className="primary" to={'/employees/' + employee.id + '/edit'}>Ubah data</Link>}</header>
    <div className={'employee-detail-sections' + (writable ? '' : ' readonly')}>
      <section aria-labelledby="employee-placement"><h2 id="employee-placement">Penempatan</h2><dl className="employee-facts"><Fact label="Cabang" value={employee.branch_name} /><Fact label="Divisi" value={employee.division_name} />{writable && <><Fact label="Jabatan" value={employee.job_title} /><Fact label="Level" value={employee.level} /></>}</dl></section>
      {writable && <div className="employee-detail-secondary"><section aria-labelledby="employee-employment"><h2 id="employee-employment">Masa kerja</h2><dl className="employee-facts"><Fact label="Status Kepegawaian" value={fieldValue(employee.employment_status, 'employment_status')} /><Fact label="Tipe PKWT" value={fieldValue(employee.pkwt_type, 'pkwt_type')} /><Fact label="Tanggal masuk" value={employee.start_date} /><Fact label="Kontrak berakhir" value={employee.contract_expiry} /></dl></section><section aria-labelledby="employee-personal"><h2 id="employee-personal">Data pribadi</h2><dl className="employee-facts"><Fact label="Tanggal lahir" value={employee.date_of_birth} /></dl></section></div>}
    </div>
  </article>;
}
