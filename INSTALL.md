# INSTALL.md — Run the app locally (FastAPI + Postgres + Redis)

This guide explains how to run the project locally using:

* **FastAPI** (Python virtual environment)
* **PostgreSQL** and **Redis** via **Docker Compose**

The setup is intentionally simple and mirrors the development environment used on a GCP Ubuntu VM.

---

## Prerequisites

Make sure you have the following installed:

* **Python 3.10+**
* **Docker**
* **Docker Compose**

Verify:

```bash
python3 --version
docker --version
docker compose version
```

---

## 1. Clone the repository

```bash
git clone <YOUR_REPO_URL>
cd fastapi-demo
```

---

## 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Upgrade pip (recommended):

```bash
pip install --upgrade pip
```

---

## 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Create environment variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+asyncpg://app:app_pw@localhost:5432/app_db
REDIS_URL=redis://localhost:6379/0
```

> You can copy this from `.env.example` if provided.

---

## 5. Start Postgres and Redis

Start the Docker services:

```bash
docker compose up -d
docker compose ps
```

You should see two running containers:

* `fastapi_postgres`
* `fastapi_redis`

---

## 6. Create the demo table and seed data

Run the following command to create a simple table and insert sample rows:

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

Verify the data:

```bash
docker exec -it fastapi_postgres psql -U app -d app_db -c "SELECT * FROM items ORDER BY id;"
```

---

## 7. Run the FastAPI application

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open in your browser:

* [http://localhost:8000/](http://localhost:8000/)
* [http://localhost:8000/health](http://localhost:8000/health)
* [http://localhost:8000/items/slow](http://localhost:8000/items/slow)
* [http://localhost:8000/items/cached](http://localhost:8000/items/cached)

---

## 8. Observe Redis caching behavior

Call the cached endpoint twice in quick succession:

```bash
curl http://localhost:8000/items/cached
curl http://localhost:8000/items/cached
```

Expected behavior:

* First call → cache miss → slow (~800ms)
* Second call → cache hit → very fast

Cache TTL is currently set to **30 seconds**.

---

## 9. Stop services

Stop containers:

```bash
docker compose down
```

Stop and delete volumes (removes DB and Redis data):

```bash
docker compose down -v
```

---

## Notes

* PostgreSQL is the **source of truth**
* Redis is used purely as a **performance cache**
* If Redis is unavailable, the app still works using Postgres
* This setup is suitable for experimentation and learning; production setups require additional hardening
