"""
Lumina 心語 - Replicate MusicGen 備用音樂生成模組
使用 Replicate 託管的 Meta MusicGen 模型生成療癒背景音樂

這是 Google Lyria 的備用方案，當 Lyria API 權限不可用時使用。

使用方式：
1. 註冊 Replicate: https://replicate.com (可用 GitHub 登入)
2. 取得 API Token: https://replicate.com/account/api-tokens
3. 設定環境變數: REPLICATE_API_TOKEN=your_token
"""

import os
import base64
import requests
import time
from io import BytesIO
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

# 情緒到音樂提示詞的映射
EMOTION_TO_PROMPT = {
    # 中文情緒標籤
    "焦慮": "calm ambient meditation music, soft pads, slow tempo 60bpm, peaceful atmosphere",
    "憤怒": "gentle soothing ambient, soft piano, calming nature sounds, 65bpm",
    "悲傷": "melancholic ambient piano, tender emotional, slow and peaceful, 55bpm",
    "恐懼": "safe warm ambient, protective atmosphere, gentle synths, reassuring, 58bpm",
    "困惑": "clarity meditation music, bell tones, zen garden, mindfulness, 62bpm",
    
    # 英文情緒標籤
    "vulnerability": "gentle intimate piano, soft ambient pads, therapeutic music, 60bpm",
    "fear": "safe soothing ambient, warm protective atmosphere, gentle, 55bpm",
    "anger": "calming peaceful waves, gentle nature sounds, relaxation, 65bpm",
    "sadness": "melancholic tender piano, emotional ambient, healing, 55bpm",
    "anxiety": "relaxing zen garden, calm meditation, spa music, 60bpm",
    "growth": "uplifting hopeful ambient, gentle strings, positive energy, 72bpm",
    "healing": "healing frequency ambient, 432hz, meditation, therapeutic, 60bpm",
    
    # 預設
    "default": "peaceful meditation ambient music, soft piano and pads, calming atmosphere, therapeutic, 66bpm"
}


@dataclass
class ReplicateMusicConfig:
    """Replicate MusicGen 配置"""
    duration: int = 30  # 生成時長（秒）- Replicate 限制最多 30 秒
    model_version: str = "melody"  # small, medium, melody, large
    temperature: float = 1.0
    top_k: int = 250
    top_p: float = 0.0
    classifier_free_guidance: int = 3


