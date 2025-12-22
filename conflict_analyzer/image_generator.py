"""
Lumina 心語 - 圖像生成模組 v5.0
使用 Gemini 3 Pro Image Preview (Nano Banana Pro) 生成高質量視覺化圖像
改用 google-genai SDK 調用（經測試驗證可用）
"""

import os
import base64
import time
import random
from pathlib import Path
from typing import Optional, Dict, Any, List

from google import genai
from google.genai import types

from conflict_analyzer.visual_architect import VisualArchitect, SlideContent, generate_visual_slides

# 模型常量 - Gemini 3 Pro Image Preview (Nano Banana Pro)
IMAGE_MODEL = "gemini-3-pro-image-preview"


class ImageGenerator:
    """使用 Gemini 3 Pro Image + VisualArchitect 生成高質量分析視覺化圖像"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("需要 GEMINI_API_KEY 環境變數")
        
        # 使用 google-genai SDK
        self.client = genai.Client(api_key=self.api_key)
        self.visual_architect = VisualArchitect(api_key=self.api_key)
        
        print(f"📍[ImageGenerator] 已初始化，使用模型: {IMAGE_MODEL}")
    
    def generate_image_from_prompt(
        self,
        prompt: str,
        stage_num: int = 0,
        resolution: str = "2048x2048",  # 預設 2K
        aspect_ratio: str = "16:9",
        max_retries: int = 3,
        is_summary: bool = False
    ) -> Optional[bytes]:
        """
        使用 Gemini 3 Pro Image Preview 生成圖像（透過 SDK）
        
        Args:
            prompt: 視覺意向指令（含繁體中文）
            stage_num: 階段編號（用於日誌）
            resolution: 解析度
            aspect_ratio: 寬高比
            max_retries: 最大重試次數
            is_summary: 是否為 Stage 4 總結圖
            
        Returns:
            PNG 圖像的 bytes，失敗時返回 None
        """
        print(f"   [Stage {stage_num}] 正在使用 Gemini 3 Pro Image SDK 渲染...")
        print(f"   [Stage {stage_num}] 🔍 Prompt 長度: {len(prompt)} 字元")
        print(f"   [Stage {stage_num}]    is_summary: {is_summary}")
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                print(f"   [Stage {stage_num}] 正在發送 SDK 請求... (嘗試 {attempt + 1}/{max_retries + 1})")
                
                # 使用 SDK 調用
                response = self.client.models.generate_content(
                    model=IMAGE_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"]
                    )
                )
                
                print(f"   [Stage {stage_num}] 📥 收到 SDK 回應")
                
                # 檢查回應
                if not response.candidates:
                    print(f"   [Stage {stage_num}] ⚠️ 無 candidates")
                    last_error = "無 candidates"
                    continue
                
                candidate = response.candidates[0]
                if not hasattr(candidate, 'content') or not candidate.content:
                    print(f"   [Stage {stage_num}] ⚠️ 無 content")
                    last_error = "無 content"
                    continue
                
                if not candidate.content.parts:
                    print(f"   [Stage {stage_num}] ⚠️ 無 parts")
                    last_error = "無 parts"
                    continue
                
                print(f"   [Stage {stage_num}]    parts 數量: {len(candidate.content.parts)}")
                
                # 提取圖像數據
                for idx, part in enumerate(candidate.content.parts):
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_data = part.inline_data.data
                        if image_data:
                            # SDK 返回的是 bytes，不需要 base64 解碼
                            print(f"   [Stage {stage_num}] ✅ 圖像渲染成功 ({len(image_data)} bytes)")
                            return image_data
                    elif hasattr(part, 'text') and part.text:
                        text_preview = part.text[:100] if part.text else "(空)"
                        print(f"   [Stage {stage_num}] ⚠️ 收到文字回應: {text_preview}...")
                
                print(f"   [Stage {stage_num}] ❌ 回應中無圖像數據")
                last_error = "回應中無圖像數據"
                
            except Exception as e:
                last_error = str(e)
                print(f"   [Stage {stage_num}] ❌ 錯誤類型: {type(e).__name__}")
                print(f"   [Stage {stage_num}] ❌ 錯誤訊息: {e}")
                
                if attempt < max_retries:
                    # 指數退避 + 隨機抖動
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    print(f"   [Stage {stage_num}] 等待 {delay:.1f} 秒後重試...")
                    time.sleep(delay)
                else:
                    print(f"   [Stage {stage_num}] 重試 {max_retries} 次後仍失敗")
        
        print(f"   [Stage {stage_num}] 最終失敗: {last_error}")
        return None
    
    def generate_all_images_with_slides(
        self,
        stage1_data: Dict[str, Any],
        stage2_data: Dict[str, Any],
        stage3_data: Dict[str, Any],
        output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        使用 VisualArchitect 生成高質量圖像和簡報內容
        
        ⚠️ 採用「序列化隊列」模式，避免 API 並行限制：
        - 每張圖之間加入冷卻時間
        - 限制並發數為 1（Tier 1 建議）
        - 指數退避重試機制
        
        流程：
        1. VisualArchitect 分析數據並生成結構化簡報內容
        2. 序列化使用簡報中的 image_prompt 呼叫 Gemini Image
        3. 返回圖像和簡報數據
        """
        print("\n" + "=" * 60)
        print("🎨 開始生成視覺化簡報（序列化隊列模式）")
        print("=" * 60)
        
        # Step 1: VisualArchitect 生成結構化簡報內容
        print("\n📍[Step 1/2] VisualArchitect 正在分析數據...")
        slides = self.visual_architect.generate_all_slides(
            stage1_data, 
            stage2_data, 
            stage3_data
        )
        print(f"   ✅ 已生成 {len(slides)} 張簡報結構")
        
        # Step 2: 序列化生成圖像（避免並行限制）
        print("\n📍[Step 2/2] 開始序列化渲染圖像...")
        print("   ⚠️ 為避免 API 限流，每張圖之間會有冷卻時間")
        
        images = {}
        stage_keys = ["stage1", "stage2", "stage3", "combined"]
        total_slides = len(slides)
        
        # ============ 序列化隊列：逐張生成 ============
        for i, slide in enumerate(slides):
            key = stage_keys[i]
            is_stage4 = (i == 3)
            progress = f"[{i+1}/{total_slides}]"
            
            print(f"\n   {progress} 📋 正在處理：{slide.slide_title}")
            print(f"   {progress} 🎯 Prompt 長度：{len(slide.image_prompt)} 字元")
            
            if is_stage4:
                print(f"   {progress} 🧠 Stage 4 融合圖 - 較長處理時間")
            
            # 生成圖像
            image_bytes = self.generate_image_from_prompt(
                slide.image_prompt, 
                slide.stage_id,
                is_summary=is_stage4
            )
            images[key] = image_bytes
            
            if image_bytes:
                print(f"   {progress} ✅ 生成成功！({len(image_bytes)} bytes)")
                
                # 儲存圖像
                if output_dir:
                    output_path = output_dir / f"{key}_visualization.png"
                    with open(output_path, "wb") as f:
                        f.write(image_bytes)
                    print(f"   {progress} 💾 已儲存：{output_path.name}")
            else:
                print(f"   {progress} ❌ 生成失敗")
            
            # ============ 冷卻時間：避免 API 限流 ============
            # Tier 1 限制很嚴格，每次請求後等待一段時間
            if i < total_slides - 1:  # 最後一張不需要等
                cooldown = 3 + random.uniform(0, 2)  # 3-5 秒冷卻
                print(f"   {progress} ⏳ 冷卻中... ({cooldown:.1f}s)")
                time.sleep(cooldown)
        
        slides_dict = [slide.to_dict() for slide in slides]
        
        # 統計結果
        success_count = sum(1 for v in images.values() if v is not None)
        
        print("\n" + "=" * 60)
        print(f"✅ 視覺化簡報生成完成！成功：{success_count}/{total_slides}")
        print("=" * 60 + "\n")
        
        return {
            "images": images,
            "slides": slides_dict
        }
    
    def generate_all_images(
        self,
        stage1_data: Dict[str, Any],
        stage2_data: Dict[str, Any],
        stage3_data: Dict[str, Any],
        output_dir: Optional[Path] = None
    ) -> Dict[str, Optional[bytes]]:
        """
        生成全部四張圖像（向後兼容的接口）
        
        Returns:
            包含四張圖像 bytes 的字典
        """
        result = self.generate_all_images_with_slides(
            stage1_data, stage2_data, stage3_data, output_dir
        )
        return result["images"]
    
    @staticmethod
    def bytes_to_base64(image_bytes: bytes) -> str:
        """將圖像 bytes 轉換為 base64 字串"""
        return base64.b64encode(image_bytes).decode('utf-8')


