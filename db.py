# db.py
import os
import asyncpg
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL не задан")
    raise RuntimeError("DATABASE_URL не задан")

# Параметры пула — подстрой под нагрузку. Для Railway разумно маленькое число.
POOL_MIN_SIZE = int(os.getenv("POOL_MIN_SIZE", "1"))
POOL_MAX_SIZE = int(os.getenv("POOL_MAX_SIZE", "5"))
POOL_TIMEOUT = float(os.getenv("POOL_TIMEOUT", "60"))  # seconds
POOL_MAX_INACTIVE = float(os.getenv("POOL_MAX_INACTIVE", "300"))  # seconds

# Функция создаёт пул с retry/backoff
async def get_db_pool(retries: int = 5, initial_delay: float = 1.0) -> asyncpg.pool.Pool:
    delay = initial_delay
    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Попытка {attempt}/{retries}: создаём пул подключений к БД (min={POOL_MIN_SIZE}, max={POOL_MAX_SIZE})")
            pool = await asyncpg.create_pool(
                dsn=DATABASE_URL,
                min_size=POOL_MIN_SIZE,
                max_size=POOL_MAX_SIZE,
                timeout=POOL_TIMEOUT,
                max_inactive_connection_lifetime=POOL_MAX_INACTIVE
            )
            logger.info("Пул БД создан успешно")
            return pool
        except Exception as e:
            last_exc = e
            logger.warning(f"Не удалось создать пул (attempt {attempt}): {e!r}. Ждём {delay} сек и повторяем...")
            await asyncio.sleep(delay)
            delay *= 2  # экспоненциальный backoff
    logger.error("Не удалось создать пул БД после всех попыток")
    raise last_exc  # пробрасываем последнюю ошибку

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
            manager_id BIGINT REFERENCES users(telegram_id),
            content TEXT,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS offers(
            id SERIAL PRIMARY KEY,
            request_id INT REFERENCES requests(id) ON DELETE CASCADE,
            supplier_id BIGINT REFERENCES users(telegram_id),
            content TEXT,
            price NUMERIC,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

async def close_pool(pool: asyncpg.pool.Pool):
    try:
        await pool.close()
        logger.info("Пул БД закрыт")
    except Exception as e:
        logger.warning(f"Ошибка при закрытии пула: {e!r}")