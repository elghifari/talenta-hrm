import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { Link, Outlet, useLocation } from 'react-router';
import { errorText } from '../api/client';
import { useSession } from '../auth/SessionProvider';
import { Breadcrumbs } from './Breadcrumbs';
import { Sidebar } from './Sidebar';
const mobileQuery = '(max-width: 680px)';
function subscribeMobile(listener: () => void) {
  const query = window.matchMedia?.(mobileQuery);
  query?.addEventListener('change', listener);
  return () => query?.removeEventListener('change', listener);
}
function mobileSnapshot() { return window.matchMedia?.(mobileQuery).matches ?? false; }
export function AppShell() {
  const session = useSession(); const location = useLocation();
  const [dirty, setDirty] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const mobile = useSyncExternalStore(subscribeMobile, mobileSnapshot);
  const compact = collapsed && !mobile;
  const [menu, setMenu] = useState(false); const [error, setError] = useState('');
  const menuButton = useRef<HTMLButtonElement>(null);
  const main = useRef<HTMLElement>(null);
  useEffect(() => { const h = main.current?.querySelector('h1'); if (h) { h.tabIndex = -1; h.focus(); } }, [location.pathname]);
  function closeMenu() { setMenu(false); menuButton.current?.focus(); }
  return <div className={'app-shell' + (compact ? ' sidebar-collapsed' : '')} onKeyDown={event => { if (event.key === 'Escape' && menu) closeMenu(); }}>
    <a className="skip-link" href="#main">Ke konten utama</a>
    <Sidebar open={menu} compact={compact} onCollapse={() => setCollapsed(value => !value)} onNavigate={() => { if (mobile) closeMenu(); else setMenu(false); }} />
    <div className="workspace"><header className="app-header"><button className="menu-toggle" ref={menuButton} aria-expanded={menu} aria-controls="primary-nav" onClick={() => setMenu(x => !x)}>Menu</button><div className="account"><span>{session.identity?.email}</span><button disabled={session.busy} onClick={() => { if (dirty && !window.confirm('Perubahan belum disimpan. Keluar dari akun?')) return; setError(''); session.logout().catch(e => setError(errorText(e))); }}>Keluar</button></div></header>
    <main id="main" className="content" ref={main}>{error && <p className="error" role="alert">{error}</p>}{session.identity?.capabilities.employees_read ? <><Breadcrumbs /><Outlet context={{ setDirty }} /></> : <><h1>Akses tidak tersedia</h1><p>Akun ini tidak memiliki izin untuk melihat data pegawai.</p><Link to="/login">Periksa akun</Link></>}</main></div>
  </div>;
}
