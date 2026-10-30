import { Link, useLocation, useMatches } from 'react-router';

type Crumb = { label: string; to?: string };
export function Breadcrumbs() {
  const { pathname } = useLocation();
  const matches = useMatches();
  if ((matches.at(-1)?.handle as { breadcrumb?: boolean } | undefined)?.breadcrumb === false) return null;
  const crumbs: Crumb[] = [{ label: 'Personnel', ...(pathname !== '/personnel' ? { to: '/personnel' } : {}) }];
  if (pathname === '/personnel/activity') crumbs.push({ label: 'Log aktivitas' });
  else if (pathname === '/employees/groups') crumbs.push({ label: 'Cabang & Divisi' });
  else if (pathname !== '/personnel') {
    crumbs.push({ label: 'Data pegawai', ...(pathname !== '/employees' ? { to: '/employees' } : {}) });
    if (pathname === '/employees/new') crumbs.push({ label: 'Tambah pegawai' });
    else if (pathname === '/employees/import') crumbs.push({ label: 'Batch Upload' });
    else if (pathname.startsWith('/employees/imports/')) crumbs.push({ label: 'Batch Upload', to: '/employees/import' }, { label: 'Pratinjau CSV' });
    else if (/^\/employees\/[^/]+\/edit$/.test(pathname)) crumbs.push({ label: 'Detail pegawai', to: pathname.replace(/\/edit$/, '') }, { label: 'Ubah data pegawai' });
    else if (/^\/employees\/[^/]+$/.test(pathname)) crumbs.push({ label: 'Detail pegawai' });
    else if (pathname !== '/employees') crumbs.push({ label: 'Halaman tidak ditemukan' });
  }
  return <nav className="breadcrumbs" aria-label="Breadcrumb"><ol>{crumbs.map((crumb, index) => <li key={index}>{crumb.to ? <Link to={crumb.to}>{crumb.label}</Link> : <span aria-current={index === crumbs.length - 1 ? 'page' : undefined}>{crumb.label}</span>}</li>)}</ol></nav>;
}
