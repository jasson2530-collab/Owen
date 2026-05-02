"""
time_parser.py - 中文時間解析模組
將「明天早上9點」、「30分鐘後」等中文時間表達轉換為 datetime 物件
"""

import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import dateparser
import pytz

logger = logging.getLogger(__name__)

# 台北時區
TAIPEI_TZ = pytz.timezone("Asia/Taipei")

# ── 重複提醒模式對照表 ──────────────────────────────────────────────────────────
# key: 正規表達式  value: 儲存用的 pattern 代碼
RECURRING_PATTERNS = {
    r"每天|每日":                   "daily",
    r"每(週|周|星期)一":            "weekly_MON",
    r"每(週|周|星期)二":            "weekly_TUE",
    r"每(週|周|星期)三":            "weekly_WED",
    r"每(週|周|星期)四":            "weekly_THU",
    r"每(週|周|星期)五":            "weekly_FRI",
    r"每(週|周|星期)六":            "weekly_SAT",
    r"每(週|周|星期)(日|天)":       "weekly_SUN",
    r"每週|每周":                   "weekly",      # 未指定星期幾，以當天為主
}

# dateparser 設定
DATEPARSER_SETTINGS = {
    "PREFER_DATES_FROM": "future",          # 優先解析未來時間
    "RETURN_AS_TIMEZONE_AWARE": True,       # 返回有時區資訊的 datetime
    "TIMEZONE": "Asia/Taipei",              # 輸入時間視為台北時區
    "TO_TIMEZONE": "UTC",                   # 輸出轉為 UTC
    "DATE_ORDER": "YMD",                    # 年月日順序（台灣習慣）
    "PREFER_DAY_OF_MONTH": "first",
}

# ── 主要對外函式 ────────────────────────────────────────────────────────────────

def extract_reminder_parts(text: str) -> Optional[Tuple[str, str]]:
    """
    從完整訊息中拆分出「時間部分」和「提醒內容」

    範例：
      「明天早上9點提醒我叫貨」  → ('明天早上9點', '叫貨')
      「30分鐘後提醒我開會」     → ('30分鐘後', '開會')
      「每天早上8點提醒我巡倉」  → ('每天早上8點', '巡倉')

    返回 None 代表格式不符
    """
    match = re.search(r"^(.+?)提醒我[，,]?\s*(.+)$", text.strip())
    if match:
        time_str = match.group(1).strip()
        content  = match.group(2).strip()
        return time_str, content
    return None


def detect_recurring(time_str: str) -> Tuple[bool, Optional[str]]:
    """
    檢測時間字串是否包含重複模式

    返回 (is_recurring, pattern_code)
    例：detect_recurring("每天早上8點") → (True, "daily")
    """
    for pattern, code in RECURRING_PATTERNS.items():
        if re.search(pattern, time_str):
            return True, code
    return False, None


def parse_time(time_str: str) -> Optional[datetime]:
    """
    將時間字串解析為 UTC datetime

    先移除重複關鍵字（每天、每週一…），再丟給 dateparser 解析
    """
    # 移除重複關鍵字，只保留時間部分
    clean_str = re.sub(
        r"每(天|日|(週|周|星期)[一二三四五六日天]?)",
        "",
        time_str,
    ).strip()

    # 若移除後為空（例如只說「每天」），預設為明天早上 8 點
    if not clean_str:
        tomorrow_8am = (
            datetime.now(TAIPEI_TZ)
            .replace(hour=8, minute=0, second=0, microsecond=0)
            + timedelta(days=1)
        )
        return tomorrow_8am.astimezone(timezone.utc)

    # 嘗試繁體中文解析
    parsed = dateparser.parse(clean_str, languages=["zh-Hant", "zh"],
                               settings=DATEPARSER_SETTINGS)

    # 如果失敗，改用英文 fallback（處理數字格式如 "12/25 10:00"）
    if parsed is None:
        parsed = dateparser.parse(clean_str, settings=DATEPARSER_SETTINGS)

    if parsed is None:
        logger.warning("無法解析時間字串：%s（清理後：%s）", time_str, clean_str)

    return parsed


def calculate_next_recurring(remind_at: datetime, pattern: str) -> datetime:
    """
    計算重複提醒的下一次觸發時間

    pattern 格式：daily | weekly | weekly_MON … weekly_SUN
    """
    if pattern == "daily":
        return remind_at + timedelta(days=1)

    if pattern.startswith("weekly"):
        return remind_at + timedelta(weeks=1)

    # 預設每天
    return remind_at + timedelta(days=1)


def format_taipei_time(dt: datetime) -> str:
    """將 UTC datetime 轉為台北時間的易讀字串"""
    taipei_dt = dt.astimezone(TAIPEI_TZ)
    return taipei_dt.strftime("%m/%d (%a) %H:%M").replace(
        "Mon", "一").replace("Tue", "二").replace("Wed", "三").replace(
        "Thu", "四").replace("Fri", "五").replace("Sat", "六").replace(
        "Sun", "日")


def format_recurring_label(pattern: str) -> str:
    """將 pattern 代碼轉為人類可讀的中文"""
    mapping = {
        "daily":      "每天",
        "weekly":     "每週",
        "weekly_MON": "每週一",
        "weekly_TUE": "每週二",
        "weekly_WED": "每週三",
        "weekly_THU": "每週四",
        "weekly_FRI": "每週五",
        "weekly_SAT": "每週六",
        "weekly_SUN": "每週日",
    }
    return mapping.get(pattern, pattern)
