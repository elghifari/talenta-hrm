import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { ApiError, errorText, isAbort } from '../api/client';
import { useSession } from '../auth/SessionProvider';
import { decodeEmployee, type Employee } from '../employees/types';
import { canonical, editable, initialValues, same, unitDefaults, type Editable } from './api';
import { decodeDocuments, decodeDraft, decodeReceipt, decodeReferences, kinds, mime, type Draft, type Kind, type Receipt, type References, type Values } from './types';
type Attempt = { kind: 'create' | 'save'; id: string; revision: number; resultRevision: number; pkwt_type: Kind; input: Editable } | { kind: 'generate'; id: string; revision: number };
export function useContractEditor(employeeId: string, draftId?: string) {
  const session = useSession(), { request } = session;
  const navigate = useNavigate(), location = useLocation();
  const [employee, setEmployee] = useState<Employee>();
  const [references, setReferences] = useState<References>();
  const [draft, setDraft] = useState<Draft>();
  const [selectedKind, setSelectedKind] = useState<Kind>();
  const [baselineKind, setBaselineKind] = useState<Kind>();
  const [input, setInput] = useState<Editable>({ source_unit: null, job_default_key: null, values: {} });
  const [baseline, setBaseline] = useState<Editable>(input);
  const [loading, setLoading] = useState(true), [loadError, setLoadError] = useState<unknown>();
  const [message, setMessage] = useState(location.state?.saved ? 'Draf tersimpan.' : '');
  const [error, setError] = useState(''), [errors, setErrors] = useState<Values>({});
  const [busy, setBusy] = useState(false), [uncertain, setUncertain] = useState<Attempt>();
  const [documents, setDocuments] = useState<Receipt[]>([]);
  const [selection, setSelection] = useState<{ input: Editable; kind?: Kind }>();
  const [retry, setRetry] = useState(0);
  const lock = useRef(false), alive = useRef(true), abort = useRef(new AbortController());
  const createId = useRef(crypto.randomUUID());
  const allowLeave = useRef(false);
  useEffect(() => {
    alive.current = true;
    const controller = new AbortController(); abort.current = controller;
    const signal = controller.signal;

    async function load() {
      try {
        const person = decodeEmployee(await request(`/api/employees/${employeeId}/`, { signal }));
        const saved = draftId ? decodeDraft(await request(`/api/contract-drafts/${draftId}/`, { signal })) : undefined;
        if (saved && saved.employee !== employeeId) throw new ApiError('protocol', 200, null, null);
        const refs = decodeReferences(await request('/api/contract-references/' + (saved ? `?version=${encodeURIComponent(saved.reference_version)}` : ''), { signal }));
        const docs = saved ? decodeDocuments(await request(`/api/contract-drafts/${saved.id}/documents/`, { signal })) : [];
        if (signal.aborted) return;
        const startKind = saved?.pkwt_type ?? (person.employment_status === 'magang' ? 'yayasan' : kinds.includes(person.pkwt_type as Kind) ? person.pkwt_type as Kind : undefined);
        const start = saved ? editable(saved) : startKind ? initialValues({ ...person, pkwt_type: startKind }, refs) : { source_unit: null, job_default_key: null, values: {} };
        setSelectedKind(startKind); setBaselineKind(startKind);
        setEmployee(person); setDraft(saved); setReferences(refs); setInput(start); setBaseline(start); setDocuments(docs);
      } catch (cause) { if (!signal.aborted && !isAbort(cause)) setLoadError(cause); }
      finally { if (!signal.aborted) setLoading(false); }
    }
    void load();
    return () => { alive.current = false; controller.abort(); };
  }, [employeeId, draftId, request, session.generation, retry]);
  const kind = (draft?.pkwt_type ?? selectedKind ?? '') as Kind;
  const fields = references?.fields[kind] ?? [];
  const dirty = !same(input, baseline) || (!draft && selectedKind !== baselineKind);
  const eligible = employee?.employment_status === 'kontrak' || employee?.employment_status === 'magang';
  const configured = Boolean(references?.available && (!draft || (references.version === draft.reference_version && references.templates[kind]?.sha256 === draft.template_sha256)));
  const complete = fields.length > 0 && fields.every(f => !f.required_for_generation || Boolean(input.values[f.key]?.trim()));
  function accept(saved: Draft) {
    if (saved.employee !== employeeId) throw new ApiError('protocol', 200, null, 'uncertain');
    setDraft(saved); setInput(editable(saved)); setBaseline(editable(saved)); setUncertain(undefined);
    setError(''); setMessage('Draf tersimpan.');
    if (!draftId) { allowLeave.current = true; navigate(`/employees/${employeeId}/contracts/${saved.id}`, { replace: true, state: { saved: true } }); }
  }
  function failure(cause: unknown, attempt?: Attempt) {
    if (!alive.current || isAbort(cause)) return;
    if (cause instanceof ApiError && cause.status === 400 && cause.body && typeof cause.body === 'object') {
      const next = Object.fromEntries(Object.entries(cause.body).map(([key, value]) => [key, Array.isArray(value) ? value.join(' ') : 'Isian tidak valid.']));
      setErrors(next); setError('Periksa isian kontrak.');
      requestAnimationFrame(() => document.getElementById('contract-' + Object.keys(next)[0])?.focus());
    } else if (cause instanceof ApiError && cause.status === 409) setError('Draf telah berubah. Isian Anda tetap tersedia; buka ulang draf untuk membandingkan.');
    else { setError(errorText(cause)); if (attempt && cause instanceof ApiError && cause.writeOutcome === 'uncertain') setUncertain(attempt); }
  }
  async function run(operation: () => Promise<void>) {
    if (lock.current || !alive.current) return;
    lock.current = true; setBusy(true); setError(''); setErrors({}); setMessage('');
    try { await operation(); } finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  async function save() {
    if (uncertain || (!draft && (!eligible || !configured || !kinds.includes(kind)))) return;
    const values = canonical(input.values, fields);
    const next = { ...input, values };
    const attempt: Attempt = { kind: draft ? 'save' : 'create', id: draft?.id ?? createId.current, revision: draft?.revision ?? 0, resultRevision: draft && same(next, editable(draft)) ? draft.revision : (draft?.revision ?? 0) + 1, pkwt_type: kind, input: next };
    await run(async () => {
      try {
        const saved = decodeDraft(await request(`/api/contract-drafts/${draft ? draft.id + '/' : ''}`, { method: draft ? 'PATCH' : 'POST', signal: abort.current.signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(draft ? { expected_revision: draft.revision, ...next } : { id: attempt.id, employee: employeeId, pkwt_type: attempt.pkwt_type, ...next }) }), true);
        if (saved.pkwt_type !== attempt.pkwt_type) throw new ApiError('protocol', 200, null, 'uncertain');
        if (alive.current) accept(saved);
      } catch (cause) { failure(cause, attempt); }
    });
  }
  async function generate() {
    if (!draft || dirty || !complete || !configured || uncertain) return;
    const attempt: Attempt = { kind: 'generate', id: draft.id, revision: draft.revision };
    await run(async () => {
      try {
        const receipt = decodeReceipt(await request(`/api/contract-drafts/${draft.id}/generate/`, { method: 'POST', signal: abort.current.signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ expected_revision: draft.revision }) }), true);
        if (receipt.draft !== draft.id || receipt.revision !== draft.revision || receipt.template_sha256 !== draft.template_sha256) throw new ApiError('protocol', 200, null, 'uncertain');
        if (alive.current) { setDocuments(old => [receipt, ...old.filter(row => row.id !== receipt.id)]); setMessage('DOCX dibuat.'); }
      } catch (cause) { failure(cause, attempt); }
    });
  }
  async function recover() {
    if (!uncertain) return;
    const attempt = uncertain;
    await run(async () => {
      try {
        if (attempt.kind === 'generate') {
          const receipts = decodeDocuments(await request(`/api/contract-drafts/${attempt.id}/documents/`, { signal: abort.current.signal }));
          const found = receipts.find(row => row.revision === attempt.revision && row.template_sha256 === draft?.template_sha256);
          if (!found) { setError('Hasil belum dapat dipastikan. Periksa lagi.'); return; }
          if (alive.current) { setDocuments(receipts); setUncertain(undefined); setMessage('DOCX dibuat.'); }
        } else {
          const saved = decodeDraft(await request(`/api/contract-drafts/${attempt.id}/`, { signal: abort.current.signal }));
          if (saved.employee !== employeeId || saved.pkwt_type !== attempt.pkwt_type || saved.revision !== attempt.resultRevision || !same(editable(saved), attempt.input)) { setError('Hasil berbeda dari isian yang dikirim. Bandingkan draf tersimpan sebelum melanjutkan.'); return; }
          if (alive.current) accept(saved);
        }
      } catch (cause) { if (alive.current && !isAbort(cause)) setError('Hasil belum dapat dipastikan. Periksa lagi.'); }
    });
  }
  async function download(receipt: Receipt) {
    await run(async () => {
      let url: string | undefined;
      try {
        const response = await fetch(receipt.download_url, { credentials: 'same-origin', signal: abort.current.signal });
        if (response.status === 403) { session.retryIdentity(); return; }
        if (!response.ok || response.headers.get('content-type')?.split(';')[0] !== mime) throw new ApiError('protocol', response.status, null, null);
        const blob = await response.blob();
        if (!alive.current || abort.current.signal.aborted) return;
        const verified = await request<{ id: number; capabilities: { employees_write: boolean } }>('/api/auth/me/', { signal: abort.current.signal });
        if (verified.id !== session.identity?.id || !verified.capabilities?.employees_write) { session.retryIdentity(); return; }
        if (!alive.current || abort.current.signal.aborted) return;
        url = URL.createObjectURL(blob);
        const anchor = document.createElement('a'); anchor.href = url; anchor.download = receipt.filename; anchor.click();
      } catch (cause) { failure(cause); }
      finally { if (url) URL.revokeObjectURL(url); }
    });
  }
  function choose(type: 'unit' | 'job', key: string) {
    if (!references || lock.current || uncertain) return;
    let next: Editable;
    if (type === 'unit') next = { source_unit: key || null, job_default_key: null, values: { ...input.values, ...(key ? unitDefaults(references, key, kind) : {}) } };
    else {
      const row = references.jobs.find(x => x.key === key && x.pkwt_type === kind && x.unit.trim().toLowerCase() === input.source_unit?.trim().toLowerCase());
      next = { ...input, job_default_key: row?.key ?? null, values: { ...input.values, ...(row ? { jabatan: row.title, jobdesk: row.jobdesk } : {}) } };
    }
    const replacesReviewedValue = Object.keys(next.values).some(field => Boolean(input.values[field]?.trim()) && next.values[field] !== input.values[field]);
    if ((dirty || replacesReviewedValue) && !same(next.values, input.values)) setSelection({ input: next }); else setInput(next);
  }
  function chooseKind(value: string) {
    if (draft || !employee || !references || lock.current || uncertain || !kinds.includes(value as Kind) || value === kind) return;
    const nextKind = value as Kind;
    const next = initialValues({ ...employee, pkwt_type: nextKind }, references);
    if (dirty && !same(next, input)) setSelection({ input: next, kind: nextKind });
    else { setSelectedKind(nextKind); setInput(next); setErrors({}); }
  }
  return { employee, draft, references, fields, kind, input, dirty, eligible, configured, complete, loading, loadError, error, errors, message, busy, uncertain, documents, selection, allowLeave,
    change: (key: string, value: string) => setInput(old => ({ ...old, values: { ...old.values, [key]: value } })),
    choose, chooseKind, confirmSelection: () => { if (lock.current || uncertain) return; if (selection) { setInput(selection.input); if (selection.kind) { setSelectedKind(selection.kind); setErrors({}); } } setSelection(undefined); }, cancelSelection: () => setSelection(undefined),
    save, generate, recover, download, retry: () => { setLoading(true); setLoadError(undefined); setRetry(x => x + 1); } };
}
