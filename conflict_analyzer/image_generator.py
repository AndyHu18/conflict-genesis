"""
衝突基因 - 圖像生成模組 v2.0
整合 VisualArchitect 生成高質量、基於上下文的視覺化圖像
"""

import os
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types

from conflict_analyzer.visual_architect import VisualArchitect, SlideContent, generate_visual_slides

# 模型常量
IMAGE_MODEL = "imagen-4.0-generate-001"


class ImageGenerator:
    """使用 Imagen + VisualArchitect 生成高質量分析視覺化圖像"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("需要 GEMINI_API_KEY 環境變數")
        self.client = genai.Client(api_key=self.api_key)
        self.visual_architect = VisualArchitect(api_key=self.api_key)
    
    def generate_image_from_prompt(
        self,
        prompt: str,
        stage_num: int = 0
    ) -> Optional[bytes]:
        """
        根據英文 prompt 生成圖像
        
        Args:
            prompt: 英文視覺意向指令
            stage_num: 階段編號（用於日誌）
            
        Returns:
            PNG 圖像的 bytes，失敗時返回 None
        """
        try:
            print(f"   🎨 正在渲染 Stage {stage_num} 圖像...")
            
            response = self.client.models.generate_images(
                model=IMAGE_MODEL,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                )
            )
            
            if response.generated_images:
                image = response.generated_images[0].image
                print(f"   ✅ Stage {stage_num} 圖像渲染成功！")
                return image.image_bytes
            else:
                print(f"   ⚠️ Stage {stage_num} 圖像渲染無結果")
                return None
                
        except Exception as e:
            print(f"   ❌ 渲染圖像錯誤 (Stage {stage_num}): {e}")
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
        
        流程：
        1. VisualArchitect 分析數據並生成結構化簡報內容
        2. 使用簡報中的 image_prompt 呼叫 Imagen
        3. 返回圖像和簡報數據
        
        Args:
            stage1_data: 一階分析結果
            stage2_data: 二階分析結果
            stage3_data: 三階分析結果
            output_dir: 可選的輸出目錄
            
        Returns:
            {
                "images": {"stage1": bytes, "stage2": bytes, "stage3": bytes, "combined": bytes},
                "slides": [SlideContent dict x 4]
            }
        """
        print("\n" + "=" * 60)
        print("🎨 開始生成視覺化簡報（VisualArchitect 模式）")
        print("=" * 60)
        
        # Step 1: VisualArchitect 生成結構化簡報內容
        slides = self.visual_architect.generate_all_slides(
            stage1_data, 
            stage2_data, 
            stage3_data
        )
        
        # Step 2: 使用 slide.image_prompt 生成圖像
        print("\n📍[ImageGenerator] 開始渲染圖像...")
        images = {}
        stage_keys = ["stage1", "stage2", "stage3", "combined"]
        
        for i, slide in enumerate(slides):
            key = stage_keys[i]
            print(f"\n   📋 Slide {i+1}: {slide.slide_title}")
            print(f"   🎯 Prompt: {slide.image_prompt[:100]}...")
            
            image_bytes = self.generate_image_from_prompt(
                slide.image_prompt, 
                slide.stage_id
            )
            images[key] = image_bytes
            
            # 儲存圖像（如果指定目錄）
            if output_dir and image_bytes:
                output_path = output_dir / f"{key}_visualization.png"
                with open(output_path, "wb") as f:
                    f.write(image_bytes)
                print(f"   💾 已儲存：{output_path}")
        
        print("\n" + "=" * 60)
        print("✅ 視覺化簡報生成完成！")
        print("=" * 60 + "\n")
        
        return {
            "images": images,
            "slides": [slide.to_dict() for slide in slides]
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
