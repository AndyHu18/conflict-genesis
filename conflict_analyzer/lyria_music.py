"""
Lumina 心語 - Lyria 音樂生成模組
使用 Google Lyria RealTime API 生成療癒背景音樂

核心功能：
1. 根據情緒標籤生成原創器樂背景音樂
2. 與 Gemini API 共用相同的身份驗證
3. 48kHz 高品質音頻輸出
4. 可調整 BPM、調性、密度等參數
"""

import os
import asyncio
import wave
from io import BytesIO
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# Google GenAI SDK
from google import genai
from google.genai import types

# 情緒到音樂風格的映射
EMOTION_TO_MUSIC_STYLE = {
    # 中文情緒標籤
    "焦慮": {"prompts": ["Calm Piano", "Soft Ambient"], "bpm": 60, "scale": "C_MAJOR"},
    "憤怒": {"prompts": ["Gentle Strings", "Peaceful"], "bpm": 65, "scale": "F_MAJOR"},
    "悲傷": {"prompts": ["Melancholic Piano", "Soft"], "bpm": 55, "scale": "A_MINOR"},
    "恐懼": {"prompts": ["Soothing Ambient", "Safe", "Warm"], "bpm": 58, "scale": "G_MAJOR"},
    "困惑": {"prompts": ["Clarity", "Meditative Bells"], "bpm": 62, "scale": "D_MAJOR"},
    
    # 英文情緒標籤
    "vulnerability": {"prompts": ["Gentle Piano", "Intimate"], "bpm": 60, "scale": "C_MAJOR"},
    "fear": {"prompts": ["Safe Ambient", "Soft Atmosphere"], "bpm": 55, "scale": "G_MAJOR"},
    "anger": {"prompts": ["Calming Waves", "Peace"], "bpm": 65, "scale": "F_MAJOR"},
    "sadness": {"prompts": ["Melancholic", "Tender Piano"], "bpm": 55, "scale": "A_MINOR"},
    "anxiety": {"prompts": ["Relaxing", "Zen Garden"], "bpm": 60, "scale": "C_MAJOR"},
    "growth": {"prompts": ["Uplifting Strings", "Hopeful"], "bpm": 72, "scale": "D_MAJOR"},
    "healing": {"prompts": ["Healing Frequency", "432Hz", "Ambient"], "bpm": 60, "scale": "C_MAJOR"},
    
    # 預設
    "default": {"prompts": ["Meditation Piano", "Peaceful Ambient"], "bpm": 66, "scale": "C_MAJOR"}
}


@dataclass
class LyriaMusicConfig:
    """Lyria 音樂生成配置"""
    bpm: int = 66
    scale: str = "C_MAJOR"
    temperature: float = 0.8
    density: float = 0.3  # 音符密度，療癒音樂應該較低
    duration_seconds: int = 300  # 5 分鐘


