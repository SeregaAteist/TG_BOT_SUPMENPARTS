# db.py
import os, asyncio, logging
import asyncpg
from typing import Optional

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL не задан")
    raise RuntimeError("DATABASE_URL не задан")

POOL_MIN_SIZE = int(os.getenv("POOL_MIN_SIZE", "1"))
POOL_MAX_SIZE = int(os.getenv("POOL_MAX_SIZE", "3"))  # разумное значение для Railway
POOL_TIMEOUT = float(os.getenv("POOL_TIMEOUT", "60"))
POOL_MAX_INACTIVE = float(os.getenv("POOL_MAX_INACTIVE", "300"))

async def get_db_pool(retries: int = 5, initial_delay: float = 1.0) -> asyncpg.pool.Pool:
    delay = initial_delay
    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"DB pool attempt {attempt}/{retries} (min={POOL_MIN_SIZE}, max={POOL_MAX_SIZE})")
            pool = await asyncpg.create_pool(
                dsn=DATABASE_URL,
                min_size=POOL_MIN_SIZE,
                max_size=POOL_MAX_SIZE,
                timeout=POOL_TIMEOUT,
                max_inactive_connection_lifetime=POOL_MAX_INACTIVE
            )
            logger.info("DB pool created")
            return pool
        except Exception as e:
            last_exc = e
            logger.warning(f"DB pool create failed: {e!r}, sleeping {delay}s")
            await asyncio.sleep(delay)
            delay *= 2
    logger.error("DB pool creation failed after retries")
    raise last_exc

async def init_db(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE,
            username TEXT,
            role TEXT,
            extra_info TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS requests(
            id SERIAL PRIMARY KEY,
            manager_id BIGINT,
            content TEXT,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS offers(
            id SERIAL PRIMARY KEY,
            request_id INT REFERENCES requests(id) ON DELETE CASCADE,
            supplier_id BIGINT,
            content TEXT,
            price NUMERIC,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)
    logger.info("DB init (tables) done")

async def close_pool(pool):
    try:
        await pool.close()
        logger.info("DB pool closed")
    except Exception as e:
        logger.warning(f"Error closing pool: {e!r}")