class ReplicateMusicGenerator:
    """
    Replicate MusicGen 音樂生成器
    
    使用 Replicate 託管的 Meta MusicGen 模型生成背景音樂
    作為 Google Lyria 的備用方案
    """
    
    # Replicate MusicGen 模型
    MODEL_ID = "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedead"
    
    # 備用模型（更便宜）
    MODEL_ID_SMALL = "pphu/musicgen-small:b98e1f72d64dc9f1c6d8e1e4d7c4e90a2c2e6a9f8b7d6e5c4f3a2b1c0d9e8f7a"
    
    def __init__(self, api_token: Optional[str] = None):
        """
        初始化 Replicate 生成器
        
        Args:
            api_token: Replicate API Token（可選，會從環境變數讀取）
        """
        self.api_token = api_token or os.getenv("REPLICATE_API_TOKEN")
        
        if not self.api_token:
            print("⚠️ REPLICATE_API_TOKEN 未設定")
            print("   請前往 https://replicate.com/account/api-tokens 取得 API Token")
            print("   然後設定環境變數: REPLICATE_API_TOKEN=your_token")
        
        self.base_url = "https://api.replicate.com/v1"
    
    def is_available(self) -> bool:
        """檢查 Replicate API 是否可用"""
        return bool(self.api_token)
    
    def get_music_prompt(self, emotion: str) -> str:
        """
        根據情緒獲取音樂生成提示詞
        
        Args:
            emotion: 情緒標籤
            
        Returns:
            音樂生成的英文提示詞
        """
        emotion_lower = emotion.lower()
        
        # 精確匹配
        if emotion_lower in EMOTION_TO_PROMPT:
            return EMOTION_TO_PROMPT[emotion_lower]
        
        # 模糊匹配
        for key, prompt in EMOTION_TO_PROMPT.items():
            if key in emotion_lower or emotion_lower in key:
                return prompt
        
        # 預設
        return EMOTION_TO_PROMPT["default"]
    
    def generate_bgm(
        self,
        emotion: str = "healing",
        duration_seconds: int = 30,
        config: Optional[ReplicateMusicConfig] = None
    ) -> bytes:
        """
        生成背景音樂
        
        Args:
            emotion: 情緒標籤
            duration_seconds: 目標時長（實際會生成到 Replicate 上限）
            config: 可選的生成配置
            
        Returns:
            WAV 音頻 bytes
        """
        if not self.is_available():
            raise ValueError("REPLICATE_API_TOKEN 未設定，無法使用 Replicate API")
        
        print("\n" + "=" * 50)
        print("🎼 開始 Replicate MusicGen 音樂生成")
        print("=" * 50)
        
        # 獲取音樂提示詞
        prompt = self.get_music_prompt(emotion)
        print(f"📍[Replicate] 情緒: {emotion}")
        print(f"📍[Replicate] 提示詞: {prompt}")
        
        # 設定參數
        cfg = config or ReplicateMusicConfig()
        duration = min(duration_seconds, 30)  # Replicate 限制最多 30 秒
        
        print(f"📍[Replicate] 目標時長: {duration} 秒")
        
        try:
            # 發送生成請求
            headers = {
                "Authorization": f"Token {self.api_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "version": self.MODEL_ID.split(":")[-1],
                "input": {
                    "prompt": prompt,
                    "duration": duration,
                    "model_version": cfg.model_version,
                    "output_format": "wav",
                    "normalization_strategy": "peak"
                }
            }
            
            print("📍[Replicate] 發送生成請求...")
            
            response = requests.post(
                f"{self.base_url}/predictions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 201:
                raise Exception(f"Replicate API 錯誤: {response.status_code} - {response.text}")
            
            prediction = response.json()
            prediction_id = prediction.get("id")
            
            print(f"📍[Replicate] 預測 ID: {prediction_id}")
            print("📍[Replicate] 等待生成完成...")
            
            # 輪詢等待結果
            max_wait = 120  # 最多等待 120 秒
            poll_interval = 2
            waited = 0
            
            while waited < max_wait:
                status_response = requests.get(
                    f"{self.base_url}/predictions/{prediction_id}",
                    headers=headers,
                    timeout=10
                )
                
                status_data = status_response.json()
                status = status_data.get("status")
                
                if status == "succeeded":
                    output_url = status_data.get("output")
                    if output_url:
                        print(f"✅ [Replicate] 生成成功！")
                        
                        # 下載音頻
                        audio_response = requests.get(output_url, timeout=60)
                        if audio_response.status_code == 200:
                            audio_data = audio_response.content
                            print(f"📍[Replicate] 下載完成: {len(audio_data)} bytes")
                            
                            print("=" * 50)
                            print(f"✅ Replicate 音樂生成完成！時長約 {duration} 秒")
                            print("=" * 50 + "\n")
                            
                            return audio_data
                        else:
                            raise Exception(f"下載音頻失敗: {audio_response.status_code}")
                    else:
                        raise Exception("生成成功但沒有輸出 URL")
                
                elif status == "failed":
                    error = status_data.get("error", "未知錯誤")
                    raise Exception(f"生成失敗: {error}")
                
                elif status == "canceled":
                    raise Exception("生成被取消")
                
                # 仍在處理中
                time.sleep(poll_interval)
                waited += poll_interval
                
                if waited % 10 == 0:
                    print(f"   ⏳ 已等待 {waited} 秒...")
            
            raise Exception(f"生成超時（等待了 {max_wait} 秒）")
            
        except requests.exceptions.Timeout:
            raise Exception("Replicate API 請求超時")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Replicate API 網路錯誤: {e}")
    
    def generate_and_loop(
        self,
        emotion: str = "healing",
        target_duration_seconds: int = 300
    ) -> bytes:
        """
        生成音樂並循環拼接到目標時長
        
        因為 Replicate 限制最多 30 秒，需要循環拼接
        
        Args:
            emotion: 情緒標籤
            target_duration_seconds: 目標時長（秒）
            
        Returns:
            循環拼接後的 WAV 音頻 bytes
        """
        try:
            from pydub import AudioSegment
            
            # 生成基礎片段
            base_audio_bytes = self.generate_bgm(emotion, duration_seconds=30)
            
            # 載入音頻
            base_audio = AudioSegment.from_wav(BytesIO(base_audio_bytes))
            base_duration = len(base_audio)  # 毫秒
            
            target_ms = target_duration_seconds * 1000
            
            if base_duration >= target_ms:
                # 不需要循環
                output = base_audio[:target_ms]
            else:
                # 循環拼接
                loops_needed = (target_ms // base_duration) + 1
                print(f"📍[Replicate] 循環拼接 {loops_needed} 次...")
                
                looped = base_audio * loops_needed
                output = looped[:target_ms]
            
            # 添加淡入淡出
            fade_duration = min(3000, target_ms // 4)
            output = output.fade_in(fade_duration).fade_out(fade_duration)
            
            # 輸出為 WAV
            output_buffer = BytesIO()
            output.export(output_buffer, format="wav")
            output_buffer.seek(0)
            
            return output_buffer.read()
            
        except ImportError:
            print("⚠️ pydub 未安裝，無法循環拼接")
            return base_audio_bytes


# 便捷函數
def generate_bgm_replicate(emotion: str = "healing", duration_sec: int = 30) -> bytes:
    """
    便捷函數：使用 Replicate 生成背景音樂
    
    Args:
        emotion: 情緒標籤
        duration_sec: 時長（秒，最多 30）
        
    Returns:
        WAV 音頻 bytes
    """
    generator = ReplicateMusicGenerator()
    return generator.generate_bgm(emotion, duration_sec)


def is_replicate_available() -> bool:
    """檢查 Replicate API 是否可用"""
    return bool(os.getenv("REPLICATE_API_TOKEN"))


# 模組資訊
__all__ = [
    "ReplicateMusicGenerator",
    "ReplicateMusicConfig",
    "generate_bgm_replicate",
    "is_replicate_available",
    "EMOTION_TO_PROMPT"
]
