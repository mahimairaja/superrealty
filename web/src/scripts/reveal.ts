// Scroll-reveal, ported from the useScrollReveal hook to a single global
// observer. Re-runs after every client navigation via astro:page-load. The CSS
// convention ([data-reveal] -> [data-revealed]) and the prefers-reduced-motion
// guard live in global.css.
function setupReveal() {
  if (typeof window === 'undefined' || !('IntersectionObserver' in window)) return;
  const els = document.querySelectorAll<HTMLElement>('[data-reveal]:not([data-revealed])');
  if (els.length === 0) return;
  const observer = new IntersectionObserver(
    (entries, obs) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.setAttribute('data-revealed', 'true');
          obs.unobserve(entry.target);
        }
      }
    },
    { threshold: 0.15, rootMargin: '0px 0px -40px 0px' },
  );
  els.forEach((el) => observer.observe(el));
}

document.addEventListener('astro:page-load', setupReveal);
