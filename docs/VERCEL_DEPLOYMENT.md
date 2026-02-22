# Deploy to Vercel (Frontend + Backend)

This guide deploys the full GAT app (React frontend + FastAPI backend) to a **single Vercel project** so the site keeps all functionality (Google sign-in, vaults, upload, search, documents).

## Important: Data on Vercel

- **Database & file storage** on Vercel serverless use **ephemeral** storage by default (in-memory /tmp). Data may not persist across deployments or between different serverless instances.
- For a **demo or testing** deployment, this is fine: sign-in, create vault, upload, and search will work within a session.
- For **production with persistence**, use [Vercel Postgres](https://vercel.com/docs/storage/vercel-postgres) (set `GAT_DATABASE_URL` in Environment Variables). Document/vault file storage will still be ephemeral unless you add external blob storage later.

## Prerequisites

1. [Vercel account](https://vercel.com/signup)
2. [Vercel CLI](https://vercel.com/docs/cli) (optional): `npm i -g vercel`
3. Google OAuth Client ID (same as local dev):
   - [Google Cloud Console](https://console.cloud.google.com/apis/credentials) → Create OAuth 2.0 Client ID (Web application)
   - Add **Authorized JavaScript origins**: `https://your-app.vercel.app`, `https://*.vercel.app` (for previews)
   - Add **Authorized redirect URIs** if needed for your flow

## 1. Push your code

Ensure the repo is on GitHub / GitLab / Bitbucket (Vercel connects to it).

## 2. Import project in Vercel

1. Go to [Vercel Dashboard](https://vercel.com/dashboard) → **Add New** → **Project**
2. Import your repository (e.g. `gat`)
3. **Root Directory**: leave as `.` (repo root)
4. **Framework Preset**: Other (we use custom `vercel.json`)
5. Build and output are set in `vercel.json`:
   - **Install Command**: `cd frontend && npm ci`
   - **Build Command**: `cd frontend && npm run build`
   - **Output Directory**: `frontend/dist`
   - API is served from `api/index.py` for all `/api/*` routes.

Do not override these unless you know what you’re doing.

## 3. Environment variables

In the Vercel project: **Settings → Environment Variables**. Add:

| Variable | Value | Notes |
|----------|--------|--------|
| `GOOGLE_CLIENT_ID` or `GAT_GOOGLE_CLIENT_ID` | Your Google OAuth Web client ID | Required for sign-in |
| `GAT_SERVER_SECRET` | Min 32 characters | Encrypts per-user SSE keys (use a strong secret) |
| `GAT_JWT_SECRET` | Any secret string | Signs JWTs (use a strong secret) |
| `VITE_GOOGLE_CLIENT_ID` | Same as `GOOGLE_CLIENT_ID` | Required so the frontend can use Google sign-in |

**Optional**

- `GAT_DATABASE_URL` – e.g. Vercel Postgres connection string for persistent DB (otherwise SQLite in /tmp, ephemeral).
- Do **not** set `VITE_API_URL` in production so the frontend uses the same origin and calls `/api/*` on your Vercel domain.

Apply to **Production** and **Preview** if you want preview deployments to work the same way.

## 4. Deploy

- **From dashboard**: push to the connected branch; Vercel will build and deploy.
- **From CLI**: in the repo root run:
  ```bash
  vercel
  ```
  Follow the prompts (link to existing project or create new one).

## 5. After deploy

1. Open the deployment URL (e.g. `https://gat-xxx.vercel.app`).
2. You should see the login page; sign in with Google.
3. Create or open a vault, then upload and search as in local dev.

If the **API returns 404** for `/api/*`:

- Confirm `api/index.py` exists and that the build completed.
- In Vercel, check **Functions** for the deployment and ensure the Python function is present and that rewrites in `vercel.json` send `/api/(.*)` to `/api/index`.

## 6. Keeping functionality intact

- **Frontend**: Built from `frontend/`; all routes (Dashboard, Performance, Judge Mode, etc.) are served from the same origin.
- **Backend**: All routes (`/api/auth/*`, `/api/documents/*`, `/api/vault/*`, `/api/vaults/*`, `/api/performance`, etc.) are handled by the same FastAPI app in `api/index.py`; no routes are removed.
- **CORS**: Configured for `*.vercel.app` so the same-origin deployment and preview URLs work with credentials.
- **Storage**: On Vercel, DB and files use `/tmp` by default (ephemeral). For persistent data, set `GAT_DATABASE_URL` to Vercel Postgres; document storage will still be per-instance unless you add blob storage later.

## 7. Optional: persistent database (Vercel Postgres)

1. In the Vercel project: **Storage** → **Create Database** → **Postgres**.
2. Connect it to the project; Vercel will add `POSTGRES_URL` (or similar).
3. Add **Environment Variable**: `GAT_DATABASE_URL` = that connection string (e.g. `postgresql://...`).
4. Redeploy. The app will use Postgres for users and vault metadata. Table creation is done by the app; for Postgres you may need to run migrations or ensure the schema matches (the app uses SQLAlchemy and creates tables on startup for SQLite; for Postgres you might need to apply the same schema once).

## Troubleshooting

- **Build fails (frontend)**  
  Run locally: `cd frontend && npm ci && npm run build`. Fix any TypeScript or build errors, then push again.

- **Build fails (API)**  
  Vercel builds the Python function from `api/` and installs `api/requirements.txt`. Ensure `backend/` and `api/` are in the repo and that `api/index.py` imports the app correctly.

- **“Create or open a vault first”**  
  Sign in, then use the vault menu (bottom left) to create a new vault or open an existing one.

- **Data disappears**  
  Expected if you’re not using Vercel Postgres and are using the default ephemeral storage. Add `GAT_DATABASE_URL` (and optionally blob storage) for persistence.
