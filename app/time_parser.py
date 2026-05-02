"""
time_parser.py - 中文時間解析模組
優先使用手動規則解析，dateparser 作為 fallback
"""

import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import pytz

logger = logging.getLogger(__name__)

TAIPEI_TZ = pytz.timezone("Asia/Taipei")

# ── 中文數字對照表 ──────────────────────────────────────────────────────────────
CN_NUM = {
    "零": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    "十": 10, "十一": 11, "十二": 12,
}

# ── 重複提醒模式對照表 ──────────────────────────────────────────────────────────
RECURRING_PATTERNS = {
    r"每天|每日":                    "daily",
    r"每(週|周|星期)一":             "weekly_MON",
    r"每(週|周|星期)二":             "weekly_TUE",
    r"每(週|周|星期)三":             "weekly_WED",
    r"每(週|周|星期)四":             "weekly_THU",
    r"每(週|周|星期)五":             "weekly_FRI",
    r"每(週|周|星期)六":             "weekly_SAT",
    r"每(週|周|星期)(日|天)":        "weekly_SUN",
    r"每週|每周":                    "weekly",
}

DATEPARSER_SETTINGS = {
    "PREFER_DATES_FROM": "future",
    "RETURN_AS_TIMEZONE_AWARE": True,
    "TIMEZONE": "Asia/Taipei",
    "TO_TIMEZONE": "UTC",
    "DATE_ORDER": "YMD",
}


# ── 工具函式 ────────────────────────────────────────────────────────────────────

def _cn_to_int(s: str) -> Optional[int]:
    """將中文數字或阿拉伯數字字串轉為 int"""
    if s is None:
        return None
    s = s.strip()
    if s.isdigit():
        return int(s)
    # 處理「十X」格式
    if s == "十":
        return 10
    if s.startswith("十") and len(s) == 2:
        return 10 + CN_NUM.get(s[1], 0)
    return CN_NUM.get(s)


def _extract_hour_minute(time_str: str) -> Tuple[Optional[int], int]:
    """
    從時間字串中提取小時與分鐘
    處理「X點」「X點Y分」「X點半」等格式
    中文數字和阿拉伯數字都支援
    """
    # 匹配「X點Y分」或「X點半」或「X點」
    pattern = r"([零一二兩三四五六七八九十\d]+)\s*[點点時]([零一二兩三四五六七八九十\d]*分|半)?"
    m = re.search(pattern, time_str)
    if not m:
        return None, 0

    hour = _cn_to_int(m.group(1))
    if hour is None:
        return None, 0

    minute_str = m.group(2) or ""
    if minute_str == "半":
        minute = 30
    elif minute_str.endswith("分"):
        minute = _cn_to_int(minute_str[:-1]) or 0
    else:
        minute = 0

    return hour, minute


def _apply_period(hour: int, time_str: str) -> int:
    """根據上午/下午/晚上等關鍵字調整小時（12小時制 → 24小時制）"""
    if re.search(r"下午|午後|傍晚", time_str):
        if hour != 12:
            hour += 12
    elif re.search(r"晚上|夜晚|夜裡|凌晨後", time_str):
        if hour != 12:
            hour += 12
    elif re.search(r"早上|上午|早晨|清晨", time_str):
        if hour == 12:
            hour = 0
    elif re.search(r"中午", time_str):
        hour = 12
    elif re.search(r"凌晨", time_str):
        pass  # 凌晨不調整，1-5 點就是凌晨
    return hour


# ── 主要手動解析函式 ────────────────────────────────────────────────────────────

