import { useEffect, useRef } from 'react';
import { Link, useOutletContext, useParams } from 'react-router';
import { PageTitle } from '../app/PageTitle';
import { errorText } from '../api/client';
import { useSession } from '../auth/SessionProvider';
import { useUnsavedChanges } from '../employees/useUnsavedChanges';
import { ContractFields } from './fields';
import { useContractEditor } from './useContractEditor';
import './contracts.css';
function Editor({ employeeId, draftId }: { employeeId: string; draftId?: string }) {
  const editor = useContractEditor(employeeId, draftId);
  const { setDirty } = useOutletContext<{ setDirty(value: boolean): void }>();
  const blocker = useUnsavedChanges(editor.dirty || editor.busy || Boolean(editor.uncertain), editor.allowLeave);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { setDirty(editor.dirty || Boolean(editor.uncertain)); return () => setDirty(false); }, [editor.dirty, editor.uncertain, setDirty]);
  useEffect(() => { if (editor.selection) dialog.current?.showModal(); else if (dialog.current?.open) dialog.current.close(); }, [editor.selection]);
  if (editor.loading) return <p role="status">Memuat draf kontrak…</p>;
  if (editor.loadError) return <><PageTitle>Draf belum dapat dimuat</PageTitle><p role="alert">{errorText(editor.loadError)}</p><button onClick={editor.retry}>Coba lagi</button><Link to={'/employees/' + employeeId}>Detail pegawai</Link></>;
  const disabled = editor.busy || Boolean(editor.uncertain);
  return <div className="contract-editor"><div className="page-heading"><div><PageTitle>{draftId ? 'Draf perpanjangan PKWT' : 'Buat draf perpanjangan'}</PageTitle><p>{editor.employee?.full_name} · ID Karyawan <strong>{editor.employee?.employee_code}</strong></p><p>Unit pegawai: {editor.employee?.branch_name || '-'} · Divisi: {editor.employee?.division_name || '-'}</p>{editor.draft && <p>Revisi {editor.draft.revision} · Referensi {editor.draft.reference_version}</p>}</div></div>
    {blocker.state === 'blocked' && <section className="notice" role="alertdialog" aria-label="Perubahan belum disimpan"><p>Perubahan belum disimpan. Tinggalkan halaman ini?</p><div className="form-actions"><button autoFocus onClick={() => blocker.reset()}>Tetap mengedit</button><button onClick={() => blocker.proceed()}>Tinggalkan halaman</button></div></section>}
    {editor.error && <div role="alert" className="error"><p>{editor.error}</p>{editor.uncertain && <button disabled={editor.busy} onClick={() => void editor.recover()}>Periksa hasil</button>}{editor.draft && <Link to={`/employees/${employeeId}/contracts/${editor.draft.id}`} target="_blank" rel="noopener">Buka draf tersimpan</Link>}</div>}
    {editor.message && <p role="status" className="success">{editor.message}</p>}
    {!editor.configured && <p role="alert">Referensi kontrak belum tersedia. Riwayat dokumen tetap dapat dibuka.</p>}
    {!editor.draft && !editor.eligible ? <p>Lengkapi status Kontrak dan tipe PKWT pada <Link to={'/employees/' + employeeId + '/edit'}>data pegawai</Link>.</p> : <form className="record" noValidate onSubmit={event => { event.preventDefault(); void editor.save(); }}>
      <fieldset className="contract-fields"><legend>Default sumber</legend><div className="form-field"><label htmlFor="contract-source-unit">Unit sumber</label><select id="contract-source-unit" disabled={disabled || !editor.configured} value={editor.input.source_unit ?? ''} onChange={event => editor.choose('unit', event.target.value)}><option value="">Pilih Unit sumber</option>{editor.references?.units.map(row => <option key={row.key} value={row.key}>{row.unit}</option>)}</select></div>
      <div className="form-field"><label htmlFor="contract-source-job">Default jabatan</label><select id="contract-source-job" disabled={disabled || !editor.configured || !editor.input.source_unit} value={editor.input.job_default_key ?? ''} onChange={event => editor.choose('job', event.target.value)}><option value="">Isi tugas secara manual</option>{editor.references?.jobs.filter(row => row.pkwt_type === editor.kind && row.unit.trim().toLowerCase() === editor.input.source_unit?.trim().toLowerCase()).map(row => <option key={row.key} value={row.key}>{row.division || '(Umum)'} / {row.title}</option>)}</select></div></fieldset>
      <ContractFields fields={editor.fields} values={editor.input.values} errors={editor.errors} disabled={disabled} change={editor.change} />
      <div className="form-actions"><button className="primary" type="submit" disabled={disabled || (!editor.draft && !editor.configured) || (Boolean(editor.draft) && !editor.dirty)}>Simpan draf</button><button type="button" disabled={disabled || !editor.draft || editor.dirty || !editor.complete || !editor.configured} onClick={() => void editor.generate()}>Buat DOCX</button><Link to={'/employees/' + employeeId}>Batal</Link></div>
      {editor.draft && editor.dirty && <p>Simpan perubahan sebelum membuat DOCX.</p>}
    </form>}
    <section className="record contract-documents" aria-labelledby="contract-documents"><h2 id="contract-documents">Dokumen tersimpan</h2>{!editor.documents.length ? <p>Belum ada dokumen.</p> : <ul>{editor.documents.map(doc => <li key={doc.id}><div><strong>{doc.filename}</strong><p>Revisi {doc.revision} · {new Date(doc.generated_at).toLocaleString('id-ID')}</p></div><button disabled={editor.busy} onClick={() => void editor.download(doc)}>Download DOCX</button></li>)}</ul>}</section>
    <dialog ref={dialog} className="contract-default-confirm" onCancel={event => { event.preventDefault(); editor.cancelSelection(); }}><h2>Ganti isian dengan default?</h2><p>Isian yang telah diedit akan diganti untuk default yang dipilih.</p><div className="form-actions"><button autoFocus onClick={editor.cancelSelection}>Batal</button><button onClick={editor.confirmSelection}>Gunakan default</button></div></dialog>
  </div>;
}
export function ContractEditorPage() {
  const { identity } = useSession();
  const { employeeId = '', draftId } = useParams();
  if (!identity?.capabilities.employees_write) return <PageTitle>Akses tidak tersedia</PageTitle>;
  return <Editor key={employeeId + ':' + (draftId ?? 'new')} employeeId={employeeId} draftId={draftId} />;
}
