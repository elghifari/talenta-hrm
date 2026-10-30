import { useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link, useLocation } from 'react-router';
import { useSession } from '../auth/SessionProvider';
import './sidebar.css';

type Props = { open: boolean; compact: boolean; onCollapse: () => void; onNavigate: () => void };
function Chevron({ direction }: { direction: 'left' | 'right' | 'down' | 'up' }) {
  return <svg className={'sidebar-icon chevron-' + direction} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true" focusable="false"><path d="m9 5 7 7-7 7" /></svg>;
}
function PersonnelIcon() {
  return <svg className="sidebar-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true" focusable="false"><circle cx="9" cy="7" r="3" /><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 4a3 3 0 0 1 0 6m2 4a5 5 0 0 1 3 4v3" /></svg>;
}

export function Sidebar({ open, compact, onCollapse, onNavigate }: Props) {
  const { identity } = useSession();
  const { pathname } = useLocation();
  const [expanded, setExpanded] = useState(true);
  const [flyout, setFlyout] = useState({ path: pathname, open: false });
  const trigger = useRef<HTMLButtonElement>(null);
  const popup = useRef<HTMLElement>(null);
  if (flyout.path !== pathname) setFlyout({ path: pathname, open: false });
  const showingFlyout = compact && flyout.path === pathname && flyout.open;
  const links = [
    { to: '/personnel', label: 'Ringkasan', active: pathname === '/personnel' },
    { to: '/employees', label: 'Data pegawai', active: pathname.startsWith('/employees') && pathname !== '/employees/groups' },
    ...(identity?.capabilities.employees_write ? [{ to: '/employees/groups', label: 'Cabang & Divisi', active: pathname === '/employees/groups' }] : []),
    ...(identity?.capabilities.audit_read ? [{ to: '/personnel/activity', label: 'Log aktivitas', active: pathname === '/personnel/activity' }] : []),
  ];
  useLayoutEffect(() => {
    if (!showingFlyout) return;
    const place = () => {
      const anchor = trigger.current?.getBoundingClientRect();
      const menu = popup.current;
      if (!anchor || !menu) return;
      menu.style.left = Math.max(8, Math.min(anchor.right + 12, innerWidth - menu.offsetWidth - 8)) + 'px';
      menu.style.top = Math.max(8, Math.min(anchor.top, innerHeight - menu.offsetHeight - 8)) + 'px';
    };
    const close = () => setFlyout({ path: pathname, open: false });
    const outside = (event: PointerEvent) => {
      if (!popup.current?.contains(event.target as Node) && !trigger.current?.contains(event.target as Node)) close();
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { close(); trigger.current?.focus(); }
    };
    const resize = () => { if (window.matchMedia?.('(max-width: 680px)').matches) close(); else place(); };
    place();
    popup.current?.querySelector<HTMLAnchorElement>('a')?.focus({ preventScroll: true });
    document.addEventListener('pointerdown', outside);
    document.addEventListener('keydown', escape);
    window.addEventListener('resize', resize);
    window.addEventListener('scroll', place, true);
    return () => {
      document.removeEventListener('pointerdown', outside);
      document.removeEventListener('keydown', escape);
      window.removeEventListener('resize', resize);
      window.removeEventListener('scroll', place, true);
    };
  }, [showingFlyout, pathname]);
  function navigate() { setFlyout({ path: pathname, open: false }); onNavigate(); }
  function items() {
    return links.map(link => <li key={link.to}><Link to={link.to} className={link.active ? 'active' : undefined} aria-current={link.active ? 'page' : undefined} onClick={() => { navigate(); if (compact && link.active) trigger.current?.focus(); }}>{link.label}</Link></li>);
  }
  const selected = links.some(link => link.active);
  return <>
    <aside className={'sidebar' + (open ? ' open' : '') + (compact ? ' is-compact' : '')} id="primary-nav">
      <div className="sidebar-heading">
        <div className="brand">{compact ? <abbr title="Talenta HRIS">TH</abbr> : <>Talenta HRIS<span>Administrasi kepegawaian</span></>}</div>
        <button className="sidebar-collapse" type="button" aria-label={compact ? 'Perluas sidebar' : 'Ciutkan sidebar'} title={compact ? 'Perluas sidebar' : 'Ciutkan sidebar'} onClick={() => { setFlyout({ path: pathname, open: false }); onCollapse(); }}><Chevron direction={compact ? 'right' : 'left'} /></button>
      </div>
      <nav aria-label="Modul">
        {identity?.capabilities.employees_read && <>
          <button ref={trigger} type="button" className={'sidebar-group' + (selected ? ' is-active' : '')} aria-label="Personnel" title={compact ? 'Personnel' : undefined} aria-expanded={compact ? showingFlyout : expanded} aria-controls={compact ? (showingFlyout ? 'personnel-flyout' : undefined) : 'personnel-navigation'} onClick={() => compact ? setFlyout({ path: pathname, open: !showingFlyout }) : setExpanded(value => !value)}>
            <PersonnelIcon /><span className="sidebar-group-label">Personnel</span>{!compact && <Chevron direction={expanded ? 'up' : 'down'} />}
          </button>
          {!compact && <ul className="sidebar-links" id="personnel-navigation" hidden={!expanded}>{items()}</ul>}
        </>}
      </nav>
    </aside>
    {showingFlyout && createPortal(<nav className="sidebar-flyout" id="personnel-flyout" aria-label="Personnel" ref={popup} onKeyDown={event => {
      if (event.key !== 'Tab') return;
      const anchors = popup.current?.querySelectorAll('a');
      if ((event.shiftKey && event.target === anchors?.[0]) || (!event.shiftKey && event.target === anchors?.[anchors.length - 1])) {
        if (event.shiftKey) event.preventDefault();
        setFlyout({ path: pathname, open: false }); trigger.current?.focus();
      }
    }}><p className="sidebar-flyout-title">Personnel</p><ul className="sidebar-links">{items()}</ul></nav>, document.body)}
  </>;
}
