"""
Lumina 心語 - 核心分析模組
一階：衝突演化追蹤器
二階：深層溯源與接納橋樑
三階：個人成長行動方案
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from google import genai
from google.genai import types

from .schemas import (
    ConflictAnalysisResult, Stage1Result, Stage2Result, Stage3Result,
    FullAnalysisResult, AnalysisError
)
from .prompts import (
    DEFAULT_STAGE1_PROMPT, DEFAULT_STAGE2_PROMPT, DEFAULT_STAGE3_PROMPT,
    get_analysis_prompt, get_stage2_prompt, get_stage3_prompt,
    SYSTEM_INSTRUCTION, DEFAULT_SYSTEM_PROMPT
)
from .audio_processor import AudioProcessor, AudioInfo


@dataclass
class AnalysisConfig:
    """分析配置"""
    model: str = "gemini-3-flash-preview"
    temperature: float = 0.7
    max_output_tokens: int = 8192
    include_reasoning: bool = True


class ConflictAnalyzerError(Exception):
    """衝突分析器錯誤"""
    pass


class ConflictAnalyzer:
    """
    衝突分析器
    支援三階分析：
    - 一階：衝突演化追蹤
    - 二階：深層溯源與接納橋樑
    - 三階：個人成長行動方案
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[AnalysisConfig] = None
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ConflictAnalyzerError("❌ 未找到 API Key")
        
        self.config = config or AnalysisConfig()
        self.client = genai.Client(api_key=self.api_key)
        self.audio_processor = AudioProcessor()
        
        print(f"📍[ConflictAnalyzer] 初始化完成，使用模型: {self.config.model}")
    
    def _upload_audio(self, file_path: str) -> Any:
        """上傳音訊檔案"""
        path = Path(file_path)
        mime_type = self.audio_processor.get_mime_type(file_path)
        
        print(f"📍[ConflictAnalyzer] 上傳音訊: {path.name}")
        
        try:
            uploaded_file = self.client.files.upload(file=str(path))
            print(f"📍[ConflictAnalyzer] 上傳成功: {uploaded_file.name}")
            return uploaded_file
        except Exception as e:
            raise ConflictAnalyzerError(f"❌ 音訊上傳失敗: {e}")
    
    def _fix_truncated_json(self, raw_text: str) -> str:
        """
        嘗試修復被截斷的 JSON 字符串
        
        常見情況：
        1. 末尾缺少 } 或 ]
        2. 字符串未正確閉合
        3. 多餘的逗號
        """
        import re
        
        text = raw_text.strip()
        
        # 統計開閉括號
        open_braces = text.count('{')
        close_braces = text.count('}')
        open_brackets = text.count('[')
        close_brackets = text.count(']')
        
        # 嘗試修復未閉合的字符串
        # 找最後一個未閉合的引號
        in_string = False
        escape_next = False
        for i, c in enumerate(text):
            if escape_next:
                escape_next = False
                continue
            if c == '\\':
                escape_next = True
                continue
            if c == '"':
                in_string = not in_string
        
        # 如果在字符串中結束，添加閉合引號
        if in_string:
            text += '"'
        
        # 移除末尾多餘的逗號
        text = re.sub(r',\s*$', '', text)
        text = re.sub(r',\s*}', '}', text)
        text = re.sub(r',\s*]', ']', text)
        
        # 補充缺失的括號
        missing_braces = open_braces - text.count('}')
        missing_brackets = open_brackets - text.count(']')
        
        text += ']' * missing_brackets
        text += '}' * missing_braces
        
        print(f"⚠️ [JSON修復] 補充了 {missing_braces} 個 '}}' 和 {missing_brackets} 個 ']'")
        
        return text
    
    
    def analyze_stage1(
        self,
        audio_path: str,
        additional_context: str = "",
        system_prompt: Optional[str] = None,
        verbose: bool = True
    ) -> Stage1Result:
        """
        【一階分析】衝突演化追蹤
        
        分析音訊中的衝突演化過程，輸出行為層面的觀察。
        """
        active_prompt = system_prompt if system_prompt else DEFAULT_STAGE1_PROMPT
        
        # 驗證音訊
        is_valid, message = self.audio_processor.validate_audio_file(audio_path)
        if not is_valid:
            raise ConflictAnalyzerError(message)
        
        if verbose:
            print(message)
        
        # 獲取音訊資訊
        audio_info = self.audio_processor.get_audio_info(audio_path)
        if verbose:
            print(f"📍[一階分析] 音訊時長: {self.audio_processor.format_duration(audio_info.duration_seconds)}")
        
        # 上傳音訊
        uploaded_file = self._upload_audio(audio_path)
        
        # 構建提示詞
        analysis_prompt = get_analysis_prompt(additional_context)
        
        if verbose:
            print(f"📍[一階分析] 開始分析：衝突演化追蹤...")
        
        try:
            response = self.client.models.generate_content(
                model=self.config.model,
                contents=[uploaded_file, analysis_prompt],
                config=types.GenerateContentConfig(
                    system_instruction=active_prompt,
                    temperature=self.config.temperature,
                    max_output_tokens=self.config.max_output_tokens,
                    response_mime_type="application/json",
                    response_schema=Stage1Result
                )
            )
        except Exception as e:
            raise ConflictAnalyzerError(f"❌ 一階分析 API 調用失敗: {e}")
        
        if verbose:
            print(f"📍[一階分析] ✅ 完成")
        
        try:
            raw_text = response.text
            # 嘗試直接解析
            try:
                result_data = json.loads(raw_text)
            except json.JSONDecodeError as parse_err:
                # 嘗試修復截斷的 JSON
                print(f"⚠️ [一階分析] JSON 解析失敗，嘗試修復: {parse_err}")
                fixed_text = self._fix_truncated_json(raw_text)
                result_data = json.loads(fixed_text)
            
            result = Stage1Result.model_validate(result_data)
            return result
        except Exception as e:
            # 打印原始響應以便調試
            print(f"❌ [一階分析] 原始響應（前 500 字元）: {response.text[:500]}...")
            raise ConflictAnalyzerError(f"❌ 一階結果解析失敗: {e}")
    
    def analyze_stage2(
        self,
        stage1_result: dict,
        additional_context: str = "",
        system_prompt: Optional[str] = None,
        verbose: bool = True
    ) -> Stage2Result:
        """
        【二階分析】深層溯源與接納橋樑
        
        基於一階分析結果，探索深層心理動力。
        上下文：一階結果
        """
        active_prompt = system_prompt if system_prompt else DEFAULT_STAGE2_PROMPT
        
        if verbose:
            print(f"📍[二階分析] 開始分析：深層溯源與接納橋樑...")
        
        # 構建二階提示詞（以一階結果為上下文）
        stage2_prompt = get_stage2_prompt(stage1_result, additional_context)
        
        try:
            response = self.client.models.generate_content(
                model=self.config.model,
                contents=[stage2_prompt],
                config=types.GenerateContentConfig(
                    system_instruction=active_prompt,
                    temperature=self.config.temperature,
                    max_output_tokens=self.config.max_output_tokens,
                    response_mime_type="application/json",
                    response_schema=Stage2Result
                )
            )
        except Exception as e:
            raise ConflictAnalyzerError(f"❌ 二階分析 API 調用失敗: {e}")
        
        if verbose:
            print(f"📍[二階分析] ✅ 完成")
        
        try:
            raw_text = response.text
            # 嘗試直接解析
            try:
                result_data = json.loads(raw_text)
            except json.JSONDecodeError as parse_err:
                # 嘗試修復截斷的 JSON
                print(f"⚠️ [二階分析] JSON 解析失敗，嘗試修復: {parse_err}")
                fixed_text = self._fix_truncated_json(raw_text)
                result_data = json.loads(fixed_text)
            
            result = Stage2Result.model_validate(result_data)
            return result
        except Exception as e:
            # 打印原始響應以便調試
            print(f"❌ [二階分析] 原始響應（前 500 字元）: {response.text[:500]}...")
            raise ConflictAnalyzerError(f"❌ 二階結果解析失敗: {e}")
    
    def analyze_stage3(
        self,
        stage1_result: dict,
        stage2_result: dict,
        additional_context: str = "",
        system_prompt: Optional[str] = None,
        verbose: bool = True
    ) -> Stage3Result:
        """
        【三階分析】個人成長行動方案
        
        基於一階和二階分析結果，提供「我能做什麼」的行動方案。
        上下文：一階結果 + 二階結果
        """
        active_prompt = system_prompt if system_prompt else DEFAULT_STAGE3_PROMPT
        
        if verbose:
            print(f"📍[三階分析] 開始分析：個人成長行動方案...")
        
        # 構建三階提示詞（以一階＋二階結果為上下文）
        stage3_prompt = get_stage3_prompt(stage1_result, stage2_result, additional_context)
        
        try:
            response = self.client.models.generate_content(
                model=self.config.model,
                contents=[stage3_prompt],
                config=types.GenerateContentConfig(
                    system_instruction=active_prompt,
                    temperature=self.config.temperature,
                    max_output_tokens=self.config.max_output_tokens,
                    response_mime_type="application/json",
                    response_schema=Stage3Result
                )
            )
        except Exception as e:
            raise ConflictAnalyzerError(f"❌ 三階分析 API 調用失敗: {e}")
        
        if verbose:
            print(f"📍[三階分析] ✅ 完成")
        
        try:
            raw_text = response.text
            # 嘗試直接解析
            try:
                result_data = json.loads(raw_text)
            except json.JSONDecodeError as parse_err:
                # 嘗試修復截斷的 JSON
                print(f"⚠️ [三階分析] JSON 解析失敗，嘗試修復: {parse_err}")
                fixed_text = self._fix_truncated_json(raw_text)
                result_data = json.loads(fixed_text)
            
            result = Stage3Result.model_validate(result_data)
            return result
        except Exception as e:
            # 打印原始響應以便調試
            print(f"❌ [三階分析] 原始響應（前 500 字元）: {response.text[:500]}...")
            raise ConflictAnalyzerError(f"❌ 三階結果解析失敗: {e}")
    
    def full_analysis(
        self,
        audio_path: str,
        additional_context: str = "",
        stage1_prompt: Optional[str] = None,
        stage2_prompt: Optional[str] = None,
        stage3_prompt: Optional[str] = None,
        verbose: bool = True
    ) -> Tuple[Stage1Result, Stage2Result, Stage3Result]:
        """
        完整三階段分析：自動串接，上下文逐層傳遞
        
        流程：
        1. 一階分析（音訊 → 衝突演化地圖）
        2. 二階分析（一階結果 → 深層溯源）
        3. 三階分析（一階+二階結果 → 個人成長方案）
        
        Returns:
            (一階結果, 二階結果, 三階結果)
        """
        # ==================== 一階分析 ====================
        if verbose:
            print("\n" + "=" * 60)
            print("🔬 【第一階段】衝突演化追蹤")
            print("    分析音訊中的行為模式與互動軌跡")
            print("=" * 60)
        
        stage1_result = self.analyze_stage1(
            audio_path=audio_path,
            additional_context=additional_context,
            system_prompt=stage1_prompt,
            verbose=verbose
        )
        
        # ==================== 二階分析 ====================
        if verbose:
            print("\n" + "=" * 60)
            print("💡 【第二階段】深層溯源與接納橋樑")
            print("    探索行為背後的心理動力與冰山下方")
            print("    📥 上下文傳遞：一階分析結果")
            print("=" * 60)
        
        stage1_dict = stage1_result.model_dump()
        
        stage2_result = self.analyze_stage2(
            stage1_result=stage1_dict,
            additional_context=additional_context,
            system_prompt=stage2_prompt,
            verbose=verbose
        )
        
        # ==================== 三階分析 ====================
        if verbose:
            print("\n" + "=" * 60)
            print("🌱 【第三階段】個人成長行動方案")
            print("    聚焦「我能做什麼」的具體行動")
            print("    📥 上下文傳遞：一階 + 二階分析結果")
            print("=" * 60)
        
        stage2_dict = stage2_result.model_dump()
        
        stage3_result = self.analyze_stage3(
            stage1_result=stage1_dict,
            stage2_result=stage2_dict,
            additional_context=additional_context,
            system_prompt=stage3_prompt,
            verbose=verbose
        )
        
        # ==================== 完成 ====================
        if verbose:
            print("\n" + "=" * 60)
            print("✅ 三階段完整分析完成")
            print("=" * 60)
        
        return stage1_result, stage2_result, stage3_result
    
    # 向後相容
    def analyze(
        self,
        audio_path: str,
        additional_context: str = "",
        system_prompt: Optional[str] = None,
        verbose: bool = True
    ) -> ConflictAnalysisResult:
        """向後相容的一階分析方法"""
        result = self.analyze_stage1(audio_path, additional_context, system_prompt, verbose)
        return ConflictAnalysisResult.model_validate(result.model_dump())
    
    def analyze_with_retry(
        self,
        audio_path: str,
        max_retries: int = 3,
        **kwargs
    ) -> ConflictAnalysisResult:
        """帶重試機制的一階分析"""
        import time
        
        last_error = None
        for attempt in range(max_retries):
            try:
                return self.analyze(audio_path, **kwargs)
            except ConflictAnalyzerError as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"⚠️ 分析失敗 (嘗試 {attempt + 1}/{max_retries})，{wait_time} 秒後重試...")
                    time.sleep(wait_time)
        
        raise last_error
    
    def get_audio_info(self, audio_path: str) -> AudioInfo:
        """獲取音訊檔案資訊"""
        return self.audio_processor.get_audio_info(audio_path)
