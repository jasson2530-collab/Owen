"""
models.py - SQLAlchemy 資料模型定義
定義提醒事項的資料表結構
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Reminder(Base):
    """提醒事項資料表"""
    __tablename__ = "reminders"

    # 主鍵（自動遞增）
    id = Column(Integer, primary_key=True, autoincrement=True)

    # LINE 使用者 ID（格式：U + 32碼英數字）
    user_id = Column(String(64), nullable=False, index=True)

    # 提醒內容（例如：「叫貨」、「開會」）
    content = Column(Text, nullable=False)

    # 提醒時間（統一儲存 UTC，顯示時轉為台北時間）
    remind_at = Column(DateTime(timezone=True), nullable=False)

    # 是否為重複提醒（每天/每週）
    is_recurring = Column(Boolean, default=False, nullable=False)

    # 重複規則（例如：daily、weekly_MON、weekly_FRI）
    recurring_pattern = Column(String(32), nullable=True)

    # 是否已完成（非重複提醒推播後設為 True）
    is_done = Column(Boolean, default=False, nullable=False)

    # 建立時間（UTC）
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<Reminder id={self.id} user={self.user_id} "
            f"content='{self.content}' remind_at={self.remind_at}>"
        )
