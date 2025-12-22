"""
Lumina 心語 - Pydantic Schemas
一階：衝突演化追蹤器
二階：深層溯源與接納橋樑
三階：個人成長行動方案
"""

import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from enum import Enum


def truncate_repetition(text: str, max_repeat: int = 3) -> str:
    """
    檢測並截斷重複內容
    
    如果同一段文字重複超過 max_repeat 次，則截斷為一次 + 提示
    """
    if not text or len(text) < 50:
        return text
    
    # 尋找重複模式（至少 20 個字符的重複）
    for chunk_size in range(20, min(len(text) // 2, 200)):
        pattern = text[:chunk_size]
        count = text.count(pattern)
        if count > max_repeat:
            # 發現重複，截斷到第一次出現
            first_occurrence = text.find(pattern)
            end_of_first = first_occurrence + len(pattern)
            # 找到句號或逗號作為結束點
            end_point = text.find('。', end_of_first)
            if end_point == -1:
                end_point = text.find('，', end_of_first)
            if end_point == -1:
                end_point = end_of_first + 50
            
            return text[:end_point + 1] if end_point < len(text) else text[:end_of_first]
    
    return text



class EnergyPattern(str, Enum):
    """能量變化模式"""
    STEADY_RISE = "穩定上升"
    SUDDEN_EXPLOSION = "突然引爆"
    WAVE_CYCLE = "波浪循環"
    MALIGNANT_RESONANCE = "惡性共振"


# ============ 一階分析輸出結構 ============

class EvolutionPhase(BaseModel):
    """演化階段"""
    phase: str = Field(description="階段名稱")
    description: str = Field(description="這個階段發生了什麼")
    speaker_a_contribution: str = Field(description="A 的行為/語調/態度如何影響走向")
    speaker_b_contribution: str = Field(description="B 的行為/語調/態度如何影響走向")
    key_observation: str = Field(description="關鍵的聲學或語義觀察")


class TurningPoint(BaseModel):
    """關鍵轉折點"""
    moment: str = Field(description="描述該時刻")
    why_critical: str = Field(description="為什麼這是關鍵轉折")
    missed_alternative: str = Field(description="如果當時不同處理，可能的走向")


class DualPerspective(BaseModel):
    """雙方視角"""
    speaker_a_experience: str = Field(description="從 A 的角度，這場對話可能感受如何")
    speaker_b_experience: str = Field(description="從 B 的角度，這場對話可能感受如何")
    core_mismatch: str = Field(description="雙方的核心落差是什麼")


class RepairAnalysis(BaseModel):
    """修復嘗試分析"""
    attempts: str = Field(description="是否有任何降溫/修復嘗試")
    responses: str = Field(description="這些嘗試如何被回應")
    missed_opportunities: str = Field(description="哪些時刻本可降溫但被錯過")


class Stage1Result(BaseModel):
    """一階分析結果：衝突演化追蹤"""
    overall_dynamic: str = Field(description="一句話描述這場衝突的本質模式")
    energy_pattern: str = Field(description="情緒能量如何流動")
    evolution_map: List[EvolutionPhase] = Field(description="衝突演化階段列表")
    turning_points: List[TurningPoint] = Field(description="關鍵轉折點列表")
    dual_perspective: DualPerspective = Field(description="雙方各自的主觀體驗")
    repair_analysis: RepairAnalysis = Field(description="修復嘗試分析")
    intensity_score: int = Field(ge=1, le=10, default=5, description="衝突烈度 1-10")
    conflict_detected: bool = Field(default=True, description="是否偵測到衝突")


# ============ 二階分析輸出結構 ============

class IcebergAnalysis(BaseModel):
    """冰山下方分析"""
    speaker_id: str = Field(description="說話者標識 (A 或 B)", max_length=20)
    surface_behavior: str = Field(description="表面行為描述", max_length=300)
    underlying_fear: str = Field(description="深層恐懼", max_length=300)
    underlying_desire: str = Field(description="深層渴望", max_length=300)
    unmet_need: str = Field(description="未滿足的需求", max_length=300)
    possible_trigger: str = Field(description="可能的觸發來源", max_length=400)
    
    @field_validator('*', mode='before')
    @classmethod
    def truncate_all_fields(cls, v: Any) -> Any:
        """截斷所有字段中的重複內容"""
        if isinstance(v, str):
            return truncate_repetition(v)
        return v


class PerspectiveShift(BaseModel):
    """視角轉換練習"""
    for_speaker: str = Field(description="這個練習是給誰的", max_length=20)
    prompt: str = Field(description="換位思考的引導問題", max_length=300)
    insight: str = Field(description="透過這個視角可能獲得的洞察", max_length=400)


class DefenseMechanismInsight(BaseModel):
    """防禦機制洞察"""
    speaker_id: str = Field(description="說話者標識", max_length=20)
    defense_pattern: str = Field(description="防禦模式描述", max_length=300)
    trigger_for_other: str = Field(description="這如何觸發了對方的防禦", max_length=400)
    self_awareness_prompt: str = Field(description="自我覺察的引導", max_length=300)


class HealingReframe(BaseModel):
    """療癒性重構"""
    original_statement: str = Field(description="原始的攻擊性話語或行為", max_length=300)
    vulnerable_translation: str = Field(description="翻譯成脆弱性需求的版本", max_length=400)
    compassionate_response: str = Field(description="對方可以如何回應這個需求", max_length=300)


class ActionableChange(BaseModel):
    """可執行的微小改變"""
    for_speaker: str = Field(description="這個建議是給誰的", max_length=20)
    trigger_situation: str = Field(description="觸發情境", max_length=300)
    old_pattern: str = Field(description="舊的反應模式", max_length=300)
    new_approach: str = Field(description="建議的新做法", max_length=400)
    cooling_phrase: str = Field(description="降溫用語", max_length=200)


class Stage2Result(BaseModel):
    """二階分析結果：深層溯源與接納橋樑"""
    deep_insight_summary: str = Field(description="這場衝突的深層動力總結", max_length=500)
    iceberg_analysis: List[IcebergAnalysis] = Field(description="雙方各自的冰山下方分析")
    attachment_dynamic: str = Field(description="雙方依附模式如何互動", max_length=500)
    cognitive_style_clash: str = Field(description="認知風格差異如何影響衝突", max_length=500)
    perspective_shifts: List[PerspectiveShift] = Field(description="視角轉換練習")
    defense_insights: List[DefenseMechanismInsight] = Field(description="防禦機制洞察")
    healing_reframes: List[HealingReframe] = Field(description="療癒性重構")
    actionable_changes: List[ActionableChange] = Field(description="可執行的微小改變")
    shared_responsibility: str = Field(description="共同責任重構", max_length=500)
    healing_message: str = Field(description="療癒寄語", max_length=500)


# ============ 三階分析輸出結構 ============

class SelfRepair(BaseModel):
    """我能做的修復"""
    emotional_care: str = Field(description="自我情緒照顧：這次衝突在我身上留下什麼？我需要什麼？")
    inner_clarity: str = Field(description="內在整理：我真正想要的和感受到的是什麼？")
    proactive_options: str = Field(description="主動修復選項：如果我想主動，我可以怎麼開口/表達？")
    if_no_response: str = Field(description="如果對方沒有正面回應，我如何自處？")


class MyPatterns(BaseModel):
    """我的模式認識"""
    triggers: str = Field(description="我的觸發點和自動化反應")
    blind_spots: str = Field(description="我可能的盲點")
    ideal_self: str = Field(description="我想成為的樣子 vs 現在的我")
    gap_bridge: str = Field(description="縮小差距的切入點")


class MyToolkit(BaseModel):
    """我的調節工具箱"""
    warning_signs: str = Field(description="我的預警信號")
    cooling_methods: str = Field(description="對我有效的降溫方法")
    solo_pause_strategy: str = Field(description="不需要對方同意的暫停策略")


class AlternativePath(BaseModel):
    """替代路徑"""
    what_i_did: str = Field(description="這次我說的/做的")
    what_i_could_try: str = Field(description="我可以嘗試的替代方式")
    why_better_for_me: str = Field(description="為什麼這對「我自己」比較好")
    micro_experiment: str = Field(description="這週可以嘗試的一個微小實驗")


class MyBoundaries(BaseModel):
    """我的邊界與底線"""
    core_needs: str = Field(description="我的核心需求")
    acceptance_levels: str = Field(description="可以接受的/很難接受的/絕對不能接受的")
    how_to_express: str = Field(description="如何表達邊界")
    how_to_protect: str = Field(description="如何保護自己")


class MeaningMaking(BaseModel):
    """意義重構"""
    what_this_reveals: str = Field(description="這次衝突照見了我什麼")
    lesson_learning: str = Field(description="我正在學習的功課")
    message_to_self: str = Field(description="送給自己的話")


class Stage3Result(BaseModel):
    """三階分析結果：個人成長行動方案"""
    
    # 定位
    positioning: str = Field(
        description="建立正確期待：我能影響的 vs 我不能控制的"
    )
    
    # 我能做的修復
    repair_self_led: SelfRepair = Field(
        description="我能做的修復——自我照顧、內在整理、主動選項"
    )
    
    # 我的模式
    know_my_patterns: MyPatterns = Field(
        description="我的觸發點、自動化反應、盲點、想成為的樣子"
    )
    
    # 調節工具箱
    my_toolkit: MyToolkit = Field(
        description="我的預警信號、降溫方法、單方面暫停策略"
    )
    
    # 替代路徑
    alternatives: AlternativePath = Field(
        description="替代路徑、為什麼對我比較好、微小實驗"
    )
    
    # 邊界與底線
    my_boundaries: MyBoundaries = Field(
        description="核心需求、底線、如何表達和保護"
    )
    
    # 意義重構
    meaning_making: MeaningMaking = Field(
        description="這次照見了什麼、我在學習什麼、送給自己的話"
    )
    
    # 反思提問
    reflection_prompts: List[str] = Field(
        description="引導自我覺察的問題列表"
    )
    
    # 結語
    closing: str = Field(
        description="承認努力、給予鼓勵、提醒力量在自己手中"
    )


# ============ 完整分析結果 ============

class FullAnalysisResult(BaseModel):
    """完整分析結果（三階段）"""
    stage1: Stage1Result = Field(description="一階：衝突演化追蹤")
    stage2: Stage2Result = Field(description="二階：深層溯源與接納橋樑")
    stage3: Stage3Result = Field(description="三階：個人成長行動方案")


# ============ 向後相容 ============

class ConflictAnalysisResult(BaseModel):
    """向後相容的一階結果"""
    overall_dynamic: str = Field(description="衝突本質")
    energy_pattern: str = Field(description="能量流動")
    evolution_map: List[EvolutionPhase] = Field(description="演化階段")
    turning_points: List[TurningPoint] = Field(description="轉折點")
    dual_perspective: DualPerspective = Field(description="雙方視角")
    repair_analysis: RepairAnalysis = Field(description="修復分析")
    intensity_score: int = Field(ge=1, le=10, default=5)
    conflict_detected: bool = Field(default=True)


class EvolutionAnalysis(BaseModel):
    dynamic_summary: str = Field(description="動態摘要")
    energy_trend: str = Field(description="能量趨勢")
    peak_escalation_stage: int = Field(ge=1, le=4, default=1)


class AnalysisError(BaseModel):
    success: bool = Field(default=False)
    error_code: str = Field(description="錯誤代碼")
    error_message: str = Field(description="錯誤訊息")
    suggestions: List[str] = Field(default_factory=list)
