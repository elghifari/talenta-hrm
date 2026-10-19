import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router';
import { errorText } from '../api/client';
import { useSession } from '../auth/SessionProvider';
export function AppShell() {
  const session = useSession(); const location = useLocation();
  const [menu, setMenu] = useState(false); const [error, setError] = useState('');
  const menuButton = useRef<HTMLButtonElement>(null);
  const main = useRef<HTMLElement>(null);
  useEffect(() => { const h = main.current?.querySelector('h1'); if (h) { h.tabIndex = -1; h.focus(); } }, [location.pathname]);
  function closeMenu() { setMenu(false); menuButton.current?.focus(); }
  return <div className="app-shell" onKeyDown={event => { if (event.key === 'Escape' && menu) closeMenu(); }}>
    <a className="skip-link" href="#main">Ke konten utama</a>
    <aside className={'sidebar' + (menu ? ' open' : '')} id="primary-nav"><div className="brand">Talenta HRIS<span>Administrasi kepegawaian</span></div><p className="nav-label">Ruang kerja</p><nav aria-label="Modul"><NavLink to="/employees" onClick={() => setMenu(false)}>Personnel</NavLink></nav></aside>
    <div className="workspace"><header className="app-header"><span className="breadcrumb">Personnel / Data pegawai</span><button className="menu-toggle" ref={menuButton} aria-expanded={menu} aria-controls="primary-nav" onClick={() => setMenu(x => !x)}>Menu</button><div className="account"><span>{session.identity?.email}</span><button disabled={session.busy} onClick={() => { setError(''); session.logout().catch(e => setError(errorText(e))); }}>Keluar</button></div></header>
    <main id="main" className="content" ref={main}>{error && <p className="error" role="alert">{error}</p>}{session.identity?.capabilities.employees_read ? <Outlet /> : <><h1>Akses tidak tersedia</h1><p>Akun ini tidak memiliki izin untuk melihat data pegawai.</p><Link to="/login">Periksa akun</Link></>}</main></div>
  </div>;
}
