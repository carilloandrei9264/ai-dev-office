---
id: nextjs
name: Next.js (React)
---

Notes from general knowledge, no versions pinned. Next.js changes fast, especially caching and data-fetching behavior: read the docs for the version in `package.json` before relying on a detail.

## Commands
- Run: npm run dev
- Test: npm test
- Lint / types: npm run lint
- Build: npm run build

## Start
- `npx create-next-app@latest <name>`; answer the prompts (TypeScript, ESLint, Tailwind, App Router) according to the plan.
- A fresh app has no test runner. Make setting one up the first slice: a unit runner (Vitest or Jest) and Playwright for the critical flow, and add a `test` script.

## Conventions
- App Router: components are server components by default. Add `"use client"` only where interactivity needs it, as low in the tree as possible.
- Fetch data on the server. Use route handlers for APIs and server actions for mutations.
- Use `next/image` for images and the metadata API for titles, descriptions and share images.
- `npm run build` must pass before a slice counts as done; it catches type and lint problems that dev mode hides.

## Security
- Treat every server action and route handler as a public endpoint: authenticate, authorize and validate input inside it.
- Variables prefixed `NEXT_PUBLIC_` are sent to the browser. Never put a secret in one, and never import server-only code into a client component.
- Keep secrets in server environment variables. Set security headers in `next.config` or at the host.

## Testing
- Unit tests for pure logic and server functions; component tests where behavior is non-trivial; Playwright for sign-in, the main flow and one failure path.
- Run the production build and start it (`npm run build && npm start`) for the browser check, not only dev mode.

## Release
- Confirm the host's supported Next.js features (server actions, image optimization, edge). Set environment variables on the host, run `npm run build`, check the deployed pages, not only the build log.
