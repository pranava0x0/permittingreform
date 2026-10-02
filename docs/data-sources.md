# Data sources: what answers a script and what does not

Checked 2026-10-01. A route marked dead should not be retried without a new idea.

## Routes that work

| Source | Route | Notes |
|---|---|---|
| Bill text | `epw.senate.gov` and `energy.senate.gov` PDFs | Plain GET. The page number printed on each page equals the PDF page. |
| Earlier bills | `govinfo.gov/content/pkg/BILLS-<id>/html/BILLS-<id>.htm` | Plain text in a `<pre>`. Used for H.R. 4776 (eh) and S. 4753 (rs). |
| U.S. Code | `govinfo.gov/content/pkg/USCODE-2023-title42/html/...sec4336a.htm` | Used to read NEPA sections 106 to 111 as amended in 2023. Links on the site go to `law.cornell.edu/uscode/text/<title>/<section>`. |
| Federal Register | `federalregister.gov/api/v1/documents/<number>.json` | The HTML pages refuse scripts; the API does not. `govfetch.resolve_api_escape` rewrites the URL. |
| X posts | `publish.twitter.com/oembed?url=<post url>` | Returns the post text and author, no key. |
| Bluesky posts | `public.api.bsky.app/xrpc/app.bsky.feed.getPostThread?uri=at://<handle>/app.bsky.feed.post/<id>` | Returns the post text, no key. |
| POLITICO, POLITICO Pro, E&E News | `https://r.jina.ai/<url>` | Returns the free part of the page: live-update pages and some E&E stories whole, politico.com stories and Pro articles as their first paragraphs. Mark such items as read from a preview. `rss.politico.com/energy.xml` and `congress.xml` list recent headlines. Checked 2026-10-02. |
| Heatmap News | Plain GET | Free, including most Plus pieces. `heatmap.news/sitemap.xml` lists only the last 1,500 URLs. |
| YouTube | `youtube.com/oembed?format=json&url=<video url>` | Title and channel only. Quotes from video cannot be machine-checked. |

## Walls

| Source | What happens | Status |
|---|---|---|
| Reddit | `curl` gets 403; `old.reddit.com` and `.json` redirect to a login wall; the built-in browser, the Chrome extension and web search all refuse the domain. | Dead for automation. Threads can be added by hand to `data/research/media_extra.json`. |
| `congress.gov` | 403 to scripts. | Use govinfo for text. |
| `uscode.house.gov` | Timed out on every request. | Use govinfo or Cornell. |
| `thehill.com`, `nrdc.org`, `washingtontimes.com`, `punchbowl.news`, `bipartisanpolicy.org`, `nmpoliticalreport.com`, `energynow.com` | 403 to scripts; open in a browser. | The link checker lists them as blocked and the site says so beside each link. |
| `politico.com`, `nytimes.com`, `reuters.com`, `wsj.com`, `apnews.com` | Not reachable by the search tool; politico.com gives curl a Cloudflare 403. | AP is cited through PBS and ABC; Politico through Yahoo syndication or the r.jina.ai reader. |
| Wayback Machine for POLITICO | The CDX index lists 2026 politico.com and Pro URLs, but every capture is a 403 or a paywall preview. | Use the index to find URLs, not text. |
| Apple Podcasts | TLS handshake fails from Python 3.9. | `webfetch` falls back to `curl`. |

## Not found

- A video of the full September 30 press conference. Only Whitehouse's own upload of his remarks.
- September 30 statements from Earthjustice, the Sierra Club (quoted in press only), the Data Center Coalition, the building trades, NRECA and APPA.
