# db.py
import os
import asyncpg
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.error("DATABASE_URL не задан")
    raise RuntimeError("DATABASE_URL не задан")

async def get_db_pool():
    pool = await asyncpg.create_pool(DATABASE_URL)
    logger.info("Пул БД создан")
    return pool

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
    logger.info("Таблицы созданы или уже существуют")