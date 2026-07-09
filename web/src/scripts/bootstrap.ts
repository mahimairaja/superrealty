// Init-once client bootstrap. Runs a single time per full page load (Astro
// module scripts are not re-executed on client-side navigations), which is
// exactly what these one-shot registrations want.

// PostHog: loaded off the critical path (dynamic import on idle). Session
// recording stays disabled for this marketing site; exception autocapture on.
// Absence-tolerant: a missing key must never break the page.
const posthogKey = import.meta.env.PUBLIC_POSTHOG_KEY as string | undefined;
const posthogHost =
  (import.meta.env.PUBLIC_POSTHOG_HOST as string | undefined) || 'https://us.i.posthog.com';

if (typeof window !== 'undefined' && posthogKey) {
  const initPosthog = () =>
    import('posthog-js').then(({ default: posthog }) => {
      posthog.init(posthogKey, {
        api_host: posthogHost,
        defaults: '2026-01-30',
        person_profiles: 'identified_only',
        disable_session_recording: true,
        capture_exceptions: true,
      });
    });
  if (typeof window.requestIdleCallback === 'function') {
    window.requestIdleCallback(() => initPosthog());
  } else {
    window.setTimeout(initPosthog, 1);
  }
}
