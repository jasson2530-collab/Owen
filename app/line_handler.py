"""
line_handler.py - LINE 訊息處理模組
解析使用者傳來的訊息，執行對應的提醒操作並回覆結果
"""

import logging
import re
from typing import Optional

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.messaging.exceptions import ApiException
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from app.database import get_session
from app.reminder_service import (
    create_reminder,
    list_user_reminders,
    delete_reminder,
    complete_reminder,
)
from app.time_parser import (
    extract_reminder_parts,
    detect_recurring,
    parse_time,
    format_taipei_time,
    format_recurring_label,
)

logger = logging.getLogger(__name__)

# ── 說明訊息 ────────────────────────────────────────────────────────────────────

HELP_TEXT = """📋 提醒機器人使用說明

【新增提醒】
直接輸入：時間 + 提醒我 + 事項

範例：
• 明天早上9點提醒我叫貨
• 30分鐘後提醒我開會
• 下午3點半提醒我吃藥
• 每天早上8點提醒我巡倉
• 每週五下午5點提醒我送貨單
• 12/25 早上10點提醒我開箱

【查詢提醒】
輸入：列表 或 查詢

【刪除提醒】
輸入：刪除 [編號]
例：刪除 3

【完成提醒】
輸入：完成 [編號]
例：完成 2

【說明】
輸入：help 或 說明"""


# ── 回覆函式 ────────────────────────────────────────────────────────────────────

def _reply(reply_token: str, text: str, line_token: str) -> None:
    """
    使用 Reply API 回覆訊息（免費，不消耗推播配額）
    """
    try:
        config = Configuration(access_token=line_token)
        with ApiClient(config) as client:
            api = MessagingApi(client)
            api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(type="text", text=text)],
                )
            )
    except ApiException as e:
        logger.error("回覆訊息失敗（LINE API %s）：%s", e.status, e.body)
    except Exception as e:  # noqa: BLE001
        logger.error("回覆訊息時發生未知錯誤：%s", e)


# ── 指令處理函式 ────────────────────────────────────────────────────────────────

def _handle_list(user_id: str) -> str:
    """處理「列表/查詢」指令，回傳格式化的提醒清單"""
    db = get_session()
    try:
        reminders = list_user_reminders(db, user_id)
    finally:
        db.close()

    if not reminders:
        return "📭 目前沒有待辦的提醒事項\n\n輸入「help」查看使用說明"

    lines = ["📋 你的提醒清單：\n"]
    for r in reminders:
        time_str = format_taipei_time(r.remind_at)

        if r.is_recurring:
            label = format_recurring_label(r.recurring_pattern or "")
            lines.append(f"#{r.id} 🔁{label} {time_str}\n   {r.content}")
        else:
            lines.append(f"#{r.id} ⏰ {time_str}\n   {r.content}")

    lines.append("\n輸入「刪除 [編號]」可刪除提醒")
    return "\n".join(lines)


def _handle_delete(user_id: str, reminder_id: int) -> str:
    """處理「刪除 N」指令"""
    db = get_session()
    try:
        success = delete_reminder(db, reminder_id, user_id)
    finally:
        db.close()

    if success:
        return f"🗑️ 提醒 #{reminder_id} 已刪除"
    return f"❌ 找不到提醒 #{reminder_id}，請輸入「列表」確認編號"


def _handle_complete(user_id: str, reminder_id: int) -> str:
    """處理「完成 N」指令"""
    db = get_session()
    try:
        reminder = complete_reminder(db, reminder_id, user_id)
    finally:
        db.close()

    if reminder:
        return f"✅ 提醒 #{reminder_id}「{reminder.content}」已標記完成！"
    return f"❌ 找不到提醒 #{reminder_id}，請輸入「列表」確認編號"


def _handle_add(user_id: str, text: str) -> str:
    """
    處理新增提醒訊息
    格式：「時間提醒我事項」
    """
    # 拆分時間與內容
    parts = extract_reminder_parts(text)
    if parts is None:
        return (
            "❓ 格式不太對喔！\n\n"
            "請這樣輸入：\n"
            "明天早上9點提醒我叫貨\n\n"
            "輸入「help」查看更多範例"
        )

    time_str, content = parts

    # 解析時間
    remind_at = parse_time(time_str)
    if remind_at is None:
        return (
            f"⚠️ 無法解析時間「{time_str}」\n\n"
            "支援格式範例：\n"
            "• 明天早上9點\n"
            "• 30分鐘後\n"
            "• 下午3點半\n"
            "• 12/25 早上10點"
        )

    # 檢測重複模式
    is_recurring, pattern = detect_recurring(time_str)

    # 存入資料庫
    db = get_session()
    try:
        reminder = create_reminder(
            db=db,
            user_id=user_id,
            content=content,
            remind_at=remind_at,
            is_recurring=is_recurring,
            recurring_pattern=pattern,
        )
    finally:
        db.close()

    # 組合成功回覆
    time_display = format_taipei_time(remind_at)
    if is_recurring:
        label = format_recurring_label(pattern or "")
        return (
            f"✅ 已設定定期提醒！\n\n"
            f"📌 事項：{content}\n"
            f"🔁 頻率：{label}\n"
            f"⏰ 下次提醒：{time_display}\n\n"
            f"提醒編號：#{reminder.id}"
        )
    else:
        return (
            f"✅ 提醒已設定！\n\n"
            f"📌 事項：{content}\n"
            f"⏰ 提醒時間：{time_display}\n\n"
            f"提醒編號：#{reminder.id}"
        )


# ── 主要入口 ────────────────────────────────────────────────────────────────────

def handle_text_message(event: MessageEvent, line_token: str) -> None:
    """
    LINE 文字訊息的主要處理函式
    根據訊息內容路由到對應的處理邏輯
    """
    user_id = event.source.user_id
    text = event.message.text.strip()
    reply_token = event.reply_token

    logger.info("收到訊息 user=%s text=%r", user_id, text)

    # ── 查詢提醒 ──
    if re.match(r"^(列表|查詢|查看|我的提醒)$", text):
        reply = _handle_list(user_id)

    # ── 刪除提醒：「刪除 3」 ──
    elif m := re.match(r"^刪除\s*(\d+)$", text):
        reply = _handle_delete(user_id, int(m.group(1)))

    # ── 完成提醒：「完成 2」 ──
    elif m := re.match(r"^完成\s*(\d+)$", text):
        reply = _handle_complete(user_id, int(m.group(1)))

    # ── 說明 ──
    elif re.match(r"^(help|說明|使用說明|指令)$", text, re.IGNORECASE):
        reply = HELP_TEXT

    # ── 新增提醒：含「提醒我」關鍵字 ──
    elif "提醒我" in text:
        reply = _handle_add(user_id, text)

    # ── 其他：顯示說明 ──
    else:
        reply = (
            "👋 你好！我是提醒機器人\n\n"
            "輸入「help」或「說明」查看使用方式\n\n"
            "快速範例：\n"
            "明天早上9點提醒我開會"
        )

    _reply(reply_token, reply, line_token)
