"""
Lumina 心語 - 視覺架構師模組 (Visual Architect)
將衝突分析數據轉化為結構化簡報內容與繪圖指令
Premium Edition - 高端暖色系視覺設計
"""

import os
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from google import genai
from google.genai import types


# 四階段高端暖色系配色（Premium Warm Palette）
# 設計理念：奢華、溫暖、專業、療癒
STAGE_COLORS = {
    1: {
        "name": "衝突覺察",
        "hex": "#C9A962",           # 琥珀金 Amber Gold
        "accent": "#8B7355",        # 摩卡棕 Mocha Brown
        "mood": "awareness, insight",
        "palette": "golden amber with cream"
    },
    2: {
        "name": "深層探索",
        "hex": "#B87351",           # 赤陶褐 Terracotta
        "accent": "#D4A574",        # 焦糖色 Caramel
        "mood": "depth, understanding",
        "palette": "terracotta with warm beige"
    },
    3: {
        "name": "成長轉化",
        "hex": "#A3B899",           # 柔和鼠尾草綠 Sage Green
        "accent": "#C9B896",        # 亞麻金 Linen Gold
        "mood": "growth, transformation",
        "palette": "sage green with golden cream"
    },
    4: {
        "name": "療癒和諧",
        "hex": "#D4A5A5",           # 珊瑚玫瑰 Coral Rose
        "accent": "#E8D5C4",        # 奶油杏 Creamy Apricot
        "mood": "harmony, healing",
        "palette": "coral rose with ivory"
    },
}


@dataclass
class SlideContent:
    """簡報卡片內容結構"""
    slide_title: str           # 具震撼力的短標題
    core_insight: str          # 一句溫暖且中立的引言
    data_bullets: List[str]    # 3 個基於事實的關鍵洞察
    image_prompt: str          # 給繪圖模型的英文視覺意向指令（由程式碼硬編碼組合）
    stage_id: int              # 階段編號
    color_theme: str           # 色彩主題
    visual_essence: str = ""   # 視覺核心摘要（30字內英文），用於 Stage 4 融合
    emotions: str = ""         # 情緒關鍵字（英文）
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============ 關鍵修正點 1：固定風格標籤 (CONSTANT_STYLE) ============
# 根據 /nano 示範：所有圖片共用同一個風格標籤，確保視覺一致性
CONSTANT_STYLE = "Artstyle: Professional Infographic, clean typography, isometric illustrations, warm color palette, soft studio lighting, 16:9 aspect ratio, 4K resolution."

# 階段對應的背景色（用於硬編碼組合）
STAGE_BACKGROUNDS = {
    1: "warm cream backdrop with amber gold accents",
    2: "warm beige backdrop with terracotta accents", 
    3: "soft linen backdrop with sage green accents",
    4: "ivory backdrop with coral rose accents"
}


