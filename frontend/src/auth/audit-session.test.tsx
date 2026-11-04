import { act, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { SessionProvider, useSession } from './SessionProvider';

function Probe() {
  const session = useSession();
  return <div data-testid="identity">{JSON.stringify({ status: session.status, generation: session.generation, read: session.identity?.capabilities.audit_read })}</div>;
}
afterEach(() => vi.unstubAllGlobals());

test('missing audit capability defaults false', async () => {
  const capabilities = { employees_read: true, employees_write: true };
  vi.stubGlobal('fetch', vi.fn(async () => Response.json({ id: 1, email: 'hr@example.test', capabilities })));
  render(<SessionProvider><Probe /></SessionProvider>);
  await waitFor(() => expect(JSON.parse(screen.getByTestId('identity').textContent!).read).toBe(false));
});

test.each([null, 'true', 1])('invalid audit capability %s fails bootstrap', async audit_read => {
  vi.stubGlobal('fetch', vi.fn(async () => Response.json({ id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: true, audit_read } })));
  render(<SessionProvider><Probe /></SessionProvider>);
  await waitFor(() => expect(JSON.parse(screen.getByTestId('identity').textContent!).status).toBe('error'));
});

test('audit-only revocation increments session generation', async () => {
  let audit_read = true;
  vi.stubGlobal('fetch', vi.fn(async () => Response.json({ id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: true, audit_read } })));
  render(<SessionProvider><Probe /></SessionProvider>);
  await waitFor(() => expect(JSON.parse(screen.getByTestId('identity').textContent!).read).toBe(true));
  const previous = JSON.parse(screen.getByTestId('identity').textContent!).generation;
  audit_read = false;
  await act(async () => window.dispatchEvent(new Event('focus')));
  await waitFor(() => expect(JSON.parse(screen.getByTestId('identity').textContent!).generation).toBeGreaterThan(previous));
  expect(JSON.parse(screen.getByTestId('identity').textContent!).read).toBe(false);
});
