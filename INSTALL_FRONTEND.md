# Frontend setup guide

This file is retained as a short entry point for existing project references. The maintained documentation is in [`docs/deployment.md`](docs/deployment.md), [`docs/architecture.md`](docs/architecture.md), and [`docs/operations-runbook.md`](docs/operations-runbook.md).

## Local development

From the repository root:

```bash
cd frontend
npm ci
```

Create `frontend/.env.local`:

```dotenv
STOCKOUT_RADAR_API_URL=http://127.0.0.1:8001
```

Start the frontend:

```bash
npm run dev
```

Open <http://localhost:3000>. Start the FastAPI backend separately on port `8001`.

## Production

The Vercel frontend project uses root directory `frontend`. Configure these Production variables:

- `STOCKOUT_RADAR_API_URL` — deployed backend origin, without `/api/v1`.
- `STOCKOUT_RADAR_API_KEY` — same bearer token as the backend project.
- `STOCKOUT_RADAR_ADMIN_USER` — administrator username.
- `STOCKOUT_RADAR_ADMIN_PASSWORD` — strong administrator password.

The production frontend proxy keeps the backend API key server-side and applies HTTP Basic Authentication to the application routes. This is a shared single-administrator gate, not multi-user authentication.
