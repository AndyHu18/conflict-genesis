"""
Lumina 心語 - 簡報卡片合成器 (Slide Composer)
將 Imagen 生成的圖片與分析文字融合為專業簡報卡片
"""

import io
import os
import sys
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont, ImageFilter


# ============ 字體發現邏輯 ============

def _find_chinese_font() -> str:
    """
    跨平台發現中文字體路徑
    優先級：專案內嵌 → 系統字體 → Fallback
    
    Returns:
        字體檔案路徑
    """
    # 1. 專案內嵌字體（部署時最可靠）
    project_fonts = [
        Path(__file__).parent.parent / "assets" / "fonts" / "NotoSansCJK-Regular.ttc",
        Path(__file__).parent.parent / "assets" / "fonts" / "NotoSansTC-Regular.ttf",
        Path(__file__).parent.parent / "assets" / "fonts" / "SourceHanSans-Regular.ttc",
    ]
    for font_path in project_fonts:
        if font_path.exists():
            print(f"📍[SlideComposer] 使用內嵌字體: {font_path.name}")
            return str(font_path)
    
    # 2. Windows 系統字體
    if sys.platform == "win32":
        windows_fonts = [
            r"C:\Windows\Fonts\msjh.ttc",       # 微軟正黑體
            r"C:\Windows\Fonts\msyh.ttc",       # 微軟雅黑
            r"C:\Windows\Fonts\mingliu.ttc",    # 細明體
            r"C:\Windows\Fonts\simsun.ttc",     # 宋體
            r"C:\Windows\Fonts\simhei.ttf",     # 黑體
            r"C:\Windows\Fonts\NotoSansCJK-Regular.ttc",
        ]
        for font_path in windows_fonts:
            if os.path.exists(font_path):
                print(f"📍[SlideComposer] 使用 Windows 字體: {Path(font_path).name}")
                return font_path
    
    # 3. macOS 系統字體
    elif sys.platform == "darwin":
        mac_fonts = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
        ]
        for font_path in mac_fonts:
            if os.path.exists(font_path):
                print(f"📍[SlideComposer] 使用 macOS 字體: {Path(font_path).name}")
                return font_path
    
    # 4. Linux 系統字體（Render/Railway 部署環境）
    else:
        linux_fonts = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # fallback ASCII
        ]
        for font_path in linux_fonts:
            if os.path.exists(font_path):
                print(f"📍[SlideComposer] 使用 Linux 字體: {Path(font_path).name}")
                return font_path
    
    # 5. 最終 fallback：Pillow 內建字體（不支援中文，但不會崩潰）
    print("⚠️ [SlideComposer] 未找到中文字體，使用 Pillow 內建字體")
    return None


# ============ 階段配色 ============

STAGE_STYLES = {
    1: {
        "name": "衝突演化",
        "bg_color": (245, 158, 11, 200),    # 橙黃 + alpha
        "text_color": (255, 255, 255),       # 白字
        "accent_color": (251, 191, 36),      # 亮橙
    },
    2: {
        "name": "深層溯源",
        "bg_color": (8, 145, 178, 200),      # 深青 + alpha
        "text_color": (255, 255, 255),
        "accent_color": (34, 211, 238),      # 亮青
    },
    3: {
        "name": "成長方案",
        "bg_color": (34, 197, 94, 200),      # 嫩綠 + alpha
        "text_color": (255, 255, 255),
        "accent_color": (74, 222, 128),      # 亮綠
    },
    4: {
        "name": "療癒旅程",
        "bg_color": (236, 72, 153, 200),     # 和諧粉 + alpha
        "text_color": (255, 255, 255),
        "accent_color": (244, 114, 182),     # 亮粉
    },
}


@dataclass
class SlideLayout:
    """簡報卡片布局配置"""
    width: int = 1024
    height: int = 1024
    padding: int = 40
    title_font_size: int = 56
    insight_font_size: int = 32
    bullet_font_size: int = 26
    overlay_height_ratio: float = 0.45  # 底部遮罩高度比例


