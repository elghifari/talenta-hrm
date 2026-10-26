import { ApiError, errorText, type apiRequest } from '../api/client';

export type GroupChoice = { id: string; name: string; branch?: string; branch_name?: string };
export type DivisionSettings = { kinerja_enabled: boolean; pelimpahan_enabled: boolean };
export type DivisionChoice = GroupChoice & DivisionSettings & { branch: string; branch_name: string };
export function divisionSettings(division: DivisionSettings): DivisionSettings {
  return { kinerja_enabled: division.kinerja_enabled, pelimpahan_enabled: division.pelimpahan_enabled };
}
export type GroupKind = 'branches' | 'divisions';
export function decodeChoice(value: unknown): GroupChoice {
  const choice = value as GroupChoice | null;
  if (!choice || typeof choice.id !== 'string' || typeof choice.name !== 'string' || !choice.name.trim()) throw new ApiError('protocol', 200, null, null);
  return choice;
}
export function decodeChoices(value: unknown): GroupChoice[] {
  if (!Array.isArray(value)) throw new ApiError('protocol', 200, null, null);
  return value.map(decodeChoice);
}
export function decodeDivisionChoices(value: unknown): DivisionChoice[] {
  return decodeChoices(value).map(choice => {
    const division = choice as DivisionChoice;
    if (typeof division.branch !== 'string' || !division.branch || typeof division.branch_name !== 'string' || !division.branch_name.trim() || typeof division.kinerja_enabled !== 'boolean' || typeof division.pelimpahan_enabled !== 'boolean') throw new ApiError('protocol', 200, null, null);
    return division;
  });
}
export async function saveChoice(request: typeof apiRequest, kind: GroupKind, input: { name: string; branch?: string }, id?: string, signal?: AbortSignal) {
  const value = await request('/api/organization/' + kind + '/' + (id ? encodeURIComponent(id) + '/' : ''), { method: id ? 'PATCH' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input), signal });
  try { return kind === 'divisions' ? decodeDivisionChoices([value])[0] : decodeChoice(value); } catch { throw new ApiError('protocol', id ? 200 : 201, null, 'uncertain'); }
}
export function choiceError(error: unknown) {
  if (error instanceof ApiError && error.status === 400 && error.body && typeof error.body === 'object') {
    const messages = Object.entries(error.body).filter(([key]) => key === 'name' || key === 'branch').flatMap(([key, value]) => Array.isArray(value) && value.every(item => typeof item === 'string') ? [(key === 'branch' ? 'Cabang: ' : '') + value.join(' ')] : []);
    if (messages.length) return messages.join(' ');
  }
  return errorText(error);
}