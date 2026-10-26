import { Link } from 'react-router';
import { decodeChoices, decodeDivisionChoices } from './group-api';
import type { Employee, EmployeeInput } from './types';
import { useEmployeeRead } from './useEmployeeRead';

type Props = { values: EmployeeInput; employee?: Employee; disabled: boolean; errors: Partial<Record<keyof EmployeeInput, string>>; change(key: 'branch' | 'division', value: string | null): void };
function ChoiceField({ kind, ...props }: Props & { kind: 'branch' | 'division' }) {
  const label = kind === 'branch' ? 'Cabang' : 'Divisi';
  const resource = useEmployeeRead('/api/organization/' + (kind === 'branch' ? 'branches' : 'divisions') + '/', kind === 'branch' ? decodeChoices : decodeDivisionChoices);
  const choices = kind === 'division' ? resource.data?.filter(choice => choice.branch === props.values.branch) : resource.data;
  const value = props.values[kind] ?? '';
  const currentName = props.employee?.[kind === 'branch' ? 'branch_name' : 'division_name'];
  return <div className="form-field"><label htmlFor={'employee-' + kind}>{label}</label><select id={'employee-' + kind} name={kind} value={value} disabled={props.disabled || resource.loading || Boolean(resource.error) || (kind === 'division' && !props.values.branch)} aria-invalid={Boolean(props.errors[kind])} aria-describedby={props.errors[kind] ? kind + '-error' : kind + '-hint'} onChange={event => props.change(kind, event.target.value || null)}><option value="">Belum ditentukan</option>{value && !choices?.some(choice => choice.id === value) && <option value={value}>{currentName || label + ' saat ini'}</option>}{choices?.map(choice => <option value={choice.id} key={choice.id}>{choice.name}</option>)}</select>
    {resource.loading && <p className="hint" role="status">Memuat pilihan {label.toLowerCase()}…</p>}
    {Boolean(resource.error) && <p className="error">Pilihan {label.toLowerCase()} belum dapat dimuat. <button type="button" onClick={resource.retry}>Coba lagi</button></p>}
    <p className="hint" id={kind + '-hint'}>{kind === 'division' && !props.values.branch ? 'Pilih cabang terlebih dahulu.' : kind === 'division' && choices?.length === 0 ? 'Belum ada divisi untuk cabang ini.' : kind === 'branch' ? 'Kosongkan untuk melepas cabang dan divisi utama.' : 'Hanya divisi milik cabang terpilih. Kosongkan untuk melepas divisi utama.'}</p>
    {props.errors[kind] && <p className="error" id={kind + '-error'}>{props.errors[kind]}</p>}
  </div>;
}
export function EmployeeGroupingFields(props: Props) {
  return <><ChoiceField {...props} kind="branch" /><ChoiceField {...props} kind="division" /><Link className="back" to="/employees/groups">Kelola Cabang dan Divisi</Link></>;
}