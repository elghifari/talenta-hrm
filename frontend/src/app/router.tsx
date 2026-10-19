import { Navigate, createBrowserRouter, createMemoryRouter } from 'react-router';
import { useSession } from '../auth/SessionProvider';
import { LoginPage } from '../auth/LoginPage';
import { EmployeeListPage } from '../employees/EmployeeListPage';
import { EmployeeDetailPage } from '../employees/EmployeeDetailPage';
import { AppShell } from './AppShell';
function Gate() {
  const session = useSession();
  if (session.status === 'checking') return <main className="session-state" role="status">Memeriksa sesi…</main>;
  if (session.status === 'error') return <main className="session-state"><p role="alert">Sesi belum dapat diperiksa.</p><button onClick={session.retryIdentity}>Coba lagi</button></main>;
  if (session.status === 'anonymous') return <LoginPage />;
  return <AppShell key={session.generation} />;
}
export function makeRouter(initialEntries?: string[]) {
  const routes = [{ element: <Gate />, children: [
    { path: '/', element: <Navigate replace to="/employees" /> },
    { path: '/login', element: <Navigate replace to="/employees" /> },
    { path: '/employees', element: <EmployeeListPage /> },
    { path: '/employees/:id', element: <EmployeeDetailPage /> },
    { path: '*', element: <><h1>Halaman tidak ditemukan</h1><a href="/employees">Kembali ke data pegawai</a></> },
  ] }];
  return initialEntries ? createMemoryRouter(routes, { initialEntries }) : createBrowserRouter(routes);
}
