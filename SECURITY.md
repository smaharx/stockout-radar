# Security policy

## Supported deployment

The maintained deployment uses a Next.js frontend, a FastAPI backend and Neon PostgreSQL. Production secrets are configured through Vercel environment variables, not committed to the repository.

## Current security controls

- Frontend routes are protected by a shared administrator HTTP Basic Authentication gate in `frontend/proxy.ts`.
- Backend `/api/v1` routes require a bearer API key in production.
- The Next.js server-side API proxy adds the backend bearer key; the browser should not receive it.
- The production database URL is server-side only.
- Production database configuration rejects SQLite and requires `DATABASE_URL`.

## Important limitations

These controls are appropriate as a limited academic/demo gate but are not a complete multi-user production identity and authorization system:

- One shared administrator username/password; no individual accounts, MFA, roles or tenant isolation.
- A shared backend bearer token between the frontend proxy and backend.
- No documented rate limiting or user-level audit identity.
- Schema changes are not yet managed through Alembic migrations.

Do not use this release as a multi-tenant commercial inventory platform without a security architecture review and additional controls.

## Reporting a vulnerability

Do not publish API keys, passwords, database URLs, private customer data or an exploitable vulnerability in a public issue. Use GitHub's private vulnerability reporting/security advisory feature for this repository if available, or contact the repository maintainers privately through GitHub.

Include the affected component, impact, reproduction steps that do not expose live secrets, and any relevant request/deployment identifiers. Redact tokens, passwords, cookies, IP information not needed for triage, and database connection strings.

## Secret exposure response

If a production secret is exposed:

1. Rotate the backend bearer token in both Vercel projects if the API key is affected.
2. Rotate the frontend administrator password if the admin credential is affected.
3. Redeploy the affected project(s) so the new values take effect.
4. Review Vercel deployment/runtime logs and database access history where available.
5. Remove the exposed value from public logs, commits or artifacts where possible; remember that deleting a later file version does not erase the secret from Git history.
