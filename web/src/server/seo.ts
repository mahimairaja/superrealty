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
  url: SITE_URL,
  offers: { '@type': 'Offer', url: `${SITE_URL}/#book` },
};

const FAQ_LD = {
  '@type': 'FAQPage',
  mainEntity: [
    ['Is it really free?', 'Yes. Super Realty is open source under the MIT license. Clone it, run it, and own it. There is no company to pay and no subscription.'],
    ['What does it cost to run?', 'Only your own API usage: an OpenAI key, a Deepgram key, and a phone number if you want inbound calls. You pay those providers directly, nothing to us.'],
    ['Do I need to be technical?', 'Some comfort with Docker helps: it is one command, make up. If you would rather not touch a terminal, reach out and I can set it up for you.'],
    ["Is my data mine?", "Completely. It runs on your own infrastructure with your own keys. Your buyers and calls never touch anyone else's servers."],
    ['Does it sound like a robot?', 'No. It answers in a natural voice, in your name, and only ever describes homes you have connected. Never a generic script.'],
    ['Does it work after hours?', 'That is the whole point. It answers first ring, day or night, weekends included, when most calls actually come in.'],
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