class LyriaMusicGenerator:
    """
    Lyria 音樂生成器
    
    使用 Google Lyria RealTime API 生成原創療癒音樂
    """
    
    # 支援的模型
    REALTIME_MODEL = "models/lyria-realtime-exp"  # 即時串流
    OFFLINE_MODEL = "lyria-002"  # 離線生成
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Lyria 生成器
        
        Args:
            api_key: Gemini API Key（可選，會從環境變數讀取）
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("需要 GEMINI_API_KEY 環境變數")
        
        # 使用 v1alpha API 版本（Lyria 需要）
        self.client = genai.Client(
            api_key=self.api_key,
            http_options={'api_version': 'v1alpha'}
        )
    
    def get_music_style(self, emotion: str) -> Dict[str, Any]:
        """
        根據情緒獲取音樂風格配置
        
        Args:
            emotion: 情緒標籤
            
        Returns:
            包含 prompts, bpm, scale 的配置字典
        """
        emotion_lower = emotion.lower()
        
        # 嘗試匹配情緒
        if emotion_lower in EMOTION_TO_MUSIC_STYLE:
            return EMOTION_TO_MUSIC_STYLE[emotion_lower]
        
        # 模糊匹配
        for key, style in EMOTION_TO_MUSIC_STYLE.items():
            if key in emotion_lower or emotion_lower in key:
                return style
        
        # 預設
        return EMOTION_TO_MUSIC_STYLE["default"]
    
    async def generate_bgm_realtime(
        self,
        emotion: str = "healing",
        duration_seconds: int = 300,
        config: Optional[LyriaMusicConfig] = None
    ) -> bytes:
        """
        使用 Lyria RealTime 生成背景音樂
        
        這是主要的音樂生成方法，使用即時串流 API。
        
        Args:
            emotion: 情緒標籤
            duration_seconds: 音樂時長（秒）
            config: 可選的音樂配置
            
        Returns:
            48kHz 立體聲 PCM 音頻 bytes
        """
        print("\n" + "=" * 50)
        print("🎼 開始 Lyria 音樂生成（RealTime）")
        print("=" * 50)
        
        # 獲取音樂風格
        style = self.get_music_style(emotion)
        print(f"📍[Lyria] 情緒: {emotion} → 風格: {style['prompts']}")
        
        # 設定配置
        bpm = config.bpm if config else style["bpm"]
        scale = config.scale if config else style["scale"]
        
        print(f"   🎵 BPM: {bpm}, Scale: {scale}")
        print(f"   ⏱️ 目標時長: {duration_seconds} 秒")
        
        audio_chunks = []
        
        try:
            # 連接到 Lyria RealTime
            async with self.client.aio.live.music.connect(
                model=self.REALTIME_MODEL
            ) as session:
                
                # 設定權重提示詞
                weighted_prompts = [
                    types.WeightedPrompt(text=prompt, weight=1.5)
                    for prompt in style["prompts"]
                ]
                await session.set_weighted_prompts(prompts=weighted_prompts)
                
                # 設定音樂生成配置
                await session.set_music_generation_config(
                    config=types.LiveMusicGenerationConfig(
                        bpm=bpm,
                        temperature=0.8,
                        scale=getattr(types.Scale, scale, types.Scale.C_MAJOR)
                    )
                )
                
                print("📍[Lyria] 開始接收音頻串流...")
                
                # 計算需要接收的音頻量
                # 48kHz * 2 channels * 2 bytes * seconds
                target_bytes = 48000 * 2 * 2 * duration_seconds
                received_bytes = 0
                
                async for message in session.receive():
                    if message.server_content and message.server_content.audio_chunks:
                        chunk = message.server_content.audio_chunks.data
                        audio_chunks.append(chunk)
                        received_bytes += len(chunk)
                        
                        # 進度報告
                        progress = (received_bytes / target_bytes) * 100
                        if int(progress) % 20 == 0:
                            print(f"   📊 進度: {progress:.0f}%")
                        
                        if received_bytes >= target_bytes:
                            break
            
            # 合併音頻
            pcm_data = b"".join(audio_chunks)
            
            # 轉換為 WAV
            wav_data = self._pcm_to_wav(pcm_data, channels=2, rate=48000)
            
            print("=" * 50)
            print(f"✅ Lyria 音樂生成完成！時長: {len(pcm_data) / (48000 * 2 * 2):.1f} 秒")
            print("=" * 50 + "\n")
            
            return wav_data
            
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            print(f"\n❌ Lyria 生成失敗!")
            print(f"   錯誤類型: {error_type}")
            print(f"   錯誤訊息: {error_msg}")
            
            # 診斷常見錯誤
            if "403" in error_msg or "PERMISSION_DENIED" in error_msg:
                print("   📍 診斷: API 權限不足")
                print("      建議: 確認 GEMINI_API_KEY 有 Lyria 音樂生成權限")
            elif "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                print("   📍 診斷: API 配額超出")
                print("      建議: 等待配額重置或升級方案")
            elif "UNAVAILABLE" in error_msg or "INTERNAL" in error_msg:
                print("   📍 診斷: Lyria 服務暫時不可用")
                print("      建議: 稍後重試")
            elif "models/lyria" in error_msg:
                print("   📍 診斷: Lyria 模型可能需要特殊權限")
                print("      建議: 確認 API Key 已啟用 Lyria 音樂功能")
            else:
                print("   📍 診斷: 未知錯誤")
                print("      建議: 檢查網路連線和 API Key 有效性")
            
            print("   將使用備用方案（本地 BGM 或純語音）...")
            raise
    
    def generate_bgm_sync(
        self,
        emotion: str = "healing",
        duration_seconds: int = 300
    ) -> bytes:
        """
        同步版本的 BGM 生成
        
        Args:
            emotion: 情緒標籤
            duration_seconds: 時長
            
        Returns:
            WAV 音頻 bytes
        """
        return asyncio.run(
            self.generate_bgm_realtime(emotion, duration_seconds)
        )
    
    def _pcm_to_wav(
        self,
        pcm_data: bytes,
        channels: int = 2,
        rate: int = 48000,
        sample_width: int = 2
    ) -> bytes:
        """
        將 PCM 數據轉換為 WAV 格式
        
        Args:
            pcm_data: 原始 PCM 數據
            channels: 聲道數
            rate: 取樣率
            sample_width: 樣本寬度（bytes）
            
        Returns:
            WAV 格式的 bytes
        """
        buffer = BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm_data)
        
        buffer.seek(0)
        return buffer.read()
    
    def resample_to_24khz(self, audio_48khz: bytes) -> bytes:
        """
        將 48kHz 音頻降採樣到 24kHz
        
        用於與 TTS 語音（24kHz）對齊
        
        Args:
            audio_48khz: 48kHz WAV 音頻
            
        Returns:
            24kHz WAV 音頻
        """
        try:
            from pydub import AudioSegment
            
            audio = AudioSegment.from_wav(BytesIO(audio_48khz))
            resampled = audio.set_frame_rate(24000)
            
            output = BytesIO()
            resampled.export(output, format="wav")
            output.seek(0)
            
            return output.read()
            
        except ImportError:
            print("⚠️ pydub 未安裝，無法重取樣")
            return audio_48khz


# 便捷函數
def generate_healing_bgm(emotion: str = "healing", duration_sec: int = 300) -> bytes:
    """
    便捷函數：生成療癒背景音樂
    
    Args:
        emotion: 情緒標籤
        duration_sec: 時長（秒）
        
    Returns:
        WAV 音頻 bytes
    """
    generator = LyriaMusicGenerator()
    return generator.generate_bgm_sync(emotion, duration_sec)


# 情緒映射表（供外部使用）
def get_emotion_music_mapping() -> Dict[str, Dict]:
    """
    獲取情緒到音樂風格的完整映射表
    
    Returns:
        映射表字典
    """
    return EMOTION_TO_MUSIC_STYLE.copy()
