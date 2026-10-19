import { useEffect, useRef, type ReactNode } from 'react';
export function PageTitle({ children }: { children: ReactNode }) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus({ preventScroll: true }); }, []);
  return <h1 ref={heading} tabIndex={-1}>{children}</h1>;
}
