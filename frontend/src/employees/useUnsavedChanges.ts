import { useCallback, type RefObject } from 'react';
import { useBeforeUnload, useBlocker } from 'react-router';
export function useUnsavedChanges(dirty: boolean, allowLeave: RefObject<boolean>) {
  const blocker = useBlocker(({ currentLocation, nextLocation }) => dirty && !allowLeave.current && currentLocation.pathname !== nextLocation.pathname);
  useBeforeUnload(useCallback((event: BeforeUnloadEvent) => {
    if (dirty && !allowLeave.current) { event.preventDefault(); event.returnValue = ''; }
  }, [dirty, allowLeave]));
  return blocker;
}
