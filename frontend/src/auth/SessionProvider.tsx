import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { ApiError, apiRequest, getCsrf } from '../api/client';
export type Identity = { id: number; email: string; capabilities: { employees_read: boolean; employees_write: boolean } };
function decodeIdentity(value: unknown): Identity {
  const x = value as Identity | null;
  if (!x || typeof x.id !== 'number' || typeof x.email !== 'string' ||
      typeof x.capabilities?.employees_read !== 'boolean' || typeof x.capabilities?.employees_write !== 'boolean') {
    throw new ApiError('protocol', 200, null, null);
  }
  return x;
}
type Status = 'checking' | 'authenticated' | 'anonymous' | 'error';
type Session = {
  status: Status; identity: Identity | null; expired: boolean; busy: boolean; generation: number;
  login(email: string, password: string): Promise<void>; logout(): Promise<void>; retryIdentity(): void;
  request<T>(path: string, options?: Parameters<typeof apiRequest>[1]): Promise<T>;
};
const Context = createContext<Session | null>(null);
export function SessionProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>('checking');
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [expired, setExpired] = useState(false);
  const [busy, setBusy] = useState(false);
  const [generation, setGeneration] = useState(0);
  const epoch = useRef(0);
  const clear = useCallback((expiration: boolean) => {
    epoch.current += 1; setGeneration(epoch.current); setIdentity(null); setExpired(expiration); setStatus('anonymous');
  }, []);
  const retryIdentity = useCallback(() => {
    const current = ++epoch.current; setGeneration(current); setStatus('checking');
    apiRequest<unknown>('/api/auth/me/').then(decodeIdentity).then(user => {
      if (epoch.current !== current) return;
      setIdentity(user); setStatus('authenticated');
    }).catch(error => {
      if (epoch.current !== current) return;
      setIdentity(null); setStatus(error instanceof ApiError && error.status === 403 ? 'anonymous' : 'error');
    });
  }, []);
  useEffect(() => { retryIdentity(); return () => { epoch.current += 1; }; }, [retryIdentity]);
  const login = useCallback(async (email: string, password: string) => {
    const current = ++epoch.current; setBusy(true);
    try {
      const csrfToken = await getCsrf();
      await apiRequest('/api/auth/login/', { method: 'POST', csrfToken, body: new URLSearchParams({ username: email, password }) });
      await getCsrf();
      const user = decodeIdentity(await apiRequest('/api/auth/me/'));
      if (epoch.current !== current) return;
      setGeneration(current); setIdentity(user); setExpired(false); setStatus('authenticated');
    } finally { if (epoch.current === current) setBusy(false); }
  }, []);
  const logout = useCallback(async () => {
    const current = epoch.current; setBusy(true);
    try {
      try { await apiRequest('/api/auth/logout/', { method: 'POST' }); }
      catch (error) {
        if (!(error instanceof ApiError && error.status === 403)) throw error;
        try { await apiRequest('/api/auth/me/'); throw error; }
        catch (verification) { if (!(verification instanceof ApiError && verification.status === 403)) throw verification; }
      }
      if (epoch.current === current) clear(false);
    } finally { setBusy(false); }
  }, [clear]);
  const request = useCallback(async <T,>(path: string, options?: Parameters<typeof apiRequest>[1]): Promise<T> => {
    const current = epoch.current;
    try {
      const result = await apiRequest<T>(path, options);
      if (current !== epoch.current) throw new DOMException('Stale session', 'AbortError');
      return result;
    } catch (error) {
      if (current !== epoch.current) throw new DOMException('Stale session', 'AbortError');
      if (error instanceof ApiError && error.status === 403) {
        try { decodeIdentity(await apiRequest('/api/auth/me/')); }
        catch (verification) {
          if (current === epoch.current && verification instanceof ApiError && verification.status === 403) clear(true);
        }
      }
      throw error;
    }
  }, [clear]);
  return <Context.Provider value={{ status, identity, expired, busy, generation, login, logout, retryIdentity, request }}>{children}</Context.Provider>;
}
export function useSession() {
  const session = useContext(Context);
  if (!session) throw new Error('Session provider missing');
  return session;
}
