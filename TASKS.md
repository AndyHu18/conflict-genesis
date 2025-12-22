# 任務追蹤 (Lumina 心語)

## ✅ 已完成任務
- [x] **音頻播放器修復**
    - [x] 修復 StreamingAudioPlayer 進度條不更新問題
    - [x] 實現串流模式下的分段時長累計
- [x] **BGM 混合系統升級**
    - [x] 實現 `StreamingBGMMixer` 類
    - [x] 支援串流模式下的即時 BGM 混合 (每片段帶 BGM)
    - [x] 前端新增 `bgm_loaded`, `bgm_warning`, `audio` (含 `has_bgm`) 事件處理
- [x] **TTS 情緒控制**
    - [x] 實現 `_build_healing_tts_prompt` (Audio Profile)
    - [x] 支援 Director's Notes (Style, Pacing, Breathing, Emotional Arc)
    - [x] 根據階段 (PART_1 ~ PART_5) 自動調整情緒曲線
- [x] **UI/UX 優化**
    - [x] 移除圖像卡片預設的「載入中...」文字
    - [x] 確保純語音與混合 BGM 版本無縫切換
    - [x] 新增 `showToast` 通知 (第一張圖/第一段音頻)

## 🚧 進行中任務
- [ ] **部署流程**
    - [ ] 準備部署配置文件 (Procfile, requirements.txt, render.yaml/vercel.json)
    - [ ] 執行部署檢查
    - [ ] 發布到生產環境

## 📋 待辦事項
- [ ] **效能優化**
    - [ ] 實現 BGM 資源快取 (避免重複下載/生成)
    - [ ] 優化 TTS 請求並發
- [ ] **錯誤處理增強**
    - [ ] 增加對 Lyria API 429 錯誤的優雅降級
    - [ ] 完善前端重試機制的 UI 反饋
