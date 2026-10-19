import { useState } from 'react';
import { RouterProvider } from 'react-router';
import { makeRouter } from './router';
import '../styles.css';
import { SessionProvider } from '../auth/SessionProvider';
export function App({ initialEntries }: { initialEntries?: string[] }) {
  const [router] = useState(() => makeRouter(initialEntries));
  return <SessionProvider><RouterProvider router={router} /></SessionProvider>;
}
