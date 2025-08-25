import asyncpg
import logging

logger = logging.getLogger(__name__)

async def get_db_pool(database_url):
    return await asyncpg.create_pool(database_url)

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
        logger.info("DB initialized successfully.")

async def add_user(pool, telegram_id, username, role, extra_info=None):
    async with pool.acquire() as conn:
        await conn.execute("""
        INSERT INTO users(telegram_id, username, role, extra_info)
        VALUES($1,$2,$3,$4)
        ON CONFLICT(telegram_id) DO UPDATE SET username=$2, role=$3, extra_info=$4
        """, telegram_id, username, role, extra_info)
        logger.info(f"User registered: {telegram_id}, role={role}, info={extra_info}")

async def get_role(pool, telegram_id):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT role FROM users WHERE telegram_id=$1", telegram_id)
        return row['role'] if row else None

async def get_suppliers(pool):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT telegram_id FROM users WHERE role='supplier'")
        return [r['telegram_id'] for r in rows]