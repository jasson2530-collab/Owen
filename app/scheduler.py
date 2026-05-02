"""
scheduler.py - APScheduler 排程模組
每 60 秒掃描到期提醒，自動透過 LINE 推播通知
使用 SQLAlchemyJobStore 持久化排程，重啟後不遺失
"""

import logging
import os
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
)
from linebot.v3.messaging.exceptions import ApiException

from app.database import DATABASE_URL, get_session
from app.reminder_service import get_due_reminders, mark_sent
from app.time_parser import format_taipei_time, format_recurring_label

logger = logging.getLogger(__name__)

# 模組層級的排程器實例
_scheduler: BackgroundScheduler | None = None


def _build_jobstore() -> dict:
    """
    建立 Job Store：
    - PostgreSQL：使用 SQLAlchemy，排程持久化（重啟不遺失）
    - SQLite：使用記憶體，避免 SQLite 併發問題
    """
    if DATABASE_URL.startswith("sqlite"):
        logger.info("使用 MemoryJobStore（SQLite 模式）")
        return {"default": MemoryJobStore()}
    else:
        logger.info("使用 SQLAlchemyJobStore（PostgreSQL 模式）")
        return {"default": SQLAlchemyJobStore(url=DATABASE_URL)}


def _send_line_push(user_id: str, message: str) -> bool:
    """
    透過 LINE Messaging API 發送推播訊息
    返回 True 代表成功
    """
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token:
        logger.error("LINE_CHANNEL_ACCESS_TOKEN 未設定，無法推播")
        return False

    try:
        config = Configuration(access_token=token)
        with ApiClient(config) as client:
            api = MessagingApi(client)
            api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(type="text", text=message)],
                )
            )
        return True

    except ApiException as e:
        logger.error("LINE API 錯誤（%s）：%s", e.status, e.body)
        return False
    except Exception as e:  # noqa: BLE001
        logger.error("LINE 推播失敗（未知錯誤）：%s", e)
        return False


def _check_and_push() -> None:
    """
    排程核心任務：掃描到期提醒並推播
    每 60 秒執行一次
    """
    db = get_session()
    try:
        due_list = get_due_reminders(db)
        if not due_list:
            return

        logger.info("發現 %d 筆到期提醒，開始推播...", len(due_list))

        for reminder in due_list:
            # 組合推播訊息內容
            if reminder.is_recurring:
                label = format_recurring_label(reminder.recurring_pattern or "")
                msg = f"⏰ 定期提醒（{label}）\n\n{reminder.content}"
            else:
                msg = f"⏰ 提醒時間到了！\n\n{reminder.content}"

            # 發送 LINE 推播
            success = _send_line_push(reminder.user_id, msg)

            if success:
                # 推播成功：非重複→標記完成；重複→更新下次時間
                mark_sent(db, reminder)
                logger.info("提醒 #%d 推播成功", reminder.id)
            else:
                # 推播失敗：不標記完成，下次循環重試
                logger.warning("提醒 #%d 推播失敗，下次將重試", reminder.id)

    except Exception as e:  # noqa: BLE001
        logger.error("排程任務執行異常：%s", e)
    finally:
        db.close()


# ── 對外介面 ────────────────────────────────────────────────────────────────────

def init_scheduler() -> BackgroundScheduler:
    """
    建立並返回 BackgroundScheduler 實例（不啟動）
    由 main.py 在 startup 事件中呼叫
    """
    global _scheduler

    jobstores = _build_jobstore()
    executors = {"default": ThreadPoolExecutor(max_workers=4)}

    _scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        timezone="Asia/Taipei",
        job_defaults={
            "coalesce": True,          # 錯過的多次執行合併為一次
            "max_instances": 1,        # 同一任務最多同時執行 1 個實例
            "misfire_grace_time": 60,  # 允許最多延遲 60 秒執行
        },
    )
    return _scheduler


def start_scheduler() -> None:
    """啟動排程器並加入每分鐘掃描任務"""
    global _scheduler

    if _scheduler is None:
        init_scheduler()

    # 加入定期掃描任務（每 60 秒執行一次）
    _scheduler.add_job(
        _check_and_push,
        trigger="interval",
        seconds=60,
        id="check_and_push",
        replace_existing=True,         # 重啟後替換舊任務
        next_run_time=datetime.now(),  # 啟動後立即執行一次
    )

    _scheduler.start()
    logger.info("排程器已啟動，每 60 秒掃描一次到期提醒")


def stop_scheduler() -> None:
    """優雅地停止排程器"""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("排程器已停止")
