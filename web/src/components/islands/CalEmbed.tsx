import React, { useEffect } from 'react';
import Cal, { getCalApi } from '@calcom/embed-react';

const CAL_LINK =
  (import.meta.env.PUBLIC_CAL_LINK as string | undefined) || 'mahimairaja/discovery';

// Clean light-theme tokens mapped into Cal.com's CSS variables.
// Same palette for light + dark since the site has no dark mode.
const CAL_VARS: Record<string, string> = {
  'cal-bg': '#ffffff',
  'cal-bg-emphasis': '#ffffff',
  'cal-bg-subtle': '#ffffff',
  'cal-bg-muted': '#f9fafb',
  'cal-bg-inverted': '#0a0a0a',
  'cal-bg-info': '#ffffff',
  'cal-bg-success': '#ffffff',
  'cal-bg-attention': '#ffffff',
  'cal-bg-error': '#ffffff',

  'cal-border': '#e5e7eb',
  'cal-border-emphasis': '#d1d5db',
  'cal-border-subtle': '#f3f4f6',
  'cal-border-booker': '#e5e7eb',
  'cal-border-error': '#dc2626',

  'cal-text': '#111827',
  'cal-text-emphasis': '#0a0a0a',
  'cal-text-subtle': '#6b7280',
  'cal-text-muted': '#9ca3af',
  'cal-text-inverted': '#ffffff',
  'cal-text-error': '#dc2626',

  'cal-brand': '#2563eb',
  'cal-brand-emphasis': '#1d4ed8',
  'cal-brand-text': '#ffffff',
};

const CAL_THEME_VARS = {
  light: CAL_VARS,
  dark: CAL_VARS,
};

const CalEmbed: React.FC = () => {
  useEffect(() => {
    (async () => {
      const cal = await getCalApi({ namespace: 'discovery' });
      cal('ui', {
        theme: 'light',
        hideEventTypeDetails: false,
        layout: 'month_view',
        cssVarsPerTheme: CAL_THEME_VARS,
      });
    })();
  }, []);

  if (!CAL_LINK) {
    return (
      <div className="rounded-xl border border-gray-200 bg-gray-50 p-12 text-center">
        <p className="text-sm text-gray-600">
          Booking is being set up. In the meantime, reach us at{' '}
          <a href="mailto:contact@mahimai.ca" className="text-ink font-semibold underline">
            contact@mahimai.ca
          </a>
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-[640px] overflow-hidden rounded-xl">
      <Cal
        namespace="discovery"
        calLink={CAL_LINK}
        config={{ layout: 'month_view', theme: 'light' }}
        style={{ width: '100%', height: '100%', overflow: 'auto', minHeight: '640px' }}
      />
    </div>
  );
};

export default CalEmbed;
