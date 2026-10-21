import { useState } from 'react';
import { employeeFields, fieldLabel, fieldValue } from '../fields';
import type { ImportRow } from './api';

const marker = { new: 'New', update: 'Upd', unchanged: '-', error: '!' };
const statusLabel = { new: 'Karyawan baru', update: 'Diperbarui', unchanged: 'Tidak berubah', error: 'Perlu diperbaiki' };
export function ImportComparison({ row }: { row: ImportRow }) {
  const [all, setAll] = useState(false);
  const fields = row.status === 'update' && !all ? employeeFields.filter(field => row.changes.includes(field.key)) : employeeFields;
  const summary = row.status === 'new' ? 'Karyawan baru' : row.status === 'unchanged' ? 'Tidak ada perubahan' : row.status === 'error' ? 'Periksa data dari CSV' : `${row.changes.length} perubahan: ${row.changes.slice(0, 2).map(fieldLabel).join(', ')}${row.changes.length > 2 ? ` +${row.changes.length - 2} lainnya` : ''}`;
  return <li className="import-line">
    <span className={'import-marker ' + (row.status === 'error' ? 'error' : '')} aria-label={statusLabel[row.status]}>{marker[row.status]}</span>
    <details className="import-record" open={row.status === 'error'}>
      <summary className="import-summary"><span className="employee-code"><span className="mobile-label">ID Karyawan</span>{row.employee_code || 'Belum diisi'}</span><strong><span className="mobile-label">Nama lengkap</span>{row.full_name || 'Belum diisi'}</strong><span>{summary}<span className="import-action"><span className="when-closed">{row.status === 'update' ? 'Lihat perubahan' : 'Lihat data'}</span><span className="when-open">Tutup rincian</span></span></span></summary>
      <div className="import-comparison">
        {Object.entries(row.errors).map(([key, messages]) => <p className="error" key={key}>{fieldLabel(key)}: {messages.join(' ')}</p>)}
        {row.status === 'update' && <button className="comparison-toggle" onClick={() => setAll(value => !value)}>{all ? 'Hanya perubahan' : 'Lihat semua kolom'}</button>}
        <table className="diff-table" aria-label={'Perbandingan ' + (row.employee_code || 'baris ' + row.row)}><thead><tr><th>Kolom</th><th>Saat ini</th><th>Dari CSV</th></tr></thead><tbody>{fields.map(field => <tr key={field.key}><th scope="row">{field.label}</th><td><span className="mobile-label" aria-hidden="true">Saat ini</span>{row.current ? fieldValue(row.current[field.key]) : 'Belum terdaftar'}</td><td><span className="mobile-label" aria-hidden="true">Dari CSV</span>{fieldValue(row.incoming[field.key])}</td></tr>)}</tbody></table>
      </div>
    </details>
  </li>;
}