# 視覺架構師 System Prompt (v3.0 - 分離式輸出)
# 關鍵修正：不再要求 LLM 生成完整 image_prompt，改為輸出 visual_essence 和 emotions
VISUAL_ARCHITECT_PROMPT = """# Role

你是一位「視覺轉譯師」。你的任務是從衝突分析報告中**提取視覺核心元素**，讓程式碼組裝成最終的繪圖指令。

---

# 核心任務（極重要）

你**不需要**生成完整的 image_prompt。你只需要輸出：
1. **visual_essence**：從分析數據中提取的核心視覺主體（30字內英文描述）
2. **emotions**：情緒關鍵字（2-3個英文詞，逗號分隔）

程式碼會將這些元素與固定風格標籤組合成最終 prompt。

---

# 輸出格式 (JSON)

請直接輸出以下格式：

{
    "slide_title": "4-6字的中文標題（禁止 emoji）",
    "core_insight": "10-15字的中文引言（禁止 emoji）",
    "data_bullets": ["要點1", "要點2", "要點3"],
    "visual_essence": "核心視覺主體（30字內英文）",
    "emotions": "emotion1, emotion2, emotion3"
}

---

# 如何提取 visual_essence

根據階段不同，提取對應的視覺隱喻：

**Stage 1 (衝突覺察)**：
- 觀察衝突動態類型（追逃、批評防禦、冷戰等）
- 範例："two silhouettes in push-pull dynamic, one reaching forward while other stepping back"

**Stage 2 (深層探索)**：
- 觀察冰山下方的恐懼與渴望
- 範例："iceberg metaphor with hidden fears beneath surface, longing for validation visible in depths"

**Stage 3 (成長蛻變)**：
- 觀察成長方向與行動方案  
- 範例："pathway diverging into new possibilities, growth plant breaking through cracks"

**Stage 4 (療癒和諧)**：
- 融合前三階段的視覺元素
- 範例："bridge connecting two shores, previously distant figures now in harmonious dialogue"

---

# emotions 範例

常用情緒關鍵字：
- 衝突類：frustration, defensiveness, withdrawal, suffocation, invalidation
- 渴望類：longing, yearning, hope, seeking validation, need for connection
- 療癒類：breakthrough, reconciliation, understanding, acceptance, renewal

---

# 絕對禁止

- 禁止輸出完整的 image_prompt（這由程式碼組合）
- 禁止使用任何 emoji
- 禁止使用中文在 visual_essence 和 emotions 中
- 禁止使用通用詞彙（如 generic, simple, basic）
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
        previous_essences: Optional[List[str]] = None  # 修正點：Stage 4 需要前三階段的 visual_essence
    ) -> SlideContent:
        """
        生成單一階段的簡報卡片內容
        
        關鍵修正（遵循 /nano 示範）：
        1. 程式碼層級硬編碼組合 image_prompt
        2. LLM 只負責提取 visual_essence 和 emotions
        3. Stage 4 傳入 previous_essences 進行融合
        
        Args:
            stage_id: 階段編號 (1-4)
            stage_result: 該階段的分析結果 JSON
            previous_essences: 只有 Stage 4 需要，包含前三階段的 visual_essence
            
        Returns:
            SlideContent 物件
        """
        color_info = STAGE_COLORS.get(stage_id, STAGE_COLORS[1])
        
        # ============ 關鍵修正點 2：Stage 4 全域融合邏輯 ============
        if stage_id == 4 and previous_essences:
            # Stage 4：要求 LLM 將前三階段的視覺種子融合成一張全域圖
            user_context = f"""## 全域視覺融合任務

前三階段的視覺核心：
- Stage 1: {previous_essences[0] if len(previous_essences) > 0 else 'conflict awareness'}
- Stage 2: {previous_essences[1] if len(previous_essences) > 1 else 'deep exploration'}
- Stage 3: {previous_essences[2] if len(previous_essences) > 2 else 'growth transformation'}

### 任務
請將以上三個視覺元素融合成一個全域視覺隱喻，描述關係的療癒與和諧。

### 附加上下文
{json.dumps(stage_result, ensure_ascii=False, indent=2)[:2000]}
"""
        else:
            # Stage 1-3：正常提取
            user_context = f"""## 階段 {stage_id}：{color_info['name']}

### 分析數據 (JSON)：
```json
{json.dumps(stage_result, ensure_ascii=False, indent=2)[:4000]}
```

### 你需要做的事：
1. 從分析數據中提取 **visual_essence**（核心視覺主體，30字內英文描述）
2. 從分析數據中識別 **emotions**（2-3個情緒關鍵字，英文）
3. 生成中文標題和引言

