import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import { App } from './App';

function identity(write = true, audit = true) {
  vi.stubGlobal('fetch', vi.fn(async (path: string) => Response.json(path.endsWith('/me/')
    ? { id: 1, email: 'hr@example.test', capabilities: { employees_read: true, employees_write: write, audit_read: audit } }
    : [])));
}
afterEach(() => { vi.unstubAllGlobals(); window.history.replaceState({}, '', '/'); });

test('Personnel discloses a second navigation level without the workspace label', async () => {
  identity();
  render(<App initialEntries={['/employees']} />);
  const user = userEvent.setup();
  const nav = await screen.findByRole('navigation', { name: 'Modul' });
  const personnel = within(nav).getByRole('button', { name: 'Personnel' });
  expect(personnel).toHaveAttribute('aria-expanded', 'true');
  expect(within(nav).getByRole('link', { name: 'Ringkasan' })).toHaveAttribute('href', '/personnel');
  expect(within(nav).getByRole('link', { name: 'Data pegawai' })).toHaveAttribute('aria-current', 'page');
  expect(within(nav).getByRole('link', { name: 'Cabang & Divisi' })).toBeVisible();
  expect(within(nav).getByRole('link', { name: 'Log aktivitas' })).toBeVisible();
  expect(screen.queryByText(/ruang kerja/i)).not.toBeInTheDocument();
  await user.click(personnel);
  expect(personnel).toHaveAttribute('aria-expanded', 'false');
  expect(within(nav).queryByRole('link', { name: 'Data pegawai' })).not.toBeInTheDocument();
  await user.keyboard(' ');
  expect(personnel).toHaveAttribute('aria-expanded', 'true');
  expect(within(nav).getByRole('link', { name: 'Data pegawai' })).toBeVisible();
});

test('compact rail opens a keyboard-accessible flyout and restores focus on Escape', async () => {
  identity();
  render(<App initialEntries={['/employees']} />);
  const user = userEvent.setup();
  await user.click(await screen.findByRole('button', { name: 'Ciutkan sidebar' }));
  expect(screen.getByRole('button', { name: 'Perluas sidebar' })).toHaveFocus();
  const trigger = within(screen.getByRole('navigation', { name: 'Modul' })).getByRole('button', { name: 'Personnel' });
  expect(trigger).toHaveAttribute('aria-expanded', 'false');
  expect(screen.queryByRole('link', { name: 'Ringkasan' })).not.toBeInTheDocument();
  await user.click(trigger);
  const flyout = screen.getByRole('navigation', { name: 'Personnel' });
  expect(within(flyout).getByRole('link', { name: 'Ringkasan' })).toHaveAttribute('href', '/personnel');
  await user.keyboard('{Escape}');
  expect(screen.queryByRole('navigation', { name: 'Personnel' })).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
  await user.keyboard('{Enter}');
  await user.click(within(screen.getByRole('navigation', { name: 'Personnel' })).getByRole('link', { name: 'Ringkasan' }));
  expect(await screen.findByRole('heading', { name: 'Personnel' })).toBeInTheDocument();
  expect(screen.queryByRole('navigation', { name: 'Personnel' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Perluas sidebar' })).toBeInTheDocument();
  await user.click(trigger);
  await user.click(within(screen.getByRole('navigation', { name: 'Personnel' })).getByRole('link', { name: 'Ringkasan' }));
  expect(trigger).toHaveFocus();
  await user.click(trigger);
  await user.click(screen.getByRole('main'));
  expect(screen.queryByRole('navigation', { name: 'Personnel' })).not.toBeInTheDocument();
});

test('navigation keeps write and audit destinations out of a read-only account', async () => {
  identity(false, false);
  render(<App initialEntries={['/employees']} />);
  const nav = await screen.findByRole('navigation', { name: 'Modul' });
  expect(within(nav).getByRole('link', { name: 'Data pegawai' })).toBeVisible();
  expect(within(nav).queryByRole('link', { name: 'Cabang & Divisi' })).not.toBeInTheDocument();
  expect(within(nav).queryByRole('link', { name: 'Log aktivitas' })).not.toBeInTheDocument();
});
