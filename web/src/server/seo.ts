const SITE_URL = 'https://superrealty.mahimai.ca';
const SITE_NAME = 'Super Realty';
const DEFAULT_OG_IMAGE = `${SITE_URL}/og-image.png`;
const ORG_ID = `${SITE_URL}/#organization`;
const SITE_ID = `${SITE_URL}/#website`;

export interface RouteMeta {
  title: string;
  description: string;
  ogImage?: string;
}

const ROUTE_META = {
  '/': {
    title: 'Super Realty: an AI receptionist that never misses a lead',
    description:
      'Super Realty answers every call in your name, qualifies the buyer, books the showing, and remembers every caller. Built for solo real estate agents.',
  },
} as const;

function getOrganizationJsonLd(): object {
  return {
    '@type': 'Organization',
    '@id': ORG_ID,
    name: SITE_NAME,
    url: SITE_URL,
    description: 'AI receptionist for solo real estate agents: answers every call, qualifies buyers, books showings.',
    sameAs: [
      'https://www.linkedin.com/in/mahimairaja',
      'https://github.com/mahimairaja',
      'https://x.com/mahimaidev',
    ],
    founder: {
      '@type': 'Person',
      name: 'Mahimai Raja J',
      url: 'https://mahimai.ca',
    },
  };
}

function getWebSiteJsonLd(): object {
  return {
    '@type': 'WebSite',
    '@id': SITE_ID,
    name: SITE_NAME,
    url: SITE_URL,
    inLanguage: 'en',
    publisher: { '@id': ORG_ID },
  };
}

function getServiceJsonLd(): object {
  return {
    '@type': 'ProfessionalService',
    name: SITE_NAME,
    url: SITE_URL,
    description: 'AI receptionist that answers every buyer call, qualifies leads, and books showings for solo real estate agents.',
    provider: {
      '@type': 'Person',
      name: 'Mahimai Raja J',
      url: 'https://mahimai.ca',
    },
    hasOfferCatalog: {
      '@type': 'OfferCatalog',
      name: 'Services',
      itemListElement: [
        {
          '@type': 'Offer',
          itemOffered: {
            '@type': 'Service',
            name: 'AI voice receptionist for real estate',
            description:
              'An AI agent that answers every buyer inquiry in your name, qualifies the lead, books the showing, and remembers every caller.',
          },
        },
      ],
    },
  };
}

const PRODUCT_LD = {
  '@type': 'Product',
  name: 'Super Realty',
  description: 'An always-on AI voice receptionist for solo real estate agents.',
  brand: { '@type': 'Brand', name: 'Super Realty' },
  url: 'https://superrealty.mahimai.ca',
};

const FAQ_LD = {
  '@type': 'FAQPage',
  mainEntity: [
    ['Does it sound like a robot?', 'No. It answers in your synthesized voice and only ever talks about homes you have connected, never a generic script.'],
    ['Is it really mine?', 'Yes. I build it, hand it over, and you own it. No subscription that never ends.'],
    ['What does it cost?', 'You pay for the build, not a monthly trap. Book a call and I will scope it to your business.'],
    ['How long to build?', 'Weeks, not months. It onboards from your website, so most of the setup is already done.'],
    ['Does it work after hours?', 'That is the point. It answers first ring, day or night, weekends included.'],
  ].map(([q, a]) => ({ '@type': 'Question', name: q, acceptedAnswer: { '@type': 'Answer', text: a } })),
};

function buildJsonLd(pathname: string): string {
  const graph: object[] = [getWebSiteJsonLd(), getOrganizationJsonLd()];

  if (pathname === '/') {
    graph.push(getServiceJsonLd(), PRODUCT_LD, FAQ_LD);
  }

  const ld = { '@context': 'https://schema.org', '@graph': graph };
  return JSON.stringify(ld);
}

/** Always returns one absolute canonical URL. Strips query strings. Used by getPageSeo(). */
export function getCanonicalUrl(pathname: string): string {
  const pathOnly = pathname.split('?')[0]!.split('#')[0]!;
  if (pathOnly === '/') return SITE_URL;
  const normalized = pathOnly.replace(/\/+$/, '');
  return `${SITE_URL}${normalized}`;
}

export function isKnownRoute(pathname: string): boolean {
  return (ROUTE_META as Record<string, unknown>)[pathname] != null;
}

export interface PageSeo {
  title: string;
  description: string;
  canonical: string;
  ogImage: string;
  ogImageAlt: string;
  ogType: 'website' | 'article';
  jsonLd: string;
  known: boolean;
}

/**
 * Structured per-route meta consumed natively by Layout.astro. Unknown routes
 * are soft-404: noindex with a root canonical.
 */
export function getPageSeo(pathname: string): PageSeo {
  const known = isKnownRoute(pathname);
  const meta = (ROUTE_META as Record<string, RouteMeta>)[pathname] ?? (ROUTE_META as Record<string, RouteMeta>)['/']!;
  return {
    title: meta.title,
    description: meta.description,
    canonical: known ? getCanonicalUrl(pathname) : SITE_URL,
    ogImage: meta.ogImage ?? DEFAULT_OG_IMAGE,
    ogImageAlt: `${meta.title} cover image`,
    ogType: 'website',
    jsonLd: buildJsonLd(pathname),
    known,
  };
}
