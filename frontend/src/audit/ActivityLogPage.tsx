import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { ApiError, errorText, isAbort } from '../api/client';
import { PageTitle } from '../app/PageTitle';
import { useSession } from '../auth/SessionProvider';
import { actions, auditPath, decodeAuditPage, emptyFilters, type AuditEvent, type AuditFilters, type AuditPage } from './types';
import './activity-log.css';

const timeFormat = new Intl.DateTimeFormat('id-ID', { timeZone: 'Asia/Jakarta', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
const targetNames = { employee: 'Pegawai', branch: 'Cabang', division: 'Divisi', unknown: 'Objek' };
function EventDetails({ event }: { event: AuditEvent }) {
  const entries = Object.entries(event.changes);
  return <><strong>{event.action_label}</strong>{entries.length ? entries.map(([key, diff]) => <span className="audit-detail" key={key}>{key === 'kinerja_enabled' ? 'Kinerja' : 'Pelimpahan'}: {diff.old ? 'Aktif' : 'Nonaktif'} → {diff.new ? 'Aktif' : 'Nonaktif'}</span>) : <span className="audit-detail">Rincian perubahan tidak tercatat.</span>}</>;
}
function ActivityLogContent() {
  const { request } = useSession();
  const [draft, setDraft] = useState<AuditFilters>(emptyFilters);
  const [applied, setApplied] = useState<AuditFilters>(emptyFilters);
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const path = auditPath(applied, page);
  const key = path + '#' + revision;
  const [result, setResult] = useState<{ key: string; data?: AuditPage; error?: unknown } | null>(null);
  const ready = result?.key === key;
  const data = ready ? result.data : undefined;
  const error = ready ? result.error : undefined;
  const loading = !ready;
  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    request<unknown>(path, { signal: controller.signal, cache: 'no-store' }).then(decodeAuditPage).then(data => {
      if (current) setResult({ key, data });
    }).catch(error => { if (current && !isAbort(error)) setResult({ key, error }); });
    return () => { current = false; controller.abort(); };
  }, [request, path, key]);
  function apply(event: FormEvent) {
    event.preventDefault(); setApplied({ ...draft }); setPage(1); setRevision(value => value + 1);
  }
  function reset() { setDraft(emptyFilters); setApplied(emptyFilters); setPage(1); setRevision(value => value + 1); }
  const filtered = Object.values(applied).some(value => value.trim());
  const unavailable = error instanceof ApiError && error.status === 404;
  const denied = error instanceof ApiError && error.status === 403;
  const validation = error instanceof ApiError && error.status === 400;
  return <section className="activity-log" aria-label="Log aktivitas">
    <div className="page-heading"><PageTitle>Log aktivitas</PageTitle></div>
    <form className="audit-filters" aria-label="Filter log aktivitas" onSubmit={apply}>
      <div><label htmlFor="audit-actor">Pelaku (email)</label><input id="audit-actor" type="text" maxLength={254} value={draft.actor} onChange={event => setDraft({ ...draft, actor: event.target.value })} /></div>
      <div><label htmlFor="audit-action">Aktivitas</label><select id="audit-action" value={draft.action} onChange={event => setDraft({ ...draft, action: event.target.value })}><option value="">Semua aktivitas</option>{Object.entries(actions).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
      <div><label htmlFor="audit-from">Dari tanggal</label><input id="audit-from" type="date" value={draft.date_from} onChange={event => setDraft({ ...draft, date_from: event.target.value })} /></div>
      <div><label htmlFor="audit-to">Sampai tanggal</label><input id="audit-to" type="date" value={draft.date_to} onChange={event => setDraft({ ...draft, date_to: event.target.value })} /></div>
      <div className="audit-filter-actions"><button className="primary" type="submit">Terapkan filter</button><button type="button" onClick={reset}>Reset</button></div>
    </form>
    {loading && <p role="status">Memuat log aktivitas…</p>}
    {Boolean(error) && <div role="alert" className="error"><p>{denied ? 'Akses log aktivitas tidak tersedia.' : unavailable ? 'Halaman log ini tidak tersedia. Kembali ke halaman pertama.' : validation ? 'Filter tidak valid. Periksa pelaku, aktivitas, dan rentang tanggal.' : errorText(error)}</p>{unavailable ? <button type="button" onClick={() => { setPage(1); setRevision(value => value + 1); }}>Halaman pertama</button> : !denied && !validation && <button type="button" onClick={() => setRevision(value => value + 1)}>Coba lagi</button>}</div>}
    {data && <>
      {data.results.length ? <>
        <p className="audit-note">Nama objek mengikuti data saat ini.</p>
        <table className="audit-table"><caption className="sr-only">Aktivitas HR tercatat</caption><thead><tr><th scope="col">Waktu</th><th scope="col">Pelaku</th><th scope="col">Aktivitas</th><th scope="col">Objek</th></tr></thead><tbody>{data.results.map(event => <tr key={event.id}>
          <td data-label="Waktu"><time dateTime={event.created_at}>{timeFormat.format(new Date(event.created_at))} WIB</time></td>
          <td data-label="Pelaku">{event.actor.email}</td>
          <td data-label="Aktivitas"><EventDetails event={event} /></td>
          <td data-label="Objek"><span className="audit-target-type">{targetNames[event.target.type]}</span>{event.target.type === 'employee' && event.target.label !== null ? <Link to={'/employees/' + event.target.id}>{event.target.label}</Link> : <span>{event.target.label ?? event.target.id}</span>}</td>
        </tr>)}</tbody></table>
      </> : <p role="status">{filtered ? 'Tidak ada aktivitas yang cocok dengan filter.' : 'Belum ada aktivitas tercatat.'}</p>}
      <nav className="audit-pagination" aria-label="Halaman log aktivitas"><button type="button" disabled={!data.previous} onClick={() => setPage(value => value - 1)}>Sebelumnya</button><span role="status">Halaman {page}</span><button type="button" disabled={!data.next} onClick={() => setPage(value => value + 1)}>Berikutnya</button></nav>
    </>}
  </section>;
}
export function ActivityLogPage() {
  const { identity } = useSession();
  if (!identity?.capabilities.audit_read) return <><PageTitle>Log aktivitas</PageTitle><p role="alert">Akses log aktivitas tidak tersedia.</p></>;
  return <ActivityLogContent />;
}
