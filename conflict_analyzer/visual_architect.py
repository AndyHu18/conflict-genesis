"""
衝突基因 - 視覺架構師模組 (Visual Architect)
將衝突分析數據轉化為結構化簡報內容與繪圖指令
"""

import os
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from google import genai
from google.genai import types


# 四階段對應的情緒色彩
STAGE_COLORS = {
    1: {"name": "焦慮/引爆", "hex": "#F59E0B", "mood": "tension, upheaval"},    # 橙黃
    2: {"name": "冷戰/深層", "hex": "#0891B2", "mood": "depth, hidden truth"},   # 深青
    3: {"name": "成長/重塑", "hex": "#22C55E", "mood": "growth, renewal"},       # 嫩綠
    4: {"name": "療癒/和諧", "hex": "#EC4899", "mood": "harmony, healing"},      # 和諧粉
}


@dataclass
class SlideContent:
    """簡報卡片內容結構"""
    slide_title: str           # 具震撼力的短標題
    core_insight: str          # 一句溫暖且中立的引言
    data_bullets: List[str]    # 3 個基於事實的關鍵洞察
    image_prompt: str          # 給繪圖模型的英文視覺意向指令
    stage_id: int              # 階段編號
    color_theme: str           # 色彩主題
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# 視覺架構師 System Prompt
VISUAL_ARCHITECT_PROMPT = """# Role

你是一位具備心理洞察力的「數據視覺化與簡報設計大師」。你的任務是將衝突分析報告轉化為具備專業感、結構化且具備深度洞察的視覺簡報。

---

# Core Principle (核心原則)

1. **結構大於敘述**：產出具備標題與要點（Bullet Points）的結構化資訊，不要長篇大論。
2. **隱喻與留白**：給予繪圖模型發揮空間。不要描述具體的吵架場景，要描述「情緒的質地」（例如：斷裂的線、透光的裂縫、深海的氣泡、崩塌的建築）。
3. **上下文錨點**：必須從 JSON 中提取該階段最關鍵的衝突事實，確保簡報內容「獨一無二」且「緊扣實況」。

---

# 視覺風格指南 (Style Guide)

* **風格**：現代極簡、數位療癒感、高質感紋理、科技未來感
* **配色**：根據階段情緒自動調整
  - Stage 1 (焦慮/引爆)：橙黃色調，捕捉瞬間失衡的動態感
  - Stage 2 (冷戰/深層)：深青色調，呈現深層的渴望與隱藏的真實
  - Stage 3 (成長/重塑)：嫩綠色調，呈現清晰的邊界與出口，給予力量
  - Stage 4 (療癒/和諧)：粉色調，呈現融合與包容，強調新的平衡

---

# 輸出格式 (JSON)

請直接輸出以下 JSON 格式，不需任何額外說明：

{
    "slide_title": "具備震撼力的短標題（8字以內）",
    "core_insight": "一句溫暖且中立的引言（30字以內）",
    "data_bullets": [
        "基於事實的洞察點 1",
        "基於事實的洞察點 2",
        "基於事實的洞察點 3"
    ],
    "image_prompt": "English visual concept for the image generation model. Focus on: abstract emotions, light and shadow, metaphorical imagery, texture. Include 1-2 specific keywords from the conflict context. Style: modern minimal, digital healing aesthetic, sci-fi futuristic glow. The image should represent [specific emotion/concept from this stage]. DO NOT include any text, logos, or brand names in the image."
}

---

# 絕對禁止

- 禁止提及任何品牌名稱（Gemini, Google, AI 等）
- 禁止在 image_prompt 中要求繪製文字
- 禁止長篇大論，必須精簡有力
"""


class VisualArchitect:
    """視覺架構師：將分析數據轉化為結構化簡報內容"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("需要 GEMINI_API_KEY 環境變數")
        self.client = genai.Client(api_key=self.api_key)
    
    def generate_slide_content(
        self,
        stage_id: int,
        stage_result: Dict[str, Any],
        stage_description: str = ""
    ) -> SlideContent:
        """
        生成單一階段的簡報卡片內容
        
        Args:
            stage_id: 階段編號 (1-4)
            stage_result: 該階段的分析結果 JSON
            stage_description: 額外的階段描述
            
        Returns:
            SlideContent 物件
        """
        color_info = STAGE_COLORS.get(stage_id, STAGE_COLORS[1])
        
        # 構建階段特定的提示
        stage_contexts = {
            1: "這是衝突的「能量引爆點」與轉折數據。捕捉瞬間失衡的動態感。重點關注：衝突如何演化、轉折點在哪裡。",
            2: "這是冰山下的「核心脆弱」與未滿足需求。呈現深層的渴望與隱藏的真實。重點關注：雙方真正害怕什麼、渴望什麼。",
            3: "這是個人的「改變權力」與未來路徑。呈現清晰的邊界與出口，給予力量。重點關注：可以做什麼改變、如何成長。",
            4: "這是關係的「重構與共生」總結。呈現融合與包容，強調新的平衡。重點關注：療癒的可能性、新的開始。"
        }
        
        user_prompt = f"""## 階段 {stage_id}：{color_info['name']}

### 分析數據 (JSON)：
```json
{json.dumps(stage_result, ensure_ascii=False, indent=2)[:3000]}
```

### 階段側重：
{stage_contexts.get(stage_id, '')}

### 色彩情緒：
{color_info['mood']}

