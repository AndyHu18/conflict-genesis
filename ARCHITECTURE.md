# Conflict Genesis - 專案架構文檔

> 最後更新：2025-12-23 08:52

## 📁 Project Structure

```
conflict-genesis/
├── web_app.py              # 主 Flask 應用 (245KB, 包含前端 HTML/CSS/JS)
├── main.py                 # CLI 入口 (終端機版本)
├── demo.py                 # 演示腳本
├── requirements.txt        # Python 依賴
│
├── conflict_analyzer/      # 核心分析引擎
│   ├── __init__.py         # 模組初始化
│   ├── conflict_analyzer.py # 衝突分析器 (Gemini API)
│   ├── prompts.py          # 系統提示詞 (三階段分析)
│   ├── schemas.py          # Pydantic 資料模型
│   ├── audio_processor.py  # 音訊處理 (上傳/轉換)
│   ├── audio_mixer.py      # 音頻混音器 (BGM + TTS)
│   ├── bgm_manager.py      # 背景音樂管理
│   ├── healing_audio.py    # 療癒音頻生成 (TTS)
│   ├── image_generator.py  # Imagen 4 圖像生成
│   ├── visual_architect.py # 視覺設計師 (圖像提示詞)
│   ├── slide_composer.py   # 幻燈片構圖器
│   ├── pdf_generator.py    # PDF 報告生成器
│   ├── lyria_music.py      # Lyria 音樂生成 (未使用)
│   └── replicate_music.py  # Replicate 音樂 API (未使用)
│
├── assets/                 # 靜態資源
│   ├── bgm/                # 9 首背景音樂 MP3
│   └── fonts/              # 中文字體 (Noto Sans TC)
│
├── reports/                # 生成的報告 JSON
├── uploads/                # 用戶上傳的音訊檔案
├── generated_images/       # 生成的圖像暫存
│
├── tests/                  # 測試檔案
│   └── test_slide_composer.py
│
├── Procfile               # Render/Railway 啟動命令
├── render.yaml            # Render 部署配置
├── railway.toml           # Railway 部署配置
├── nixpacks.toml          # Nixpacks 配置
└── vercel.json            # Vercel 配置 (不適用)
```

## 🛠 Tech Stack

| 類別 | 技術 | 版本 |
|:---|:---|:---|
| 後端 | Flask | ≥3.1.0 |
| AI | Google GenAI (Gemini 2.5 Flash) | ≥1.56.0 |
| 圖像 | Imagen 4 | - |
| 資料驗證 | Pydantic | ≥2.12.0 |
| 音訊處理 | pydub | ≥0.25.1 |
| PDF 生成 | fpdf2 | ≥2.8.0 |
| WSGI | Gunicorn | ≥21.0.0 |
| 環境變數 | python-dotenv | ≥1.2.0 |

## 📊 Development Status

### 核心功能

| 模組 | 狀態 | 備註 |
|:---|:---:|:---|
| 音訊上傳 | ✅ | WAV/MP3/AAC/FLAC/M4A 支援 |
| 三階段分析 | ✅ | Gemini 2.5 Flash |
| 視覺化圖像 | ✅ | Imagen 4 + 自動重試 (20次) |
| 療癒音頻 | ✅ | TTS + BGM 混音 + 串流播放 |
| PDF 報告 | ✅ | 動態封面 + 事件簡介 |
| 音頻播放器 | ✅ | 波形可視化 + 上下首切換 |

### 播放器功能

| 功能 | 狀態 | 備註 |
|:---|:---:|:---|
| 播放/暫停 | ✅ | 支援串流與傳統模式 |
| 進度條 | ✅ | 可點擊跳轉 |
| 波形可視化 | ✅ | Web Audio API + 模擬模式 |
| 上一首/下一首 | ✅ | 串流模式支援片段切換 |
| Toast 通知 | ✅ | 圖片/音頻/PDF 生成通知 |

### 部署配置

| 平台 | 狀態 | 備註 |
|:---|:---:|:---|
| Render | ✅ | 主要部署平台 |
| Railway | 🚧 | 配置存在但未測試 |
| Vercel | ❌ | 不適用 (Flask 應用) |

## 🔑 環境變數

| 變數名 | 必填 | 說明 |
|:---|:---:|:---|
| `GEMINI_API_KEY` | ✅ | Google AI Studio API Key |
| `PORT` | ❌ | 伺服器端口 (預設 5000) |

## 📝 已知問題

1. ~~上傳區域點擊無反應~~ → 已修復 (canvas 重複宣告)
2. ~~波形第一次不顯示~~ → 已修復 (添加備用模擬波形)
3. ~~PDF 文字超出邊框~~ → 已修復 (固定 Y 位置)

## 🚀 本地開發

```bash
# 建立虛擬環境
python -m venv venv
venv\Scripts\activate  # Windows

# 安裝依賴
pip install -r requirements.txt

# 設置環境變數
cp .env.example .env
# 編輯 .env 填入 GEMINI_API_KEY

# 啟動伺服器
python web_app.py
```

## 🌐 部署到 Render

1. 連接 GitHub 倉庫
2. 設置環境變數 `GEMINI_API_KEY`
3. 部署會自動使用 `Procfile` 和 `render.yaml`
