# CDG Digital Media — DEAL SIGNAL / The 35% Club

A static, mobile-first Black Friday deal-monitoring website with a **hard, fail-closed 35% discount threshold**, an auditable price-evidence model, and a scheduled discovery/revalidation pipeline. No user account, cookies, analytics, or JavaScript framework required. Copyright © 2026 CDG Digital Media.

## What you get

- `site/index.html` — complete standalone preview with *server-rendered deal cards*, full responsive design, search, sort, retailer and category filters, and client-side saved deals.
- `site/deals.json` — the published, strictly filtered feed. The static site periodically checks this file for new data once deployed on a web server.
- `scripts/deal_logic.py` — exact Decimal price calculations and fail-closed discount/source/freshness validation.
- `scripts/refresh_deals.py` — price evidence refresh from merchant pages; scans six public specialist RSS sources for *research leads only*. The source registry is in `data/sources.json`.
- `data/review_queue.json` — discoveries that still need direct official-retailer price evidence. These **are not published**.
- `.github/workflows/refresh.yml` — checks every ~30 minutes (GitHub's schedule may delay runs); commits the refreshed feed and site.
- `scripts/build_site.py` — regenerates a fully readable HTML page from the verified feed; content remains useful with JavaScript off.
- `tests/test_deals.py` — regression tests, including 34.9% and 34.99% rejection, price mismatch, future and stale proof rejection.

## Bold redesign (Nov 10, 2026)

Inspired by Wedge's Brami identity: full-bleed color fields (cobalt hero and Deal Check, ice Brand Watch, warm cream Sources, sunny closing band), duotone deal-card headers per category (cobalt / sun / cranberry / pine / plum), 1.5px ink linework with hard offset shadows on hover, an oversized Playfair display scale, extended-width Archivo labels, and a rotating "35% Club" sticker seal beside the headline (stops for reduced-motion users). The CSS lives in the "BOLD LAYER" block at the end of the stylesheet, so it's easy to tune or remove.

## Cleanup pass (Nov 10, 2026)

Pill-shaped controls replaced with underline tabs (categories, brand filters, mobile section nav), squared 8px buttons (Saved, Follow, card save) and plain text links (Deal Check examples). Removed the scrolling ticker, dashed borders, hatched shading, snowflake textures, gradient bars and Unicode star/check glyphs; save/follow now use simple SVG icons. Winter palette unchanged.

## Brand watch, sale calendar, deal check (Nov 10, 2026)

- **Brand watch** (`data/brands.json`): 12 brands with where real markdowns tend to show up, the specific trap to watch for, and an editorial "Often / Sometimes / Rarely clears 35%" read. Visitors can **follow** brands (stored in their browser only); followed brands get a "★ Watching" badge on deal cards and a **My brands** filter chip on the board. Each brand shows how many live deals match and links to a filtered board. Matching is by whole-word `match` strings against each deal's brand and title. Edit the JSON to add or change brands; the ratings never affect what gets published.
- **Brand list (33):** Target, Nike, Pottery Barn, Milwaukee, Kohl's, Gap, Crate & Barrel, LG, LOFT, The North Face, Bass Pro Shops, Best Buy, Ann Taylor, Dick's Sporting Goods, Disney/Pixar, Patagonia, Hollister, Coach, Old Navy, Quince, DEWALT, Samsung, Athleta, Banana Republic, Gap Factory, Banana Republic Factory, Sony, Apple, Dyson, KitchenAid, Ninja/Shark, LEGO, Husky. All Gap Inc. lines (Gap incl. GapKids/babyGap/Gap Maternity/GapBody/GapFit/GapStudio, Gap Factory/Outlet, Old Navy, Banana Republic, Banana Republic Factory, Athleta, per Gap Inc.'s FY2025 10-K) have their own chip. Entries with `"scope": "store"` (Target, Kohl's, Best Buy, Dick's, Bass Pro Shops) match on the deal's retailer instead of its brand. The first 12 in file order show by default (followed brands jump to the front); "Show all" reveals the rest. A new `apparel` card visual is available for clothing deals.
- **Sale calendar** (`data/calendar.json`): announced 2026 retailer sale windows on one timeline with a live "today" line, "Running now" and "Coming up next" summaries, and a plain list. Dates come from 9to5Toys' Nov 4, 2026 schedule (linked on the page). Events without an announced end date fade out ("end TBA"). Amazon is listed as not officially announced. Update this file as retailers announce or change dates.
- **Check any deal**: a calculator that runs the same 35% test on any price pair, shows the sale price needed to qualify, and compares against the lowest price the visitor has seen to flag inflated "was" prices.

## Winter theme (Nov 10, 2026)

White page throughout (header, hero, footer). Winter palette: deep navy ink, glacier blue, evergreen for "verified", cranberry for the 35% cut line, frost/ice tints, subtle snowflake texture in the hero, card headers and closing band. Large titles use **Playfair Display** (Google Fonts, Georgia fallback); body and data stay in Archivo / JetBrains Mono. Footer is centered.

## What changed in v2 (Nov 10, 2026)

- **Redesigned front end** (`site/template.html`): Archivo + JetBrains Mono, category line-icons instead of text stamps, discount numeral as the card hero, a "you pay X% of reference" bar with the 35% line marked, and a **Show the math** receipt on every card (exact calculation, floor rule, evidence text, source link).
- **Signal panel** in the hero: live countdown to Black Friday / Cyber Monday and a gauge plotting every live listing against the 35% cut line.
- **Filters**: minimum-discount toggle (35/40/45/50%+), category chips with counts, store, sort (incl. freshest evidence), saved-only. Sticky filter bar on desktop.
- **Evidence freshness meter** per card (hours left before the 24h evidence window closes).
- **Recently expired archive**: offers that were valid at capture but have aged out stay visible for 7 days below the board, clearly labeled *not currently verified*, with no live-deal styling. New `expired_record()` in `deal_logic.py`; `refresh_deals.py` writes `recently_expired` to `deals.json`.
- **Mobile**: section nav stays reachable (scrollable pill row), filters unstick so they don't eat the screen.
- **Source network** split into *Lead sources* (deal sites) vs *Proof sources* (retailers).
- FAQ section, toast confirmations, no-JS snapshot still fully server-rendered (`build_site.py` mirrors the client renderer and reads the icons from the template).
- Nav still uses buttons, not `#` anchors, so in-app previews don't intercept it.
- 4 new tests (16 total) covering the archive rules.

## Read this first: accuracy and coverage

**The site does not and cannot claim to index “all” websites.** Live shopping data requires retailer APIs, access agreements, and continuously maintained merchant-specific extractors. The supplied version includes **nine real merchant-priced offers researched on November 10, 2026**, and source links. Seed prices are deliberately time-limited; a failed or blocked refresh does **not** renew them.

Deal blog posts (DealNews, Slickdeals, BFAds, ad scans, etc.) are discovery signals, **not** evidence that a specific retailer currently offers the deal. “Up to 60%,” percentage-only announcements, coupon stacking, BOGO, mismatched product variants, old promo ads, price ranges, missing reference prices, and claims without price pairs do not become public listings.

When a merchant page cannot be read or its price pair cannot be confirmed, the existing evidence expires within 24 hours. The board may then be empty, which is preferable to publishing stale or unproven claims. Automatic revalidation does not guess replacement prices.

The current threshold measures **discount relative to the retailer's published reference (“was”/regular) price**, not the item's lowest price in the previous 30–90 days. A genuine historical-price audit requires separate price history and/or trusted comparison datasets. A verified pair is *not* proof that the reference price was ever widely charged.

**Source licensing:** The feed parser is used for internal discovery queues. Do not copy/reprint full feed content commercially without checking each publisher's terms. In particular, DealNews's RSS policy requires attribution and imposes conditions on displaying its feed. The public board publishes independently summarized product and merchant pricing evidence with source links; it does **not** republish RSS snippets/images.

## Preview navigation and in-app browser warnings

The **Find Real Deals**, **Deal board**, **Our standard**, **Source network**, and **Saved deals** controls scroll within the current page using buttons rather than `href="#..."` anchors. This avoids link-interception warnings in some ChatGPT/Claude/other in-app file previews. Clicking **VIEW DEAL** or any source/merchant URL *does* leave the preview and should still request permission from the host app. The published website behaves normally in Safari, Chrome, and other standalone browsers.

## Open now

Open `site/index.html` in a browser. It contains the initial nine listings and works offline; JavaScript powers the filters. Each listing has a direct merchant/product/category link and a retailer-source link. The display itself imposes a second 35% check and automatically removes expired items in JavaScript-enabled browsers.

## Refresh locally

Requires Python 3.10+. No third-party Python packages.

```bash
python scripts/refresh_deals.py
python scripts/build_site.py
python -m unittest discover -s tests -v
python -m http.server --directory site 8000
```

Open `http://localhost:8000` in a browser. For a reproducible snapshot without external requests:

```bash
python scripts/refresh_deals.py --offline --at 2026-11-10T09:15:00Z
python scripts/build_site.py
```

`--at` is for tests and historical offline reconstruction, *not* for a live production schedule. Normal refresh uses the actual current UTC timestamp. The auto-expiry logic is unchanged.

## Deploy to Cloudflare Pages (suggested)

1. Create a **private or public GitHub repository** with the contents of this project, including `.github/workflows/refresh.yml`.
2. In Cloudflare Pages, connect the GitHub repository, use **no framework preset**, leave the build command empty, and enter `site` as the output directory.
3. Enable GitHub Actions with `Read and write permissions` under repository **Settings → Actions → General → Workflow permissions**. Run the **Refresh 35%+ deal intelligence** workflow once using **Actions → Run workflow**.
4. Cloudflare Pages deploys commits containing updated `site/` files. GitHub's schedule triggers approximately every 30 minutes; exact execution time isn't guaranteed.
5. Point a CDG subdomain such as `deals.cdgdigitalmedia.com` to the Cloudflare Pages project when DNS settings are available. This is a **suggested address**, not a created site.

Cloudflare's free tier and GitHub Actions have rate and usage limits; review them when adding feeds or retailers.

## How to add a verified offer

Edit `data/seed_offers.json`. Each entry needs a stable `id`, real `title`, `store`, `category`, `sale_price`, `reference_price`, official merchant `url` and `source_url`, `source_name`, exact time `observed_at`, `valid_until` (≤24h after observation), `evidence`, `source_type: "retailer"`, and a **specific** `verification_keyword` (unique model or product phrase). A new seed should be based on a current, individually checked merchant page. Run the refresh and build commands.

Only products that actually compute to 35%+ are published:

```
percent_off = (reference_price - sale_price) / reference_price * 100
```

All math is computed, never accepted from an ad's percentage label. The display **floors** percentages so it never inflates a 49.87% saving to 50%. Prices shown exclude shipping, taxes, membership conditions, and checkout-specific coupon requirements. Conditional offers should not be seeded unless final checkout eligibility has been independently established and clearly explained.

## Scale-up architecture

For continuous, **broad** coverage rather than a small curated initial dataset, add approved retailer product feeds/APIs (e.g., retailer affiliate product feeds or licensed commerce data), with individual item IDs, direct URLs, current prices, reference prices, stock and timestamps. Merchant adapters must output the same evidence schema and pass `validated_offer()`. Use a deduplication key based on retailer + product/variant ID; do not merge unlike capacities, sizes or bundles. Retain pricing history to detect misleading reference prices. Respect robots.txt, publisher terms and API rates. This is the major next engineering step before promising extensive coverage.

## Test results

16 automated tests passed on November 10, 2026. v2 was also checked in headless Chromium at 1440px and 390px (no horizontal scroll, no console errors; filters, save, math receipts, nav, and the empty/expired state exercised). The downloadable site should be tested on its deployment origin before public launch.

**Brand/contact:** [CDG Digital Media](https://cdgdigitalmedia.com/). The official CDG logo (gold, footer) and a one-color navy CDG mark (header) live in `site/assets/` and are embedded into `index.html` at build time.
