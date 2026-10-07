"""SQLite 저장소 (aiosqlite)"""
from __future__ import annotations

import json
import os
from typing import Any, Iterable, Optional, Sequence

import aiosqlite

import config

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS members (
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    display    TEXT,
    job        TEXT,
    level      INTEGER DEFAULT 1,
    rank       TEXT DEFAULT '길드원',
    rank_order INTEGER DEFAULT 99,
    note       TEXT,
    active     INTEGER DEFAULT 1,
    joined_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS warnings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id     INTEGER NOT NULL,
    user_id      INTEGER NOT NULL,
    reason       TEXT,
    moderator_id INTEGER,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_warn ON warnings(guild_id, user_id);

CREATE TABLE IF NOT EXISTS votes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    channel_id  INTEGER,
    message_id  INTEGER,
    title       TEXT NOT NULL,
    description TEXT,
    options     TEXT NOT NULL,
    anonymous   INTEGER DEFAULT 0,
    multi       INTEGER DEFAULT 0,
    closes_at   TEXT,
    closed      INTEGER DEFAULT 0,
    creator_id  INTEGER,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ballots (
    vote_id      INTEGER NOT NULL,
    user_id      INTEGER NOT NULL,
    option_index INTEGER NOT NULL,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (vote_id, user_id, option_index)
);

CREATE TABLE IF NOT EXISTS distributions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    item       TEXT NOT NULL,
    boss       TEXT,
    mode       TEXT DEFAULT '입찰',
    min_bid    INTEGER DEFAULT 0,
    status     TEXT DEFAULT 'open',
    winner_id  INTEGER,
    price      INTEGER,
    creator_id INTEGER,
    channel_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    closed_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_dist ON distributions(guild_id, status);

CREATE TABLE IF NOT EXISTS entries (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    dist_id    INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    kind       TEXT NOT NULL,
    amount     INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_entries ON entries(dist_id, user_id);

CREATE TABLE IF NOT EXISTS history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id   INTEGER NOT NULL,
    item       TEXT NOT NULL,
    boss       TEXT,
    mode       TEXT,
    winner_id  INTEGER,
    price      INTEGER,
    dist_id    INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_history ON history(guild_id, created_at DESC);

CREATE TABLE IF NOT EXISTS points (
    guild_id INTEGER NOT NULL,
    user_id  INTEGER NOT NULL,
    points   INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS settings (
    guild_id INTEGER NOT NULL,
    key      TEXT NOT NULL,
    value    TEXT,
    PRIMARY KEY (guild_id, key)
);
"""

_conn: Optional[aiosqlite.Connection] = None


# ---------------------------------------------------------------- 저수준
async def connect() -> aiosqlite.Connection:
    global _conn
    if _conn is not None:
        return _conn
    path = config.DB_PATH
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    _conn = await aiosqlite.connect(path)
    _conn.row_factory = aiosqlite.Row
    await _conn.executescript(SCHEMA)
    await _conn.commit()
    return _conn


async def close() -> None:
    global _conn
    if _conn is not None:
        await _conn.close()
        _conn = None


async def execute(sql: str, params: Sequence[Any] = ()) -> int:
    conn = await connect()
    cur = await conn.execute(sql, tuple(params))
    await conn.commit()
    rid = cur.lastrowid
    await cur.close()
    return rid


async def executemany(sql: str, seq: Iterable[Sequence[Any]]) -> None:
    conn = await connect()
    await conn.executemany(sql, [tuple(x) for x in seq])
    await conn.commit()


async def fetchone(sql: str, params: Sequence[Any] = ()):
    conn = await connect()
    cur = await conn.execute(sql, tuple(params))
    row = await cur.fetchone()
    await cur.close()
    return row


async def fetchall(sql: str, params: Sequence[Any] = ()):
    conn = await connect()
    cur = await conn.execute(sql, tuple(params))
    rows = await cur.fetchall()
    await cur.close()
    return rows


async def scalar(sql: str, params: Sequence[Any] = (), default=0):
    row = await fetchone(sql, params)
    if row is None:
        return default
    value = row[0]
    return default if value is None else value


# ---------------------------------------------------------------- 설정
async def get_setting(guild_id: int, key: str, default=None):
    row = await fetchone("SELECT value FROM settings WHERE guild_id=? AND key=?", (guild_id, key))
    return row["value"] if row is not None else default


async def set_setting(guild_id: int, key: str, value) -> None:
    await execute(
        "INSERT INTO settings (guild_id, key, value) VALUES (?,?,?) "
        "ON CONFLICT(guild_id, key) DO UPDATE SET value=excluded.value",
        (guild_id, key, "" if value is None else str(value)),
    )


async def all_settings(guild_id: int) -> dict:
    rows = await fetchall("SELECT key, value FROM settings WHERE guild_id=?", (guild_id,))
    return {r["key"]: r["value"] for r in rows}


# ---------------------------------------------------------------- 길드원
def _rank_order(rank: str) -> int:
    try:
        return config.DEFAULT_RANKS.index(rank)
    except ValueError:
        return 99


async def upsert_member(guild_id: int, user_id: int, display: str, job: str = None,
                        level: int = None, rank: str = None, note: str = None) -> None:
    row = await fetchone("SELECT * FROM members WHERE guild_id=? AND user_id=?", (guild_id, user_id))
    if row is None:
        await execute(
            "INSERT INTO members (guild_id, user_id, display, job, level, rank, rank_order, note, active) "
            "VALUES (?,?,?,?,?,?,?,?,1)",
            (guild_id, user_id, display, job, level or 1, rank or "길드원", _rank_order(rank or "길드원"), note),
        )
        return

    fields, params = [], []
    if display is not None:
        fields.append("display=?")
        params.append(display)
    if job is not None:
        fields.append("job=?")
        params.append(job)
    if level is not None:
        fields.append("level=?")
        params.append(level)
    if rank is not None:
        fields.append("rank=?")
        params.append(rank)
        fields.append("rank_order=?")
        params.append(_rank_order(rank))
    if note is not None:
        fields.append("note=?")
        params.append(note)
    fields.append("active=1")
    fields.append("updated_at=CURRENT_TIMESTAMP")
    params.extend([guild_id, user_id])
    await execute(f"UPDATE members SET {', '.join(fields)} WHERE guild_id=? AND user_id=?", params)


async def get_member(guild_id: int, user_id: int):
    return await fetchone("SELECT * FROM members WHERE guild_id=? AND user_id=?", (guild_id, user_id))


async def delete_member(guild_id: int, user_id: int) -> None:
    await execute("DELETE FROM members WHERE guild_id=? AND user_id=?", (guild_id, user_id))


async def set_rank(guild_id: int, user_id: int, rank: str) -> None:
    await execute(
        "UPDATE members SET rank=?, rank_order=?, updated_at=CURRENT_TIMESTAMP WHERE guild_id=? AND user_id=?",
        (rank, _rank_order(rank), guild_id, user_id),
    )


async def list_members(guild_id: int, include_inactive: bool = False):
    sql = "SELECT * FROM members WHERE guild_id=?"
    if not include_inactive:
        sql += " AND active=1"
    sql += " ORDER BY rank_order ASC, level DESC, display COLLATE NOCASE ASC"
    return await fetchall(sql, (guild_id,))


async def count_members(guild_id: int) -> int:
    return await scalar("SELECT COUNT(*) FROM members WHERE guild_id=? AND active=1", (guild_id,))


async def jobs_in_use(guild_id: int):
    rows = await fetchall(
        "SELECT DISTINCT job FROM members WHERE guild_id=? AND job IS NOT NULL AND job<>'' ORDER BY job",
        (guild_id,),
    )
    return [r["job"] for r in rows]


# ---------------------------------------------------------------- 경고
async def add_warning(guild_id: int, user_id: int, reason: str, moderator_id: int) -> int:
    await execute(
        "INSERT INTO warnings (guild_id, user_id, reason, moderator_id) VALUES (?,?,?,?)",
        (guild_id, user_id, reason, moderator_id),
    )
    return await count_warnings(guild_id, user_id)


async def count_warnings(guild_id: int, user_id: int) -> int:
    return await scalar("SELECT COUNT(*) FROM warnings WHERE guild_id=? AND user_id=?", (guild_id, user_id))


async def list_warnings(guild_id: int, user_id: int):
    return await fetchall(
        "SELECT * FROM warnings WHERE guild_id=? AND user_id=? ORDER BY id DESC", (guild_id, user_id)
    )


async def clear_warnings(guild_id: int, user_id: int) -> int:
    n = await count_warnings(guild_id, user_id)
    await execute("DELETE FROM warnings WHERE guild_id=? AND user_id=?", (guild_id, user_id))
    return n


# ---------------------------------------------------------------- 투표
async def create_vote(guild_id: int, title: str, description: str, options, anonymous: bool,
                      multi: bool, closes_at: str, creator_id: int) -> int:
    return await execute(
        "INSERT INTO votes (guild_id, title, description, options, anonymous, multi, closes_at, creator_id) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (guild_id, title, description, json.dumps(options, ensure_ascii=False),
         1 if anonymous else 0, 1 if multi else 0, closes_at, creator_id),
    )


async def set_vote_message(vote_id: int, channel_id: int, message_id: int) -> None:
    await execute("UPDATE votes SET channel_id=?, message_id=? WHERE id=?", (channel_id, message_id, vote_id))


async def get_vote(vote_id: int):
    return await fetchone("SELECT * FROM votes WHERE id=?", (vote_id,))


async def list_open_votes(guild_id: int = None):
    if guild_id is None:
        return await fetchall("SELECT * FROM votes WHERE closed=0")
    return await fetchall("SELECT * FROM votes WHERE guild_id=? AND closed=0", (guild_id,))


async def close_vote(vote_id: int) -> None:
    await execute("UPDATE votes SET closed=1 WHERE id=?", (vote_id,))


async def add_ballot(vote_id: int, user_id: int, index: int) -> None:
    await execute(
        "INSERT OR IGNORE INTO ballots (vote_id, user_id, option_index) VALUES (?,?,?)",
        (vote_id, user_id, index),
    )


async def remove_ballot(vote_id: int, user_id: int, index: int) -> None:
    await execute(
        "DELETE FROM ballots WHERE vote_id=? AND user_id=? AND option_index=?", (vote_id, user_id, index)
    )


async def get_ballots(vote_id: int):
    return await fetchall("SELECT * FROM ballots WHERE vote_id=?", (vote_id,))


async def get_user_ballots(vote_id: int, user_id: int):
    rows = await fetchall(
        "SELECT option_index FROM ballots WHERE vote_id=? AND user_id=?", (vote_id, user_id)
    )
    return [r["option_index"] for r in rows]


async def clear_user_ballots(vote_id: int, user_id: int) -> None:
    await execute("DELETE FROM ballots WHERE vote_id=? AND user_id=?", (vote_id, user_id))


# ---------------------------------------------------------------- 분배
async def get_active_distribution(guild_id: int):
    return await fetchone(
        "SELECT * FROM distributions WHERE guild_id=? AND status='open' ORDER BY id DESC LIMIT 1", (guild_id,)
    )


async def start_distribution(guild_id: int, item: str, boss: str, mode: str, min_bid: int,
                             creator_id: int, channel_id: int) -> int:
    await execute(
        "UPDATE distributions SET status='cancelled', closed_at=CURRENT_TIMESTAMP "
        "WHERE guild_id=? AND status='open'",
        (guild_id,),
    )
    return await execute(
        "INSERT INTO distributions (guild_id, item, boss, mode, min_bid, creator_id, channel_id) "
        "VALUES (?,?,?,?,?,?,?)",
        (guild_id, item, boss, mode, min_bid, creator_id, channel_id),
    )


async def add_entry(dist_id: int, user_id: int, kind: str, amount: int = None) -> None:
    await execute("INSERT INTO entries (dist_id, user_id, kind, amount) VALUES (?,?,?,?)",
                  (dist_id, user_id, kind, amount))


async def get_entries(dist_id: int):
    return await fetchall("SELECT * FROM entries WHERE dist_id=? ORDER BY id ASC", (dist_id,))


async def best_bid(dist_id: int, user_id: int):
    return await fetchone(
        "SELECT MAX(amount) AS amount FROM entries WHERE dist_id=? AND user_id=? AND kind='입찰'",
        (dist_id, user_id),
    )


async def finish_distribution(dist_id: int, winner_id: int, price: int) -> None:
    await execute(
        "UPDATE distributions SET status='closed', winner_id=?, price=?, closed_at=CURRENT_TIMESTAMP "
        "WHERE id=?",
        (winner_id, price, dist_id),
    )
    row = await fetchone("SELECT * FROM distributions WHERE id=?", (dist_id,))
    if row is not None:
        await execute(
            "INSERT INTO history (guild_id, item, boss, mode, winner_id, price, dist_id) VALUES (?,?,?,?,?,?,?)",
            (row["guild_id"], row["item"], row["boss"], row["mode"], winner_id, price, dist_id),
        )


async def cancel_distribution(dist_id: int) -> None:
    await execute(
        "UPDATE distributions SET status='cancelled', closed_at=CURRENT_TIMESTAMP WHERE id=?", (dist_id,)
    )


async def loot_history(guild_id: int, limit: int = 10):
    return await fetchall(
        "SELECT * FROM history WHERE guild_id=? ORDER BY id DESC LIMIT ?", (guild_id, limit)
    )


async def loot_history_for(guild_id: int, user_id: int, limit: int = 10):
    return await fetchall(
        "SELECT * FROM history WHERE guild_id=? AND winner_id=? ORDER BY id DESC LIMIT ?",
        (guild_id, user_id, limit),
    )


async def loot_count(guild_id: int) -> int:
    return await scalar("SELECT COUNT(*) FROM history WHERE guild_id=?", (guild_id,))


# ---------------------------------------------------------------- 포인트(DKP)
async def add_points(guild_id: int, user_id: int, delta: int) -> int:
    await execute(
        "INSERT INTO points (guild_id, user_id, points) VALUES (?,?,?) "
        "ON CONFLICT(guild_id, user_id) DO UPDATE SET points = points + excluded.points",
        (guild_id, user_id, delta),
    )
    return await get_points(guild_id, user_id)


async def get_points(guild_id: int, user_id: int) -> int:
    return await scalar("SELECT points FROM points WHERE guild_id=? AND user_id=?", (guild_id, user_id), 0)


async def top_points(guild_id: int, limit: int = 10):
    return await fetchall(
        "SELECT * FROM points WHERE guild_id=? ORDER BY points DESC LIMIT ?", (guild_id, limit)
    )
