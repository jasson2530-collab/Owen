"""
database.py - 資料庫連線與初始化
支援本地 SQLite（開發測試）和雲端 PostgreSQL（正式部署）
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models import Base

logger = logging.getLogger(__name__)


def _build_database_url() -> str:
    """
    讀取 DATABASE_URL 環境變數並修正格式
    Render/Railway 的 PostgreSQL URL 以 postgres:// 開頭，
    SQLAlchemy 2.x 需要 postgresql://
    """
    url = os.getenv("DATABASE_URL", "sqlite:///./reminders.db")

    # 修正舊版 PostgreSQL URL 前綴
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
        logger.info("已將 postgres:// 轉換為 postgresql://")

    return url


DATABASE_URL = _build_database_url()

# 根據資料庫類型設定不同的連線參數
if DATABASE_URL.startswith("sqlite"):
    # SQLite 需要 check_same_thread=False 允許多執行緒存取
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    # PostgreSQL：設定連線池大小（雲端部署用）
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,   # 每次取出連線前先 ping，避免斷線問題
        echo=False,
    )

# 建立 Session 工廠
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """建立所有資料表（若不存在才建立）"""
    Base.metadata.create_all(bind=engine)
    logger.info("資料庫初始化完成，DATABASE_URL 類型：%s",
                "SQLite" if DATABASE_URL.startswith("sqlite") else "PostgreSQL")


def get_db() -> Session:
    """
    取得資料庫 Session（FastAPI 依賴注入用）
    使用 with 語法自動關閉：
        with get_db() as db:
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session() -> Session:
    """直接取得 Session（非 FastAPI 依賴注入場合，如排程器）"""
    return SessionLocal()
