import { useEffect, useState } from 'react';

const QUERY = '(prefers-reduced-motion: reduce)';

// Tracks the user's prefers-reduced-motion setting so JS-driven animations
// (looping sequences, timers) can be skipped, mirroring the CSS guards.
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(
    () => typeof window !== 'undefined' && window.matchMedia(QUERY).matches,
  );

  useEffect(() => {
    const query = window.matchMedia(QUERY);
    const handler = (event: MediaQueryListEvent) => setReduced(event.matches);
    query.addEventListener('change', handler);
    return () => query.removeEventListener('change', handler);
  }, []);

  return reduced;
}
