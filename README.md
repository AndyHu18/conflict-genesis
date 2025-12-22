# Conflict Genesis - 音訊衝突源頭判定系統

⚔️ 利用 Gemini AI 多模態能力分析雙人對話，判斷誰先導致了情緒升級或衝突。

## ✨ 功能特色

- 🎙️ **多模態音訊分析**：直接分析音訊檔案，無需預先轉錄
- 🔍 **衝突發起者判定**：識別對話中誰先升級情緒
- 📊 **結構化輸出**：以 JSON 格式返回詳細分析結果
- 🎯 **被動攻擊識別**：能識別冷暴力、陰陽怪氣等隱性衝突
- ⏱️ **時間戳定位**：精確定位衝突轉折點

## 🚀 快速開始

### 1. 安裝依賴

```bash
cd conflict-genesis
pip install -r requirements.txt
```

### 2. 設置 API Key

複製 `.env.example` 為 `.env`，填入你的 Gemini API Key：

```bash
cp .env.example .env
# 編輯 .env 填入 API Key
```

或者從 [Google AI Studio](https://aistudio.google.com/apikey) 獲取 API Key。

### 3. 運行分析

```bash
# 基本用法
python main.py your_conversation.mp3

# 帶情境說明
python main.py argument.wav --context "這是一對夫妻關於財務的對話"

# 匯出結果
python main.py debate.mp3 --output result.json

# 僅檢查環境
python main.py --check

# 查看音訊資訊
python main.py audio.mp3 --info
```

## 📋 命令行參數

| 參數 | 說明 |
|------|------|
| `audio_file` | 要分析的音訊檔案路徑 |
| `-c, --context` | 額外情境說明（如對話雙方關係） |
| `-m, --model` | 使用的模型（預設: gemini-2.5-flash） |
| `-o, --output` | 匯出結果的 JSON 路徑 |
| `-v, --verbose` | 詳細輸出模式 |
| `-q, --quiet` | 靜默模式 |
| `--check` | 僅檢查環境配置 |
| `--info` | 顯示音訊檔案資訊 |

## 📊 輸出格式

分析結果包含以下資訊：

```json
{
  "conflict_detected": true,
  "instigator": "Speaker A",
  "trigger_timestamp": "02:35",
  "conflict_type": "Emotional Escalation",
  "conflict_intensity_score": 6,
  "speakers": [
    {
      "speaker_id": "Speaker A",
      "voice_characteristics": "音色較高亢，語速偏快",
      "baseline_emotion": "中性"
    }
  ],
  "trigger_details": {
    "timestamp": "02:35",
    "trigger_content": "你總是這樣！",
    "trigger_type": "Verbal Aggression"
  },
  "reasoning_analysis": {
    "acoustic_evidence": "音量突然提高約 50%",
    "semantic_evidence": "使用了「你總是」這種標籤化語言"
  },
  "summary": "對話在 2:35 時出現衝突..."
}
```

## 🧐 判定規則

系統按以下優先級判定衝突發起者：

1. **情緒挑釁 (Emotional Escalation)**
   - 誰先從中性語氣轉變為輕蔑、嘲諷或憤怒

2. **語義攻擊 (Verbal Aggression)**
   - 誰先使用人身攻擊、標籤化語言（如「你總是...」）

3. **對話侵略 (Conversational Aggression)**
   - 誰先頻繁打斷對方、提高音量蓋過對方

4. **被動攻擊 (Passive Aggressive)** ⚠️ 特別注意
   - 沉默以對、故意忽視、陰陽怪氣
   - **有時候先大聲的人不是發起者，而是被冷暴力逼瘋的人**

## 🎧 支援的音訊格式

- WAV (audio/wav)
- MP3 (audio/mp3)
- AIFF (audio/aiff)
- AAC (audio/aac)
- OGG Vorbis (audio/ogg)
- FLAC (audio/flac)

## ⚙️ 技術規格

- **Token 消耗**：32 tokens/秒（1 分鐘 ≈ 1,920 tokens）
- **最大長度**：9.5 小時（單一 Prompt）
- **建議長度**：30 分鐘以內效果最佳
- **降採樣**：自動降至 16 Kbps

## 🧪 運行測試

```bash
cd conflict-genesis
python tests/test_analyzer.py
```

## 📁 專案結構

```
conflict-genesis/
├── main.py                    # 主程式入口 + CLI
├── conflict_analyzer/
│   ├── __init__.py
│   ├── audio_processor.py     # 音訊預處理
│   ├── conflict_analyzer.py   # Gemini API 封裝
│   ├── schemas.py             # Pydantic 資料模型
│   └── prompts.py             # System Instruction
├── tests/
│   └── test_analyzer.py       # 測試腳本
├── requirements.txt
├── .env.example
└── README.md
```

## 📝 開發備註

### API 版本
本專案使用 2025 年新版 Google GenAI SDK (`google-genai`)，而非舊版 `google-generativeai`。

### 結構化輸出
使用 Pydantic 定義 Schema，透過 `response_schema` 參數傳遞給 Gemini API。

### 音訊處理
- 需要 FFmpeg 進行格式轉換和切片
- Windows 用戶：從 [ffmpeg.org](https://ffmpeg.org/download.html) 下載並加入 PATH

## ⚠️ 限制與已知問題

1. **Speaker Diarization**：在多人嘈雜環境下可能混淆說話者
2. **時間戳精度**：長音訊的時間戳可能有誤差
3. **非即時分析**：不支援即時串流分析

## 📜 授權

MIT License
