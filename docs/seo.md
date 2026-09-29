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

References: [Google robots directives](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag),
[sitemap guidance](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview),
and [supported metadata](https://developers.google.com/search/docs/crawling-indexing/special-tags).
