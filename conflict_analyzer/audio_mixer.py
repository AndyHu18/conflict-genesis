"""
Lumina 心語 - 音頻混音模組 (Audio Mixer)
將療癒語音與背景音樂混合輸出

核心功能：
1. 載入語音和 BGM
2. 自動調整音量（語音保持，BGM 降低 20dB）
3. 自動裁切/循環 BGM 對齊語音長度
4. 淡入淡出效果
5. 輸出混音後的音頻
"""

import os
import random
from pathlib import Path
from io import BytesIO
from typing import Optional, Dict, Any, List

# 嘗試導入 pydub
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    print("⚠️ pydub 未安裝，混音功能不可用")


# 情緒到 BGM 風格的映射
EMOTION_TO_BGM_STYLE = {
    "焦慮": "calm",
    "憤怒": "gentle",
    "悲傷": "ambient",
    "恐懼": "soothing",
    "困惑": "meditative",
    "vulnerability": "ambient",
    "fear": "soothing",
    "anger": "gentle",
    "sadness": "ambient",
    "anxiety": "calm",
    "default": "healing"
}


class AudioMixer:
    """
    音頻混音器：將療癒語音與背景音樂混合
    
    使用方式：
        mixer = AudioMixer()
        mixed_audio = mixer.mix_voice_with_bgm(voice_bytes, emotion="calm")
    """
    
    def __init__(self, bgm_folder: Optional[Path] = None, auto_download: bool = True):
        """
        初始化混音器
        
        Args:
            bgm_folder: 背景音樂文件夾路徑。如果不指定，使用預設的 assets/bgm/
            auto_download: 是否自動下載 BGM（如果文件夾為空）
        """
        if not PYDUB_AVAILABLE:
            raise ImportError("pydub 未安裝，請執行 pip install pydub")
        
        # 設定 BGM 文件夾
        if bgm_folder:
            self.bgm_folder = Path(bgm_folder)
        else:
            self.bgm_folder = Path(__file__).parent.parent / "assets" / "bgm"
        
        # 確保文件夾存在
        self.bgm_folder.mkdir(parents=True, exist_ok=True)
        
        # 混音參數（專業級設定）
        self.config = {
            "bgm_volume_reduction": -20,  # BGM 降低 20dB（輕柔包裹感）
            "fade_in_duration": 3000,     # 淡入 3 秒
            "fade_out_duration": 5000,    # 淡出 5 秒
            "crossfade_duration": 500,    # 交叉淡化 0.5 秒
        }
        
        # 自動下載 BGM（如果需要）
        if auto_download and not self.get_available_bgm():
            self._ensure_bgm_available()
    
    def _ensure_bgm_available(self):
        """
        確保有可用的 BGM
        
        嘗試順序：
        1. 調用 BGMResourceManager 下載
        2. 生成程序化環境音
        """
        try:
            from conflict_analyzer.bgm_manager import BGMResourceManager
            
            manager = BGMResourceManager(self.bgm_folder)
            manager.download_sample_bgm()
            
        except Exception as e:
            print(f"⚠️ BGM 自動下載失敗: {e}")
    
    def get_available_bgm(self) -> List[Path]:
        """
        獲取可用的 BGM 文件列表
        
        Returns:
            BGM 文件路徑列表
        """
        supported_formats = [".mp3", ".wav", ".ogg", ".m4a", ".flac"]
        bgm_files = []
        
        if self.bgm_folder.exists():
            for f in self.bgm_folder.iterdir():
                if f.suffix.lower() in supported_formats:
                    bgm_files.append(f)
        
        return bgm_files
    
    def select_bgm(self, emotion: str = "default") -> Optional[Path]:
        """
        根據情緒選擇合適的 BGM
        
        Args:
            emotion: 情緒標籤（如 calm, healing, anxiety）
            
        Returns:
            選中的 BGM 文件路徑，如果沒有可用的 BGM 則返回 None
        """
        bgm_files = self.get_available_bgm()
        
        if not bgm_files:
            print("⚠️ BGM 文件夾為空，將輸出純語音")
            return None
        
        # 嘗試找到匹配情緒的 BGM（文件名包含情緒關鍵詞）
        style = EMOTION_TO_BGM_STYLE.get(emotion.lower(), "healing")
        
        for bgm in bgm_files:
            if style.lower() in bgm.stem.lower():
                print(f"📍[AudioMixer] 選擇匹配 BGM: {bgm.name}")
                return bgm
        
        # 如果沒有匹配的，隨機選擇一個
        selected = random.choice(bgm_files)
        print(f"📍[AudioMixer] 隨機選擇 BGM: {selected.name}")
        return selected
    
    def load_audio(self, audio_data: bytes, format: str = "wav") -> AudioSegment:
        """
        從 bytes 載入音頻
        
        Args:
            audio_data: 音頻數據 bytes
            format: 音頻格式
            
        Returns:
            AudioSegment 對象
        """
        buffer = BytesIO(audio_data)
        return AudioSegment.from_file(buffer, format=format)
    
    def prepare_bgm(self, bgm: AudioSegment, target_duration: int) -> AudioSegment:
        """
        準備 BGM：調整長度以匹配語音
        
        Args:
            bgm: 背景音樂 AudioSegment
            target_duration: 目標時長（毫秒）
            
        Returns:
            調整後的 BGM
        """
        bgm_duration = len(bgm)
        
        if bgm_duration >= target_duration:
            # BGM 太長，裁切
            result = bgm[:target_duration]
            print(f"   📐 BGM 裁切至 {target_duration/1000:.1f} 秒")
        else:
            # BGM 太短，循環拼接
            loops_needed = (target_duration // bgm_duration) + 1
            result = bgm * loops_needed
            result = result[:target_duration]
            print(f"   🔁 BGM 循環 {loops_needed} 次並裁切至 {target_duration/1000:.1f} 秒")
        
        return result
    
    def apply_effects(self, audio: AudioSegment) -> AudioSegment:
        """
        應用淡入淡出效果
        
        Args:
            audio: 原始音頻
            
        Returns:
            處理後的音頻
        """
        fade_in = self.config["fade_in_duration"]
        fade_out = self.config["fade_out_duration"]
        
        # 確保淡入淡出時長不超過音頻長度的一半
        audio_duration = len(audio)
        max_fade = audio_duration // 3
        
        fade_in = min(fade_in, max_fade)
        fade_out = min(fade_out, max_fade)
        
        return audio.fade_in(fade_in).fade_out(fade_out)
    
    def mix_voice_with_bgm(
        self,
        voice_bytes: bytes,
        emotion: str = "default",
        voice_format: str = "wav",
        bgm_path: Optional[Path] = None
    ) -> bytes:
        """
        將語音與背景音樂混合
        
        這是主要的混音方法。
        
        Args:
            voice_bytes: 語音音頻的 bytes
            emotion: 情緒標籤（用於選擇 BGM 風格）
            voice_format: 語音格式
            bgm_path: 可選的指定 BGM 路徑
            
        Returns:
            混合後的 WAV 音頻 bytes
        """
        print("\n" + "=" * 50)
        print("🎵 開始音頻混音 (Audio Mixing)")
        print("=" * 50)
        
        # 1. 載入語音
        print("📍[AudioMixer] 載入語音...")
        voice = self.load_audio(voice_bytes, voice_format)
        voice_duration = len(voice)
        print(f"   ✅ 語音時長: {voice_duration/1000:.1f} 秒")
        
        # 2. 選擇並載入 BGM
        if bgm_path is None:
            bgm_path = self.select_bgm(emotion)
        
        if bgm_path is None:
            # 沒有 BGM，只返回處理後的語音
            print("   ⚠️ 無可用 BGM，返回純語音")
            result = self.apply_effects(voice)
            output_buffer = BytesIO()
            result.export(output_buffer, format="wav")
            output_buffer.seek(0)
            return output_buffer.read()
        
        # 3. 載入 BGM
        print(f"📍[AudioMixer] 載入 BGM: {bgm_path.name}")
        bgm = AudioSegment.from_file(str(bgm_path))
        
        # 4. 準備 BGM（調整長度）
        print("📍[AudioMixer] 準備 BGM...")
        # BGM 需要比語音長一點，為了淡出效果
        total_duration = voice_duration + self.config["fade_out_duration"]
        bgm = self.prepare_bgm(bgm, total_duration)
        
        # 5. 調整 BGM 音量
        volume_reduction = self.config["bgm_volume_reduction"]
        bgm = bgm + volume_reduction  # pydub 使用 + 運算符調整 dB
        print(f"   🔊 BGM 音量降低 {abs(volume_reduction)}dB")
        
        # 6. 混音（疊加）
        print("📍[AudioMixer] 執行混音...")
        # 先對 BGM 應用淡入淡出
        bgm = self.apply_effects(bgm)
        
        # 疊加：語音覆蓋在 BGM 上
        # 語音從頭開始疊加
        mixed = bgm.overlay(voice, position=0)
        
        # 7. 輸出
        output_buffer = BytesIO()
        mixed.export(output_buffer, format="wav")
        output_buffer.seek(0)
        
        print("=" * 50)
        print(f"✅ 混音完成！總時長: {len(mixed)/1000:.1f} 秒")
        print("=" * 50 + "\n")
        
        return output_buffer.read()
    
    def mix_with_ducking(
        self,
        voice_bytes: bytes,
        emotion: str = "default",
        voice_format: str = "wav",
        duck_amount: int = -6
    ) -> bytes:
        """
        進階混音：帶有自動閃避 (Ducking) 效果
        
        當語音出現時，BGM 自動降低音量；語音停頓時，BGM 稍微升回。
        這是專業療癒音頻的標準做法。
        
        注意：這個功能需要更複雜的實作，目前僅作為接口預留。
        
        Args:
            voice_bytes: 語音音頻
            emotion: 情緒標籤
            voice_format: 語音格式
            duck_amount: Ducking 時額外降低的 dB（預設 -6dB）
            
        Returns:
            混合後的音頻 bytes
        """
        # TODO: 實作真正的 ducking 邏輯
        # 目前先使用基礎混音
        print("📍[AudioMixer] Ducking 功能開發中，使用標準混音")
        return self.mix_voice_with_bgm(voice_bytes, emotion, voice_format)
    
    def mix_voice_with_lyria(
        self,
        voice_bytes: bytes,
        emotion: str = "healing",
        voice_format: str = "wav"
    ) -> bytes:
        """
        使用 Lyria 生成原創 BGM 並與語音混合
        
        這是最推薦的方法：使用 Google Lyria API 根據情緒
        動態生成原創療癒音樂。
        
        Args:
            voice_bytes: 語音音頻
            emotion: 情緒標籤
            voice_format: 語音格式
            
        Returns:
            混合後的音頻 bytes
        """
        print("\n" + "=" * 50)
        print("🎼 使用 Lyria 生成原創 BGM")
        print("=" * 50)
        
        try:
            from conflict_analyzer.lyria_music import LyriaMusicGenerator
            
            # 載入語音計算時長
            voice = self.load_audio(voice_bytes, voice_format)
            voice_duration_sec = len(voice) // 1000 + 10  # 多 10 秒確保足夠
            
            print(f"📍[Lyria] 語音時長: {len(voice)/1000:.1f}s，生成 {voice_duration_sec}s BGM")
            
            # 使用 Lyria 生成 BGM
            lyria = LyriaMusicGenerator()
            bgm_bytes = lyria.generate_bgm_sync(emotion, voice_duration_sec)
            
            # 降採樣到 24kHz（與語音對齊）
            bgm_24khz = lyria.resample_to_24khz(bgm_bytes)
            
            # 載入並處理 BGM
            bgm = AudioSegment.from_wav(BytesIO(bgm_24khz))
            
            # 調整音量
            volume_reduction = self.config["bgm_volume_reduction"]
            bgm = bgm + volume_reduction
            print(f"   🔊 Lyria BGM 音量降低 {abs(volume_reduction)}dB")
            
            # 裁切到語音長度
            total_duration = len(voice) + self.config["fade_out_duration"]
            bgm = self.prepare_bgm(bgm, total_duration)
            
            # 應用淡入淡出
            bgm = self.apply_effects(bgm)
            
            # 混音
            print("📍[AudioMixer] 執行混音...")
            mixed = bgm.overlay(voice, position=0)
            
            # 輸出
            output_buffer = BytesIO()
            mixed.export(output_buffer, format="wav")
            output_buffer.seek(0)
            
            print("=" * 50)
            print(f"✅ Lyria 混音完成！總時長: {len(mixed)/1000:.1f} 秒")
            print("=" * 50 + "\n")
            
            return output_buffer.read()
            
        except Exception as e:
            print(f"\n⚠️ Lyria 生成失敗: {e}")
            print("   錯誤類型:", type(e).__name__)
            
            # 嘗試 Replicate MusicGen 作為第二備用
            print("   嘗試 Replicate MusicGen 備用方案...")
            try:
                from conflict_analyzer.replicate_music import ReplicateMusicGenerator, is_replicate_available
                
                if is_replicate_available():
                    replicate_gen = ReplicateMusicGenerator()
                    
                    # 計算需要的時長
                    voice = self.load_audio(voice_bytes, voice_format)
                    voice_duration_sec = len(voice) // 1000 + 10
                    
                    # 使用 Replicate 生成並循環
                    bgm_bytes = replicate_gen.generate_and_loop(emotion, voice_duration_sec)
                    
                    # 載入並處理 BGM
                    bgm = AudioSegment.from_wav(BytesIO(bgm_bytes))
                    
                    # 調整音量
                    volume_reduction = self.config["bgm_volume_reduction"]
                    bgm = bgm + volume_reduction
                    print(f"   🔊 Replicate BGM 音量降低 {abs(volume_reduction)}dB")
                    
                    # 裁切到語音長度
                    total_duration = len(voice) + self.config["fade_out_duration"]
                    bgm = self.prepare_bgm(bgm, total_duration)
                    
                    # 應用淡入淡出
                    bgm = self.apply_effects(bgm)
                    
                    # 混音
                    print("📍[AudioMixer] 執行 Replicate BGM 混音...")
                    mixed = bgm.overlay(voice, position=0)
                    
                    # 輸出
                    output_buffer = BytesIO()
                    mixed.export(output_buffer, format="wav")
                    output_buffer.seek(0)
                    
                    print("=" * 50)
                    print(f"✅ Replicate 混音完成！總時長: {len(mixed)/1000:.1f} 秒")
                    print("=" * 50 + "\n")
                    
                    return output_buffer.read()
                else:
                    print("   ⚠️ REPLICATE_API_TOKEN 未設定，跳過 Replicate")
                    
            except ImportError:
                print("   ⚠️ Replicate 模組未找到")
            except Exception as replicate_error:
                print(f"   ⚠️ Replicate 也失敗了: {replicate_error}")
            
            # 降級使用本地 BGM
            print("   降級使用本地 BGM...")
            try:
                result = self.mix_voice_with_bgm(voice_bytes, emotion, voice_format)
                return result
            except Exception as fallback_error:
                print(f"\n🚨 [AudioMixer] 完全失敗！無法進行混音")
                print(f"   Lyria 失敗原因: {e}")
                print(f"   本地 BGM 失敗原因: {fallback_error}")
                print(f"   📍 診斷建議：")
                print(f"      1. 設定 REPLICATE_API_TOKEN 使用 Replicate 備用方案")
                print(f"      2. 檢查 GEMINI_API_KEY 是否有 Lyria 權限")
                print(f"      3. 檢查 assets/bgm/ 資料夾是否有 MP3/WAV 檔案")
                print(f"      4. 確認 FFmpeg 已正確安裝")
                print("   將返回純語音（無背景音樂）")
                return voice_bytes


# 便捷函數
def mix_audio(
    voice_bytes: bytes,
    emotion: str = "default",
    bgm_folder: Optional[Path] = None,
    use_lyria: bool = True
) -> bytes:
    """
    便捷函數：將語音與 BGM 混合
    
    Args:
        voice_bytes: 語音 bytes
        emotion: 情緒標籤
        bgm_folder: BGM 文件夾路徑
        use_lyria: 是否使用 Lyria 生成 BGM（預設 True）
        
    Returns:
        混合後的音頻 bytes
    """
    mixer = AudioMixer(bgm_folder, auto_download=not use_lyria)
    
    if use_lyria:
        return mixer.mix_voice_with_lyria(voice_bytes, emotion)
    else:
        return mixer.mix_voice_with_bgm(voice_bytes, emotion)


def mix_audio_with_lyria(voice_bytes: bytes, emotion: str = "healing") -> bytes:
    """
    便捷函數：使用 Lyria 生成原創 BGM 並混合
    
    Args:
        voice_bytes: 語音 bytes
        emotion: 情緒標籤
        
    Returns:
        混合後的音頻 bytes
    """
    mixer = AudioMixer(auto_download=False)
    return mixer.mix_voice_with_lyria(voice_bytes, emotion)
