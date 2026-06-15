import aiosqlite
import logging

logger = logging.getLogger(__name__)

DB_PATH = "bot_database.db"
_db = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        await _db.execute("PRAGMA foreign_keys = ON")
        logger.info("Соединение с БД установлено")
    return _db


async def init_db():
    try:
        db = await get_db()
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                verified BOOLEAN DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP
            )
        ''')
        
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_verified ON users(verified)")
        
        await db.commit()
        logger.info("База данных инициализирована")
        
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        raise


async def add_user_if_not_exists(user_id: int, username: str = None, first_name: str = None):
    try:
        db = await get_db()
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name)
        )
        await db.commit()
    except Exception as e:
        logger.error(f"Ошибка добавления пользователя {user_id}: {e}")


async def set_user_verified(user_id: int):
    try:
        db = await get_db()
        await db.execute(
            "UPDATE users SET verified = 1, verified_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()
        logger.info(f"User {user_id} marked as verified")
    except Exception as e:
        logger.error(f"Ошибка верификации пользователя {user_id}: {e}")


async def is_user_verified(user_id: int) -> bool:
    try:
        db = await get_db()
        async with db.execute(
            "SELECT verified FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else False
    except Exception as e:
        logger.error(f"Ошибка проверки верификации {user_id}: {e}")
        return False


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None
        logger.info("Соединение с БД закрыто")
