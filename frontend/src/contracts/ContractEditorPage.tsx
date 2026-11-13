import { useEffect, useRef } from 'react';
import { Link, useOutletContext, useParams } from 'react-router';
import { PageTitle } from '../app/PageTitle';
import { errorText } from '../api/client';
import { useSession } from '../auth/SessionProvider';
import { useUnsavedChanges } from '../employees/useUnsavedChanges';
import { pkwtTypes } from '../employees/classification';
import { ContractFields } from './fields';
import { ContractSectionNav } from './ContractSectionNav';
import { contractFieldGroups } from './sections';
import { useContractEditor } from './useContractEditor';
import './contracts.css';
function Editor({ employeeId, draftId }: { employeeId: string; draftId?: string }) {
  const editor = useContractEditor(employeeId, draftId);
  const { setDirty } = useOutletContext<{ setDirty(value: boolean): void }>();
  const blocker = useUnsavedChanges(editor.dirty || editor.busy || Boolean(editor.uncertain), editor.allowLeave);
  const dialog = useRef<HTMLDialogElement>(null);
  const editorRoot = useRef<HTMLDivElement>(null);
  const employeeContext = useRef<HTMLParagraphElement>(null);
  useEffect(() => { setDirty(editor.dirty || Boolean(editor.uncertain)); return () => setDirty(false); }, [editor.dirty, editor.uncertain, setDirty]);
  useEffect(() => { if (editor.selection) dialog.current?.showModal(); else if (dialog.current?.open) dialog.current.close(); }, [editor.selection]);
  useEffect(() => {
    const root = editorRoot.current, context = employeeContext.current;
    if (!root || !context) return;
    const measure = () => root.style.setProperty('--contract-context-height', `${context.getBoundingClientRect().height}px`);
    measure();
    const observer = typeof ResizeObserver === 'undefined' ? undefined : new ResizeObserver(measure);
    observer?.observe(context);
    window.addEventListener('resize', measure);
    return () => { observer?.disconnect(); window.removeEventListener('resize', measure); };
  }, [editor.loading, editor.loadError]);
  if (editor.loading) return <p role="status">Memuat draf kontrak…</p>;
  if (editor.loadError) return <><PageTitle>Draf belum dapat dimuat</PageTitle><p role="alert">{errorText(editor.loadError)}</p><button onClick={editor.retry}>Coba lagi</button><Link to={'/employees/' + employeeId}>Detail pegawai</Link></>;
  const disabled = editor.busy || Boolean(editor.uncertain);
  const groups = contractFieldGroups(editor.fields);
  const sections = [
    { id: 'contract-template', label: 'Template', filled: Number(Boolean(editor.kind)) + Number(Boolean(editor.input.source_unit)) + Number(Boolean(editor.input.job_default_key)), total: 3, errors: Number(Boolean(editor.errors.pkwt_type)) + Number(Boolean(editor.errors.source_unit)) + Number(Boolean(editor.errors.job_default_key)) },
    ...groups.map(group => ({ id: group.id, label: group.label, filled: group.fields.filter(field => Boolean(editor.input.values[field.key]?.trim())).length, total: group.fields.length, errors: group.fields.filter(field => Boolean(editor.errors[field.key])).length })),
  ];
  return <div ref={editorRoot} className="contract-editor"><div className="page-heading"><div><PageTitle>{draftId ? 'Draf perpanjangan PKWT' : 'Buat draf perpanjangan'}</PageTitle><p>Unit pegawai: {editor.employee?.branch_name || '-'} · Divisi: {editor.employee?.division_name || '-'}</p>{editor.draft && <p>Revisi {editor.draft.revision} · Referensi {editor.draft.reference_version}</p>}</div></div>
    <p ref={employeeContext} className="contract-employee-context"><strong>{editor.employee?.full_name}</strong><span>· ID Karyawan <strong>{editor.employee?.employee_code}</strong></span></p>
    {blocker.state === 'blocked' && <section className="notice" role="alertdialog" aria-label="Perubahan belum disimpan"><p>Perubahan belum disimpan. Tinggalkan halaman ini?</p><div className="form-actions"><button autoFocus onClick={() => blocker.reset()}>Tetap mengedit</button><button onClick={() => blocker.proceed()}>Tinggalkan halaman</button></div></section>}
    {editor.error && <div role="alert" className="error"><p>{editor.error}</p>{editor.uncertain && <button disabled={editor.busy} onClick={() => void editor.recover()}>Periksa hasil</button>}{editor.draft && <Link to={`/employees/${employeeId}/contracts/${editor.draft.id}`} target="_blank" rel="noopener">Buka draf tersimpan</Link>}</div>}
    {editor.message && <p role="status" className="success">{editor.message}</p>}
    {!editor.configured && <p role="alert">Referensi kontrak belum tersedia. Riwayat dokumen tetap dapat dibuka.</p>}
    {!editor.draft && !editor.eligible ? <p>Draf tersedia untuk status Kontrak atau Magang. Periksa <Link to={'/employees/' + employeeId + '/edit'}>data pegawai</Link>.</p> : <form className="contract-form" noValidate onSubmit={event => { event.preventDefault(); void editor.save(); }}>
      <div className="contract-editor-layout">
        <ContractSectionNav sections={sections} />
        <div className="record contract-form-record">
          <section id="contract-template" className="contract-form-section" aria-labelledby="contract-template-heading">
            <header className="contract-section-heading"><h2 id="contract-template-heading" tabIndex={-1}>Template</h2><span>1 / {sections.length}</span></header>
            <div className="contract-fields">
              <div className="form-field"><label htmlFor="contract-pkwt_type">Tipe PKWT</label>{editor.draft ? <input id="contract-pkwt_type" value={pkwtTypes.find(row => row.value === editor.kind)?.label ?? editor.kind} readOnly /> : <select id="contract-pkwt_type" name="pkwt_type" required disabled={disabled || !editor.configured} value={editor.kind} aria-invalid={Boolean(editor.errors.pkwt_type)} aria-describedby={editor.errors.pkwt_type ? 'contract-pkwt_type-error' : undefined} onChange={event => editor.chooseKind(event.target.value)}>{pkwtTypes.map(row => <option key={row.value} value={row.value} disabled={!row.value}>{row.value ? row.label : 'Pilih tipe PKWT'}</option>)}</select>}{editor.errors.pkwt_type && <p id="contract-pkwt_type-error" className="error">{editor.errors.pkwt_type}</p>}</div>
              <div className="form-field"><label htmlFor="contract-source-unit">Unit</label><select id="contract-source-unit" disabled={disabled || !editor.configured} value={editor.input.source_unit ?? ''} aria-invalid={Boolean(editor.errors.source_unit)} aria-describedby={editor.errors.source_unit ? 'contract-source-unit-error' : undefined} onChange={event => editor.choose('unit', event.target.value)}><option value="">Pilih Unit</option>{editor.references?.units.map(row => <option key={row.key} value={row.key}>{row.unit}</option>)}</select>{editor.errors.source_unit && <p id="contract-source-unit-error" className="error">{editor.errors.source_unit}</p>}</div>
              <div className="form-field"><label htmlFor="contract-source-job">Jabatan</label><select id="contract-source-job" disabled={disabled || !editor.configured || !editor.input.source_unit} value={editor.input.job_default_key ?? ''} aria-invalid={Boolean(editor.errors.job_default_key)} aria-describedby={editor.errors.job_default_key ? 'contract-source-job-error' : undefined} onChange={event => editor.choose('job', event.target.value)}><option value="">Isi tugas secara manual</option>{editor.references?.jobs.filter(row => row.pkwt_type === editor.kind && row.unit.trim().toLowerCase() === editor.input.source_unit?.trim().toLowerCase()).map(row => <option key={row.key} value={row.key}>{row.division || '(Umum)'} / {row.title}</option>)}</select>{editor.errors.job_default_key && <p id="contract-source-job-error" className="error">{editor.errors.job_default_key}</p>}</div>
            </div>
          </section>
          <ContractFields fields={editor.fields} values={editor.input.values} errors={editor.errors} disabled={disabled} change={editor.change} />
        </div>
      </div>
      {editor.documents.length > 0 && <section className="record contract-documents" aria-labelledby="contract-documents"><h2 id="contract-documents">Dokumen tersimpan</h2><ul>{editor.documents.map(doc => <li key={doc.id}><div><strong>{doc.filename}</strong><p>Revisi {doc.revision} · {new Date(doc.generated_at).toLocaleString('id-ID')}</p></div><button type="button" disabled={editor.busy} onClick={() => void editor.download(doc)}>Download DOCX</button></li>)}</ul></section>}
      <div className="contract-actionbar">
        <div className="contract-save-state"><p>{editor.uncertain ? 'Hasil belum dapat dipastikan' : editor.busy ? 'Memproses…' : editor.dirty ? 'Perubahan belum disimpan' : editor.draft ? 'Draf tersimpan' : 'Draf belum disimpan'}</p>{editor.draft && editor.dirty && <p className="hint">Simpan perubahan sebelum membuat DOCX.</p>}</div>
        <div className="form-actions"><button className="primary" type="submit" disabled={disabled || (!editor.draft && (!editor.configured || !editor.kind)) || (Boolean(editor.draft) && !editor.dirty)}>Simpan draf</button><button type="button" disabled={disabled || !editor.draft || editor.dirty || !editor.complete || !editor.configured} onClick={() => void editor.generate()}>Buat DOCX</button><Link to={'/employees/' + employeeId}>Batal</Link></div>
      </div>
    </form>}
    <dialog ref={dialog} className="contract-default-confirm" onCancel={event => { event.preventDefault(); editor.cancelSelection(); }}><h2>Ganti isian dengan default?</h2><p>Isian yang telah diedit akan diganti untuk default yang dipilih.</p><div className="form-actions"><button autoFocus onClick={editor.cancelSelection}>Batal</button><button onClick={editor.confirmSelection}>Gunakan default</button></div></dialog>
  </div>;
}
export function ContractEditorPage() {
  const { identity } = useSession();
  const { employeeId = '', draftId } = useParams();
  if (!identity?.capabilities.employees_write) return <PageTitle>Akses tidak tersedia</PageTitle>;
  return <Editor key={employeeId + ':' + (draftId ?? 'new')} employeeId={employeeId} draftId={draftId} />;
}
