import type { Field, Values } from './types';
export function ContractFields({ fields, values, errors, disabled, change }: { fields: Field[]; values: Values; errors: Values; disabled: boolean; change(key: string, value: string): void }) {
  const groups = [...new Set(fields.map(f => f.group))];
  return <>{groups.map(group => <fieldset key={group} className="contract-fields"><legend>{group}</legend>{fields.filter(f => f.group === group).map(field => {
    const id = 'contract-' + field.key;
    const props = { id, name: field.key, value: values[field.key] ?? '', disabled, 'aria-invalid': Boolean(errors[field.key]), 'aria-describedby': errors[field.key] ? id + '-error' : undefined, onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => change(field.key, event.target.value) };
    return <div className={'form-field' + (field.kind === 'textarea' ? ' contract-wide' : '')} key={field.key}><label htmlFor={id}>{field.label}</label>{field.kind === 'choice' ? <select {...props}><option value="">Pilih…</option>{field.choices.map(choice => <option key={choice} value={choice}>{choice}</option>)}</select> : field.kind === 'textarea' ? <textarea {...props} rows={7} maxLength={field.max_length} /> : <input {...props} type={field.kind === 'number' ? 'number' : field.kind === 'date' ? 'date' : 'text'} step={field.kind === 'number' ? 1 : undefined} min={field.kind === 'number' ? 0 : undefined} maxLength={field.max_length} />}{errors[field.key] && <p id={id + '-error'} className="error">{errors[field.key]}</p>}</div>;
  })}</fieldset>)}</>;
}
