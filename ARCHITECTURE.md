# Lumina 心語 (Conflict Genesis) - 專案憲法

> 最後更新: 2025-12-23
> 版本: 4.5.0 (串流 BGM 混合 + TTS 情緒控制 + UI 優化)

## 🎯 專案概述

**Lumina 心語** 是一個專業的衝突分析與療癒系統，透過四階段深度分析將衝突錄音轉化為可視化報告與療癒音頻。

### 核心功能
- 🎙️ 音訊處理：支援長達 8 小時的錄音分析
- 📊 四階段分析：演化追蹤 → 深層溯源 → 成長方案 → 數位催眠療癒
- 🎨 視覺化簡報：Imagen 生成高品質情境圖，**去除載入中預設文字**
- 🎵 串流療癒音頻：
    - **即時 BGM 混合**：邊生成邊混合背景音樂，提供無縫收聽體驗
    - **情緒 TSS**：支援 Director's Notes，控制語速、呼吸與情感曲線
    - **即時串流**：解決 TTS 截斷問題，提升響應速度
- 📑 PDF 報告：完整四階段報告匯出

---

## 📂 專案結構

```
conflict-genesis/
├── web_app.py                    # Flask Web 應用 (主入口)
├── main.py                       # CLI 入口
├── demo.py                       # 展示腳本
├── requirements.txt              # Python 依賴
├── .env                          # 環境變數 (API Key)
├── .env.example                  # 環境變數範例
├── README.md                     # 專案說明
├── ARCHITECTURE.md               # 本文件 (專案憲法)
│
├── conflict_analyzer/            # 核心分析模組
│   ├── __init__.py               # 模組入口
│   ├── audio_processor.py        # 音訊處理 (分段上傳)
│   ├── conflict_analyzer.py      # 四階段分析引擎
│   ├── prompts.py                # System Prompts (Stage 1-4)
│   ├── schemas.py                # Pydantic 數據模型
│   ├── image_generator.py        # Imagen 圖像生成 (整合 VA)
│   ├── visual_architect.py       # 視覺架構師 (簡報內容生成)
│   ├── slide_composer.py         # 🆕 圖文合成器 (PIL 文字疊加)
│   ├── healing_audio.py          # 療育音頻 (分段生成+縫合)
│   ├── audio_mixer.py            # 音頻混音器 (語音+BGM)
│   ├── lyria_music.py            # Lyria 原創音樂生成
│   ├── bgm_manager.py            # BGM 資源管理
│   └── pdf_generator.py          # PDF 報告生成
│
├── assets/                       # 靜態資源
│   └── bgm/                      # 🆕 背景音樂庫
├── uploads/                      # 上傳暫存
├── reports/                      # 分析報告 (JSON)
├── generated_images/             # 生成的圖像
├── .audio_temp/                  # 音頻暫存
└── tests/                        # 測試檔案
```

---

## 🔧 技術棧

| 類別 | 套件 | 版本 | 用途 |
|------|------|------|------|
| Web 框架 | Flask | 3.1.x | Web 應用與 API |
| AI/ML | google-genai | 1.56.x | Gemini API (分析+音頻+圖像) |
| 資料驗證 | Pydantic | 2.12.x | Schema 與資料模型 |
| 音訊處理 | pydub | 0.25.x | 音頻縫合 + BGM 混音 |
| PDF 生成 | fpdf2 | 2.8.x | PDF 報告 (中文支援) |
| 環境變數 | python-dotenv | 1.2.x | .env 載入 |

### AI 模型
- `gemini-2.5-flash`: 四階段文本分析
- `gemini-2.5-flash-preview-tts`: 語音合成 (TTS)
- `imagen-4.0-generate-001`: 圖像生成
- `models/lyria-realtime-exp`: 🆕 原創療癒音樂生成 (48kHz)

---

## 📊 開發狀態

| 模組/功能 | 狀態 | 備註 |
|:---|:---:|:---|
| 音訊處理 (audio_processor) | ✅ | 支援 8hr 分段上傳 |
| 一階分析 (Stage 1) | ✅ | 衝突演化追蹤 |
| 二階分析 (Stage 2) | ✅ | 深層溯源與接納橋樑 |
| 三階分析 (Stage 3) | ✅ | 個人成長行動方案 |
| 四階分析 (Stage 4) | ✅ | 數位催眠療癒 |
| 視覺架構師 (VisualArchitect) | ✅ | 結構化簡報內容生成 |
| 圖像生成 (Imagen) | ✅ | 上下文驅動視覺化 |
| 分段音頻 ([PART_X] + pydub) | ✅ | 解決 TTS 截斷問題 |
| Lyria 原創 BGM (lyria_music) | ✅ | 🆕 情緒駈動的原創療癒音樂 |
| BGM 混音 (AudioMixer) | ✅ | 語音+音樂自動混合 |
| PDF 報告 | ✅ | 中文支援，完整四階段 |
| Web UI (Flask) | ✅ | NotebookLM 風格卡片 |
| 自動生成流程 | ✅ | 上傳即自動分析+圖+音 |

---

## 🔗 API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/` | GET | 主頁面 |
| `/analyze` | POST | 上傳音訊並分析 |
| `/generate-images` | POST | 生成視覺化簡報 |
| `/generate-audio` | POST | 生成療癒音頻 |
| `/download-pdf/<id>` | GET | 下載 PDF 報告 |

---

## 🎨 視覺化系統 (VisualArchitect)

### 資料流程
```
Stage JSON → VisualArchitect → SlideContent → Imagen → 簡報卡片
```

### SlideContent Schema
```python
@dataclass
class SlideContent:
    slide_title: str       # 震撼力標題 (≤8字)
    core_insight: str      # 溫暖引言 (≤30字)
    data_bullets: List[str]  # 3 個關鍵洞察
    image_prompt: str      # 英文視覺意向
    stage_id: int          # 階段編號
    color_theme: str       # 色彩主題 Hex
```

### 階段色調
- Stage 1 (衝突演化): 🟠 #F59E0B (橙黃)
- Stage 2 (深層溯源): 🔵 #0891B2 (深青)
- Stage 3 (成長方案): 🟢 #22C55E (嫩綠)
- Stage 4 (療癒旅程): 🩷 #EC4899 (和諧粉)

---

## 🎵 分段音頻系統

### 解決 TTS 截斷問題
- **問題**: TTS API 有 ~4KB 輸出限制
- **方案**: [PART_1] ~ [PART_6] 分段生成 + pydub 縫合

### System Prompt 結構
```
[PART_1] 案件連結開場 (~150字)
[PART_2] 穩定化與呼吸 (~150字)
[PART_3] 同感鏡映 (~180字)
[PART_4] 重新框架 (~180字)
[PART_5] 賦權與未來意象 (~150字)
[PART_6] 收尾與祝福 (~80字)
```

### 音頻縫合
- 使用 pydub 無縫連接
- 片段間 800ms 靜音
- 首片段 500ms 淡入
- 尾片段 1000ms 淡出

---

## 🚀 啟動方式

```powershell
# 啟動 Web 應用
.\venv\Scripts\python.exe web_app.py

# 訪問
http://localhost:5000
```

---

## 📝 待辦事項

- [ ] 多語言支援 (英文 UI)
- [ ] 用戶帳號系統
- [ ] 雲端部署 (Vercel/Cloud Run)
- [ ] 歷史報告管理
- [ ] 音頻串流播放 (非一次性載入)

---

## 🔒 環境變數

```env
GEMINI_API_KEY=your_api_key_here
```

---

> **憲法原則**: 代碼有才算有，計畫不算完成。
