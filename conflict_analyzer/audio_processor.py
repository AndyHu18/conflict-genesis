"""
Conflict Genesis - Audio Processor
音訊預處理模組：格式轉換、驗證與切片
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class AudioInfo:
    """音訊檔案資訊"""
    file_path: str
    format: str
    duration_seconds: float
    file_size_bytes: int
    sample_rate: Optional[int] = None
    channels: Optional[int] = None


@dataclass
class AudioSegment:
    """音訊片段資訊"""
    file_path: str
    start_time: float  # 秒
    end_time: float    # 秒
    segment_index: int


class AudioProcessorError(Exception):
    """音訊處理錯誤"""
    pass


class AudioProcessor:
    """
    音訊預處理器
    負責格式驗證、轉換和切片操作
    """
    
    # Gemini API 支援的音訊格式 (包含 M4A)
    SUPPORTED_FORMATS = {
        'wav': 'audio/wav',
        'mp3': 'audio/mp3',
        'aiff': 'audio/aiff',
        'aac': 'audio/aac',
        'ogg': 'audio/ogg',
        'flac': 'audio/flac',
        'm4a': 'audio/mp4'  # M4A 格式 (Apple)
    }
    
    # 建議的最大音訊長度（分鐘）
    RECOMMENDED_MAX_DURATION_MINUTES = 30
    
    # Gemini 每秒音訊消耗的 token 數
    TOKENS_PER_SECOND = 32
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        初始化音訊處理器
        
        Args:
            temp_dir: 臨時檔案目錄，預設為系統臨時目錄
        """
        self.temp_dir = Path(temp_dir) if temp_dir else Path.cwd() / ".audio_temp"
        self.temp_dir.mkdir(exist_ok=True)
        
        # 檢查 FFmpeg 是否可用
        self._ffmpeg_available = self._check_ffmpeg()
        
    def _check_ffmpeg(self) -> bool:
        """檢查 FFmpeg 是否已安裝"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    @property
    def ffmpeg_available(self) -> bool:
        """FFmpeg 是否可用"""
        return self._ffmpeg_available
    
    def validate_audio_file(self, file_path: str) -> Tuple[bool, str]:
        """
        驗證音訊檔案
        
        Args:
            file_path: 音訊檔案路徑
            
        Returns:
            (驗證結果, 訊息)
        """
        path = Path(file_path)
        
        # 檢查檔案是否存在
        if not path.exists():
            return False, f"❌ 檔案不存在: {file_path}"
        
        # 檢查檔案是否為空
        if path.stat().st_size == 0:
            return False, "❌ 檔案為空"
        
        # 檢查副檔名
        ext = path.suffix.lower().lstrip('.')
        if ext not in self.SUPPORTED_FORMATS:
            supported = ", ".join(self.SUPPORTED_FORMATS.keys())
            return False, f"❌ 不支援的格式: {ext}。支援格式: {supported}"
        
        return True, f"✅ 檔案驗證通過: {path.name}"
    
    def get_audio_info(self, file_path: str) -> AudioInfo:
        """
        獲取音訊檔案資訊
        
        Args:
            file_path: 音訊檔案路徑
            
        Returns:
            AudioInfo 物件
        """
        path = Path(file_path)
        ext = path.suffix.lower().lstrip('.')
        file_size = path.stat().st_size
        
        duration = 0.0
        sample_rate = None
        channels = None
        
        if self._ffmpeg_available:
            try:
                # 使用 ffprobe 獲取詳細資訊
                result = subprocess.run(
                    [
                        "ffprobe",
                        "-v", "quiet",
                        "-print_format", "json",
                        "-show_format",
                        "-show_streams",
                        str(path)
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    import json
                    info = json.loads(result.stdout)
                    
                    # 獲取時長
                    if "format" in info and "duration" in info["format"]:
                        duration = float(info["format"]["duration"])
                    
                    # 獲取音訊流資訊
                    for stream in info.get("streams", []):
                        if stream.get("codec_type") == "audio":
                            sample_rate = int(stream.get("sample_rate", 0)) or None
                            channels = stream.get("channels", None)
                            if not duration and "duration" in stream:
                                duration = float(stream["duration"])
                            break
                            
            except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
                print(f"📍[AudioProcessor] ffprobe 分析失敗: {e}")
        
        # 如果無法獲取時長，嘗試使用 pydub
        if duration == 0.0:
            try:
                from pydub import AudioSegment as PydubSegment
                audio = PydubSegment.from_file(str(path))
                duration = len(audio) / 1000.0  # 毫秒轉秒
                sample_rate = audio.frame_rate
                channels = audio.channels
            except Exception as e:
                print(f"📍[AudioProcessor] pydub 分析失敗: {e}")
        
        return AudioInfo(
            file_path=str(path.absolute()),
            format=ext,
            duration_seconds=duration,
            file_size_bytes=file_size,
            sample_rate=sample_rate,
            channels=channels
        )
    
    def get_mime_type(self, file_path: str) -> str:
        """
        獲取音訊檔案的 MIME 類型
        
        Args:
            file_path: 音訊檔案路徑
            
        Returns:
            MIME 類型字串
        """
        ext = Path(file_path).suffix.lower().lstrip('.')
        return self.SUPPORTED_FORMATS.get(ext, "audio/mpeg")
    
    def convert_to_format(
        self,
        input_path: str,
        output_format: str = "mp3",
        output_path: Optional[str] = None
    ) -> str:
        """
        轉換音訊格式
        
        Args:
            input_path: 輸入檔案路徑
            output_format: 目標格式（預設 mp3）
            output_path: 輸出路徑（可選）
            
        Returns:
            轉換後的檔案路徑
        """
        if not self._ffmpeg_available:
            raise AudioProcessorError("❌ FFmpeg 未安裝，無法進行格式轉換")
        
        input_path = Path(input_path)
        if not output_path:
            output_path = self.temp_dir / f"{input_path.stem}.{output_format}"
        else:
            output_path = Path(output_path)
        
        print(f"📍[AudioProcessor] 轉換中: {input_path.name} → {output_path.name}")
        
        try:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",  # 覆寫輸出檔案
                    "-i", str(input_path),
                    "-vn",  # 無視訊
                    "-acodec", "libmp3lame" if output_format == "mp3" else "copy",
                    str(output_path)
                ],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                raise AudioProcessorError(f"FFmpeg 錯誤: {result.stderr}")
                
            return str(output_path)
            
        except subprocess.TimeoutExpired:
            raise AudioProcessorError("❌ 轉換超時")
    
    def estimate_tokens(self, duration_seconds: float) -> int:
        """
        估算音訊消耗的 token 數量
        
        Args:
            duration_seconds: 音訊時長（秒）
            
        Returns:
            預估 token 數量
        """
        return int(duration_seconds * self.TOKENS_PER_SECOND)
    
    def format_duration(self, seconds: float) -> str:
        """
        格式化時長為 MM:SS 格式
        
        Args:
            seconds: 秒數
            
        Returns:
            格式化的時間字串
        """
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def split_audio(
        self,
        file_path: str,
        segment_duration_seconds: int = 600,  # 10 分鐘
        overlap_seconds: int = 30
    ) -> List[AudioSegment]:
        """
        將長音訊切分為多個片段（滑動窗口）
        
        Args:
            file_path: 音訊檔案路徑
            segment_duration_seconds: 每個片段的時長（秒）
            overlap_seconds: 片段間的重疊時長（秒）
            
        Returns:
            AudioSegment 列表
        """
        if not self._ffmpeg_available:
            raise AudioProcessorError("❌ FFmpeg 未安裝，無法切分音訊")
        
        info = self.get_audio_info(file_path)
        total_duration = info.duration_seconds
        
        if total_duration <= segment_duration_seconds:
            # 不需要切分
            return [AudioSegment(
                file_path=file_path,
                start_time=0,
                end_time=total_duration,
                segment_index=0
            )]
        
        segments = []
        current_start = 0
        index = 0
        input_path = Path(file_path)
        
        while current_start < total_duration:
            end_time = min(current_start + segment_duration_seconds, total_duration)
            
            # 生成片段檔案
            output_path = self.temp_dir / f"{input_path.stem}_seg{index:03d}.mp3"
            
            try:
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i", str(input_path),
                        "-ss", str(current_start),
                        "-t", str(end_time - current_start),
                        "-acodec", "libmp3lame",
                        str(output_path)
                    ],
                    capture_output=True,
                    timeout=120
                )
                
                segments.append(AudioSegment(
                    file_path=str(output_path),
                    start_time=current_start,
                    end_time=end_time,
                    segment_index=index
                ))
                
            except subprocess.TimeoutExpired:
                print(f"📍[AudioProcessor] 警告：片段 {index} 切分超時")
            
            # 下一個片段（帶重疊）
            current_start = end_time - overlap_seconds
            if current_start >= total_duration - overlap_seconds:
                break
            index += 1
        
        print(f"📍[AudioProcessor] 已切分為 {len(segments)} 個片段")
        return segments
    
    def cleanup_temp_files(self):
        """清理臨時檔案"""
        import shutil
        if self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                print(f"📍[AudioProcessor] 已清理臨時目錄: {self.temp_dir}")
            except Exception as e:
                print(f"📍[AudioProcessor] 清理失敗: {e}")
