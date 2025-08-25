# db.py
import os
import asyncpg
import logging

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN or not DATABASE_URL:
    logger.error("BOT_TOKEN или DATABASE_URL не заданы в переменных окружения")
    raise RuntimeError("BOT_TOKEN или DATABASE_URL не заданы в переменных окружения")


# ----------------- Подключение к базе -----------------
async def get_db_pool():
    """Создает пул подключений к базе PostgreSQL"""
    return await asyncpg.create_pool(DATABASE_URL)


async def init_db(pool):
    """Инициализация таблиц в базе"""
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


# ----------------- Пользователи -----------------
async def add_user(pool, telegram_id, username, role, extra_info=None):
    """Добавляет пользователя или обновляет его данные"""
    async with pool.acquire() as conn:
        await conn.execute("""
        INSERT INTO users(telegram_id, username, role, extra_info)
        VALUES($1,$2,$3,$4)
        ON CONFLICT(telegram_id) DO UPDATE SET username=$2, role=$3, extra_info=$4
        """, telegram_id, username, role, extra_info)
        logger.info(f"User registered: {telegram_id}, role={role}, info={extra_info}")


async def get_role(pool, telegram_id):
    """Возвращает роль пользователя по telegram_id"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT role FROM users WHERE telegram_id=$1", telegram_id)
        return row['role'] if row else None


async def get_suppliers(pool):
    """Возвращает список telegram_id всех поставщиков"""
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT telegram_id FROM users WHERE role='supplier'")
        return [r['telegram_id'] for r in rows]