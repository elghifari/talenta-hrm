import './grouping.css';
import { Fragment, useMemo, useState } from 'react';
import { Link } from 'react-router';
import { employeeFields, fieldValue, type EmployeeField } from './fields';
import { collectGroups, groupEmployees, groupOptions, type GroupMode, type GroupNode } from './grouping';
import type { Employee } from './types';

type Column = { key: keyof Employee; label: string };
export function EmployeeTable({ employees, showPrivate }: { employees: Employee[]; showPrivate: boolean }) {
  const [mode, setMode] = useState<GroupMode>('both');
  const [sortField, setSortField] = useState<EmployeeField>('employee_code');
  const [descending, setDescending] = useState(false);
  const [search, setSearch] = useState(''); const [branch, setBranch] = useState(''); const [division, setDivision] = useState('');
  const [closed, setClosed] = useState<Set<string>>(new Set());
  const matches = useMemo(() => employees.filter(employee => (!branch || (employee.branch ?? '__unset__') === branch) && (!division || (employee.division ?? '__unset__') === division) && (!search.trim() || [employee.employee_code, employee.full_name, showPrivate ? employee.job_title : ''].join(' ').toLocaleLowerCase('id').includes(search.trim().toLocaleLowerCase('id')))), [employees, branch, division, search, showPrivate]);
  const sortableFields = employeeFields.filter(field => showPrivate || field.key === 'employee_code' || field.key === 'full_name');
  const sorted = useMemo(() => {
    const collator = new Intl.Collator('id', { numeric: true, sensitivity: 'base' });
    return [...matches].sort((a, b) => {
      const left = a[sortField] ?? ''; const right = b[sortField] ?? '';
      if (!left || !right) return left ? -1 : right ? 1 : collator.compare(a.employee_code, b.employee_code);
      const order = collator.compare(left, right);
      return (descending ? -order : order) || collator.compare(a.employee_code, b.employee_code) || a.id.localeCompare(b.id);
    });
  }, [matches, sortField, descending]);
  const nodes = groupEmployees(sorted, mode); const keys = collectGroups(nodes);
  const columns: Column[] = employeeFields.filter(field => showPrivate || field.key === 'employee_code' || field.key === 'full_name').map(({ key, label }) => ({ key, label }));
  if (mode === 'division' || mode === 'none') columns.splice(2, 0, { key: 'branch_name', label: 'Cabang' });
  if (mode === 'branch' || mode === 'none') columns.splice(mode === 'none' ? 3 : 2, 0, { key: 'division_name', label: 'Divisi' });
  function reset() { setSearch(''); setBranch(''); setDivision(''); setClosed(new Set()); }
  function rows(items: GroupNode[]): React.ReactNode {
    return items.map(node => 'children' in node ? <Fragment key={node.key}>
      <tr className={'employee-group ' + node.kind} data-depth={node.depth}><td colSpan={columns.length}><button aria-expanded={!closed.has(node.key)} onClick={() => setClosed(previous => { const next = new Set(previous); if (next.has(node.key)) next.delete(node.key); else next.add(node.key); return next; })}><svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M4 2 8 6 4 10" fill="none" stroke="currentColor" strokeWidth="1.5" /></svg><span>{node.label}{' '}<span className="group-count">· {node.count} karyawan</span></span></button></td></tr>
      {!closed.has(node.key) && rows(node.children)}
    </Fragment> : <tr key={node.id} className="employee-data-row">{columns.map(column => <td key={column.key} className={column.key === 'employee_code' ? 'employee-code' : undefined}><span className="mobile-label" aria-hidden="true">{column.label}</span>{column.key === 'full_name' ? <Link to={'/employees/' + node.id}>{node.full_name}</Link> : fieldValue(node[column.key])}</td>)}</tr>);
  }
  return <section className="employee-table-view" aria-label="Daftar pegawai berkelompok">
    <div className="employee-filters"><div className="employee-search"><label htmlFor="employee-search">Cari pegawai</label><input id="employee-search" type="search" placeholder={showPrivate ? 'ID, nama, atau jabatan' : 'ID atau nama'} value={search} onChange={event => { setSearch(event.target.value); setClosed(new Set()); }} /></div>{(['branch', 'division'] as const).map(kind => <div key={kind}><label htmlFor={'filter-' + kind}>{kind === 'branch' ? 'Cabang' : 'Divisi'}</label><select id={'filter-' + kind} value={kind === 'branch' ? branch : division} onChange={event => { if (kind === 'branch') { setBranch(event.target.value); setDivision(''); } else setDivision(event.target.value); setClosed(new Set()); }}><option value="">{kind === 'branch' ? 'Semua cabang' : 'Semua divisi'}</option>{groupOptions(kind === 'division' && branch ? employees.filter(employee => (employee.branch ?? '__unset__') === branch) : employees, kind).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></div>)}</div>
    <div className="employee-viewbar"><div className="employee-view-controls"><div><select id="employee-grouping" aria-label="Grouping" value={mode} onChange={event => { setMode(event.target.value as GroupMode); setClosed(new Set()); }}><option value="both">Cabang/Divisi</option><option value="branch">Cabang</option><option value="division">Divisi</option><option value="none">All</option></select></div>{keys.length > 0 && <button onClick={() => setClosed(keys.every(key => closed.has(key)) ? new Set() : new Set(keys))}>{keys.every(key => closed.has(key)) ? 'Buka semua' : 'Tutup semua'}</button>}<button onClick={reset}>Reset filter</button></div><div className="employee-sort-controls"><select aria-label="Sort by" value={sortField} onChange={event => setSortField(event.target.value as EmployeeField)}>{sortableFields.map(field => <option key={field.key} value={field.key}>{field.label}</option>)}</select><button type="button" aria-label={descending ? "Desc: urutan menurun" : "Asc: urutan menaik"} aria-pressed={descending} onClick={() => setDescending(value => !value)}>{descending ? 'Desc' : 'Asc'}</button></div></div>
    {matches.length ? <div className="record-table grouped-record-table" role="region" aria-label="Tabel pegawai" tabIndex={0}><table className={'employee-table ' + (!showPrivate ? 'compact' : '')}><thead><tr>{columns.map(column => <th key={column.key} scope="col">{column.label}</th>)}</tr></thead><tbody>{rows(nodes)}</tbody></table></div> : <section className="empty" role="region" aria-label="Hasil pencarian kosong"><h2>Tidak ada pegawai yang cocok</h2><p>Ubah pencarian atau reset filter untuk melihat semua pegawai yang tersedia.</p><button onClick={reset}>Reset filter</button></section>}
  </section>;
}