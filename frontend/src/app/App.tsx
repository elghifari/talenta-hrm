import { useState } from 'react';
import { SessionProvider, useSession } from '../auth/SessionProvider';
import { LoginPage } from '../auth/LoginPage';
import { errorText } from '../api/client';
function Content() {
  const session = useSession(); const [error, setError] = useState('');
  if (session.status === 'checking') return <main role="status">Memeriksa sesi…</main>;
  if (session.status === 'error') return <main><p role="alert">Sesi belum dapat diperiksa.</p><button onClick={session.retryIdentity}>Coba lagi</button></main>;
  if (session.status === 'anonymous') return <LoginPage />;
  return <main><p>{session.identity?.email}</p><button onClick={() => { session.logout().catch(e => setError(errorText(e))); }} disabled={session.busy}>Keluar</button>{error && <p role="alert">{error}</p>}</main>;
}
export function App() { return <SessionProvider><Content /></SessionProvider>; }
