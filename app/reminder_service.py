"""
reminder_service.py - 提醒事項業務邏輯
封裝資料庫操作，提供乾淨的 CRUD 介面給 line_handler 和 scheduler 使用
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import Reminder
from app.time_parser import calculate_next_recurring

logger = logging.getLogger(__name__)


# ── 建立 ────────────────────────────────────────────────────────────────────────

def create_reminder(
    db: Session,
    user_id: str,
    content: str,
    remind_at: datetime,
    is_recurring: bool = False,
    recurring_pattern: Optional[str] = None,
) -> Reminder:
    """
    在資料庫中新增一筆提醒事項
    remind_at 必須是 UTC datetime（帶時區資訊）
    """
    reminder = Reminder(
        user_id=user_id,
        content=content,
        remind_at=remind_at,
        is_recurring=is_recurring,
        recurring_pattern=recurring_pattern,
        is_done=False,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    logger.info("已建立提醒 #%d：%s（用戶：%s）", reminder.id, content, user_id)
    return reminder


# ── 查詢 ────────────────────────────────────────────────────────────────────────

def list_user_reminders(db: Session, user_id: str) -> List[Reminder]:
    """
    取得某用戶所有未完成的提醒，依提醒時間排序
    """
    return (
        db.query(Reminder)
        .filter(Reminder.user_id == user_id, Reminder.is_done == False)  # noqa: E712
        .order_by(Reminder.remind_at.asc())
        .all()
    )


def get_reminder_by_id(
    db: Session, reminder_id: int, user_id: str
) -> Optional[Reminder]:
    """
    取得指定 ID 的提醒（限定同一用戶，防止越權）
    """
    return (
        db.query(Reminder)
        .filter(Reminder.id == reminder_id, Reminder.user_id == user_id)
        .first()
    )


def get_due_reminders(db: Session) -> List[Reminder]:
    """
    取得所有「時間已到且尚未完成」的提醒
    排程器每分鐘呼叫一次
    """
    now_utc = datetime.now(timezone.utc)
    return (
        db.query(Reminder)
        .filter(Reminder.remind_at <= now_utc, Reminder.is_done == False)  # noqa: E712
        .all()
    )


# ── 更新 ────────────────────────────────────────────────────────────────────────

def complete_reminder(
    db: Session, reminder_id: int, user_id: str
) -> Optional[Reminder]:
    """
    將提醒標記為已完成
    返回 None 代表找不到該提醒
    """
    reminder = get_reminder_by_id(db, reminder_id, user_id)
    if reminder is None:
        return None

    reminder.is_done = True
    db.commit()
    db.refresh(reminder)
    logger.info("提醒 #%d 已標記完成（用戶：%s）", reminder_id, user_id)
    return reminder


def advance_recurring_reminder(db: Session, reminder: Reminder) -> Reminder:
    """
    重複提醒推播後，將 remind_at 推移到下一次時間
    例如每天提醒 → remind_at + 1 天
    """
    next_time = calculate_next_recurring(reminder.remind_at, reminder.recurring_pattern)
    reminder.remind_at = next_time
    db.commit()
    db.refresh(reminder)
    logger.info(
        "重複提醒 #%d 更新下次時間為 %s",
        reminder.id,
        next_time.isoformat(),
    )
    return reminder


def mark_sent(db: Session, reminder: Reminder) -> None:
    """
    非重複提醒推播後標記完成
    重複提醒則推移時間（由 advance_recurring_reminder 處理）
    """
    if reminder.is_recurring:
        advance_recurring_reminder(db, reminder)
    else:
        reminder.is_done = True
        db.commit()


# ── 刪除 ────────────────────────────────────────────────────────────────────────

def delete_reminder(
    db: Session, reminder_id: int, user_id: str
) -> bool:
    """
    刪除指定 ID 的提醒
    返回 True 代表成功，False 代表找不到
    """
    reminder = get_reminder_by_id(db, reminder_id, user_id)
    if reminder is None:
        return False

    db.delete(reminder)
    db.commit()
    logger.info("已刪除提醒 #%d（用戶：%s）", reminder_id, user_id)
    return True
