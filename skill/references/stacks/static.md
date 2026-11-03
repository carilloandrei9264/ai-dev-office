---
id: static
name: Static site (HTML, CSS, JavaScript)
---

For brochure sites, portfolios and landing pages with no accounts and no server logic.

## Commands
- Run: python -m http.server 8000
- Test: none; check every page in a real browser (see references/web-quality.md)
- Lint / types: optional (html-validate or similar)
- Build: none

## Start
- Semantic HTML, one stylesheet, as little JavaScript as the page needs, no framework unless the plan calls for one. Mobile first. Include `<meta name="viewport" content="width=device-width, initial-scale=1">`.
- Forms need somewhere to send data. A static site has no backend: use a third-party form service or a small server function, and say which. Do not invent a backend.

## Conventions
- One `h1` per page, heading order without gaps, descriptive link text, `alt` on every meaningful image, explicit width and height on images.
- Self-host fonts and images when possible; every third-party request is a privacy and speed cost to mention.
- Keep colors and spacing as CSS variables so the design stays consistent.

## Security
- Never put a secret or API key in client code; anything in the browser is public.
- Link out with `rel="noopener"` where needed; serve over HTTPS; set security headers at the host.

## Testing
- Click every link and menu on phone and desktop widths in a real browser, tab through with the keyboard, measure contrast with `scripts/contrast.py`, and measure speed instead of guessing. If a browser tool is unavailable, report that check as not run.

## Release
- Upload to a static host, set a custom 404 page, add `sitemap.xml` and `robots.txt` for public sites, then check the live URL.
