---
id: node
name: Node.js (Express-style server)
---

Notes from general knowledge, no versions pinned. Use the current LTS Node (check nodejs.org) and read the docs of the framework version in `package.json`.

## Commands
- Run: npm run dev
- Test: npm test
- Lint / types: npm run lint
- Build: npm run build

## Start
- `npm init`, install the framework, and add scripts to `package.json`: `dev` (for example `node --watch src/server.js`), `start`, `test`, `lint`, and `build` only if you compile TypeScript. Commit the lockfile.
- Pick one module system (ESM or CommonJS) and keep it. Choose a database layer (Prisma, Drizzle, Knex or a plain driver) and its migration tool before writing models.
- Layout: `src/app.js` exports the app without listening, `src/server.js` starts it, then `routes/`, `services/`, `db/`, `middleware/`. This lets tests call the app directly.

## Conventions
- Validate all input at the edge with a schema library (zod, joi or similar). Never trust `req.body`, `req.query` or `req.params`.
- Read and validate environment variables once at startup and fail fast; keep `.env` out of git.
- One central error-handling middleware. Check whether your framework version handles rejected promises in async handlers; if not, wrap them.
- Parameterized queries or an ORM only. Never build SQL from strings.
- Set a request body size limit. Shut down gracefully (close the server and the database pool).

## Security
- `helmet` for headers, an explicit CORS allowlist (never `*` with credentials), rate limiting on login and public endpoints.
- Hash passwords with argon2 or bcrypt. Session cookies `httpOnly`, `secure`, `sameSite`. For JWTs: short expiry, fixed algorithm, no secrets in the payload.
- Check authorization on every route that reads or changes a record, not only authentication.
- `npm audit` before release; `npm ci` in CI; do not run containers as root.

## Testing
- Use `node --test` (built in) or the project's runner (Vitest, Jest) with `supertest` against the exported app. Use a separate test database and reset it between tests. Stub outbound HTTP.
- Cover denied (401, 403), invalid (400 or 422), not found, and success paths.

## Release
- `npm ci --omit=dev`, `NODE_ENV=production`, a process manager or container, health check endpoint, structured logs, environment variables set on the host.
