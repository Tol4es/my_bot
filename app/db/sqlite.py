import sqlite3
import asyncio
from pathlib import Path
from typing import Optional, List, Iterable, Sequence
from contextlib import contextmanager

from ..config import DB_PATH

# -- базове з'єднання --
def _connect(path: Path = DB_PATH) -> sqlite3.Connection:
    # гарантуємо існування директорії
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn

@contextmanager
def _conn_ctx(path: Path = DB_PATH):
    conn = _connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ініціалізація схеми
def init_db(db_path: Path = DB_PATH) -> None:
    with _conn_ctx(db_path) as con:
        # users
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id      INTEGER PRIMARY KEY,
                name    TEXT,
                phone   TEXT,
                blocked INTEGER DEFAULT 0,
                joined  TEXT
            )
            """
        )

        # cities — FOREIGN KEY оголошено inline, щоб не було синтаксичних помилок
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS cities(
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                city       TEXT    NOT NULL,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                UNIQUE (user_id, city)
            )
            """
        )

        # bugs — також FK inline
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS bugs(
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                msg        TEXT    NOT NULL,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )
            """
        )

        con.execute("CREATE INDEX IF NOT EXISTS idx_users_blocked ON users (blocked)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_cities_user ON cities (user_id)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_bugs_user ON bugs (user_id, created_at DESC)")


# базові async-утиліти
async def exec_(sql: str, args: tuple = (), db_path: Path = DB_PATH) -> None:
    def run():
        with _conn_ctx(db_path) as con:
            con.execute(sql, args)
    await asyncio.to_thread(run)

async def query(sql: str, args: tuple = (), db_path: Path = DB_PATH) -> List[sqlite3.Row]:
    def run():
        with _conn_ctx(db_path) as con:
            cur = con.execute(sql, args)
            return cur.fetchall()
    return await asyncio.to_thread(run)

async def query_one(sql: str, args: tuple = (), db_path: Path = DB_PATH) -> Optional[sqlite3.Row]:
    rows = await query(sql, args, db_path=db_path)
    return rows[0] if rows else None


# хелпери безпеки/зручності
def escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

def placeholders_for_in(items: Iterable) -> str:
    lst = list(items)
    return ", ".join("?" for _ in lst) if lst else "NULL"


# репозиторні функції
async def ensure_user(user_id: int, name: str | None = None) -> None:
    # компактний UPSERT
    await exec_(
        """
        INSERT INTO users(id, name, joined) 
        VALUES(?,?,date('now','localtime'))
        ON CONFLICT(id) DO UPDATE SET name = excluded.name
        """,
        (user_id, name or "")
    )

async def set_user_phone(user_id: int, phone: str) -> None:
    # гарантований запис телефону (UPSERT)
    await exec_(
        """
        INSERT INTO users (id, phone, joined)
        VALUES (?, ?, date('now','localtime'))
        ON CONFLICT(id) DO UPDATE SET phone = excluded.phone
        """,
        (user_id, phone)
    )

async def has_phone(user_id: int) -> bool:
    row = await query_one("SELECT phone FROM users WHERE id = ?", (user_id,))
    return bool(row and row["phone"])

async def is_blocked(user_id: int) -> bool:
    row = await query_one("SELECT blocked FROM users WHERE id = ?", (user_id,))
    return bool(row and row["blocked"])

async def block_user(user_id: int, flag: bool) -> None:
    await exec_("UPDATE users SET blocked = ? WHERE id = ?", (1 if flag else 0, user_id))

async def get_user_cities(user_id: int) -> list[str]:
    rows = await query("SELECT city FROM cities WHERE user_id = ? ORDER BY rowid", (user_id,))
    return [r["city"] for r in rows]

async def add_city(user_id: int, city: str) -> bool:
    # обмеження 3 міста (простий варіант перевірки)
    rows = await query("SELECT 1 FROM cities WHERE user_id = ? LIMIT 3", (user_id,))
    if len(rows) >= 3:
        return False
    try:
        await exec_("INSERT INTO cities(user_id, city) VALUES(?,?)", (user_id, city))
        return True
    except sqlite3.IntegrityError:
        # дубль або порушено FK/UNIQUE
        return False

async def del_city(user_id: int, city: str) -> None:
    await exec_("DELETE FROM cities WHERE user_id = ? AND city = ?", (user_id, city))


# баг-репорти
MAX_BUG_LEN = 2000

def _normalize_msg(text: str) -> str:
    text = (text or "").strip()
    if len(text) > MAX_BUG_LEN:
        text = text[:MAX_BUG_LEN]
    return text

async def add_bug(user_id: int, msg: str) -> None:
    clean = _normalize_msg(msg)
    await exec_("INSERT INTO bugs(user_id, msg) VALUES(?,?)", (user_id, clean))

async def search_bugs(user_id: int, query_text: str, limit: int = 50) -> List[sqlite3.Row]:
    q = escape_like(query_text)
    return await query(
        "SELECT id, user_id, msg, created_at "
        "FROM bugs "
        "WHERE user_id = ? AND msg LIKE ? ESCAPE '\\' "
        "ORDER BY created_at DESC LIMIT ?",
        (user_id, f"%{q}%", limit)
    )

async def get_bugs_by_ids(ids: Sequence[int]) -> List[sqlite3.Row]:
    if not ids:
        return []
    ph = placeholders_for_in(ids)
    return await query(
        f"SELECT id, user_id, msg, created_at FROM bugs WHERE id IN ({ph})",
        tuple(ids)
    )
