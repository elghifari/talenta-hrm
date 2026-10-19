import { useEffect, useState } from 'react';
import { isAbort } from '../api/client';
import { useSession } from '../auth/SessionProvider';
export function useEmployeeRead<T>(path: string, decode: (value: unknown) => T) {
  const { request, generation } = useSession();
  const [attempt, setAttempt] = useState(0);
  const key = path + ':' + generation + ':' + attempt;
  const [result, setResult] = useState<{ key: string; data?: T; error?: unknown } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    request<unknown>(path, { signal: controller.signal }).then(decode).then(data => {
      if (!controller.signal.aborted) setResult({ key, data });
    }).catch(error => { if (!controller.signal.aborted && !isAbort(error)) setResult({ key, error }); });
    return () => controller.abort();
  }, [request, path, decode, key]);
  const current = result?.key === key ? result : null;
  return { data: current?.data, error: current?.error, loading: !current, retry: () => setAttempt(x => x + 1) };
}
