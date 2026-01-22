from pathlib import Path
import os
import json
import time
import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from dotenv import load_dotenv
import redis.asyncio as redis

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "FastAPI demo yeah", "message": "Hello from FastAPI (user stef)"}
    )

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/items/slow")
async def items_slow():
    """
    Simulated expensive endpoint:
    - adds an artificial delay (pretend heavy computation / slow query)
    - queries Postgres
    """
    t0 = time.perf_counter()

    await asyncio.sleep(0.8)  # simulate slowness

    async with SessionLocal() as session:
        res = await session.execute(text("SELECT id, name FROM items ORDER BY id"))
        rows = [{"id": r[0], "name": r[1]} for r in res.all()]

    ms = (time.perf_counter() - t0) * 1000
    return {"source": "postgres", "elapsed_ms": round(ms, 2), "items": rows}

@app.get("/items/cached")
async def items_cached():
    """
    Cached endpoint:
    - if cache hit: return from Redis fast
    - if miss: do the same work as /items/slow, then store in Redis with TTL
    """
    cache_key = "items:all"
    t0 = time.perf_counter()

    cached = await redis_client.get(cache_key)
    if cached:
        ms = (time.perf_counter() - t0) * 1000
        return {"source": "redis", "elapsed_ms": round(ms, 2), "items": json.loads(cached)}

    await asyncio.sleep(0.8)  # simulate same slowness on cache miss

    async with SessionLocal() as session:
        res = await session.execute(text("SELECT id, name FROM items ORDER BY id"))
        rows = [{"id": r[0], "name": r[1]} for r in res.all()]

    await redis_client.setex(cache_key, 30, json.dumps(rows))  # cache for 30 seconds

    ms = (time.perf_counter() - t0) * 1000
    return {"source": "postgres_then_cached", "elapsed_ms": round(ms, 2), "items": rows}
