import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { ContractSectionNav } from './ContractSectionNav';
import { contractFieldGroups, type ContractSection } from './sections';
import type { Field } from './types';

const sections: ContractSection[] = [
  { id: 'contract-template', label: 'Template', filled: 0, total: 2, errors: 0 },
  { id: 'contract-section-no_urut', label: 'Surat', filled: 1, total: 3, errors: 0 },
];

function renderNavigation() {
  render(<><ContractSectionNav sections={sections} />{sections.map(section => <section id={section.id} key={section.id}><h2 id={section.id + '-heading'} tabIndex={-1}>{section.label}</h2></section>)}</>);
  const target = document.getElementById('contract-section-no_urut')!;
  vi.spyOn(target, 'getBoundingClientRect').mockReturnValue({ top: 500 } as DOMRect);
  return { target, scroll: vi.spyOn(window, 'scrollTo').mockImplementation(() => {}) };
}

afterEach(() => vi.unstubAllGlobals());

test('section links scroll smoothly without navigating away and focus the destination', () => {
  const { scroll } = renderNavigation();
  fireEvent.click(screen.getByRole('link', { name: /^Surat,/ }));
  expect(scroll).toHaveBeenLastCalledWith({ top: 472, behavior: 'smooth' });
  expect(document.getElementById('contract-section-no_urut-heading')).toHaveFocus();
  expect(screen.getByText('1 dari 5 isian terisi')).toBeInTheDocument();
});

test('mobile section selection respects reduced motion', () => {
  vi.stubGlobal('matchMedia', () => ({ matches: true }));
  const { scroll } = renderNavigation();
  fireEvent.change(screen.getByRole('combobox', { name: 'Bagian form' }), { target: { value: 'contract-section-no_urut' } });
  expect(scroll).toHaveBeenLastCalledWith({ top: 472, behavior: 'instant' });
});

test('the current section follows ordinary page scrolling', async () => {
  const { target } = renderNavigation();
  vi.spyOn(target, 'getBoundingClientRect').mockReturnValue({ top: 20 } as DOMRect);
  fireEvent.scroll(window);
  await waitFor(() => expect(screen.getByRole('link', { name: /^Surat,/ })).toHaveAttribute('aria-current', 'location'));
  expect(screen.getByRole('combobox', { name: 'Bagian form' })).toHaveValue('contract-section-no_urut');
});

test('field sections retain source order and stable field-based destinations', () => {
  const field = (key: string, group: string): Field => ({ key, group, label: key, kind: 'text', choices: [], max_length: 1000, required_for_generation: true });
  const groups = contractFieldGroups([field('no_urut', 'Surat'), field('nama', 'Identitas'), field('tgl_surat', 'Surat')]);
  expect(groups.map(group => [group.id, group.fields.map(entry => entry.key)])).toEqual([
    ['contract-section-no_urut', ['no_urut', 'tgl_surat']],
    ['contract-section-nama', ['nama']],
  ]);
});