def _manual_parse(time_str: str) -> Optional[datetime]:
    """
    手動解析常見中文時間格式，不依賴 dateparser
    支援：
      - X分鐘後 / X小時後 / X天後
      - 今天/明天/後天 + 早上/下午 + X點Y分
      - 下午X點半 / 早上X點
      - MM/DD 或 M月D日 + 時間
    """
    now = datetime.now(TAIPEI_TZ)

    # ── 相對時間 ──────────────────────────────────────────────────────────────
    m = re.search(r"(\d+)\s*分鐘?後", time_str)
    if m:
        return (now + timedelta(minutes=int(m.group(1)))).astimezone(timezone.utc)

    m = re.search(r"(\d+)\s*小時後", time_str)
    if m:
        return (now + timedelta(hours=int(m.group(1)))).astimezone(timezone.utc)

    m = re.search(r"(\d+)\s*天後", time_str)
    if m:
        return (now + timedelta(days=int(m.group(1)))).astimezone(timezone.utc)

    # ── 日期偏移（今天/明天/後天） ─────────────────────────────────────────────
    day_offset = 0
    if re.search(r"後天|後日", time_str):
        day_offset = 2
    elif re.search(r"明天|明日", time_str):
        day_offset = 1
    elif re.search(r"今天|今日", time_str):
        day_offset = 0

    base_date = now + timedelta(days=day_offset)

    # ── 絕對日期（MM/DD 或 M月D日） ──────────────────────────────────────────
    m = re.search(r"(\d{1,2})[/月](\d{1,2})日?", time_str)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        year = now.year
        try:
            base_date = now.replace(year=year, month=month, day=day)
            if base_date < now:
                base_date = base_date.replace(year=year + 1)
            day_offset = 99  # 標記已指定日期
        except ValueError:
            pass

    # ── 提取時間 ──────────────────────────────────────────────────────────────
    hour, minute = _extract_hour_minute(time_str)
    if hour is None:
        return None

    hour = _apply_period(hour, time_str)

    # 合理範圍檢查
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    target = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # 未指定日期且時間已過 → 推到明天
    if day_offset == 0 and target <= now:
        target += timedelta(days=1)

    return target.astimezone(timezone.utc)


# ── 對外介面 ────────────────────────────────────────────────────────────────────

def extract_reminder_parts(text: str) -> Optional[Tuple[str, str]]:
    """
    從完整訊息中拆分「時間部分」和「提醒內容」
    例：「明天早上9點提醒我叫貨」→ ('明天早上9點', '叫貨')
    """
    match = re.search(r"^(.+?)提醒我[，,]?\s*(.+)$", text.strip())
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None


def detect_recurring(time_str: str) -> Tuple[bool, Optional[str]]:
    """檢測重複模式，返回 (is_recurring, pattern_code)"""
    for pattern, code in RECURRING_PATTERNS.items():
        if re.search(pattern, time_str):
            return True, code
    return False, None


def parse_time(time_str: str) -> Optional[datetime]:
    """
    將時間字串解析為 UTC datetime
    流程：手動解析 → dateparser fallback
    """
    # 移除重複關鍵字
    clean_str = re.sub(
        r"每(天|日|(週|周|星期)[一二三四五六日天]?)",
        "",
        time_str,
    ).strip()

    # 若移除後為空 → 預設明天早上 8 點
    if not clean_str:
        return (
            datetime.now(TAIPEI_TZ)
            .replace(hour=8, minute=0, second=0, microsecond=0)
            + timedelta(days=1)
        ).astimezone(timezone.utc)

    # 優先：手動規則解析
    result = _manual_parse(clean_str)
    if result:
        logger.info("手動解析成功：%s → %s", clean_str, result)
        return result

    # Fallback：dateparser（需要安裝 dateparser 套件）
    try:
        import dateparser
        parsed = dateparser.parse(
            clean_str,
            languages=["zh-Hant", "zh"],
            settings=DATEPARSER_SETTINGS,
        )
        if parsed is None:
            parsed = dateparser.parse(clean_str, settings=DATEPARSER_SETTINGS)
        if parsed:
            logger.info("dateparser 解析成功：%s → %s", clean_str, parsed)
            return parsed
    except Exception as e:
        logger.warning("dateparser 失敗：%s", e)

    logger.warning("無法解析時間字串：%s", time_str)
    return None


def calculate_next_recurring(remind_at: datetime, pattern: str) -> datetime:
    """計算重複提醒的下一次觸發時間"""
    if pattern == "daily":
        return remind_at + timedelta(days=1)
    if pattern.startswith("weekly"):
        return remind_at + timedelta(weeks=1)
    return remind_at + timedelta(days=1)


def format_taipei_time(dt: datetime) -> str:
    """UTC datetime → 台北時間易讀字串"""
    taipei_dt = dt.astimezone(TAIPEI_TZ)
    return taipei_dt.strftime("%m/%d (%a) %H:%M").replace(
        "Mon", "一").replace("Tue", "二").replace("Wed", "三").replace(
        "Thu", "四").replace("Fri", "五").replace("Sat", "六").replace(
        "Sun", "日")


def format_recurring_label(pattern: str) -> str:
    """pattern 代碼 → 中文說明"""
    mapping = {
        "daily": "每天", "weekly": "每週",
        "weekly_MON": "每週一", "weekly_TUE": "每週二",
        "weekly_WED": "每週三", "weekly_THU": "每週四",
        "weekly_FRI": "每週五", "weekly_SAT": "每週六",
        "weekly_SUN": "每週日",
    }
    return mapping.get(pattern, pattern)
