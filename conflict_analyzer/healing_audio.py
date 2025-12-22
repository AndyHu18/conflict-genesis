"""
Lumina 心語 - 療育音頻生成模組 v2.0
實作「分段生成與自動串接」邏輯，解決 TTS API 輸出長度限制

核心功能：
1. script_splitter - 根據 [PART_X] 標籤拆分文稿
2. 順序生成每個片段的音頻
3. 使用 pydub 無縫縫合所有片段
"""

import os
import re
import wave
import base64
from io import BytesIO
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from google import genai
from google.genai import types

# 嘗試導入 pydub，如果失敗則使用純 WAV 拼接
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    print("⚠️ pydub 未安裝，將使用基礎 WAV 拼接")

# 模型常量
TTS_MODEL = "gemini-2.5-flash-preview-tts"  # TTS 專用模型
TEXT_MODEL = "gemini-2.5-flash"  # 用於生成文稿

# 可用的聲音選項 (中文推薦使用 Kore 或 Aoede)
VOICE_OPTIONS = {
    "warm_female": "Kore",      # 溫暖女聲
    "calm_female": "Aoede",     # 平靜女聲
    "gentle_male": "Charon",    # 溫和男聲
    "soothing_male": "Fenrir",  # 舒緩男聲
}


def split_script_by_parts(script: str) -> List[Tuple[str, str]]:
    """
    根據 [PART_X] 標籤將腳本拆分為多個片段
    
    Args:
        script: 包含 [PART_1], [PART_2] 等標籤的完整腳本
        
    Returns:
        List of tuples: [(part_name, content), ...]
    """
    # 匹配 [PART_X] 格式的標籤
    pattern = r'\[PART_(\d+)\]'
    
    # 找到所有標籤的位置
    matches = list(re.finditer(pattern, script))
    
    if not matches:
        # 如果沒有標籤，返回整個腳本作為單一片段
        print("⚠️ 未找到 [PART_X] 標籤，將整體作為單一片段處理")
        return [("PART_1", script.strip())]
    
    parts = []
    for i, match in enumerate(matches):
        part_name = f"PART_{match.group(1)}"
        start = match.end()
        
        # 結束位置是下一個標籤的開始，或者是文本末尾
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(script)
        
        content = script[start:end].strip()
        if content:  # 只添加非空內容
            parts.append((part_name, content))
    
    print(f"📍[Script Splitter] 成功拆分為 {len(parts)} 個片段")
    for name, content in parts:
        print(f"   - {name}: {len(content)} 字")
    
    return parts


