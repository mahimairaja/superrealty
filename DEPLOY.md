# Deploying RealtyRecall

Three services, continuously deployed from `main`:

```
Vercel        frontend (Vite SPA)          auto-build, SPA rewrites
Railway       backend  (FastAPI/gunicorn)  Dockerfile, /health, alembic on deploy
Railway       agent    (LiveKit worker)    Dockerfile, `main.py start`
Managed data  Neon (Postgres + pgvector) · Neo4j Aura · LiveKit Cloud
```

CI (lint + typecheck + build + unit tests) runs on every PR via GitHub Actions.
CD (`.github/workflows/deploy.yml`) deploys only the services whose paths changed
on merge to `main`. Each deploy job no-ops cleanly until its secrets exist, so the
pipeline stays green before the platforms are connected.

---

## 1. Provision managed data (once)

- **Neon** (Postgres + pgvector): create a project, note host / user / password. Create a
  database named `app`. The backend creates the `cognee_db` database and the `vector`
  extension on first boot. Neon requires SSL (`DB_SSL=require`).
- **Neo4j** (graph): either a self-hosted `neo4j:5-community` service (e.g. on Railway) or
  managed **Neo4j Aura** (free). Note the bolt/`neo4j+s://` URI and password.
- **LiveKit Cloud**: project URL + API key/secret.

> **APOC is required.** Cognee calls APOC procedures on the first `POST /onboard/confirm`, so
> the graph DB must have the APOC plugin enabled or that request returns 500 on graph writes.
> - **Self-hosted Neo4j** (Railway `neo4j:5-community`, or local `docker-compose`): set
>   `NEO4J_PLUGINS='["apoc"]'` and `NEO4J_dbms_security_procedures_unrestricted=apoc.*` on the
>   Neo4j service, then restart it. `docker-compose.yml` already sets both for local dev.
> - **Neo4j Aura**: APOC Core ships enabled, so no action is needed.
>
> On Railway, set the two vars on the `rr-neo4j` service, e.g.
> `railway variables --service rr-neo4j --set 'NEO4J_PLUGINS=["apoc"]' --set 'NEO4J_dbms_security_procedures_unrestricted=apoc.*'`

## 2. Backend service (Railway)

New service from this repo, **root directory `backend/`**. Railway reads `backend/railway.json`
(Dockerfile build, `alembic upgrade head` pre-deploy, `/health` healthcheck). Set env:

| Var | Value |
|---|---|
| `ENV` | `prod` |
| `DB_HOST` `DB_PORT` `DB_USER` `DB_PASSWORD` | from Neon |
| `DB_NAME` | `app` |
| `DB_SSL` | `require` |
| `COGNEE_DB_NAME` | `cognee_db` |
| `COGNEE_DB_HOST` `COGNEE_DB_PORT` `COGNEE_DB_USER` `COGNEE_DB_PASSWORD` | same Neon values |
| `GRAPH_DATABASE_PROVIDER` | `neo4j` |
| `GRAPH_DATABASE_URL` | `neo4j+s://<id>.databases.neo4j.io` |
| `GRAPH_DATABASE_USERNAME` `GRAPH_DATABASE_PASSWORD` `NEO4J_PASSWORD` | from Aura |
| `VECTOR_DB_PROVIDER` | `pgvector` |
| `OPENAI_API_KEY` | LLM + Cognee embeddings |
| `LIVEKIT_URL` `LIVEKIT_API_KEY` `LIVEKIT_API_SECRET` | from LiveKit |
| `JWT_SECRET_KEY` | long random string |
| `CORS_ORIGINS_STR` | `https://<your-vercel-domain>` |
| `WIDGET_ALLOWED_ORIGINS_STR` | `https://<your-vercel-domain>` |
| `CAL_API_KEY` `RR_CAL_EVENT_TYPE_ID` | optional (booking) |
| `TELNYX_API_KEY` `TELNYX_FROM_NUMBER` `REALTOR_SMS_TO` | optional (lead SMS) |

Railway injects `PORT`; gunicorn binds it automatically. Public domain = the backend base.

## 3. Agent service (Railway)

New service from this repo, **root directory `agent/`**. It is a worker (connects out to
LiveKit; no public domain needed). Set env:

| Var | Value |
|---|---|
| `LIVEKIT_URL` `LIVEKIT_API_KEY` `LIVEKIT_API_SECRET` | from LiveKit |
| `OPENAI_API_KEY` `DEEPGRAM_API_KEY` `CARTESIA_API_KEY` | speech + LLM |
| `AGENT_NAME` | `realty` |
| `AGENT_MAX_CALL_SECONDS` | `600` |
| `BACKEND_URL` | the backend public URL + `/api/v1` |
| `SENTRY_DSN` | optional |

## 4. Frontend (Vercel)

New project from this repo, **root directory `frontend/`**. `frontend/vercel.json` sets the
Vite build and the SPA rewrite. Set env (Production + Preview):

| Var | Value |
|---|---|
| `VITE_TOKEN_ENDPOINT` | `https://<backend-domain>/api/v1/token` |
| `VITE_AGENT_NAME` | `realty` |

## 5. CI/CD

CI is already wired (`lint.yml` + `test.yml`). For GitHub Actions CD (`deploy.yml`), add these
**repository secrets** (Settings → Secrets → Actions):

| Secret | From |
|---|---|
| `VERCEL_TOKEN` | Vercel account tokens |
| `VERCEL_ORG_ID` `VERCEL_PROJECT_ID` | `frontend/.vercel/project.json` after one `vercel link`, or the Vercel project settings |
| `RAILWAY_TOKEN` | a Railway **project** token |
| `RAILWAY_BACKEND_SERVICE` | the backend service name |
| `RAILWAY_AGENT_SERVICE` | the agent service name |

Once set, every merge to `main` deploys the changed services. Enable branch protection so a
PR must pass CI before it can merge.

> Alternative (zero YAML): connect Vercel's GitHub app and Railway's GitHub repo deploy for
> native auto-deploy. If you use that, do **not** also set the `deploy.yml` secrets, to avoid
> double deploys.

## 6. Smoke test

1. Backend: `GET https://<backend>/health` returns 200; `GET /docs` loads.
2. Frontend: open the Vercel URL, the console loads and `/pipeline` survives a refresh (SPA rewrite).
3. Agent: Railway logs show the worker registered with LiveKit.
4. End to end: open `/call`, start a conversation, confirm the agent answers.
