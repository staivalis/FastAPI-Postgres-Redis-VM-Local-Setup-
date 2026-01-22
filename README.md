# FastAPI + Postgres + Redis (VM – Local Setup)

This repository documents a **step-by-step setup** of a FastAPI application running on a **Ubuntu VM**, connected to **PostgreSQL** and **Redis** using Docker.

The goal of this project is to **experimentally demonstrate** how Redis can reduce response time by caching expensive database query results.

---

## Architecture Overview

```
┌────────────────────────────────────┐
│ VM (Ubuntu)                    │
│                                    │
│  FastAPI (Python, venv)            │
│        │                           │
│        ├── Postgres (Docker)       │
│        └── Redis (Docker)          │
│                                    │
└────────────────────────────────────┘
```

- FastAPI runs **directly on the VM** (not containerized yet)
- Postgres and Redis run as **Docker containers**
- Everything is **local-only** (no public exposure yet)

---

## Step 1 — Install Docker & Docker Compose

Install Docker on Ubuntu using the official repository:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Allow running Docker without sudo:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

Verify:

```bash
docker --version
docker compose version
docker ps
```

---

## Step 2 — Start Postgres & Redis with Docker Compose

Create `docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:16
    container_name: fastapi_postgres
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app_pw
      POSTGRES_DB: app_db
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app_db"]

  redis:
    image: redis:7
    container_name: fastapi_redis
    ports:
      - "6379:6379"
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis_data:/data

volumes:
  pg_data:
  redis_data:
```

Start services:

```bash
docker compose up -d
docker compose ps
```

---

## Step 3 — Verify Connectivity

### Postgres

```bash
docker exec -it fastapi_postgres psql -U app -d app_db -c "SELECT now();"
```

### Redis

```bash
docker exec -it fastapi_redis redis-cli ping
```

Expected output:

```text
PONG
```

---

## Step 4 — Create Table & Seed Data

Create a simple table and seed rows:

```bash
docker exec -it fastapi_postgres psql -U app -d app_db -c "
CREATE TABLE IF NOT EXISTS items (
  id   SERIAL PRIMARY KEY,
  name TEXT NOT NULL
);

INSERT INTO items (name)
SELECT x
FROM (VALUES ('alpha'), ('beta'), ('gamma')) AS v(x)
WHERE NOT EXISTS (SELECT 1 FROM items);
"
```

Verify:

```bash
docker exec -it fastapi_postgres psql -U app -d app_db -c "SELECT * FROM items ORDER BY id;"
```

---

## Step 5 — Python Environment & Configuration

Install dependencies inside your virtual environment:

```bash
pip install "sqlalchemy>=2" asyncpg redis python-dotenv
```

Create `.env` file:

```env
DATABASE_URL=postgresql+asyncpg://app:app_pw@localhost:5432/app_db
REDIS_URL=redis://localhost:6379/0
```

Verify imports:

```bash
python -c "import sqlalchemy, asyncpg, redis, dotenv; print('imports ok')"
```

---

## Step 6 — FastAPI: Postgres vs Redis Cache

Two endpoints demonstrate the difference:

- **`/items/slow`** → always queries Postgres + artificial delay
- **`/items/cached`** → uses Redis cache (TTL = 30s)

### Run the app

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Test locally

```bash
curl http://localhost:8000/items/slow
curl http://localhost:8000/items/cached
curl http://localhost:8000/items/cached
```

Expected behavior:
- First call: ~800ms
- Cached call: **very fast (Redis hit)**

---

## Key Concepts Demonstrated

- Redis stores cached data **in RAM**, optionally persisted to disk
- Redis does **not** cache queries automatically
- Cache keys must be **explicitly designed**
- TTL prevents stale data
- Postgres remains the **source of truth**

---

## Next Possible Extensions

- Cache invalidation on insert/update
- Parameterized cache keys
- Nginx + public exposure
- Containerize FastAPI
- Benchmark Redis vs in-process cache

---

## License

MIT

