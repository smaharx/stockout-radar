# Add the Stockout Radar frontend

1. Extract the `frontend/` directory from this ZIP into the Stockout Radar project root.
2. Keep the existing Python backend in place. The result should look like:

```text
stockout-radar/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── package.json
│   └── ...
├── src/stockout_radar/
├── scripts/
└── ...
```

3. Leave FastAPI running in its existing terminal on port `8001`.
4. Open a second terminal:

```bash
cd /run/media/shazia/SEM/CODES/stockout-radar/frontend
cp .env.example .env.local
npm install
npm run dev
```

5. Open <http://localhost:3000>.

If the backend is not using port 8001, edit `STOCKOUT_RADAR_API_URL` in `frontend/.env.local` to its origin. Do not add `/api/v1`.

Before handing over the frontend, run:

```bash
npm run typecheck
npm run lint
npm run build
```

The current backend has no authentication. Do not expose a publicly reachable instance with writable inventory or assessment endpoints until authentication, authorization, rate limiting and deployment secrets have been added.
