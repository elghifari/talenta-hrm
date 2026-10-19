export type ApiFailureKind = 'http' | 'network' | 'protocol';
export class ApiError extends Error {
  constructor(public kind: ApiFailureKind, public status: number | null,
    public body: unknown, public writeOutcome: 'rejected' | 'uncertain' | null) {
    super('API request failed');
  }
}
type Options = Omit<RequestInit, 'body'> & { body?: BodyInit; csrfToken?: string; fetcher?: typeof fetch };
export async function apiRequest<T>(path: string, options: Options = {}): Promise<T> {
  const { csrfToken, fetcher = fetch, ...init } = options;
  const unsafe = !['GET', 'HEAD', 'OPTIONS'].includes((init.method || 'GET').toUpperCase());
  if (!path.startsWith('/api/')) throw new ApiError('protocol', null, null, 'rejected');
  const headers = new Headers(init.headers);
  if (unsafe) headers.set('X-CSRFToken', csrfToken ?? await getCsrf(init.signal ?? undefined));
  let response: Response;
  try { response = await fetcher(path, { ...init, headers, credentials: 'same-origin' }); }
  catch (error) {
    if (init.signal?.aborted) throw error;
    throw new ApiError('network', null, null, unsafe ? 'uncertain' : null);
  }
  if (response.status === 204) return undefined as T;
  let body: unknown = null;
  try { if (response.headers.get('content-type')?.includes('application/json')) body = await response.json(); }
  catch { if (response.ok) throw new ApiError('protocol', response.status, null, unsafe ? 'uncertain' : null); }
  if (!response.ok) throw new ApiError('http', response.status, body,
    unsafe ? (response.status >= 500 ? 'uncertain' : 'rejected') : null);
  if (body === null) throw new ApiError('protocol', response.status, null, unsafe ? 'uncertain' : null);
  return body as T;
}
export async function getCsrf(signal?: AbortSignal): Promise<string> {
  const body = await apiRequest<{ csrfToken?: unknown }>('/api/auth/csrf/', { signal });
  if (typeof body?.csrfToken !== 'string') throw new ApiError('protocol', 200, null, null);
  return body.csrfToken;
}
export function isAbort(error: unknown) { return error instanceof DOMException && error.name === 'AbortError'; }
export function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.writeOutcome === 'uncertain') return 'Hasil penyimpanan belum dapat dipastikan. Periksa data yang tersimpan sebelum mencoba lagi.';
    if (error.status === 403) return 'Tindakan ditolak. Periksa izin akun atau muat ulang halaman sebelum mencoba lagi.';
  }
  return 'Permintaan belum dapat diselesaikan. Periksa koneksi dan coba lagi.';
}