請基於以上數據，生成這一張簡報卡片的內容。確保 image_prompt 包含至少 1-2 個來自分析數據的具體關鍵字（如：洗碗、手機、遲到、不被理解等），讓圖像真正反映這場衝突的獨特性。
"""
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=VISUAL_ARCHITECT_PROMPT,
                    temperature=0.7,
                    response_mime_type="application/json"
                )
            )
            
            result_text = response.text.strip()
            
            # 解析 JSON
            try:
                result_json = json.loads(result_text)
            except json.JSONDecodeError:
                # 嘗試修復常見的 JSON 問題
                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result_json = json.loads(json_match.group())
                else:
                    raise ValueError(f"無法解析 JSON: {result_text[:500]}")
            
            # 確保 image_prompt 有足夠的質量指令
            image_prompt = result_json.get("image_prompt", "")
            if not any(word in image_prompt.lower() for word in ["style", "aesthetic", "modern"]):
                image_prompt += " Style: modern minimal, digital healing aesthetic, abstract art, high-quality texture, cinematic lighting."
            
            return SlideContent(
                slide_title=result_json.get("slide_title", f"Stage {stage_id}"),
                core_insight=result_json.get("core_insight", ""),
                data_bullets=result_json.get("data_bullets", [])[:3],
                image_prompt=image_prompt,
                stage_id=stage_id,
                color_theme=color_info['hex']
            )
            
        except Exception as e:
            print(f"❌ 生成 Stage {stage_id} 簡報內容錯誤: {e}")
            # 返回預設內容
            return self._get_fallback_slide(stage_id, stage_result)
    
    def _get_fallback_slide(self, stage_id: int, stage_result: Dict[str, Any]) -> SlideContent:
        """生成備用簡報內容"""
        color_info = STAGE_COLORS.get(stage_id, STAGE_COLORS[1])
        
        fallback_data = {
            1: {
                "title": "衝突演化",
                "insight": "每一場衝突都是一面鏡子，映照出我們未被看見的需求。",
                "prompt": "Abstract visualization of emotional tension, fracturing lines, warm orange and amber light, modern minimal style, digital art, high quality"
            },
            2: {
                "title": "深層溯源",
                "insight": "在憤怒的表面之下，往往藏著最柔軟的渴望。",
                "prompt": "Deep ocean with rising bubbles, hidden depths, teal and cyan colors, ethereal light from above, abstract emotional art, minimalist"
            },
            3: {
                "title": "成長方案",
                "insight": "改變不是背叛自己，而是給自己更多選擇。",
                "prompt": "Fresh green shoots breaking through concrete, renewal and growth, soft green light, modern botanical abstract art, hope and strength"
            },
            4: {
                "title": "療癒旅程",
                "insight": "修復不是回到從前，而是創造一個更美好的未來。",
                "prompt": "Harmonious blend of colors, soft pink and lavender, healing light, abstract unity, two energies merging, peace and balance, artistic"
            }
        }
        
        fb = fallback_data.get(stage_id, fallback_data[1])
        
        # 從 stage_result 提取一些基本洞察
        bullets = []
        if isinstance(stage_result, dict):
            if stage_result.get("overall_dynamic"):
                bullets.append(str(stage_result["overall_dynamic"])[:50])
            if stage_result.get("intensity_score"):
                bullets.append(f"衝突烈度：{stage_result['intensity_score']}/10")
            if stage_result.get("healing_message"):
                bullets.append(str(stage_result["healing_message"])[:50])
        
        if len(bullets) < 3:
            bullets.extend(["分析數據載入中...", "請等待完整報告", "感謝您的耐心"])
        
        return SlideContent(
            slide_title=fb["title"],
            core_insight=fb["insight"],
            data_bullets=bullets[:3],
            image_prompt=fb["prompt"],
            stage_id=stage_id,
            color_theme=color_info['hex']
        )
    
    def generate_all_slides(
        self,
        stage1_result: Dict[str, Any],
        stage2_result: Dict[str, Any],
        stage3_result: Dict[str, Any]
    ) -> List[SlideContent]:
        """
        生成所有四張簡報卡片的內容
        
        Returns:
            包含 4 個 SlideContent 的列表
        """
        print("\n" + "=" * 50)
        print("🎨 視覺架構師正在設計簡報...")
        print("=" * 50)
        
        slides = []
        
        # Stage 1: 演化圖
        print("   📊 設計 Stage 1: 衝突演化...")
        slides.append(self.generate_slide_content(1, stage1_result))
        
        # Stage 2: 溯源圖
        print("   💡 設計 Stage 2: 深層溯源...")
        slides.append(self.generate_slide_content(2, stage2_result))
        
        # Stage 3: 方案圖
        print("   🌱 設計 Stage 3: 成長方案...")
        slides.append(self.generate_slide_content(3, stage3_result))
        
        # Stage 4: 綜合圖（使用所有數據）
        print("   🎵 設計 Stage 4: 療癒旅程...")
        combined_context = {
            "overall_dynamic": stage1_result.get("overall_dynamic", ""),
            "core_need": stage2_result.get("iceberg_analysis", {}).get("user", {}).get("unmet_need", ""),
            "healing_message": stage2_result.get("healing_message", ""),
            "meaning_making": stage3_result.get("meaning_making", {}),
            "closing": stage3_result.get("closing", "")
        }
        slides.append(self.generate_slide_content(4, combined_context))
        
        print("✅ 簡報設計完成！\n")
        
        return slides


# 便捷函數
def generate_visual_slides(
    stage1: Dict[str, Any],
    stage2: Dict[str, Any],
    stage3: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    便捷函數：生成所有簡報卡片內容
    
    Returns:
        包含 4 個簡報內容字典的列表
    """
    architect = VisualArchitect()
    slides = architect.generate_all_slides(stage1, stage2, stage3)
    return [slide.to_dict() for slide in slides]
