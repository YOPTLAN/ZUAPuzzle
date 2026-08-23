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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "puzzle.db")


@contextmanager
def conn_cm():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _backup_on_startup(keep: int = 10):
    """每次启动把数据库备份到 data/backup/，保留最近 keep 份。"""
    if not os.path.exists(DB_PATH):
        return
    bdir = os.path.join(DATA_DIR, "backup")
    os.makedirs(bdir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        shutil.copy2(DB_PATH, os.path.join(bdir, f"puzzle-{ts}.db"))
        olds = sorted(f for f in os.listdir(bdir)
                      if f.startswith("puzzle-") and f.endswith(".db"))
        for old in olds[:-keep]:
            os.remove(os.path.join(bdir, old))
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


def finished_rank(total: int):
    """已通关玩家，按通关时间升序（先通关的排前面）。"""
    with conn_cm() as conn:
        rows = conn.execute(
            """SELECT p.id, p.nickname, COUNT(s.level_id) AS solved,
                      MAX(s.solved_at) AS finished_at
               FROM players p JOIN solves s ON s.player_id = p.id
               GROUP BY p.id HAVING solved = ?
               ORDER BY finished_at ASC""",
            (total,),
        ).fetchall()
    return [dict(r) for r in rows]
