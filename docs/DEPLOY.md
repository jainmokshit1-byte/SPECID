# Deploy the SpecID cloud demo (free tier)

> **Live now (6 Oct 2026):** web **https://specid-0.netlify.app** · API **https://specid.onrender.com**
> (Render service `specid`, created as *Public Git Repository*, Docker, `deploy/render.Dockerfile`) ·
> Neon project `specid` (Singapore). The Netlify site was created by **drag-and-drop** (no GitHub
> link). To update the web app: rebuild (`frontend` → `vite build`), copy `dist` + `_redirects` +
> `_headers` (see `netlify-upload/`), zip it, and drag the zip onto **the site's Deploys tab** (not
> app.netlify.com/drop, which makes a new site and a new link). Visitor access must stay **public**.
> To update the API: push to GitHub, then Render → Manual Deploy → Deploy latest commit.

Three free services, about 30 minutes the first time. Nothing here costs money; no card is needed
for Neon or Netlify. Render's free plan may ask for a card on some accounts. If it does, see
"Alternatives" at the end.

```
Browser ──► Netlify (web app, static)  ──/api/*──►  Render (API, Docker)  ──►  Neon (Postgres + pgvector)
                                                        │
                                                        └──► Gemini API (only when AI_PROVIDER=gemini)
```

The cloud demo runs on **synthetic data only** (DEMO_MODE). The on-premise, air-gapped build is the
same code run with `docker compose` (see `README.md`); that is the build for real CPSE data.

---

## 0. Before you start

- Push the branch you want to deploy to GitHub (Render and Netlify build from GitHub).
- Have these ready: a GitHub login, and later your Gemini API key (optional; see step 5).

## 1. Neon: the database (5 min)

1. Sign up at neon.tech → **New project**. Name it `specid`, Postgres **16**, region **AWS Asia
   Pacific (Singapore)** (closest to Render Singapore).
2. On the project dashboard click **Connect**. Untick "Connection pooling" (use the direct
   connection) and copy the connection string. It looks like:
   `postgresql://neondb_owner:XXXX@ep-something-123456.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`
3. That's all. pgvector is available on Neon; the app runs `CREATE EXTENSION vector` itself in its
   first migration.

Keep the string private: it contains the password.

## 2. Render: the API (10 min, then 3 to 6 min of build)

1. Sign up at render.com with GitHub → **New → Blueprint** → pick this repository and the branch.
   Render reads `render.yaml` and proposes one web service, `specid-api`.
2. It asks for the values marked `sync: false`:
   - `DATABASE_URL`: paste the Neon string from step 1 as is.
   - `DEMO_PASSWORD`: any password of 8+ characters (the seeded users get it; the one-click demo
     buttons don't need it).
   - `GEMINI_API_KEY`: leave **empty** for now.
3. Click **Apply**. The first build takes a few minutes.
4. When it is live, open `https://specid-api.onrender.com/api/v1/health` (your URL may differ;
   Render shows it). You should see `"status":"ok"` and `"demo_status":"preparing"`, then
   `"ready"` after the demo data is loaded (a few minutes on the free CPU).

Free-plan facts to know before a demo:
- The service **sleeps after 15 minutes idle**; the next visit wakes it in about a minute. The login
  page says "Connecting to the server…" while that happens. **Open the link 2 to 3 minutes before
  you present.**
- 512 MB of memory: that's why `render.yaml` sets `JOB_MODE=thread` and `DEMO_ENTITIES=400`.
- Data stays in Neon, so a restart does not reload it; the demo data is created only once.

## 3. Netlify: the web app (5 min)

1. Edit `netlify.toml` in the repo: in the `/api/*` redirect, replace
   `https://specid-api.onrender.com` with your Render URL if it differs. Commit and push.
2. Sign up at netlify.com with GitHub → **Add new site → Import an existing project** → pick the
   repository and branch. Netlify reads `netlify.toml` (base `frontend`, build `npm run build`,
   publish `dist`). Click **Deploy**.
3. **Site configuration → Change site name** → e.g. `specid-demo` → your link is
   `https://specid-demo.netlify.app`.
4. Back in Render → `specid-api` → **Environment**: set `CORS_ORIGIN` to that Netlify URL and save
   (it redeploys).

Open the Netlify link. You should see the login page with **Demo: sign in as** buttons. Click
**Maker**, and you're in.

## 4. Check the demo end to end (5 min)

| Step | Where | Expect |
|---|---|---|
| Sign in as Maker | Login | Home dashboard with figures, price gaps, transfers |
| Matching runs | Data → Matching runs | One DONE run with the verdict mix |
| Look-alikes | Review → Look-alikes | Blocked look-alikes with the deciding attribute |
| Issued codes | Registry → Codes | Three national codes (NMC-…) |
| SAP form | Registry → Create material (SAP) | Type "GATE VALVE 4IN 150# WCB FLGD RF" → existing code flagged |
| Evaluation | Results → Evaluation | One DONE evaluation, seed 7, honesty panel |
| Footer | bottom right | "Cloud demo · AI: off" (never "Air-gapped" in the cloud) |

## 5. Turn on Gemini (when you have the key)

1. Get a key at aistudio.google.com → **Get API key** (free tier).
2. Render → `specid-api` → **Environment**: set `GEMINI_API_KEY` to the key and `AI_PROVIDER` to
   `gemini`. Save (it redeploys, about 3 minutes).
3. Check `/api/v1/health`: `"ai_provider":"gemini"`, `"ai_ready":true`. The footer says
   "Cloud demo · AI: Gemini (synthetic data only)".
4. Start a new run (Data → Matching runs → New run). The run console shows **What AI did in this
   run**: records read, values accepted, values rejected, and meaning-search pairs.

The key lives only in Render's environment, never in the repo. Locally it goes in `.env`
(`GEMINI_API_KEY=`), which git ignores.

## 6. Updating the demo

- Code change: push → Render **Manual Deploy → Deploy latest commit** (auto-deploy is off on
  purpose, so a push never breaks a demo in progress) and Netlify rebuilds by itself.
- Fresh demo data: in the Neon console run `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`,
  then restart the Render service. It migrates and loads the demo data again.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Login stays on "Connecting to the server…" for 3+ min | Render build failed or the service crashed | Render → Logs. Most often a wrong `DATABASE_URL`. |
| Health says `"demo_status":"failed"` | Demo data load failed | Render → Logs, look for `demo_bootstrap_failed`. Sign in with a password meanwhile. |
| Netlify shows the page but every call fails | `/api/*` redirect points to the wrong Render URL | Fix `netlify.toml`, push. |
| Render log `egress blocked` for the database | Unusual URL form | Set `DB_HOST` to the Neon host name. |
| Out of memory (Render restarts the service) | Too much demo data for 512 MB | Lower `DEMO_ENTITIES` (e.g. 300). |

## Alternatives (also free)

- **Hugging Face Spaces (Docker)**: 2 vCPU and 16 GB on the free CPU tier, sleeps after 48 h idle.
  Use `deploy/render.Dockerfile` as the Space's `Dockerfile`, set the same variables as Space
  secrets, and add `PORT=7860`. Faster runs than Render, but the URL is `*.hf.space`.
- **Koyeb / Fly.io**: work with the same Dockerfile; their free allowances change often.

## Local, fully offline (for comparison)

```
cp .env.example .env      # fill DB_PASSWORD, JWT_SECRET, DEMO_PASSWORD
make up && make seed      # http://127.0.0.1:8080
```

Footer: "Air-gapped · blocked attempts: n". No AI provider, no internet route from the API.
