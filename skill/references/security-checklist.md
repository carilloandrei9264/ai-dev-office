# Security checklist

Baseline: OWASP Top 10:2025 (the edition published after the 2021 list). OWASP revises this list every few years, so check owasp.org/Top10 for a newer edition and name the edition you used.

## Baseline
- A01 Broken Access Control: enforce permissions on the server for every request, deny by default, and check that the user owns each record they touch.
- A02 Security Misconfiguration: debug off in production, security headers set, no default credentials, least-privilege settings, separate environments.
- A03 Software Supply Chain Failures: pin and lock dependencies, audit them regularly, install only what you need, and protect the build pipeline.
- A04 Cryptographic Failures: HTTPS everywhere, hash passwords with argon2 or bcrypt, keep secrets out of code, encrypt sensitive data at rest.
- A05 Injection: parameterized queries or an ORM, validate all input, encode all output.
- A06 Insecure Design: threat-model early; add rate limits and abuse cases to the design.
- A07 Authentication Failures: throttle or lock out repeated failures, offer MFA where possible, handle sessions safely, make password reset secure.
- A08 Software or Data Integrity Failures: verify updates and packages, protect CI/CD, never deserialize untrusted data.
- A09 Security Logging and Alerting Failures: log sign-ins and failures, alert on suspicious activity, never log secrets.
- A10 Mishandling of Exceptional Conditions: handle errors explicitly, fail closed, never show stack traces or internals to users.

## By project type
- API: authenticate every endpoint, rate-limit, validate request schemas, avoid exposing extra fields.
- Accounts and login: lockout or throttling on failed sign-ins, secure password reset, email verification.
- Payments, checkout, shops: use a hosted payment provider; never store raw card data.
- File uploads: check type and size, store outside the web root, scan if possible.
- AI or LLM features: treat model input and output as untrusted; guard against prompt injection and never give a model more permissions than the user has. OWASP keeps a separate list for LLM applications.
