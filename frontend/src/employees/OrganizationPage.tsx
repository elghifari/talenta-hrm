import './grouping.css';
import { Fragment, useEffect, useRef, useState } from 'react';
import { useOutletContext } from 'react-router';
import { PageTitle } from '../app/PageTitle';
import { useSession } from '../auth/SessionProvider';
import { decodeChoices, decodeDivisionChoices } from './group-api';
import { GroupEditor, type GroupEdit } from './GroupEditor';
import { BranchDialog } from './BranchDialog';
import { useEmployeeRead } from './useEmployeeRead';
import { useUnsavedChanges } from './useUnsavedChanges';

function Management() {
  const branches = useEmployeeRead('/api/organization/branches/', decodeChoices);
  const divisions = useEmployeeRead('/api/organization/divisions/', decodeDivisionChoices);
  const [edit, setEdit] = useState<GroupEdit | null>(null); const [dirty, setDraftDirty] = useState(false);
  const [saved, setSaved] = useState(''); const [closed, setClosed] = useState(new Set<string>());
  const { setDirty } = useOutletContext<{ setDirty(value: boolean): void }>();
  const allowLeave = useRef(false); const blocker = useUnsavedChanges(dirty, allowLeave);
  const addBranch = useRef<HTMLButtonElement>(null);
  const editorTrigger = useRef<HTMLButtonElement | null>(null);
  useEffect(() => { setDirty(dirty); return () => setDirty(false); }, [dirty, setDirty]);
  function refresh() { branches.retry(); divisions.retry(); }
  function finish(owner?: string) {
    if (owner) setClosed(previous => { const next = new Set(previous); next.delete(owner); return next; });
    setSaved(edit?.kind === 'branches' ? 'Cabang tersimpan.' : 'Divisi tersimpan.'); setEdit(null); setDraftDirty(false); refresh();
    requestAnimationFrame(() => addBranch.current?.focus());
  }
  function cancel() { setEdit(null); setDraftDirty(false); requestAnimationFrame(() => editorTrigger.current?.focus()); }
  const loading = branches.loading || divisions.loading; const failed = Boolean(branches.error || divisions.error);
  return <><div className="page-heading"><div><PageTitle>Cabang dan Divisi</PageTitle><p>Setiap divisi dimiliki satu cabang. Buka cabang untuk melihat divisinya.</p></div></div>
    {blocker.state === 'blocked' && <section className="notice" role="alertdialog" aria-label="Perubahan kelompok belum disimpan" onKeyDown={event => { if (event.key === 'Escape') blocker.reset(); }}><p>Perubahan kelompok belum disimpan. Tinggalkan halaman?</p><div className="form-actions"><button autoFocus onClick={() => blocker.reset()}>Tetap di halaman</button><button onClick={() => blocker.proceed()}>Tinggalkan halaman</button></div></section>}
    <div className="form-actions organization-actions"><button ref={addBranch} className="primary" disabled={Boolean(edit) || loading || failed} onClick={event => { editorTrigger.current = event.currentTarget; setSaved(''); setEdit({ kind: 'branches' }); }}>Tambah cabang</button></div>
    {edit?.record && <BranchDialog branch={edit.record} divisions={(divisions.data ?? []).filter(item => item.branch === edit.record!.id)} reportDirty={setDraftDirty} saved={() => finish(edit.record!.id)} cancel={cancel} refresh={refresh} />}
    {edit && !edit.record && <GroupEditor key={edit.kind} edit={edit} branches={branches.data ?? []} reportDirty={setDraftDirty} saved={finish} cancel={cancel} refresh={refresh} />}
    {saved && <p className="success" role="status">{saved}</p>}
    {loading && <p role="status">Memuat cabang dan divisi…</p>}
    {failed && <div className="notice" role="alert"><p>Daftar cabang dan divisi belum dapat dimuat.</p><button onClick={refresh}>Coba lagi</button></div>}
    {branches.data && divisions.data && (branches.data.length ? <div className="record-table organization-table-wrap" role="region" aria-label="Tabel cabang dan divisi" tabIndex={0}><table className="organization-table"><thead><tr><th scope="col">Cabang / Divisi</th><th scope="col">Tindakan</th></tr></thead><tbody>{branches.data.map(branch => {
      const children = divisions.data!.filter(division => division.branch === branch.id); const expanded = !closed.has(branch.id);
      return <Fragment key={branch.id}><tr className="organization-branch" data-kind="branch" data-id={branch.id}><td><button className="organization-toggle" aria-expanded={expanded} onClick={() => setClosed(previous => { const next = new Set(previous); if (next.has(branch.id)) next.delete(branch.id); else next.add(branch.id); return next; })}><svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M4 2 8 6 4 10" fill="none" stroke="currentColor" strokeWidth="1.5" /></svg><span><span>{branch.name}</span><small>{children.length} divisi</small></span></button></td><td><button disabled={Boolean(edit)} aria-label={'Edit cabang ' + branch.name} onClick={event => { editorTrigger.current = event.currentTarget; setSaved(''); setEdit({ kind: 'branches', record: branch }); }}>Edit</button></td></tr>
      {expanded && (children.length ? children.map(division => <tr key={division.id} className="organization-division" data-kind="division" data-id={division.id}><td>{division.name}</td><td /></tr>) : <tr><td colSpan={2}><p className="hint organization-empty">Belum ada divisi di cabang ini.</p></td></tr>)}</Fragment>;
    })}</tbody></table></div> : <section className="empty"><h2>Belum ada cabang</h2><p>Tambahkan cabang terlebih dahulu, lalu tambahkan divisi di dalamnya.</p></section>)}

  </>;
}
export function GroupManagementPage() {
  const { identity } = useSession();
  return identity?.capabilities.employees_write ? <Management /> : <PageTitle>Akses tidak diizinkan</PageTitle>;
}
