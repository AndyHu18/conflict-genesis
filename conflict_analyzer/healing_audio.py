"""
衝突基因 - 療育音頻生成模組 v2.0
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
    
    def text_to_speech_single(
        self,
        text: str,
        voice: str = "warm_female",
        part_name: str = ""
    ) -> bytes:
        """
        將單一片段文字轉換為語音
        
        Args:
            text: 要轉換的文字（應控制在 200 字以內）
            voice: 聲音選項
            part_name: 片段名稱（用於日誌）
            
        Returns:
            WAV 音頻的 bytes
        """
        voice_name = VOICE_OPTIONS.get(voice, "Kore")
        
        print(f"   🎙️ 正在生成 {part_name}... ({len(text)} 字)")
        
        try:
            response = self.client.models.generate_content(
                model=TTS_MODEL,
                contents=f"用溫柔、舒緩、療癒的語調緩慢朗讀以下文字。每個「...」處自然停頓。語速放慢，讓聽眾能感受到被包裹的安全感：\n\n{text}",
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
            
            # 獲取 PCM 數據
            pcm_data = response.candidates[0].content.parts[0].inline_data.data
            
            # 轉換為 WAV
            wav_data = self._pcm_to_wav(pcm_data)
            
            print(f"   ✅ {part_name} 生成完成 ({len(wav_data)} bytes)")
            return wav_data
            
        except Exception as e:
            print(f"   ❌ {part_name} 生成錯誤: {e}")
            raise
    
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
            progress_callback(1, 4, "正在生成療育文稿...")
        
        script = self.generate_healing_script(
            stage1_result,
            stage2_result,
            stage3_result,
            system_prompt
        )
        
        # 2. 拆分文稿
        if progress_callback:
            progress_callback(2, 4, "正在拆分文稿片段...")
        
        parts = split_script_by_parts(script)
        
        # 3. 順序生成每個片段的音頻
        if progress_callback:
            progress_callback(3, 4, f"正在生成 {len(parts)} 個音頻片段...")
        
        print(f"\n📍[Sequential TTS] 開始順序生成 {len(parts)} 個音頻片段...")
        audio_clips = []
        
        for i, (part_name, content) in enumerate(parts, 1):
            try:
                audio_data = self.text_to_speech_single(content, voice, part_name)
                audio_clips.append(audio_data)
            except Exception as e:
                print(f"   ⚠️ {part_name} 生成失敗，跳過: {e}")
                continue
        
        if not audio_clips:
            raise Exception("所有音頻片段生成失敗")
        
        # 4. 縫合音頻
        if progress_callback:
            progress_callback(4, 4, "正在編織您的專屬療癒能量...")
        
        final_audio = self.stitch_audio_clips(audio_clips)
        
        # 儲存（如果指定了目錄）
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / "healing_audio.wav"
            with open(output_path, "wb") as f:
                f.write(final_audio)
            print(f"💾 已儲存: {output_path}")
        
        print("\n" + "=" * 50)
        print("✅ 療育音頻生成完成！")
        print(f"   - 片段數量: {len(audio_clips)}")
        print(f"   - 總長度: {len(final_audio)} bytes")
        print("=" * 50 + "\n")
        
        return {
            "script": script,
            "audio_base64": base64.b64encode(final_audio).decode("utf-8"),
            "duration_estimate": len(script) * 0.12,  # 估算時長（秒）
            "voice": voice,
            "parts_count": len(audio_clips)
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
