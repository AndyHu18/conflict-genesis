"""
測試 SlideComposer 圖文合成功能
"""
import os
from pathlib import Path

# 設置環境
os.environ.setdefault("GEMINI_API_KEY", "dummy_key_for_test")

from PIL import Image
import io

# 創建測試用的背景圖 (純色漸層)
def create_test_background(width=1024, height=1024) -> bytes:
    """創建測試用的漸層背景"""
    from PIL import Image, ImageDraw
    
    img = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(img)
    
    # 創建漸層
    for y in range(height):
        ratio = y / height
        r = int(30 + 60 * ratio)
        g = int(40 + 80 * ratio)
        b = int(80 + 100 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
    
    # 輸出為 bytes
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()

def test_slide_composer():
    """測試圖文合成"""
    from conflict_analyzer.slide_composer import SlideComposer
    
    print("\n" + "=" * 60)
    print("🧪 測試 SlideComposer 圖文合成功能")
    print("=" * 60)
    
    # 創建合成器
    composer = SlideComposer()
    print(f"✅ 字體路徑: {composer.font_path}")
    
    # 創建測試背景
    test_bg = create_test_background()
    print(f"✅ 測試背景: {len(test_bg)} bytes")
    
    # 測試合成
    result = composer.compose_slide(
        background_image=test_bg,
        slide_title="衝突演化",
        core_insight="每一場衝突都是一面鏡子，映照出我們未被看見的需求。",
        data_bullets=[
            "雙方情緒在 3:45 達到頂峰",
            "追逐-逃避模式反覆出現",
            "關鍵轉折點：家務分工議題"
        ],
        stage_id=1
    )
    
    # 保存結果
    output_path = Path.cwd() / "generated_images" / "test_slide.png"
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(result)
    
    print(f"✅ 合成完成: {len(result)} bytes")
    print(f"💾 已保存至: {output_path}")
    print("=" * 60)
    print("🎉 測試成功！請查看生成的圖片確認文字是否正確顯示。")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    test_slide_composer()
