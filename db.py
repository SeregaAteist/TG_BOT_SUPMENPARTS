# db.py
import os
import asyncpg
import logging
import asyncio
import traceback
from typing import Optional

logger = logging.getLogger("db")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL не задан")
    raise RuntimeError("DATABASE_URL не задан")

POOL_MIN_SIZE = int(os.getenv("POOL_MIN_SIZE", "1"))
POOL_MAX_SIZE = int(os.getenv("POOL_MAX_SIZE", "3"))
POOL_TIMEOUT = float(os.getenv("POOL_TIMEOUT", "60"))
POOL_MAX_INACTIVE = float(os.getenv("POOL_MAX_INACTIVE", "300"))

# ----------------- Создание пула с retry/backoff -----------------
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

# ----------------- Инициализация таблиц -----------------
async def init_db(pool: asyncpg.pool.Pool):
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

# ----------------- Закрытие пула -----------------
async def close_pool(pool: asyncpg.pool.Pool):
    try:
        await pool.close()
        logger.info("DB pool closed")
    except Exception as e:
        logger.warning(f"Error closing pool: {e!r}")

# ----------------- Утилиты для хендлеров -----------------
async def add_user(pool: asyncpg.pool.Pool, telegram_id: int, username: Optional[str], role: str, extra_info: Optional[str] = None):
    """
    Добавляет или обновляет пользователя по telegram_id.
    """
    sql = """
        INSERT INTO users(telegram_id, username, role, extra_info)
        VALUES($1, $2, $3, $4)
        ON CONFLICT (telegram_id) DO UPDATE
          SET username = EXCLUDED.username,
              role = EXCLUDED.role,
              extra_info = EXCLUDED.extra_info
    """
    try:
        async with pool.acquire() as conn:
            await conn.execute(sql, telegram_id, username, role, extra_info)
        logger.info(f"add_user: ok {telegram_id} role={role} info={extra_info}")
    except Exception as e:
        logger.error("add_user: ERROR executing SQL")
        logger.error("SQL: %s", sql)
        logger.error("ARGS: %r, %r, %r, %r", telegram_id, username, role, extra_info)
        logger.error("Exception: %s", e)
        logger.error("Traceback:\n" + traceback.format_exc())
        raise

async def get_role(pool: asyncpg.pool.Pool, telegram_id: int) -> Optional[str]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT role FROM users WHERE telegram_id=$1", telegram_id)
        return row['role'] if row else None

async def get_user_by_telegram_id(pool: asyncpg.pool.Pool, telegram_id: int) -> Optional[dict]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT telegram_id, username, role, extra_info FROM users WHERE telegram_id=$1", telegram_id)
        if row:
            return dict(row)
        return None

async def get_suppliers(pool: asyncpg.pool.Pool):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT telegram_id FROM users WHERE role='supplier'")
        return [r['telegram_id'] for r in rows]

async def create_request(pool: asyncpg.pool.Pool, manager_id: int, content: str) -> int:
    async with pool.acquire() as conn:
        req_id = await conn.fetchval(
            "INSERT INTO requests(manager_id, content) VALUES($1, $2) RETURNING id",
            manager_id, content
        )
        return req_id

async def create_offer(pool: asyncpg.pool.Pool, request_id: int, supplier_id: int, content: str, price: float) -> int:
    async with pool.acquire() as conn:
        offer_id = await conn.fetchval(
            "INSERT INTO offers(request_id, supplier_id, content, price) VALUES($1, $2, $3, $4) RETURNING id",
            request_id, supplier_id, content, price
        )
        return offer_id

async def get_offers_for_request(pool: asyncpg.pool.Pool, request_id: int):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM offers WHERE request_id=$1", request_id)
        return [dict(r) for r in rows]