### Stage {stage_id} 視覺提取指引：
- Stage 1：觀察衝突動態類型（追逃、批評防禦、冷戰等）
- Stage 2：觀察冰山下方的恐懼與渴望
- Stage 3：觀察成長方向與行動方案
- Stage 4：融合前三階段的視覺元素
"""
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_context,
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
                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result_json = json.loads(json_match.group())
                else:
                    raise ValueError(f"無法解析 JSON: {result_text[:500]}")
            
            # 提取字段
            slide_title = result_json.get("slide_title", f"Stage {stage_id}")
            core_insight = result_json.get("core_insight", "")
            visual_essence = result_json.get("visual_essence", "")
            emotions = result_json.get("emotions", "")
            
            # 智能截斷標題（最多 8 字，確保不在逗號後截斷）
            if len(slide_title) > 8:
                # 嘗試在標點前截斷
                for i in range(8, 0, -1):
                    if slide_title[i-1] in '。！？：；':
                        slide_title = slide_title[:i]
                        break
                else:
                    slide_title = slide_title[:8]
            
            # 副標題最多 20 字
            if len(core_insight) > 20:
                core_insight = core_insight[:20]
            
            # 如果沒有提取到 visual_essence，使用 fallback
            if not visual_essence:
                visual_essence = self._extract_context_hints(stage_id, stage_result)
                print(f"   ⚠️ Stage {stage_id}: LLM 未返回 visual_essence，使用 fallback: {visual_essence}")
            
            if not emotions:
                emotions = "emotional tension, seeking resolution"
            
            # ============ 關鍵修正點 1：程式碼層級硬編碼組合 ============
            # 不再依賴 LLM 生成完整 prompt，而是在這裡強制組合
            final_image_prompt = self._build_image_prompt(
                stage_id=stage_id,
                slide_title=slide_title,
                core_insight=core_insight,
                visual_essence=visual_essence,
                emotions=emotions
            )
            
            # 日誌：顯示提取的動態上下文
            print(f"   ✅ Stage {stage_id} visual_essence: {visual_essence[:50]}...")
            print(f"   ✅ Stage {stage_id} emotions: {emotions}")
            
            return SlideContent(
                slide_title=slide_title,
                core_insight=core_insight,
                data_bullets=result_json.get("data_bullets", [])[:3],
                image_prompt=final_image_prompt,
                stage_id=stage_id,
                color_theme=color_info['hex'],
                visual_essence=visual_essence,  # 存起來給 Stage 4 用
                emotions=emotions
            )
            
        except Exception as e:
            print(f"❌ 生成 Stage {stage_id} 簡報內容錯誤: {e}")
            return self._get_fallback_slide(stage_id, stage_result)
    
    def _build_image_prompt(
        self,
        stage_id: int,
        slide_title: str,
        core_insight: str,
        visual_essence: str,
        emotions: str
    ) -> str:
        """
        關鍵修正：程式碼層級硬編碼組合 image_prompt
        
        格式：固定風格 + 中文標題 + 視覺隱喻
        
        ⚠️ 重要修正：
        1. 所有文字必須是繁體中文
        2. 標題字體必須夠大（72pt+）
        3. 副標題字體適中（36pt+）
        4. 嚴禁任何英文標籤
        """
        background = STAGE_BACKGROUNDS.get(stage_id, "warm cream backdrop")
        
        # 硬編碼組合 - 強制中文輸出 + 大字體
        final_prompt = (
            f"Artstyle: Professional Infographic, clean typography, isometric illustrations, "
            f"warm color palette, soft studio lighting, 16:9 aspect ratio, 4K resolution. "
            f"CRITICAL LANGUAGE REQUIREMENT: ALL TEXT MUST BE IN TRADITIONAL CHINESE (繁體中文). "
            f"NO ENGLISH TEXT ALLOWED on the infographic. "
            f"Main Title: '{slide_title}' - MUST be in LARGE bold Traditional Chinese font (72pt or larger), "
            f"positioned at top center with dark navy blue color. "
            f"Subtitle: '{core_insight}' - in Traditional Chinese (36pt), charcoal gray color. "
            f"Visual metaphor: {visual_essence}. "
            f"Mood: {emotions}. "
            f"Background: {background}. "
            f"All labels and annotations on the image MUST be in Traditional Chinese ONLY. "
            f"Font size must be clearly readable - minimum 24pt for any text element."
        )
        
        return final_prompt
    
    def _extract_context_hints(self, stage_id: int, stage_result: Dict[str, Any]) -> str:
        """從分析數據中預先提取視覺上下文提示"""
        hints = []
        
        if not isinstance(stage_result, dict):
            return "emotional insight, relationship dynamic"
        
        # Stage 1: 從演化地圖提取
        if stage_id == 1:
            if stage_result.get("overall_dynamic"):
                hints.append(str(stage_result["overall_dynamic"])[:30])
            if stage_result.get("intensity_score"):
                score = stage_result["intensity_score"]
                if score >= 7:
                    hints.append("high emotional intensity")
                elif score >= 4:
                    hints.append("moderate tension")
                else:
                    hints.append("underlying unease")
        
        # Stage 2: 從冰山分析提取
        elif stage_id == 2:
            iceberg = stage_result.get("iceberg_analysis", {})
            if isinstance(iceberg, dict):
                for speaker, data in iceberg.items():
                    if isinstance(data, dict):
                        if data.get("underlying_fear"):
                            hints.append("hidden fears")
                        if data.get("underlying_desire"):
                            hints.append("unmet desires")
            if stage_result.get("attachment_dynamic"):
                hints.append("attachment patterns")
        
        # Stage 3: 從成長方案提取
        elif stage_id == 3:
            if stage_result.get("meaning_making"):
                hints.append("meaning reconstruction")
            if stage_result.get("my_toolkit"):
                hints.append("self-regulation tools")
            if stage_result.get("alternatives"):
                hints.append("new pathways")
        
        # Stage 4: 綜合（優先使用 global_visual_essence）
        elif stage_id == 4:
            # 如果有預先計算的 global_visual_essence，直接使用
            if stage_result.get("global_visual_essence"):
                return str(stage_result["global_visual_essence"])
            # 否則從個別欄位提取
            if stage_result.get("healing_message"):
                hints.append("healing journey")
            if stage_result.get("core_need"):
                hints.append("core needs recognition")
            if stage_result.get("overall_dynamic"):
                hints.append("conflict transformed")
            hints.append("harmonious reconnection")
        
        return ", ".join(hints[:3]) if hints else "emotional insight, relationship dynamic"
    
    def _get_fallback_slide(self, stage_id: int, stage_result: Dict[str, Any]) -> SlideContent:
        """生成備用簡報內容（包含動態上下文）"""
        color_info = STAGE_COLORS.get(stage_id, STAGE_COLORS[1])
        
        # 從數據中提取動態上下文
        dynamic_context = self._extract_context_hints(stage_id, stage_result)
        
        # 階段對應的背景色
        stage_backgrounds = {
            1: "warm cream with amber gold accents",
            2: "warm beige with terracotta accents",
            3: "soft linen with sage green accents",
            4: "ivory with coral rose accents"
        }
        
        fallback_data = {
            1: {
                "title": "覺察時刻",
                "insight": "每個衝突都藏著轉機",
            },
            2: {
                "title": "深層對話",
                "insight": "傾聽內心真實的渴望",
            },
            3: {
                "title": "成長蛻變",
                "insight": "改變帶來新的可能",
            },
            4: {
                "title": "和諧共處",
                "insight": "關係在理解中重生",
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
        
        # 構建包含動態上下文的 image_prompt
        image_prompt = f"Professional infographic slide with Chinese title '{fb['title']}' in bold navy blue font at top, subtitle '{fb['insight']}' in charcoal gray below. Visual context: {dynamic_context}. Include abstract conceptual icons as isometric illustrations. Background: {stage_backgrounds.get(stage_id, 'warm cream')}. Style: modern infographic, professional tech presentation, 16:9"
        
        print(f"   ⚠️ Stage {stage_id} 使用 fallback，動態上下文: {dynamic_context}")
        
        return SlideContent(
            slide_title=fb["title"],
            core_insight=fb["insight"],
            data_bullets=bullets[:3],
            image_prompt=image_prompt,
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
        
        關鍵修正（遵循 /nano 示範）：
        - 收集 Stage 1-3 的 visual_essence
        - 傳遞給 Stage 4 進行全域融合
        
        Returns:
            包含 4 個 SlideContent 的列表
        """
        print("\n" + "=" * 50)
        print("🎨 視覺架構師正在設計簡報（v3.0 硬編碼組合模式）...")
        print("=" * 50)
        
        slides = []
        previous_essences = []  # 收集前三階段的 visual_essence
        
        # Stage 1: 演化圖
        print("   📊 設計 Stage 1: 衝突演化...")
        slide1 = self.generate_slide_content(1, stage1_result)
        slides.append(slide1)
        previous_essences.append(slide1.visual_essence)
        
        # Stage 2: 溯源圖
        print("   💡 設計 Stage 2: 深層溯源...")
        slide2 = self.generate_slide_content(2, stage2_result)
        slides.append(slide2)
        previous_essences.append(slide2.visual_essence)
        
        # Stage 3: 方案圖
        print("   🌱 設計 Stage 3: 成長方案...")
        slide3 = self.generate_slide_content(3, stage3_result)
        slides.append(slide3)
        previous_essences.append(slide3.visual_essence)
        
        # Stage 4: 綜合圖（傳入前三階段的 visual_essence 進行融合）
        print("   🎵 設計 Stage 4: 療癒旅程（融合前三階段）...")
        print(f"      → 前三階段視覺種子：{previous_essences}")
        
        # 構建 Stage 4 的上下文
        combined_context = {
            "overall_dynamic": stage1_result.get("overall_dynamic", "") if isinstance(stage1_result, dict) else "",
            "healing_message": stage2_result.get("healing_message", "") if isinstance(stage2_result, dict) else "",
            "closing": stage3_result.get("closing", "") if isinstance(stage3_result, dict) else ""
        }
        
        slide4 = self.generate_slide_content(
            stage_id=4, 
            stage_result=combined_context, 
            previous_essences=previous_essences  # 關鍵：傳入前三階段的 visual_essence
        )
        slides.append(slide4)
        
        print("✅ 簡報設計完成！（使用硬編碼組合模式）\n")
        
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