class StreamingBGMMixer:
    """
    串流 BGM 混合器：邊生成邊混合背景音樂
    
    設計：
    1. 初始化時載入並準備一個足夠長的 BGM loop
    2. 追蹤當前 BGM 播放位置（毫秒）
    3. 每個 TTS 片段生成後，從 BGM 中裁剪對應長度的片段
    4. 混合 TTS 片段和 BGM 片段
    5. 更新 BGM 位置指針
    
    用法：
        mixer = StreamingBGMMixer(stage2_result)
        if mixer.is_ready:
            for tts_audio in tts_parts:
                mixed_audio = mixer.mix_segment(tts_audio)
                yield mixed_audio
    """
    
    def __init__(self, stage2_result: Dict[str, Any] = None):
        """
        初始化串流混合器
        
        Args:
            stage2_result: 用於提取情緒標籤以選擇合適的 BGM
        """
        self.is_ready = False
        self.bgm_audio = None
        self.bgm_position_ms = 0  # 當前 BGM 位置（毫秒）
        self.bgm_volume_reduction = -20  # BGM 降低 20dB
        self.fade_duration_ms = 500  # 片段間淡入淡出
        self.bgm_path = None
        
        try:
            from pydub import AudioSegment
            from conflict_analyzer.audio_mixer import AudioMixer
            
            self.AudioSegment = AudioSegment
            
            # 初始化 AudioMixer 以選擇 BGM
            mixer = AudioMixer()
            
            # 從 stage2 提取情緒
            emotion = "healing"
            if isinstance(stage2_result, dict):
                if stage2_result.get("sentiment_vibe"):
                    emotion = stage2_result["sentiment_vibe"]
            
            # 選擇 BGM
            self.bgm_path = mixer.select_bgm(emotion)
            
            if self.bgm_path:
                # 載入 BGM
                self.bgm_audio = AudioSegment.from_file(str(self.bgm_path))
                
                # 降低 BGM 音量
                self.bgm_audio = self.bgm_audio + self.bgm_volume_reduction
                
                # 確保 BGM 足夠長（至少 10 分鐘）
                target_duration_ms = 10 * 60 * 1000  # 10 分鐘
                if len(self.bgm_audio) < target_duration_ms:
                    # 循環拼接
                    loops_needed = (target_duration_ms // len(self.bgm_audio)) + 1
                    self.bgm_audio = self.bgm_audio * loops_needed
                
                self.is_ready = True
                print(f"   🎵 [StreamingBGMMixer] BGM 已載入: {self.bgm_path.name}")
                print(f"   🎵 [StreamingBGMMixer] BGM 總時長: {len(self.bgm_audio) / 1000:.1f} 秒")
            else:
                print("   ⚠️ [StreamingBGMMixer] 沒有可用的 BGM 文件")
                
        except ImportError as e:
            print(f"   ⚠️ [StreamingBGMMixer] 初始化失敗: {e}")
        except Exception as e:
            print(f"   ⚠️ [StreamingBGMMixer] 載入 BGM 失敗: {e}")
    
    def mix_segment(self, voice_audio: bytes, voice_format: str = "wav") -> bytes:
        """
        將單個 TTS 片段與 BGM 混合
        
        Args:
            voice_audio: TTS 生成的語音 bytes
            voice_format: 語音格式
            
        Returns:
            混合後的音頻 bytes
        """
        if not self.is_ready or not self.bgm_audio:
            return voice_audio  # 無 BGM，返回原音頻
        
        try:
            from io import BytesIO
            
            # 載入語音片段
            voice_buffer = BytesIO(voice_audio)
            voice_segment = self.AudioSegment.from_file(voice_buffer, format=voice_format)
            voice_duration_ms = len(voice_segment)
            
            # 從 BGM 中裁剪對應位置的片段
            bgm_start = self.bgm_position_ms
            bgm_end = bgm_start + voice_duration_ms
            
            # 確保不超出 BGM 長度（循環）
            if bgm_end > len(self.bgm_audio):
                # BGM 已播放完，從頭循環
                self.bgm_position_ms = 0
                bgm_start = 0
                bgm_end = voice_duration_ms
            
            bgm_segment = self.bgm_audio[bgm_start:bgm_end]
            
            # 更新 BGM 位置
            self.bgm_position_ms = bgm_end
            
            # 混合
            mixed = bgm_segment.overlay(voice_segment, position=0)
            
            # 輸出
            output_buffer = BytesIO()
            mixed.export(output_buffer, format="wav")
            output_buffer.seek(0)
            
            return output_buffer.read()
            
        except Exception as e:
            print(f"   ⚠️ [StreamingBGMMixer] 混合片段失敗: {e}")
            return voice_audio  # 失敗時返回原音頻
    
    def get_status(self) -> Dict[str, Any]:
        """獲取混合器狀態"""
        return {
            "is_ready": self.is_ready,
            "bgm_file": self.bgm_path.name if self.bgm_path else None,
            "current_position_ms": self.bgm_position_ms,
            "method": "streaming_local" if self.is_ready else "none"
        }


class HealingAudioGenerator:
    """生成療育音頻的核心類（支援分段生成與串接）"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("需要 GEMINI_API_KEY 環境變數")
        self.client = genai.Client(api_key=self.api_key)
    
    def generate_healing_script(
        self,
        stage1_result: Dict[str, Any],
        stage2_result: Dict[str, Any],
        stage3_result: Dict[str, Any],
        system_prompt: str,
        additional_context: str = ""
    ) -> str:
        """
        生成療育音頻文稿（帶有 [PART_X] 標籤）
        
        Returns:
            包含 [PART_1], [PART_2], ... 標籤的結構化療育腳本
        """
        from conflict_analyzer.prompts import get_stage4_prompt
        
        print("📍[HealingAudioGenerator] 正在生成分段療育文稿...")
        
        user_prompt = get_stage4_prompt(
            stage1_result, 
            stage2_result, 
            stage3_result,
            additional_context
        )
        
        try:
            response = self.client.models.generate_content(
                model=TEXT_MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.8,
                )
            )
            
            script = response.text.strip()
            print(f"📍[HealingAudioGenerator] 文稿生成成功！總長度: {len(script)} 字")
            return script
            
        except Exception as e:
            print(f"❌ 生成療育文稿錯誤: {e}")
            raise
    
    def _build_healing_tts_prompt(self, text: str, part_name: str = "") -> str:
        """
        構建帶情緒控制的 TTS Prompt（使用 Google 官方推薦的 Audio Profile 格式）
        
        療育音頻專用指令：溫暖、同理心、緩慢呼吸式停頓
        
        Args:
            text: 要朗讀的文字
            part_name: 片段名稱（如 PART_1, PART_2）
            
        Returns:
            帶風格指令的完整 prompt
        """
        # 根據片段名稱調整情緒
        emotion_guide = self._get_emotion_for_part(part_name)
        
        # 構建專業的 Audio Profile
        prompt = f"""# AUDIO PROFILE: 療育引導師
## "Healing Voice Guide"

## THE SCENE:
一個寧靜的療癒空間，柔和的燈光灑落。
聆聽者正處於一個安全、被接納的環境中。
這是一段私密的自我療癒時刻。

### DIRECTOR'S NOTES

**Style:** {emotion_guide['style']}

**Pacing:** {emotion_guide['pacing']}

**Breathing:** 每個句子結束後留下自然的呼吸空間。
在逗號和句號處適當停頓，讓聆聽者有時間吸收和感受。
不要急躁，讓每個字都帶著溫度緩緩流出。

**Emotional Arc:** {emotion_guide['emotional_arc']}

**Voice Quality:** 
- 使用「聲音微笑」技巧，讓語調帶著溫暖
- 保持低沉但清晰的音調
- 避免過度戲劇化，保持真誠自然

## TRANSCRIPT:
{text}
"""
        return prompt
    
    def _get_emotion_for_part(self, part_name: str) -> dict:
        """
        根據片段名稱返回對應的情緒指導
        
        療育音頻的情緒曲線：開場 → 共情 → 深入 → 轉化 → 希望
        """
        part_emotions = {
            "PART_1": {
                "style": "溫暖而富有同理心的開場白。像一位值得信賴的朋友，輕柔地問候。語調要讓人感到被理解、被接納。",
                "pacing": "緩慢而穩定，給予充足的空間。每分鐘約 100-120 字。",
                "emotional_arc": "從平靜開始，逐漸建立信任感。"
            },
            "PART_2": {
                "style": "深度共情和理解。承認痛苦的存在，不試圖立即修復。語調要傳達「我理解你」的訊息。",
                "pacing": "稍慢，在重要的情感詞彙前後留下停頓。",
                "emotional_arc": "深入連結，讓聆聽者感到被看見。"
            },
            "PART_3": {
                "style": "洞察與啟發。帶有一絲好奇和探索的語調。輕輕引導聆聽者看見新的角度。",
                "pacing": "中等速度，在關鍵洞察處適當加重語氣。",
                "emotional_arc": "從理解到領悟的轉折點。"
            },
            "PART_4": {
                "style": "希望與力量。語調逐漸變得明亮、堅定但不失溫柔。傳達「你可以的」的信念。",
                "pacing": "略微加快，但保持穩定和自信。",
                "emotional_arc": "向上揚起，注入希望和能量。"
            },
            "PART_5": {
                "style": "溫暖的祝福和收尾。像一個溫柔的擁抱，帶著祝福送別。",
                "pacing": "回歸緩慢，讓最後的話語沉澱在心中。",
                "emotional_arc": "平靜收尾，留下持久的溫暖。"
            }
        }
        
        # 嘗試匹配片段名稱
        for key in part_emotions:
            if key in part_name.upper():
                return part_emotions[key]
        
        # 預設情緒（適用於未知片段）
        return {
            "style": "溫暖、富有同理心、真誠自然。像一位智慧的療癒師，用心傾聯並溫柔回應。",
            "pacing": "緩慢而穩定，每分鐘約 100-120 字。自然的呼吸式停頓。",
            "emotional_arc": "保持平穩溫暖，傳達支持與理解。"
        }

    def text_to_speech_single(
        self,
        text: str,
        voice: str = "warm_female",
        part_name: str = "",
        max_retries: int = 3  # 新增：最大重試次數
    ) -> bytes:
        """
        將單一片段文字轉換為語音（帶指數退避重試機制）
        
        Args:
            text: 要轉換的文字（應控制在 200 字以內）
            voice: 聲音選項
            part_name: 片段名稱（用於日誌）
            max_retries: 最大重試次數（預設 3 次）
            
        Returns:
            WAV 音頻的 bytes
        """
        import time
        import random
        
        voice_name = VOICE_OPTIONS.get(voice, "Kore")
        
        # ============ 構建帶情緒控制的 TTS Prompt ============
        # 使用 Google 官方推薦的 Audio Profile 格式
        styled_prompt = self._build_healing_tts_prompt(text, part_name)
        
        # ============ 除錯：顯示請求資訊 ============
        print(f"   [TTS] 🔍 除錯資訊:")
        print(f"   [TTS]    片段: {part_name}")
        print(f"   [TTS]    文字長度: {len(text)} 字")
        print(f"   [TTS]    聲音: {voice_name}")
        print(f"   [TTS]    模型: {TTS_MODEL}")
        print(f"   [TTS]    🎭 已加入情緒控制指令")
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                print(f"   [TTS] 正在發送 TTS 請求... (嘗試 {attempt + 1}/{max_retries + 1})")
                
                # ============ 使用帶風格的 prompt ============
                response = self.client.models.generate_content(
                    model=TTS_MODEL,
                    contents=styled_prompt,  # 使用帶情緒控制的完整 prompt
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=voice_name,
                                )
                            ),
                        ),
                    )
                )
                
                print(f"   [TTS] 📥 收到回應")
                
                # 安全獲取 PCM 數據
                if not response.candidates:
                    raise ValueError("TTS 回應沒有 candidates")
                
                print(f"   [TTS]    候選者數量: {len(response.candidates)}")
                
                candidate = response.candidates[0]
                if not hasattr(candidate, 'content') or not candidate.content:
                    raise ValueError("TTS 回應沒有 content")
                
                if not candidate.content.parts:
                    raise ValueError("TTS 回應沒有 parts")
                
                print(f"   [TTS]    parts 數量: {len(candidate.content.parts)}")
                
                part = candidate.content.parts[0]
                if not hasattr(part, 'inline_data') or not part.inline_data:
                    # 檢查是否有文字回應（錯誤情況）
                    if hasattr(part, 'text') and part.text:
                        print(f"   [TTS] ⚠️ 收到文字回應而非音頻: {part.text[:100]}...")
                    raise ValueError("TTS 回應沒有 inline_data")
                
                pcm_data = part.inline_data.data
                if not pcm_data:
                    raise ValueError("TTS 回應的音頻數據為空")
                
                # 轉換為 WAV
                wav_data = self._pcm_to_wav(pcm_data)
                
                print(f"   [TTS] ✅ {part_name} 生成完成 ({len(wav_data)} bytes)")
                return wav_data
                
            except Exception as e:
                last_error = e
                error_str = str(e)
                
                print(f"   [TTS] ❌ 錯誤類型: {type(e).__name__}")
                print(f"   [TTS] ❌ 錯誤訊息: {e}")
                
                # ============ 增強診斷 ============
                if "403" in error_str or "PERMISSION_DENIED" in error_str:
                    print(f"   [TTS] 📍 診斷: API 權限被拒")
                    print(f"   [TTS]    建議: 確認 GEMINI_API_KEY 有 TTS 權限")
                elif "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    print(f"   [TTS] 📍 診斷: API 配額超出")
                    print(f"   [TTS]    建議: 等待配額重置或升級方案")
                elif "UNAVAILABLE" in error_str or "INTERNAL" in error_str:
                    print(f"   [TTS] 📍 診斷: TTS 服務暫時不可用")
                    print(f"   [TTS]    建議: 稍後重試")
                elif "inline_data" in error_str or "no parts" in error_str.lower():
                    print(f"   [TTS] 📍 診斷: TTS 回應格式異常（可能是 Preview 模型問題）")
                    print(f"   [TTS]    建議: 縮短文字長度或稍後重試")
                # ============ 診斷結束 ============
                
                if attempt < max_retries:
                    # 指數退避 + 隨機抖動
                    base_delay = 2 ** attempt  # 1, 2, 4 秒
                    jitter = random.uniform(0, 0.5)  # 0-0.5 秒隨機抖動
                    delay = base_delay + jitter
                    
                    print(f"   [TTS] {part_name} 第 {attempt + 1} 次失敗")
                    print(f"   [TTS] 等待 {delay:.1f} 秒後重試...")
                    time.sleep(delay)
                else:
                    print(f"   [TTS] {part_name} 重試 {max_retries} 次後仍失敗")
        
        # 所有重試都失敗後才拋出異常
        raise last_error
    
    def _pcm_to_wav(
        self, 
        pcm_data: bytes, 
        channels: int = 1, 
        rate: int = 24000, 
        sample_width: int = 2
    ) -> bytes:
        """將 PCM 數據轉換為 WAV 格式"""
        buffer = BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm_data)
        
        buffer.seek(0)
        return buffer.read()
    
    def stitch_audio_clips(
        self, 
        audio_clips: List[bytes],
        silence_duration_ms: int = 800
    ) -> bytes:
        """
        將多個音頻片段無縫縫合
        
        Args:
            audio_clips: WAV 格式的音頻片段列表
            silence_duration_ms: 片段之間的靜音時長（毫秒）
            
        Returns:
            合併後的 WAV 音頻 bytes
        """
        print(f"📍[Audio Stitcher] 正在縫合 {len(audio_clips)} 個音頻片段...")
        
        if PYDUB_AVAILABLE:
            return self._stitch_with_pydub(audio_clips, silence_duration_ms)
        else:
            return self._stitch_basic_wav(audio_clips)
    
    def _stitch_with_pydub(
        self, 
        audio_clips: List[bytes],
        silence_duration_ms: int = 800
    ) -> bytes:
        """使用 pydub 縫合音頻（支援淡入淡出）"""
        combined = AudioSegment.empty()
        
        for i, clip_data in enumerate(audio_clips):
            # 從 bytes 載入音頻
            clip = AudioSegment.from_wav(BytesIO(clip_data))
            
            # 添加淡入（首片段）和淡出（尾片段）效果
            if i == 0:
                clip = clip.fade_in(500)  # 500ms 淡入
            if i == len(audio_clips) - 1:
                clip = clip.fade_out(1000)  # 1000ms 淡出
            
            # 縫合
            if i > 0:
                # 在片段之間添加短暫靜音過渡
                silence = AudioSegment.silent(duration=silence_duration_ms)
                combined += silence
            
            combined += clip
        
        # 導出為 WAV
        output_buffer = BytesIO()
        combined.export(output_buffer, format="wav")
        output_buffer.seek(0)
        
        print(f"   ✅ 音頻縫合完成！總時長: {len(combined) / 1000:.1f} 秒")
        return output_buffer.read()
    
    def _stitch_basic_wav(self, audio_clips: List[bytes]) -> bytes:
        """基礎 WAV 拼接（不需要 pydub）"""
        if not audio_clips:
            return b""
        
        # 讀取第一個檔案獲取參數
        first_clip = BytesIO(audio_clips[0])
        with wave.open(first_clip, 'rb') as wf:
            params = wf.getparams()
            sample_rate = wf.getframerate()
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
        
        # 合併所有 PCM 數據
        all_frames = b""
        for clip_data in audio_clips:
            clip_buffer = BytesIO(clip_data)
            with wave.open(clip_buffer, 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                all_frames += frames
                # 添加 0.5 秒靜音
                silence_frames = b'\x00' * int(sample_rate * channels * sample_width * 0.5)
                all_frames += silence_frames
        
        # 寫入新的 WAV
        output_buffer = BytesIO()
        with wave.open(output_buffer, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            wf.writeframes(all_frames)
        
        output_buffer.seek(0)
        print(f"   ✅ 基礎 WAV 拼接完成")
        return output_buffer.read()
    
    def create_streaming_bgm_mixer(self, stage2_result: Dict[str, Any] = None):
        """
        創建串流 BGM 混合器（用於即時混合每個 TTS 片段）
        
        Returns:
            StreamingBGMMixer 實例
        """
        return StreamingBGMMixer(stage2_result)
    
    def _apply_bgm_mixing(
        self, 
        voice_audio: bytes,
        stage2_result: Dict[str, Any]
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        將語音與背景音樂混合
        
        Args:
            voice_audio: 語音音頻 bytes
            stage2_result: 二階分析結果（用於提取情緒）
            
        Returns:
            Tuple of:
            - 混合後的音頻 bytes（如果無 BGM 則返回原語音）
            - BGM 狀態字典 {"success": bool, "method": str, "error": str|None}
        """
        print("\n" + "=" * 50)
        print("🎵 開始 BGM 混音流程")
        print("=" * 50)
        
        bgm_status = {
            "success": False,
            "method": "none",
            "error": None,
            "voice_only": True
        }
        
        try:
            from conflict_analyzer.audio_mixer import AudioMixer
            
            # 從 stage2 提取情緒標籤
            emotion = "healing"  # 預設為療癒
            if isinstance(stage2_result, dict):
                # 嘗試從不同欄位提取情緒
                if stage2_result.get("sentiment_vibe"):
                    emotion = stage2_result["sentiment_vibe"]
                elif stage2_result.get("attachment_dynamic"):
                    # 從依附動態中提取關鍵詞
                    dynamic = str(stage2_result["attachment_dynamic"]).lower()
                    if any(word in dynamic for word in ["焦慮", "anxiety"]):
                        emotion = "calm"
                    elif any(word in dynamic for word in ["悲傷", "sad"]):
                        emotion = "sadness"
                    elif any(word in dynamic for word in ["恐懼", "fear"]):
                        emotion = "fear"
                    elif any(word in dynamic for word in ["脆弱", "vulnerable"]):
                        emotion = "vulnerability"
            
            print(f"📍[BGM Mixing] 情緒標籤: {emotion}")
            print(f"📍[BGM Mixing] 語音大小: {len(voice_audio)} bytes")
            
            # 初始化混音器（不需要自動下載，因為會使用 Lyria）
            mixer = AudioMixer(auto_download=False)
            
            # 優先使用 Lyria 生成原創 BGM
            # 如果 Lyria 失敗，會自動降級到本地 BGM
            print("📍[BGM Mixing] 嘗試使用 Lyria 生成原創 BGM...")
            
            mixed_audio = mixer.mix_voice_with_lyria(
                voice_bytes=voice_audio,
                emotion=emotion,
                voice_format="wav"
            )
            
            # 檢查混音是否真的成功（比較大小）
            if len(mixed_audio) > len(voice_audio) * 1.1:  # 混入 BGM 後應該更大
                bgm_status = {
                    "success": True,
                    "method": "lyria",
                    "error": None,
                    "voice_only": False
                }
                print(f"✅ [BGM Mixing] 混音完成！輸出大小: {len(mixed_audio)} bytes")
            else:
                bgm_status = {
                    "success": False,
                    "method": "fallback",
                    "error": "混音輸出大小異常，可能使用純語音",
                    "voice_only": True
                }
                print(f"⚠️ [BGM Mixing] 混音可能未成功（輸出大小: {len(mixed_audio)} vs 原始: {len(voice_audio)}）")
            
            return mixed_audio, bgm_status
            
        except ImportError as e:
            error_msg = f"AudioMixer 模組載入失敗: {e}"
            print(f"⚠️ {error_msg}")
            print("   這可能是因為 pydub 未安裝")
            print("   返回純語音（無背景音樂）")
            bgm_status = {
                "success": False,
                "method": "none",
                "error": error_msg,
                "voice_only": True
            }
            return voice_audio, bgm_status
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            print(f"\n🚨 [BGM Mixing] 混音過程失敗!")
            print(f"   錯誤類型: {type(e).__name__}")
            print(f"   錯誤訊息: {e}")
            print("   📍 診斷建議：")
            print("      1. 查看上方的 Lyria API 錯誤訊息")
            print("      2. 確認 GEMINI_API_KEY 有 Lyria 音樂生成權限")
            print("      3. 檢查 assets/bgm/ 資料夾是否有 MP3/WAV 檔案")
            print("      4. 檢查網路連線是否正常")
            print("   返回純語音（無背景音樂）")
            bgm_status = {
                "success": False,
                "method": "none",
                "error": error_msg,
                "voice_only": True
            }
            return voice_audio, bgm_status
    
    def generate_healing_audio(
        self,
        stage1_result: Dict[str, Any],
        stage2_result: Dict[str, Any],
        stage3_result: Dict[str, Any],
        system_prompt: str,
        voice: str = "warm_female",
        output_dir: Optional[Path] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        完整流程：生成分段療育文稿並串接為完整音頻
        
        流程：
        1. 生成帶有 [PART_X] 標籤的文稿
        2. 拆分文稿為多個片段
        3. 順序生成每個片段的音頻
        4. 使用 pydub 縫合所有片段
        
        Args:
            stage1_result: 一階分析結果
            stage2_result: 二階分析結果
            stage3_result: 三階分析結果
            system_prompt: 第四階 System Prompt
            voice: 聲音選項
            output_dir: 可選的輸出目錄
            progress_callback: 進度回調函數 (current, total, message)
            
        Returns:
            {
                "script": str,           # 完整文稿
                "audio_base64": str,     # Base64 編碼的 WAV 音頻
                "duration_estimate": float,  # 估算時長（秒）
                "voice": str,            # 使用的聲音
                "parts_count": int       # 片段數量
            }
        """
        print("\n" + "=" * 50)
        print("🎵 開始生成療育音頻（分段串接模式）")
        print("=" * 50)
        
        # 1. 生成文稿
        if progress_callback:
            progress_callback(1, 6, "正在生成療育文稿...")
        
        script = self.generate_healing_script(
            stage1_result,
            stage2_result,
            stage3_result,
            system_prompt
        )
        
        # 2. 拆分文稿
        if progress_callback:
            progress_callback(2, 6, "正在拆分文稿片段...")
        
        parts = split_script_by_parts(script)
        total_parts = len(parts)
        
        # 3. 順序生成每個片段的音頻（帶斷點續傳和狀態追蹤）
        print(f"\n[Sequential TTS] 開始順序生成 {total_parts} 個音頻片段（含自動重試）...")
        
        audio_clips = []
        failed_parts = []
        successful_parts = []
        
        for i, (part_name, content) in enumerate(parts, 1):
            # 更新進度（每個片段獨立追蹤）
            if progress_callback:
                progress_callback(
                    2 + i, 
                    2 + total_parts + 2,  # 文稿 + 拆分 + 每個片段 + 縫合 + 混音
                    f"正在生成音頻片段 {i}/{total_parts}..."
                )
            
            try:
                audio_data = self.text_to_speech_single(content, voice, part_name)
                audio_clips.append(audio_data)
                successful_parts.append(part_name)
                print(f"   [進度] 已完成 {len(successful_parts)}/{total_parts} 個片段")
            except Exception as e:
                failed_parts.append({"part": part_name, "error": str(e)})
                print(f"   [跳過] {part_name} 最終生成失敗: {e}")
                # 繼續處理下一個片段（斷點續傳原則）
                continue
        
        # 統計結果
        success_rate = len(successful_parts) / total_parts * 100 if total_parts > 0 else 0
        print(f"\n[TTS 統計] 成功: {len(successful_parts)}/{total_parts} ({success_rate:.0f}%)")
        
        if failed_parts:
            print(f"[TTS 統計] 失敗片段: {[p['part'] for p in failed_parts]}")
        
        # 局部可用性：即使部分失敗也返回已完成的部分
        if not audio_clips:
            raise Exception("所有音頻片段生成失敗，無法產生任何音頻")
        
        # 4. 縫合音頻
        if progress_callback:
            progress_callback(4, 5, "正在編織您的專屬療癒能量...")
        
        stitched_audio = self.stitch_audio_clips(audio_clips)
        
        # 5. 混音：加入背景音樂 (如果可用)
        if progress_callback:
            progress_callback(5, 5, "正在融合療癒氛圍音樂...")
        
        final_audio, bgm_status = self._apply_bgm_mixing(stitched_audio, stage2_result)
        
        # 儲存（如果指定了目錄）
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / "healing_audio.wav"
            with open(output_path, "wb") as f:
                f.write(final_audio)
            print(f"[儲存] 已儲存: {output_path}")
        
        # 計算完成度
        is_complete = len(failed_parts) == 0
        completion_rate = len(successful_parts) / total_parts * 100 if total_parts > 0 else 0
        
        print("\n" + "=" * 50)
        if is_complete:
            print("[完成] 療育音頻生成完成（100%）")
        else:
            print(f"[部分完成] 療育音頻生成 {completion_rate:.0f}%（{len(failed_parts)} 個片段失敗）")
        print(f"   - 成功片段: {len(successful_parts)}/{total_parts}")
        print(f"   - 總長度: {len(final_audio)} bytes")
        print(f"   - BGM 狀態: {bgm_status.get('method', 'unknown')}")
        print("=" * 50 + "\n")
        
        return {
            "script": script,
            "audio_base64": base64.b64encode(final_audio).decode("utf-8"),
            "duration_estimate": len(script) * 0.12,  # 估算時長（秒）
            "voice": voice,
            "parts_count": len(successful_parts),
            "total_parts": total_parts,
            "failed_parts": failed_parts,  # 新增：失敗片段詳情
            "is_complete": is_complete,     # 新增：是否完整
            "completion_rate": completion_rate,  # 新增：完成率
            "bgm_status": bgm_status
        }


# 便捷函數
def generate_healing_audio_from_analysis(
    stage1: Dict[str, Any],
    stage2: Dict[str, Any],
    stage3: Dict[str, Any],
    system_prompt: str,
    voice: str = "warm_female"
) -> Dict[str, Any]:
    """
    便捷函數：從分析結果生成療育音頻（自動分段串接）
    
    Returns:
        {
            "script": str,           # 完整文稿
            "audio_base64": str,     # Base64 編碼的 WAV 音頻
            "duration_estimate": float,  # 估算時長
            "voice": str,            # 使用的聲音
            "parts_count": int       # 片段數量
        }
    """
    generator = HealingAudioGenerator()
    return generator.generate_healing_audio(
        stage1_result=stage1,
        stage2_result=stage2,
        stage3_result=stage3,
        system_prompt=system_prompt,
        voice=voice
    )