def generate_images_with_context(
    stage1: Dict[str, Any],
    stage2: Dict[str, Any],
    stage3: Dict[str, Any]
) -> Dict[str, Any]:
    """
    便捷函數：生成基於上下文的視覺化圖像和簡報數據
    
    Returns:
        {
            "images": {
                "stage1": base64_str,
                "stage2": base64_str,
                "stage3": base64_str,
                "combined": base64_str
            },
            "slides": [
                {
                    "slide_title": str,
                    "core_insight": str,
                    "data_bullets": [str, str, str],
                    "image_prompt": str,
                    "stage_id": int,
                    "color_theme": str
                },
                ...
            ]
        }
    """
    generator = ImageGenerator()
    result = generator.generate_all_images_with_slides(stage1, stage2, stage3)
    
    # 轉換圖像為 base64
    images_base64 = {}
    for key, img_bytes in result["images"].items():
        if img_bytes:
            images_base64[key] = ImageGenerator.bytes_to_base64(img_bytes)
        else:
            images_base64[key] = None
    
    return {
        "images": images_base64,
        "slides": result["slides"]
    }


# Legacy 函數保持向後兼容
def create_summary_prompts(
    stage1: Dict[str, Any],
    stage2: Dict[str, Any],
    stage3: Dict[str, Any]
) -> Dict[str, str]:
    """
    Legacy: 創建用於圖像生成的簡化摘要提示詞
    建議使用 generate_images_with_context 代替
    """
    slides = generate_visual_slides(stage1, stage2, stage3)
    return {
        "stage1": slides[0]["image_prompt"] if len(slides) > 0 else "",
        "stage2": slides[1]["image_prompt"] if len(slides) > 1 else "",
        "stage3": slides[2]["image_prompt"] if len(slides) > 2 else "",
        "combined": slides[3]["image_prompt"] if len(slides) > 3 else ""
    }
