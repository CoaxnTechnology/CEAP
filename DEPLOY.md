# Deploy Documind to a VPS (Docker + GitHub Actions)

## 1. VPS prerequisites

```bash
# Install Docker + Compose plugin (Ubuntu 22.04/24.04)
curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker

# Optional: add your user to the docker group
sudo usermod -aG docker $USER
```

## 2. First-time server layout

```bash
sudo mkdir -p /opt/CEAP/frontend/dist /opt/CEAP/storage
sudo chown -R $USER:$USER /opt/CEAP
```

Clone once so the runtime dirs exist (or let the first deploy create them):

```bash
cd /opt/CEAP
git clone git@github.com:CoaxnTechnology/Documind.git repo
```

Create the environment file (never commit it) — **the CI/CD pipeline reads it untouched**:

```bash
sudo nano /opt/CEAP/.env
```

`.env` contents — note the **DB host is `postgres`** (the compose service name), not `localhost`:

```env
# Database (container service name is "postgres")
DB_URI=postgresql://documind_user:documind_pass@postgres:5432/documind
POSTGRES_DB=documind
POSTGRES_USER=documind_user
POSTGRES_PASSWORD=documind_pass
FLASK_SECRET_KEY=<long random string>
GROQ_API_KEY=<your key>
GEMINI_API_KEY=<your key>
AZURE_CLIENT_ID=<optional>
AZURE_CLIENT_SECRET=<optional>
AZURE_TENANT_ID=common
AZURE_REDIRECT_URI=https://ceap.coaxn.com/auth/callback
CHROMA_PATH=/app/chroma_db
```

## 3. GitHub Actions secrets

In your repo: **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `VPS_HOST` | IP or domain of the VPS |
| `VPS_USER` | SSH user (e.g. `ubuntu` or `root`) |
| `SSH_PRIVATE_KEY` | Private key that can log into the VPS |
| `RSYNC_PORT` | SSH port (defaults to 22) |

`/opt/CEAP/.env` is **managed manually on the server** — CI/CD never overwrites it. Compose loads it automatically via `env_file: .env`.

## 4. Deploy

Every push to `main` (or manual run via **Actions → Deploy → Run workflow**) will:

1. Build the frontend in CI
2. rsync `frontend/dist` → `/opt/CEAP/frontend/dist`
3. rsync backend source + compose → `/opt/CEAP/`
4. `docker compose up -d --build backend` (env untouched)

Manual first deploy:

```bash
cd /opt/CEAP
docker compose up -d --build
docker compose logs -f backend   # watch startup
```

The app is served at `https://ceap.coaxn.com/` via nginx → `127.0.0.1:8010` (compose binds the backend on loopback only).

## 5. Updating

Nothing manual — push to `main`. The workflow rebuilds the backend image and restarts.

## Notes

- **Data persistence**: ChromaDB (`./chroma_db`), Postgres (`pgdata` volume), uploaded files (`./storage`) all persist across deploys via host mounts.
- **Frontend dist** is volume-mounted from `./frontend/dist` — CI rsyncs it, so SPA changes never need a rebuild.
- **TLS**: not included. For HTTPS, put nginx/caddy in front and add `443` mapping.
