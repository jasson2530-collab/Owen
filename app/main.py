"""
main.py - FastAPI 主程式
- POST /callback  LINE Webhook（驗證簽章 + 處理訊息）
- GET  /health    健康檢查（Render/Railway 存活探針）
- GET  /          首頁狀態
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# ── 初始化環境變數（一定要在其他 app 模組前執行）
load_dotenv()

from app.database import init_db
from app.line_handler import handle_text_message
from app.scheduler import start_scheduler, stop_scheduler

# ── Logging 設定 ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── 讀取 LINE 設定 ───────────────────────────────────────────────────────────────
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    logger.warning(
        "LINE_CHANNEL_ACCESS_TOKEN 或 LINE_CHANNEL_SECRET 未設定！"
        "請確認 .env 檔案或雲端環境變數。"
    )

# Webhook 簽章驗證器
handler = WebhookHandler(LINE_CHANNEL_SECRET)


# ── 啟動 / 關閉事件 ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理：啟動時初始化 DB + 排程器，關閉時停止排程器"""
    logger.info("🚀 服務啟動中...")
    init_db()
    start_scheduler()
    logger.info("✅ 服務已就緒")
    yield
    logger.info("🛑 服務關閉中...")
    stop_scheduler()


# ── FastAPI 應用程式 ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="LINE 提醒機器人",
    description="透過 LINE 設定時間提醒，到時自動推播通知",
    version="1.0.0",
    lifespan=lifespan,
)


# ── 路由 ────────────────────────────────────────────────────────────────────────

@app.get("/", tags=["狀態"])
async def root():
    """首頁：顯示服務基本資訊"""
    return {
        "service": "LINE 提醒機器人",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "webhook": "POST /callback",
            "health":  "GET  /health",
        },
    }


@app.get("/health", tags=["狀態"])
async def health_check():
    """
    健康檢查端點
    Render / UptimeRobot 定期 ping 這個 URL 確認服務存活
    """
    return {"status": "ok"}


@app.post("/callback", tags=["LINE Webhook"])
async def callback(request: Request):
    """
    LINE Webhook 接收端點

    步驟：
    1. 取出 X-Line-Signature 標頭
    2. 驗證簽章（防止偽造請求）
    3. 交給 handler 分發到對應的事件處理函式
    """
    # 1. 取得簽章與 Body
    signature = request.headers.get("X-Line-Signature", "")
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")

    logger.debug("收到 Webhook，body 長度：%d bytes", len(body_bytes))

    # 2. 驗證 LINE 簽章
    try:
        handler.handle(body_str, signature)
    except InvalidSignatureError:
        logger.warning("簽章驗證失敗，疑似偽造請求")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error("Webhook 處理發生錯誤：%s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

    return Response(content="OK", media_type="text/plain")


# ── LINE 事件處理器 ─────────────────────────────────────────────────────────────

@handler.add(MessageEvent, message=TextMessageContent)
def on_text_message(event: MessageEvent) -> None:
    """處理文字訊息事件"""
    handle_text_message(event, LINE_CHANNEL_ACCESS_TOKEN)


# ── 本地開發啟動 ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,   # 開發模式：檔案變更自動重載
        log_level="info",
    )
