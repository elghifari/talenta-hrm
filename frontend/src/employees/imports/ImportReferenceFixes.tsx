import { useEffect, useRef, useState } from 'react';
import { ApiError, isAbort } from '../../api/client';
import { useSession } from '../../auth/SessionProvider';
import { choiceError, decodeChoices, decodeDivisionChoices, saveChoice } from '../group-api';
import { useEmployeeRead } from '../useEmployeeRead';
import type { ImportRow, MissingHierarchy } from './api';

type MissingItem = MissingHierarchy & { key: string; rows: number[] };
type UnitGroup = { key: string; name: string | null; unit?: MissingItem; divisions: MissingItem[]; rows: number[] };
const normalized = (value: string) => value.trim().toLowerCase();
export function missingItems(rows: ImportRow[]): MissingItem[] {
  const items = new Map<string, MissingItem>();
  for (const row of rows) for (const item of row.missing_hierarchy ?? []) {
    const key = JSON.stringify([item.kind, normalized(item.branch_name ?? ''), normalized(item.name)]);
    const existing = items.get(key);
    if (existing) existing.rows.push(row.row);
    else items.set(key, { ...item, key, rows: [row.row] });
  }
  return [...items.values()].sort((a, b) => a.kind === b.kind ? a.rows[0] - b.rows[0] : a.kind === 'branch' ? -1 : 1);
}

export function ImportReferenceFixes({ rows, reportBusy }: { rows: ImportRow[]; reportBusy(value: boolean): void }) {
  const branches = useEmployeeRead('/api/organization/branches/', decodeChoices);
  const divisions = useEmployeeRead('/api/organization/divisions/', decodeDivisionChoices);
  const { request } = useSession();
  const [busyKey, setBusyKey] = useState('');
  const [uncertain, setUncertain] = useState(new Set<string>());
  const [error, setError] = useState('');
  const [saved, setSaved] = useState('');
  const controller = useRef(new AbortController());
  const heading = useRef<HTMLHeadingElement>(null);
  const items = missingItems(rows);
  const grouped = new Map<string, UnitGroup>();
  for (const item of items) {
    const key = normalized(item.branch_name ?? '');
    const group = grouped.get(key) ?? { key, name: item.branch_name, divisions: [], rows: [] };
    if (item.kind === 'branch') group.unit = item;
    else group.divisions.push(item);
    group.rows = [...new Set([...group.rows, ...item.rows])].sort((a, b) => a - b);
    grouped.set(key, group);
  }
  const groups = [...grouped.values()].sort((a, b) => a.rows[0] - b.rows[0]);
  const loading = branches.loading || divisions.loading;
  const failed = Boolean(branches.error || divisions.error);
  function owner(item: MissingItem) { return branches.data?.find(branch => normalized(branch.name) === normalized(item.branch_name ?? '')); }
  function exists(item: MissingItem) {
    return item.kind === 'branch' ? Boolean(owner(item)) : Boolean(divisions.data?.some(division => division.branch === owner(item)?.id && normalized(division.name) === normalized(item.name)));
  }
  const unresolved = items.some(item => uncertain.has(item.key) && !exists(item));
  useEffect(() => { reportBusy(Boolean(busyKey) || unresolved); return () => reportBusy(false); }, [busyKey, unresolved, reportBusy]);
  useEffect(() => { const control = new AbortController(); controller.current = control; return () => control.abort(); }, []);
  function refresh() { branches.retry(); divisions.retry(); }
  async function create(item: MissingItem) {
    if (busyKey || uncertain.has(item.key) || loading || failed || exists(item)) return;
    const branch = owner(item);
    if (item.kind === 'division' && !branch) return;
    setBusyKey(item.key); setError(''); setSaved('');
    try {
      await saveChoice(request, item.kind === 'branch' ? 'branches' : 'divisions', { name: item.name, ...(branch && item.kind === 'division' ? { branch: branch.id } : {}) }, undefined, controller.current.signal);
      if (controller.current.signal.aborted) return;
      setSaved((item.kind === 'branch' ? 'Unit ' : 'Divisi ') + item.name + ' ditambahkan.');
      refresh(); heading.current?.focus();
    } catch (failure) {
      if (!controller.current.signal.aborted && !isAbort(failure)) {
        setError(choiceError(failure));
        if (failure instanceof ApiError && failure.writeOutcome === 'uncertain') setUncertain(previous => new Set(previous).add(item.key));
      }
    } finally { if (!controller.current.signal.aborted) setBusyKey(''); }
  }
  function addButton(item: MissingItem) {
    return <button type="button" aria-label={(item.kind === 'branch' ? 'Tambah unit ' : 'Tambah divisi ') + item.name + (item.kind === 'division' ? ' di ' + (item.branch_name ?? '') : '')} disabled={loading || failed || Boolean(busyKey) || exists(item) || uncertain.has(item.key) || (item.kind === 'division' && !owner(item))} onClick={() => create(item)}>{exists(item) ? 'Sudah tersedia' : busyKey === item.key ? 'Menyimpan…' : item.kind === 'branch' ? 'Tambah unit' : 'Tambah divisi'}</button>;
  }
  return <section className="import-reference-fixes" aria-labelledby="missing-references-title">
    <h2 id="missing-references-title" ref={heading} tabIndex={-1}>Unit/Divisi belum terdaftar</h2>
    <p>Periksa ejaan sebelum menambahkan. Penambahan Unit/Divisi disimpan terpisah dari impor karyawan.</p>
    {loading && <p role="status">Memeriksa Unit dan Divisi…</p>}
    {failed && <p className="error" role="alert">Daftar Unit/Divisi belum dapat dimuat.</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {saved && <p role="status">{saved}</p>}
    {unresolved && <p className="notice" role="alert">Hasil penyimpanan belum pasti. Periksa daftar terbaru sebelum melanjutkan.</p>}
    <ul className="missing-unit-list">{groups.map(group => <li key={group.key}>
      <div className="missing-reference-row missing-unit-heading">
        <div><strong>{group.name ? 'Unit: ' + group.name : 'Unit belum diisi'}</strong><p className="hint">Baris CSV: {group.rows.join(', ')}</p></div>
        {group.unit ? addButton(group.unit) : !loading && !failed && branches.data?.some(branch => normalized(branch.name) === normalized(group.name ?? '')) && <span className="hint">Unit sudah terdaftar</span>}
      </div>
      {group.divisions.length > 0 && <ul className="missing-division-list" aria-label={'Divisi pada ' + (group.name ?? 'Unit belum diisi')}>{group.divisions.map(item => <li key={item.key} className="missing-reference-row">
        <div><strong>Divisi: {item.name}</strong><p className="hint">Baris CSV: {item.rows.join(', ')}</p>
          {!loading && !failed && !owner(item) && <p>{group.name ? 'Tambahkan Unit pemilik terlebih dahulu.' : 'Isi Unit pada CSV, lalu pilih file yang sudah diperbaiki.'}</p>}
        </div>
        {addButton(item)}
      </li>)}</ul>}
    </li>)}</ul>
    <button type="button" disabled={Boolean(busyKey) || loading} onClick={refresh}>Periksa daftar terbaru</button>
  </section>;
}
