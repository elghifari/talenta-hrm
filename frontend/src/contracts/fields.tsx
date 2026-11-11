import { contractFieldGroups } from './sections';
import type { Field, Values } from './types';

const wideFields = new Set(['nama', 'jalan', 'nama_unit', 'alamat_unit', 'pihak1_nama']);

export function ContractFields({ fields, values, errors, disabled, change }: { fields: Field[]; values: Values; errors: Values; disabled: boolean; change(key: string, value: string): void }) {
  const groups = contractFieldGroups(fields);
  return <>{groups.map((group, index) => <section key={group.id} id={group.id} className="contract-form-section" aria-labelledby={group.id + '-heading'}>
    <header className="contract-section-heading"><h2 id={group.id + '-heading'} tabIndex={-1}>{group.label}</h2><span>{index + 2} / {groups.length + 1}</span></header>
    <div className="contract-fields">{group.fields.map(field => {
      const id = 'contract-' + field.key;
      const props = { id, name: field.key, value: values[field.key] ?? '', disabled, 'aria-invalid': Boolean(errors[field.key]), 'aria-describedby': errors[field.key] ? id + '-error' : undefined, onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => change(field.key, event.target.value) };
      return <div className={'form-field' + (field.kind === 'textarea' || wideFields.has(field.key) ? ' contract-wide' : '')} key={field.key}>
        <label htmlFor={id}>{field.label}{!field.required_for_generation && <span className="contract-optional"> (opsional)</span>}</label>
        {field.kind === 'choice' ? <select {...props}><option value="">Pilih…</option>{field.choices.map(choice => <option key={choice} value={choice}>{choice}</option>)}</select> : field.kind === 'textarea' ? <textarea {...props} rows={7} maxLength={field.max_length} /> : <input {...props} type={field.kind === 'number' ? 'number' : field.kind === 'date' ? 'date' : 'text'} inputMode={field.kind === 'number' ? 'numeric' : undefined} step={field.kind === 'number' ? 1 : undefined} min={field.kind === 'number' ? 0 : undefined} maxLength={field.max_length} />}
        {errors[field.key] && <p id={id + '-error'} className="error">{errors[field.key]}</p>}
      </div>;
    })}</div>
  </section>)}</>;
}
