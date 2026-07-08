# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in D-CIP, please report it privately
rather than opening a public issue.

**Contact:** adlakhadhruv20@gmail.com

Please include:
- A description of the vulnerability and its potential impact
- Steps to reproduce it
- Any relevant logs, screenshots, or proof-of-concept code

You should expect an initial response within a few days. Please allow time
for a fix to be developed and released before disclosing publicly.

## Supported Versions

| Version | Supported |
|---|---|
| 1.0.x | ✅ |
| < 1.0 | ❌ |

## Scope

D-CIP handles digital evidence and enforces role-based access control by
design — see the [Security Features section in README.md](README.md#security-features)
and [`ARCHITECTURE.md`](ARCHITECTURE.md) §3.3–3.5 and §13 for the full
security model. Reports involving any of the following are especially
welcome:

- Authentication / authorization bypass (RBAC, JWT/cookie handling)
- Evidence integrity or chain-of-custody weaknesses
- Injection vulnerabilities (SQL, command, etc.)
- Cross-case data leakage
- Secrets or credentials exposure

## Known, Accepted Risks (by design, not vulnerabilities)

Documented explicitly so they aren't re-reported as findings — see
[`ARCHITECTURE.md`](ARCHITECTURE.md) for full detail:

- The platform ships with a documented default admin account
  (`admin@dcip.local`) for local development. This **must** be rotated
  before any shared or production deployment — the app also refuses to
  boot in production with a placeholder `SECRET_KEY` or
  `AUTH_COOKIE_SECURE=false`.
- AI-generated content is grounded via prompt engineering, not a
  code-level verification step — this is a documented design tradeoff,
  not an oversight.
