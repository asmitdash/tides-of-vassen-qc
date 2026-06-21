# Tides of Vassen — Pre-Air QC Frontend

Next.js 14 App Router frontend for the Netflix QC pipeline POC.

## Dev

```bash
npm run dev
```

Expects backend at `BACKEND_URL` (defaults to `http://127.0.0.1:8787`).

## Build

```bash
npm run build
```

## Deploy

Update `vercel.json` with your deployed backend URL before pushing to Vercel. Vercel can't reach localhost.
