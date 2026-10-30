import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { ApiError, apiRequest, getCsrf } from '../api/client';
export type Identity = { id: number; email: string; capabilities: { employees_read: boolean; employees_write: boolean; audit_read: boolean } };
function decodeIdentity(value: unknown): Identity {
  const x = value as Identity | null;
  if (!x || typeof x.id !== 'number' || typeof x.email !== 'string' ||
      typeof x.capabilities?.employees_read !== 'boolean' || typeof x.capabilities?.employees_write !== 'boolean' ||
      (x.capabilities.audit_read !== undefined && typeof x.capabilities.audit_read !== 'boolean')) {
    throw new ApiError('protocol', 200, null, null);
  }
  return { ...x, capabilities: { ...x.capabilities, audit_read: x.capabilities.audit_read ?? false } };
}
function changedIdentity(previous: Identity, next: Identity) {
  return previous.id !== next.id || previous.email !== next.email ||
    previous.capabilities.employees_read !== next.capabilities.employees_read ||
    previous.capabilities.employees_write !== next.capabilities.employees_write ||
    previous.capabilities.audit_read !== next.capabilities.audit_read;
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
  const verifiedIdentity = useRef<Identity | null>(null);
  const channel = useRef<BroadcastChannel | null>(null);
  const acceptIdentity = useCallback((user: Identity) => {
    if (verifiedIdentity.current && changedIdentity(verifiedIdentity.current, user)) epoch.current += 1;
    verifiedIdentity.current = user;
    setGeneration(epoch.current); setIdentity(user); setExpired(false); setStatus('authenticated'); setBusy(false);
  }, []);
  const clear = useCallback((expiration: boolean) => {
    epoch.current += 1; verifiedIdentity.current = null;
    setGeneration(epoch.current); setIdentity(null); setExpired(expiration); setStatus('anonymous'); setBusy(false);
  }, []);
  const retryIdentity = useCallback(() => {
    const current = ++epoch.current; verifiedIdentity.current = null;
    setGeneration(current); setIdentity(null); setStatus('checking'); setBusy(false);
    apiRequest<unknown>('/api/auth/me/').then(decodeIdentity).then(user => {
      if (epoch.current === current) acceptIdentity(user);
    }).catch(error => {
      if (epoch.current !== current) return;
      setStatus(error instanceof ApiError && error.status === 403 ? 'anonymous' : 'error');
    });
  }, [acceptIdentity]);
  useEffect(() => { retryIdentity(); return () => { epoch.current += 1; }; }, [retryIdentity]);
  useEffect(() => {
    function verifyOnFocus() {
      const current = epoch.current;
      apiRequest('/api/auth/me/').then(decodeIdentity).then(user => {
        if (current === epoch.current) acceptIdentity(user);
      }).catch(error => {
        if (current === epoch.current && verifiedIdentity.current && error instanceof ApiError && error.status === 403) clear(true);
      });
    }
    if (typeof window.BroadcastChannel === 'function') {
      const connection = new window.BroadcastChannel('talenta-hrm-session');
      channel.current = connection;
      connection.onmessage = event => { if (event.data?.type === 'changed') retryIdentity(); };
    }
    window.addEventListener('focus', verifyOnFocus);
    return () => {
      window.removeEventListener('focus', verifyOnFocus);
      channel.current?.close(); channel.current = null;
    };
  }, [acceptIdentity, clear, retryIdentity]);
  const login = useCallback(async (email: string, password: string) => {
    const current = ++epoch.current; setBusy(true);
    try {
      const csrfToken = await getCsrf();
      await apiRequest('/api/auth/login/', { method: 'POST', csrfToken, body: new URLSearchParams({ username: email, password }) });
      await getCsrf();
      const user = decodeIdentity(await apiRequest('/api/auth/me/'));
      if (epoch.current !== current) return;
      acceptIdentity(user); channel.current?.postMessage({ type: 'changed' });
    } finally { if (epoch.current === current) setBusy(false); }
  }, [acceptIdentity]);
  const logout = useCallback(async () => {
    const current = epoch.current; setBusy(true);
    try {
      try { await apiRequest('/api/auth/logout/', { method: 'POST' }); }
      catch (error) {
        if (!(error instanceof ApiError && error.status === 403)) throw error;
        let anonymous = false;
        try {
          const user = decodeIdentity(await apiRequest('/api/auth/me/'));
          if (current === epoch.current) acceptIdentity(user);
        } catch (verification) {
          if (verification instanceof ApiError && verification.status === 403) anonymous = true;
          else throw verification;
        }
        if (!anonymous) throw error;
      }
      if (epoch.current === current) { clear(false); channel.current?.postMessage({ type: 'changed' }); }
    } finally { setBusy(false); }
  }, [clear, acceptIdentity]);
  const request = useCallback(async <T,>(path: string, options?: Parameters<typeof apiRequest>[1]): Promise<T> => {
    const current = epoch.current;
    try {
      const result = await apiRequest<T>(path, options);
      if (current !== epoch.current) throw new DOMException('Stale session', 'AbortError');
      return result;
    } catch (error) {
      if (current !== epoch.current) throw new DOMException('Stale session', 'AbortError');
      if (error instanceof ApiError && error.status === 403) {
        try {
          const user = decodeIdentity(await apiRequest('/api/auth/me/'));
          if (current === epoch.current) acceptIdentity(user);
        } catch (verification) {
          if (current === epoch.current && verification instanceof ApiError && verification.status === 403) clear(true);
        }
        if (current !== epoch.current) throw new DOMException('Stale session', 'AbortError');
      }
      throw error;
    }
  }, [clear, acceptIdentity]);
  return <Context.Provider value={{ status, identity, expired, busy, generation, login, logout, retryIdentity, request }}>{children}</Context.Provider>;
}
export function useSession() {
  const session = useContext(Context);
  if (!session) throw new Error('Session provider missing');
  return session;
}
