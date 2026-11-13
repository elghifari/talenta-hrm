import { useEffect, useState } from 'react';
import type { ContractSection } from './sections';

export function ContractSectionNav({ sections }: { sections: ContractSection[] }) {
  const [activeId, setActiveId] = useState(sections[0].id);
  const sectionIds = JSON.stringify(sections.map(section => section.id));

  useEffect(() => {
    const ids: string[] = JSON.parse(sectionIds);
    let frame = 0;
    function update() {
      const mobileHeight = document.querySelector<HTMLElement>('.contract-mobile-sections')?.offsetHeight ?? 0;
      const contextHeight = document.querySelector<HTMLElement>('.contract-employee-context')?.offsetHeight ?? 0;
      let current = ids[0];
      for (const id of ids) {
        const target = document.getElementById(id);
        if (target && target.getBoundingClientRect().top <= contextHeight + mobileHeight + 48) current = id;
      }
      setActiveId(current);
      frame = 0;
    }
    function schedule() {
      if (!frame) frame = requestAnimationFrame(update);
    }
    schedule();
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
    };
  }, [sectionIds]);

  function navigate(id: string) {
    const target = document.getElementById(id);
    if (!target) return;
    const mobileHeight = document.querySelector<HTMLElement>('.contract-mobile-sections')?.offsetHeight ?? 0;
    const contextHeight = document.querySelector<HTMLElement>('.contract-employee-context')?.offsetHeight ?? 0;
    const offset = contextHeight + (mobileHeight ? mobileHeight + 16 : 28);
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    document.getElementById(id + '-heading')?.focus({ preventScroll: true });
    window.scrollTo({ top: window.scrollY + target.getBoundingClientRect().top - offset, behavior: reducedMotion ? 'instant' : 'smooth' });
    setActiveId(id);
  }

  const filled = sections.reduce((total, section) => total + section.filled, 0);
  const total = sections.reduce((count, section) => count + section.total, 0);
  return <>
    <div className="contract-mobile-sections">
      <label htmlFor="contract-section-select">Bagian form</label>
      <select id="contract-section-select" value={activeId} onChange={event => navigate(event.target.value)}>
        {sections.map(section => <option key={section.id} value={section.id}>{section.label}{section.errors ? ` (Cek ${section.errors})` : ''}</option>)}
      </select>
    </div>
    <aside className="contract-section-menu" aria-labelledby="contract-section-menu-heading">
      <h2 id="contract-section-menu-heading">Bagian form</h2>
      <p className="contract-fill-count">{filled} dari {total} isian terisi</p>
      <nav aria-label="Bagian form kontrak">
        {sections.map((section, index) => <a key={section.id} href={'#' + section.id} className={'contract-section-link' + (section.errors ? ' has-error' : '')} aria-current={activeId === section.id ? 'location' : undefined} aria-label={`${section.label}, ${section.filled} dari ${section.total} isian terisi${section.errors ? `, ${section.errors} perlu diperiksa` : ''}`} onClick={event => { event.preventDefault(); navigate(section.id); }}>
          <span className="contract-section-index" aria-hidden="true">{index + 1}</span>
          <span>{section.label}</span>
          <span className="contract-section-count" aria-hidden="true">{section.errors ? `Cek ${section.errors}` : `${section.filled}/${section.total}`}</span>
        </a>)}
      </nav>
    </aside>
  </>;
}
