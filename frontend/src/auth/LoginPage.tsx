import { useState, type FormEvent } from 'react';
import { ApiError, errorText } from '../api/client';
import { useSession } from './SessionProvider';
export function LoginPage() {
  const session = useSession();
  const [email, setEmail] = useState(''); const [password, setPassword] = useState(''); const [error, setError] = useState('');
  async function submit(event: FormEvent) {
    event.preventDefault(); setError('');
    try { await session.login(email, password); setPassword(''); }
    catch (e) { setError(e instanceof ApiError && e.status === 400 ? 'Email atau sandi tidak sesuai.' : errorText(e)); }
  }
  return <main className="login-page"><form onSubmit={submit} className="login-form"><p className="product-name">Talenta HRIS</p><h1>Masuk</h1>
    {session.expired && <p role="status">Sesi Anda berakhir. Masuk kembali untuk melanjutkan.</p>}
    <label htmlFor="email">Email</label><input id="email" type="email" autoComplete="username" required value={email} onChange={e => setEmail(e.target.value)} />
    <label htmlFor="password">Sandi</label><input id="password" type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} />
    {error && <p className="error" role="alert">{error}</p>}<button className="primary" disabled={session.busy} type="submit">{session.busy ? 'Memeriksa…' : 'Masuk'}</button>
  </form></main>;
}
