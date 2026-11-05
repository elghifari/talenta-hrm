import { useState } from 'react';
import { Link } from 'react-router';
import { errorText } from '../api/client';
import { useEmployeeRead } from '../employees/useEmployeeRead';
import { decodeDocuments, decodeDraftList, type Metadata } from './types';
function Documents({ draft }: { draft: Metadata }) {
  const resource = useEmployeeRead(`/api/contract-drafts/${draft.id}/documents/`, decodeDocuments);
  if (resource.loading) return <p role="status">Memuat riwayat dokumen…</p>;
  if (resource.error) return <div role="alert"><p>{errorText(resource.error)}</p><button onClick={resource.retry}>Coba lagi</button></div>;
  if (!resource.data?.length) return <p>Belum ada dokumen.</p>;
  return <ul>{resource.data.map(doc => <li key={doc.id}><Link to={`/employees/${draft.employee}/contracts/${draft.id}#contract-documents`}>{doc.filename}</Link><span> · Revisi {doc.revision}</span></li>)}</ul>;
}
function HistoryRow({ draft }: { draft: Metadata }) {
  const [expanded, setExpanded] = useState(false);
  return <li><Link to={`/employees/${draft.employee}/contracts/${draft.id}`}>Draf {draft.pkwt_type} · Revisi {draft.revision}</Link><p>{new Date(draft.updated_at).toLocaleString('id-ID')}</p><button aria-expanded={expanded} onClick={() => setExpanded(x => !x)}>{expanded ? 'Tutup riwayat dokumen' : 'Riwayat dokumen'}</button>{expanded && <Documents draft={draft} />}</li>;
}
export function ContractHistory({ employeeId }: { employeeId: string }) {
  const [page, setPage] = useState(1);
  const resource = useEmployeeRead(`/api/contract-drafts/?employee=${employeeId}&page=${page}`, decodeDraftList);
  if (resource.loading) return <p role="status">Memuat riwayat kontrak…</p>;
  if (resource.error) return <div role="alert"><p>{errorText(resource.error)}</p><button onClick={resource.retry}>Coba lagi</button></div>;
  const data = resource.data!;
  return <div className="contract-history">{data.count === 0 ? <p>Belum ada draf perpanjangan.</p> : <><ul>{data.results.map(draft => <HistoryRow key={draft.id} draft={draft} />)}</ul><div className="form-actions"><button disabled={page === 1} onClick={() => setPage(x => x - 1)}>Sebelumnya</button><span>Halaman {page}</span><button disabled={page * 50 >= data.count} onClick={() => setPage(x => x + 1)}>Berikutnya</button></div></>}</div>;
}