class SlideComposer:
    """簡報卡片合成器：將圖片與文字融合"""
    
    def __init__(self, layout: Optional[SlideLayout] = None):
        self.layout = layout or SlideLayout()
        self.font_path = _find_chinese_font()
        
        # 預載字體
        self._title_font = self._load_font(self.layout.title_font_size)
        self._insight_font = self._load_font(self.layout.insight_font_size)
        self._bullet_font = self._load_font(self.layout.bullet_font_size)
    
    def _load_font(self, size: int) -> ImageFont.FreeTypeFont:
        """載入指定大小的字體"""
        if self.font_path:
            try:
                return ImageFont.truetype(self.font_path, size)
            except Exception as e:
                print(f"⚠️ [SlideComposer] 字體載入失敗: {e}")
        
        # Fallback: 使用 Pillow 預設字體
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            # 舊版 Pillow 不支援 size 參數
            return ImageFont.load_default()
    
    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """
        智能文字換行
        
        Args:
            text: 原始文字
            font: 字體物件
            max_width: 最大寬度 (像素)
            
        Returns:
            換行後的文字列表
        """
        if not text:
            return []
        
        lines = []
        current_line = ""
        
        for char in text:
            test_line = current_line + char
            # 使用 getbbox 計算文字寬度 (Pillow 9.2.0+)
            try:
                bbox = font.getbbox(test_line)
                text_width = bbox[2] - bbox[0]
            except AttributeError:
                # 舊版 Pillow fallback
                text_width = font.getlength(test_line)
            
            if text_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def compose_slide(
        self,
        background_image: bytes,
        slide_title: str,
        core_insight: str,
        data_bullets: List[str],
        stage_id: int = 1
    ) -> bytes:
        """
        合成完整的簡報卡片
        
        Args:
            background_image: Imagen 生成的背景圖 PNG bytes
            slide_title: 標題 (<=8字)
            core_insight: 核心洞察 (<=30字)
            data_bullets: 要點列表 (3項)
            stage_id: 階段編號 (1-4)
            
        Returns:
            合成後的 PNG 圖片 bytes
        """
        print(f"📍[SlideComposer] 合成 Stage {stage_id}: {slide_title}")
        
        # 1. 載入背景圖
        bg_img = Image.open(io.BytesIO(background_image)).convert("RGBA")
        bg_img = bg_img.resize((self.layout.width, self.layout.height), Image.Resampling.LANCZOS)
        
        # 2. 創建半透明遮罩層 (Glassmorphism 效果)
        overlay_height = int(self.layout.height * self.layout.overlay_height_ratio)
        overlay_y = self.layout.height - overlay_height
        
        # 2.1 裁切底部區域並模糊
        bottom_region = bg_img.crop((0, overlay_y, self.layout.width, self.layout.height))
        blurred_region = bottom_region.filter(ImageFilter.GaussianBlur(radius=15))
        
        # 2.2 創建半透明色彩遮罩
        style = STAGE_STYLES.get(stage_id, STAGE_STYLES[1])
        color_overlay = Image.new("RGBA", (self.layout.width, overlay_height), style["bg_color"])
        
        # 2.3 合成模糊背景 + 色彩遮罩
        blurred_region = blurred_region.convert("RGBA")
        overlay_layer = Image.alpha_composite(blurred_region, color_overlay)
        
        # 3. 將遮罩貼回主圖
        result = bg_img.copy()
        result.paste(overlay_layer, (0, overlay_y))
        
        # 4. 繪製文字
        draw = ImageDraw.Draw(result)
        text_color = style["text_color"]
        accent_color = style["accent_color"]
        max_text_width = self.layout.width - 2 * self.layout.padding
        
        # 4.1 繪製標題
        title_y = overlay_y + 30
        draw.text(
            (self.layout.padding, title_y),
            slide_title,
            font=self._title_font,
            fill=text_color
        )
        
        # 4.2 繪製核心洞察 (自動換行)
        insight_y = title_y + 70
        insight_lines = self._wrap_text(core_insight, self._insight_font, max_text_width)
        for line in insight_lines:
            draw.text(
                (self.layout.padding, insight_y),
                line,
                font=self._insight_font,
                fill=accent_color
            )
            insight_y += 40
        
        # 4.3 繪製要點列表
        bullet_y = insight_y + 20
        for i, bullet in enumerate(data_bullets[:3]):
            bullet_text = f"• {bullet}"
            bullet_lines = self._wrap_text(bullet_text, self._bullet_font, max_text_width)
            for line in bullet_lines:
                draw.text(
                    (self.layout.padding, bullet_y),
                    line,
                    font=self._bullet_font,
                    fill=text_color
                )
                bullet_y += 32
            bullet_y += 8  # 項目間距
        
        # 4.4 繪製階段標籤
        stage_label = f"Stage {stage_id} | {style['name']}"
        label_bbox = self._bullet_font.getbbox(stage_label)
        label_width = label_bbox[2] - label_bbox[0]
        draw.text(
            (self.layout.width - self.layout.padding - label_width, overlay_y + 30),
            stage_label,
            font=self._bullet_font,
            fill=(255, 255, 255, 180)
        )
        
        # 5. 輸出為 PNG bytes
        output_buffer = io.BytesIO()
        result = result.convert("RGB")  # 移除 alpha 通道以減少檔案大小
        result.save(output_buffer, format="PNG", optimize=True)
        output_buffer.seek(0)
        
        print(f"✅ [SlideComposer] Stage {stage_id} 合成完成")
        return output_buffer.getvalue()
    
    def compose_all_slides(
        self,
        images: Dict[str, bytes],
        slides: List[Dict[str, Any]]
    ) -> Dict[str, bytes]:
        """
        批量合成所有簡報卡片
        
        Args:
            images: {"stage1": bytes, "stage2": bytes, ...}
            slides: [SlideContent.to_dict(), ...]
            
        Returns:
            {"stage1": composed_bytes, "stage2": composed_bytes, ...}
        """
        print("\n" + "=" * 50)
        print("🎨 SlideComposer 開始圖文合成...")
        print("=" * 50)
        
        composed = {}
        stage_keys = ["stage1", "stage2", "stage3", "combined"]
        
        for i, (key, slide_data) in enumerate(zip(stage_keys, slides)):
            if key not in images or images[key] is None:
                print(f"⚠️ [SlideComposer] 跳過 {key}：無背景圖")
                composed[key] = None
                continue
            
            try:
                composed[key] = self.compose_slide(
                    background_image=images[key],
                    slide_title=slide_data.get("slide_title", f"Stage {i+1}"),
                    core_insight=slide_data.get("core_insight", ""),
                    data_bullets=slide_data.get("data_bullets", []),
                    stage_id=slide_data.get("stage_id", i + 1)
                )
            except Exception as e:
                print(f"❌ [SlideComposer] {key} 合成失敗: {e}")
                composed[key] = images[key]  # 失敗時返回原圖
        
        print("=" * 50)
        print("✅ 圖文合成全部完成！")
        print("=" * 50 + "\n")
        
        return composed


# ============ 便捷函數 ============

def compose_slide_cards(
    images: Dict[str, bytes],
    slides: List[Dict[str, Any]]
) -> Dict[str, bytes]:
    """
    便捷函數：將圖片與文字合成為簡報卡片
    
    Args:
        images: Imagen 生成的原始圖片
        slides: VisualArchitect 生成的簡報內容
        
    Returns:
        合成後的圖片
    """
    composer = SlideComposer()
    return composer.compose_all_slides(images, slides)
