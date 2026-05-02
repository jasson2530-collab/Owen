# 📱 LINE 提醒機器人

用 LINE 傳訊息就能設定提醒，時間到了自動推播通知！

支援：
- ⏰ **一次性提醒**：「明天早上9點提醒我叫貨」
- 🔁 **重複提醒**：「每天早上8點提醒我巡倉」
- 📋 **查詢、刪除、完成** 管理提醒

---

## 目錄

1. [申請 LINE Bot](#一申請-line-bot)
2. [本地測試](#二本地測試)
3. [部署到 Render（推薦）](#三部署到-render推薦)
4. [部署到 Railway（備用）](#四部署到-railway備用)
5. [設定 LINE Webhook URL](#五設定-line-webhook-url)
6. [加機器人好友並測試](#六加機器人好友並測試)
7. [使用範例](#七使用範例)
8. [常見問題 FAQ](#八常見問題-faq)

---

## 一、申請 LINE Bot

### 步驟 1：登入 LINE Developers

1. 打開瀏覽器，前往：**https://developers.line.biz/**
2. 點右上角 **「Log in」**
3. 用你平常用的 LINE 帳號登入（手機掃 QR Code 或輸入帳號密碼）
4. 第一次登入會要你填開發者資料：
   - **Developer name**：填你的名字（中文也可以）
   - **Email**：填你常用的 Email
   - 勾選同意條款 → 點 **「Create」**

---

### 步驟 2：建立 Provider

> Provider 就像是你的「開發者帳號空間」，可以放多個機器人。

1. 登入後在首頁點 **「Create a new provider」**
2. **Provider name** 填任意名稱（例如：`我的提醒機器人`）
3. 點 **「Create」**

---

### 步驟 3：建立 Messaging API Channel

> Channel 就是你的「機器人本體」。

1. 在 Provider 頁面點 **「Create a new channel」**
2. 選 **「Messaging API」**（不是 LINE Login）
3. 填寫以下資料：

   | 欄位 | 填什麼 |
   |------|--------|
   | Channel type | Messaging API（已選好） |
   | Provider | 剛才建立的 Provider |
   | Channel icon | 可不填，預設頭像 |
   | **Channel name** | 機器人的名字，例如：`提醒小幫手` |
   | Channel description | 簡單說明，例如：`個人提醒推播機器人` |
   | Category | 選任意，例如 `個人` |
   | Subcategory | 選任意 |
   | Email | 你的 Email |

4. 勾選兩個同意條款 → 點 **「Create」** → 點 **「OK」**

---

### 步驟 4：取得 Channel Secret

1. 進入剛建立的 Channel
2. 點上方 **「Basic settings」** 分頁
3. 找到 **「Channel secret」** 那一欄
4. 點 **「Copy」** 複製
5. 把這串字存起來 → 這是 **`LINE_CHANNEL_SECRET`**

---

### 步驟 5：取得 Channel Access Token

1. 點上方 **「Messaging API」** 分頁
2. 滾到最下面，找到 **「Channel access token（long-lived）」**
3. 點 **「Issue」** 產生 Token
4. 點 **「Copy」** 複製那一長串 → 這是 **`LINE_CHANNEL_ACCESS_TOKEN`**

---

### 步驟 6：關閉自動回覆（非常重要！）

> 如果不關，每次傳訊息都會同時出現 LINE 預設回覆，很干擾！

1. 在 **「Messaging API」** 分頁
2. 找到 **「Auto-reply messages」** → 點旁邊的 **「Edit」**
3. 會跳到「LINE Official Account Manager」
4. 把 **「自動回應訊息」** 關掉（切換成灰色）
5. 把 **「加入好友的歡迎訊息」** 也可以關掉（非必要）
6. 儲存

---

## 二、本地測試

### 1. 安裝套件

```bash
cd reminder-bot
pip install -r requirements.txt
```

### 2. 建立 .env 檔案

```bash
copy .env.example .env      # Windows
# cp .env.example .env      # Mac/Linux
```

用記事本開啟 `.env`，填入：

```
LINE_CHANNEL_ACCESS_TOKEN=（剛才複製的 Token）
LINE_CHANNEL_SECRET=（剛才複製的 Secret）
DATABASE_URL=sqlite:///./reminders.db
```

### 3. 啟動伺服器

```bash
python -m app.main
```

看到以下訊息代表成功：
```
✅ 服務已就緒
INFO: Uvicorn running on http://0.0.0.0:8000
```

### 4. 本地測試 Webhook（需要 ngrok）

LINE 的 Webhook 需要公開的 HTTPS 網址。本地測試用 ngrok：

```bash
# 安裝 ngrok：https://ngrok.com/download
ngrok http 8000
```

會得到像 `https://xxxx-xxx.ngrok.io` 的網址，
把 `https://xxxx-xxx.ngrok.io/callback` 填入 LINE Console 的 Webhook URL。

> ⚠️ ngrok 免費版每次重啟網址會變，部署到雲端後就不需要 ngrok 了。

---

## 三、部署到 Render（推薦）

> Render 免費方案：每月 750 小時，流量小的話完全免費。

### 步驟 1：把程式碼上傳到 GitHub

1. 在 GitHub 建立一個新的私人 Repository（叫 `line-reminder-bot` 或任意名稱）
2. 在 reminder-bot 資料夾執行：

```bash
git init
git add .
git commit -m "初始化 LINE 提醒機器人"
git remote add origin https://github.com/你的帳號/你的repo名稱.git
git push -u origin main
```

> ⚠️ 確認 `.env` 有在 `.gitignore` 裡，不要把 Token 上傳到 GitHub！

---

### 步驟 2：註冊 Render 帳號

1. 前往：**https://render.com/**
2. 點 **「Get Started for Free」**
3. 用 GitHub 帳號登入（推薦，之後連接 repo 更方便）

---

### 步驟 3：建立 Web Service

1. 登入 Render 後點 **「New」** → 選 **「Web Service」**
2. 點 **「Connect a repository」** → 選擇你的 GitHub repo
3. 填寫設定：

   | 欄位 | 填入 |
   |------|------|
   | Name | `line-reminder-bot`（任意） |
   | Region | `Singapore`（台灣用最近的） |
   | Branch | `main` |
   | Runtime | `Python 3` |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Plan | `Free` |

4. 點 **「Create Web Service」**

---

### 步驟 4：設定環境變數

1. 建立完成後，點左側 **「Environment」**
2. 點 **「Add Environment Variable」**，一個一個加入：

   | Key | Value |
   |-----|-------|
   | `LINE_CHANNEL_ACCESS_TOKEN` | 你的 Token |
   | `LINE_CHANNEL_SECRET` | 你的 Secret |
   | `TIMEZONE` | `Asia/Taipei` |

3. 點 **「Save Changes」**

---

### 步驟 5：建立 PostgreSQL 資料庫

1. 點左上角 **「New」** → 選 **「PostgreSQL」**
2. 設定：

   | 欄位 | 填入 |
   |------|------|
   | Name | `line-reminder-db` |
   | Region | `Singapore` |
   | Plan | `Free` |

3. 點 **「Create Database」**
4. 等待建立完成（約 1-2 分鐘）

---

### 步驟 6：連接資料庫到 Web Service

1. 進入剛才的 PostgreSQL，找到 **「Internal Database URL」**
2. 複製整串 URL（以 `postgres://` 開頭）
3. 回到 Web Service → **「Environment」**
4. 新增環境變數：

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | 剛才複製的 Internal URL |

5. 點 **「Save Changes」**，服務會自動重新部署

---

### 步驟 7：取得部署網址

1. 部署完成後（約 3-5 分鐘），點 **「Logs」** 看是否出現 `✅ 服務已就緒`
2. 頁面最上方有你的網址，格式：`https://line-reminder-bot-xxxx.onrender.com`
3. 記下這個網址，下一步要用到

---

## 四、部署到 Railway（備用）

> 如果 Render 有問題可以用 Railway。

### 步驟 1：註冊 Railway

1. 前往：**https://railway.app/**
2. 點 **「Login with GitHub」**

### 步驟 2：建立專案

1. 點 **「New Project」** → **「Deploy from GitHub repo」**
2. 選擇你的 repo
3. Railway 會自動偵測 Python 專案並部署

### 步驟 3：設定環境變數

1. 點專案 → 點 **「Variables」**
2. 加入：
   - `LINE_CHANNEL_ACCESS_TOKEN`
   - `LINE_CHANNEL_SECRET`
   - `TIMEZONE` = `Asia/Taipei`

### 步驟 4：加入 PostgreSQL

1. 點 **「New」** → **「Database」** → **「PostgreSQL」**
2. Railway 會自動把 `DATABASE_URL` 注入到你的 Web Service

### 步驟 5：取得網址

點 Web Service → **「Settings」** → **「Domains」** → **「Generate Domain」**

---

## 五、設定 LINE Webhook URL

> 這步驟讓 LINE 知道要把訊息傳到哪裡

### 步驟 1：回到 LINE Developers Console

1. 前往：**https://developers.line.biz/**
2. 進入你的 Channel → 點 **「Messaging API」** 分頁

### 步驟 2：填入 Webhook URL

1. 找到 **「Webhook URL」**
2. 點 **「Edit」**
3. 填入：`你的 Render 網址/callback`

   例如：`https://line-reminder-bot-xxxx.onrender.com/callback`

4. 點 **「Update」**

### 步驟 3：啟用 Webhook

1. 把 **「Use webhook」** 切換為 **開啟（藍色）**

### 步驟 4：驗證連線

1. 點 **「Verify」** 按鈕
2. 出現 **「Success」** 綠色訊息代表設定正確 ✅
3. 如果失敗，確認 Render 服務是否正常運行（去看 Logs）

---

## 六、加機器人好友並測試

1. 在 LINE Developers Console → **「Messaging API」** 分頁
2. 找到你機器人的 **QR Code**
3. 用手機 LINE 掃描 QR Code → 點 **「加入好友」**
4. 傳訊息給機器人試試看：

```
help
```

出現使用說明代表一切正常！🎉

---

## 七、使用範例

### 新增一次性提醒

```
你：明天早上9點提醒我叫貨
Bot：✅ 提醒已設定！
     📌 事項：叫貨
     ⏰ 提醒時間：05/03 (六) 09:00
     提醒編號：#1
```

```
你：30分鐘後提醒我開會
Bot：✅ 提醒已設定！
     📌 事項：開會
     ⏰ 提醒時間：05/02 (五) 14:30
     提醒編號：#2
```

### 新增重複提醒

```
你：每天早上8點提醒我巡倉
Bot：✅ 已設定定期提醒！
     📌 事項：巡倉
     🔁 頻率：每天
     ⏰ 下次提醒：05/03 (六) 08:00
     提醒編號：#3
```

### 查詢提醒清單

```
你：列表
Bot：📋 你的提醒清單：

     #1 ⏰ 05/03 (六) 09:00
        叫貨
     #3 🔁每天 05/03 (六) 08:00
        巡倉

     輸入「刪除 [編號]」可刪除提醒
```

### 時間到了自動推播

```
Bot（自動）：⏰ 提醒時間到了！

             叫貨
```

### 刪除提醒

```
你：刪除 1
Bot：🗑️ 提醒 #1 已刪除
```

---

## 八、常見問題 FAQ

### ❓ 傳訊息給機器人沒有任何回應？

**檢查清單：**
1. Render 服務是否正常運行？（去 Render → Logs 看看）
2. Webhook URL 是否填正確，最後有 `/callback`？
3. **「Use webhook」** 是否有開啟？
4. 是否有關掉「自動回覆訊息」？

---

### ❓ 提醒時間到了但沒收到推播？

**可能原因：**
1. **Render 免費方案睡著了** → 見下方「防止休眠」說明
2. 環境變數 `LINE_CHANNEL_ACCESS_TOKEN` 填錯 → 去 Render → Environment 確認
3. 時區問題 → 確認 `TIMEZONE=Asia/Taipei` 有設定

---

### ❓ Render 免費方案會睡著怎麼辦？

Render 免費方案在 **15 分鐘沒有流量**時會進入休眠，醒來需要約 30 秒，
這段時間的提醒可能會延遲。

**解決方法：用 UptimeRobot 每 5 分鐘 ping 一次**

1. 前往：**https://uptimerobot.com/**
2. 免費註冊
3. 點 **「Add New Monitor」**
4. 設定：
   - Monitor Type：`HTTP(s)`
   - Friendly Name：`LINE 提醒機器人`
   - URL：`https://你的網址.onrender.com/health`
   - Monitoring Interval：`5 minutes`
5. 點 **「Create Monitor」**

這樣機器人就會 24 小時保持清醒！

---

### ❓ 怎麼更新程式碼？

只要 `git push` 到 GitHub，Render 會自動重新部署（約 2-3 分鐘）。

---

### ❓ LINE 免費方案有推播限制嗎？

有！LINE 官方帳號每月免費推播訊息有上限（目前為 200 則/月）。
個人使用通常夠用，超過需要付費升級。

---

## 專案結構

```
reminder-bot/
├── app/
│   ├── __init__.py          # 套件初始化
│   ├── main.py              # FastAPI 主程式 + Webhook 端點
│   ├── line_handler.py      # 解析 LINE 訊息、執行指令
│   ├── reminder_service.py  # 資料庫 CRUD 操作
│   ├── scheduler.py         # APScheduler 排程、自動推播
│   ├── time_parser.py       # 中文時間解析
│   ├── database.py          # 資料庫連線（SQLite/PostgreSQL）
│   └── models.py            # SQLAlchemy 資料模型
├── .env.example             # 環境變數範本
├── .env                     # 你的設定（不要上傳 Git！）
├── .gitignore
├── requirements.txt
├── Procfile                 # Render/Railway 啟動指令
├── runtime.txt              # Python 版本
├── render.yaml              # Render 一鍵部署設定
└── README.md
```
