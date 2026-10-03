# Search discovery

Indexable public pages: `/`, `/features`, and `/updates`. Each has a unique title
and description, an absolute canonical without query parameters, and Open Graph /
Twitter sharing metadata. The homepage provides factual WebSite and WebApplication
JSON-LD without invented ratings, reviews, prices, or rich-result claims.

`/sitemap.xml` lists only those canonical URLs. `/robots.txt` advertises it and
permits crawling so search engines can read the `X-Robots-Tag: noindex, nofollow`
headers on account pages, private workspaces, exports, APIs, errors, and other
non-discovery routes. Authentication still controls access; robots rules are not
an access-control mechanism. Signed-in public responses are also noindex.

`PUBLIC_SITE_URL` defaults to `https://studentsuccess.onrender.com`. Set this to the
preferred HTTPS origin when adopting a custom domain. Canonicals never derive from
untrusted Host headers. Keep the origin consistent and redirect retired domains
at the hosting layer when a domain migration actually occurs.

## Owner-side follow-up

1. Add the live URL-prefix property in Google Search Console.
2. For HTML-tag verification, put Google's token (not the entire tag) in the
   `GOOGLE_SITE_VERIFICATION` environment variable and redeploy, or use Google's
   domain-verification method for a custom domain you control.
3. Submit `https://studentsuccess.onrender.com/sitemap.xml`, inspect the public
   URLs, and monitor indexing, search queries, and Core Web Vitals. No verification
   token or Search Console access was available during this implementation.
4. Improve content from actual student questions and measure usage before adding
   more pages. Avoid duplicate pages, keyword stuffing, or fabricated testimonials.

Search engines decide whether and when pages appear; these changes do not promise
rankings. No new analytics/tracking was installed. Cold-start hosting latency can
still affect page experience and should be evaluated with real measurements.

## Launch-readiness spot checks (2026-10-03)

- The live HTTP homepage redirected to the same HTTPS URL (301); HTTPS returned
  200. The live sitemap listed only the homepage, Features, and Updates, and
  `robots.txt` advertised that sitemap.
- The local Playwright discovery check passed at 320, 390, and 1440 pixels for
  those three public pages, including canonical/description/H1 checks, JavaScript
  error monitoring, and the Features FAQ with JavaScript disabled. This does not
  cover every private workspace screen.
- One warm live request measured 0.161 s to first byte for the homepage and
  0.189 s for Features. These are single-request observations, not Lighthouse,
  cold-start, or Core Web Vitals measurements.
- The source social-preview PNG was losslessly recompressed from 1,094,387 to
  981,556 bytes (10.3% smaller, pixel-identical). The live image remains at its
  deployed size until this source change is released.

References: [Google robots directives](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag),
[sitemap guidance](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview),
and [supported metadata](https://developers.google.com/search/docs/crawling-indexing/special-tags).
