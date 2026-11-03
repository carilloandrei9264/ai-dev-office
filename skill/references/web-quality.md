# Web quality bar

Use for any slice people look at, and for ship mode. Mark each item pass, fail or not run with evidence; skip items that do not apply and say why.

## Content and structure
- Every page has one clear purpose, a unique title and a meta description. Headings have one `h1` and no skipped levels.
- Real content, not lorem ipsum, before a page counts as done. Copy matches what the product does.

## Look and feel
- One visual direction for the whole project. Reuse the accepted one for new pages. Avoid the generic template look (centered headline, three icon cards, soft gradient) unless the brief asks for it.
- Type scale, spacing and color come from a small set of tokens, not one-off values.

## Responsive
- Phone, tablet and desktop widths rendered for real. No horizontal scrolling, tap targets large enough, text readable without zoom. Viewport emulation is not device testing.

## Accessibility
- Contrast measured, not eyeballed: `python <skill>/scripts/contrast.py "<fg>" "<bg>"` (4.5:1 for normal text).
- Everything reachable and usable by keyboard with a visible focus. Labels on inputs, `alt` on meaningful images, buttons are buttons and links are links.
- Motion respects `prefers-reduced-motion`.

## States and forms
- Empty, loading, error and long-content states exist for every list and form. Forms validate on the server (client checks are only a convenience), show clear errors, and survive a double submit.
- A custom 404 and a friendly error page. No stack traces shown to visitors.

## Performance
- Images sized and compressed with width and height set, lazy loaded below the fold. No render-blocking scripts you do not need. Fonts limited and swapped.
- Measure (Lighthouse or the host's tools) before optimizing. Report the numbers, or report not measured.

## Search and sharing (public sites)
- Canonical URL, share image, favicon, `sitemap.xml`, `robots.txt`; structured data where it fits.

## Security and privacy
- HTTPS, secrets only on the server, input validated on the server, authorization on every protected route, security headers set. A privacy note when third parties (fonts, analytics, embeds) load.

## Definition of done for a UI slice
Acceptance sentence satisfied in a real browser, states and errors handled, keyboard and contrast checked, phone layout checked, project checks passing, evidence recorded.
