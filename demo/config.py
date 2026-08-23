# -*- coding: utf-8 -*-
"""ZUA-2026 Demo 统一配置模块
所有可调参数集中在此，修改后即时生效，无需改动业务代码。
"""
from pathlib import Path
from dataclasses import dataclass

BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Config:
    # 服务
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Cookie / Session
    COOKIE_NAME: str = "zua_session"
    COOKIE_MAX_AGE: int = 7 * 24 * 3600  # 7 天

    # 限流（内存简易限流，多 worker 需换 Redis）
    RATE_LIMIT_PER_MIN: int = 20
    RATE_LIMIT_COOLDOWN: int = 60
    WRONG_ANSWER_COOLDOWN: int = 3

    # 数据库与备份
    DATA_DIR: Path = BASE_DIR / "data"
    DB_NAME: str = "puzzle.db"
    BACKUP_DIR: Path = BASE_DIR / "data" / "backup"
    BACKUP_KEEP: int = 10
    BACKUP_PREFIX: str = "puzzle-"

    # 会话 / 玩家
    NICKNAME_MAX_LEN: int = 24
    TOKEN_HASH_CHARS: int = 8  # 取 token sha256 前 N 字符做确定性种子

    # 关卡元数据
    FINAL_LEVEL_ID: int = 15
    FRAGMENT_LEVEL_RANGE: tuple = (1, 14)  # 含首含尾

    # Python 环境与依赖安装（setup.ps1 运行时动态检测，不预设版本）
    PIP_INDEX_URL: str = "https://pypi.tuna.tsinghua.edu.cn/simple"


config = Config()