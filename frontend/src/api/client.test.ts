import { afterEach, expect, test, vi } from 'vitest';
import { ApiError, apiRequest } from './client';
afterEach(() => vi.unstubAllGlobals());
test('unsafe requests use same-origin cookies, CSRF and accept empty 204', async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
  expect(await apiRequest('/api/auth/logout/', { method: 'POST', csrfToken: 'valid', fetcher })).toBeUndefined();
  expect(fetcher).toHaveBeenCalledWith('/api/auth/logout/', expect.objectContaining({ credentials: 'same-origin', method: 'POST' }));
  expect((fetcher.mock.calls[0][1].headers as Headers).get('X-CSRFToken')).toBe('valid');
});
test('HTML permission errors remain sanitized and rejected without mutation retry', async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response('<script>private</script>', { status: 403 }));
  await expect(apiRequest('/api/employees/', { method: 'POST', csrfToken: 'valid', fetcher })).rejects.toMatchObject({ status: 403, body: null, writeOutcome: 'rejected' });
  expect(fetcher).toHaveBeenCalledTimes(1);
});
test('lost mutation response is uncertain, never automatically repeated', async () => {
  const fetcher = vi.fn().mockRejectedValue(new TypeError('Connection lost'));
  await expect(apiRequest('/api/employees/', { method: 'POST', csrfToken: 'valid', fetcher })).rejects.toMatchObject({ kind: 'network', writeOutcome: 'uncertain' });
  expect(fetcher).toHaveBeenCalledTimes(1);
});
test('invalid success payload is uncertain for mutation', async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response('not JSON', { status: 201, headers: { 'content-type': 'application/json' } }));
  await expect(apiRequest('/api/employees/', { method: 'POST', csrfToken: 'valid', fetcher })).rejects.toMatchObject({ kind: 'protocol', writeOutcome: 'uncertain' });
});
test('transport cannot be directed to an outside origin', async () => {
  const fetcher = vi.fn();
  await expect(apiRequest('https://outside.example/api/', { fetcher })).rejects.toBeInstanceOf(ApiError);
  expect(fetcher).not.toHaveBeenCalled();
});
