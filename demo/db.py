# -*- coding: utf-8 -*-
"""SQLite 存储：players / solves 两张表。
数据文件在 demo/data/puzzle.db（首次启动自动创建）。
"""
import os
import shutil
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime

import config

cfg = config.config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = cfg.DATA_DIR
DB_PATH = DATA_DIR / cfg.DB_NAME
BACKUP_DIR = cfg.BACKUP_DIR
BACKUP_PREFIX = cfg.BACKUP_PREFIX
BACKUP_KEEP = cfg.BACKUP_KEEP


@contextmanager
def conn_cm():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _backup_on_startup():
    """每次启动把数据库备份到 data/backup/，保留最近 keep 份。"""
    if not os.path.exists(DB_PATH):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        shutil.copy2(DB_PATH, os.path.join(BACKUP_DIR, f"{BACKUP_PREFIX}{ts}.db"))
        olds = sorted(f for f in os.listdir(BACKUP_DIR)
                      if f.startswith(BACKUP_PREFIX) and f.endswith(".db"))
        for old in olds[:-BACKUP_KEEP]:
            os.remove(os.path.join(BACKUP_DIR, old))
    except OSError:
        pass  # 备份失败不阻塞启动


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    _backup_on_startup()
    with conn_cm() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS players(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                nickname TEXT DEFAULT '',
                created_at REAL NOT NULL)"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS solves(
                player_id INTEGER NOT NULL,
                level_id INTEGER NOT NULL,
                solved_at REAL NOT NULL,
                PRIMARY KEY(player_id, level_id))"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS level_views(
                player_id INTEGER NOT NULL,
                level_id INTEGER NOT NULL,
                viewed_at REAL NOT NULL,
                PRIMARY KEY(player_id, level_id))"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS hints_revealed(
                player_id INTEGER NOT NULL,
                level_id INTEGER NOT NULL,
                hint_index INTEGER NOT NULL,
                revealed_at REAL NOT NULL,
                PRIMARY KEY(player_id, level_id, hint_index))"""
        )


def mark_level_view(player_id: int, level_id: int):
    """记录首次打开关卡的时间（用于提示解锁计时），重复打开不覆盖。"""
    with conn_cm() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO level_views(player_id, level_id, viewed_at) VALUES(?,?,?)",
            (player_id, level_id, time.time()),
        )


def first_viewed_at(player_id: int, level_id: int):
    with conn_cm() as conn:
        row = conn.execute(
            "SELECT viewed_at FROM level_views WHERE player_id=? AND level_id=?",
            (player_id, level_id),
        ).fetchone()
    return row["viewed_at"] if row else None


def revealed_hint_indices(player_id: int, level_id: int):
    """已解锁的提示下标（升序）。持久化存储，重启不丢。"""
    with conn_cm() as conn:
        rows = conn.execute(
            "SELECT hint_index FROM hints_revealed WHERE player_id=? AND level_id=? ORDER BY hint_index",
            (player_id, level_id),
        ).fetchall()
    return [r["hint_index"] for r in rows]


def reveal_hint(player_id: int, level_id: int, hint_index: int):
    with conn_cm() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO hints_revealed(player_id, level_id, hint_index, revealed_at) VALUES(?,?,?,?)",
            (player_id, level_id, hint_index, time.time()),
        )


def get_or_create_player(token: str):
    now = time.time()
    with conn_cm() as conn:
        row = conn.execute("SELECT * FROM players WHERE token=?", (token,)).fetchone()
        if row:
            return dict(row)
        cur = conn.execute(
            "INSERT INTO players(token, created_at) VALUES(?,?)", (token, now)
        )
        return {"id": cur.lastrowid, "token": token, "nickname": "", "created_at": now}


def solved_set(player_id: int) -> set:
    with conn_cm() as conn:
        rows = conn.execute(
            "SELECT level_id FROM solves WHERE player_id=?", (player_id,)
        ).fetchall()
    return {r["level_id"] for r in rows}


def record_solve(player_id: int, level_id: int):
    with conn_cm() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO solves(player_id, level_id, solved_at) VALUES(?,?,?)",
            (player_id, level_id, time.time()),
        )


def set_nickname(player_id: int, nickname: str):
    with conn_cm() as conn:
        conn.execute("UPDATE players SET nickname=? WHERE id=?", (nickname, player_id))


def finished_rank(total: int, level_ids):
    """已通关玩家（只统计传入的常规关 id 集合，附加关不参与），
    按通关时间升序（先通关的排前面）。"""
    marks = ",".join("?" * len(level_ids))
    with conn_cm() as conn:
        rows = conn.execute(
            f"""SELECT p.id, p.nickname, COUNT(s.level_id) AS solved,
                      MAX(s.solved_at) AS finished_at
               FROM players p JOIN solves s ON s.player_id = p.id
                                AND s.level_id IN ({marks})
               GROUP BY p.id HAVING solved = ?
               ORDER BY finished_at ASC""",
            (*level_ids, total),
        ).fetchall()
    return [dict(r) for r in rows]