"""
衝突基因 - PDF 報告生成模組
生成完整的四階段分析 PDF 報告
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from fpdf import FPDF


class ConflictReportPDF(FPDF):
    """自定義 PDF 類，支援中文"""
    
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
        
        # 嘗試添加中文字體
        font_paths = [
            "C:/Windows/Fonts/msjh.ttc",      # 微軟正黑體
            "C:/Windows/Fonts/mingliu.ttc",   # 細明體
            "C:/Windows/Fonts/simsun.ttc",    # 宋體
        ]
        
        font_added = False
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    self.add_font("Chinese", "", font_path, uni=True)
                    self.add_font("Chinese", "B", font_path, uni=True)
                    font_added = True
                    break
                except Exception:
                    continue
        
        if not font_added:
            # 如果沒有中文字體，使用 Arial（部分中文可能顯示為方塊）
            pass
        
        self.font_name = "Chinese" if font_added else "Arial"
    
    def header(self):
        """頁眉"""
        self.set_font(self.font_name, 'B', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, '衝突基因 - 專業衝突分析報告', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        """頁腳"""
        self.set_y(-15)
        self.set_font(self.font_name, '', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    
    def chapter_title(self, title: str, color: tuple = (212, 175, 55)):
        """章節標題"""
        self.set_font(self.font_name, 'B', 14)
        self.set_text_color(*color)
        self.cell(0, 10, title, 0, 1)
        self.set_text_color(0, 0, 0)
        self.ln(3)
    
    def section_title(self, title: str):
        """小節標題"""
        self.set_font(self.font_name, 'B', 11)
        self.set_text_color(80, 80, 80)
        self.cell(0, 8, title, 0, 1)
        self.set_text_color(0, 0, 0)
        self.ln(2)
    
    def body_text(self, text: str):
        """正文"""
        self.set_font(self.font_name, '', 10)
        self.set_text_color(50, 50, 50)
        # 處理換行
        self.multi_cell(0, 6, text)
        self.ln(3)
    
    def key_value(self, key: str, value: str):
        """鍵值對"""
        self.set_font(self.font_name, 'B', 10)
        self.set_text_color(80, 80, 80)
        self.cell(50, 6, f"{key}:", 0, 0)
        self.set_font(self.font_name, '', 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 6, str(value) if value else "N/A")
    
    def bullet_point(self, text: str):
        """項目符號"""
        self.set_font(self.font_name, '', 10)
        self.set_text_color(50, 50, 50)
        self.cell(5, 6, "•", 0, 0)
        self.multi_cell(0, 6, text)


def generate_pdf_report(
    report_data: Dict[str, Any],
    report_id: str,
    output_path: Optional[Path] = None
) -> bytes:
    """
    生成完整的四階段 PDF 報告
    
    Args:
        report_data: 包含 stage1, stage2, stage3 的完整報告數據
        report_id: 報告編號
        output_path: 可選的輸出路徑
        
    Returns:
        PDF 文件的 bytes
    """
    pdf = ConflictReportPDF()
    
    # ========== 封面頁 ==========
    pdf.add_page()
    pdf.set_font(pdf.font_name, 'B', 24)
    pdf.set_text_color(212, 175, 55)
    pdf.ln(40)
    pdf.cell(0, 15, "衝突基因", 0, 1, 'C')
    pdf.set_font(pdf.font_name, '', 14)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "專業衝突分析報告", 0, 1, 'C')
    pdf.ln(20)
    pdf.set_font(pdf.font_name, '', 10)
    pdf.cell(0, 8, f"報告編號: {report_id}", 0, 1, 'C')
    pdf.cell(0, 8, f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'C')
    pdf.ln(30)
    pdf.set_font(pdf.font_name, '', 9)
    pdf.set_text_color(128, 128, 128)
    pdf.multi_cell(0, 5, "本報告由先進人工智慧驅動生成\n四階段分析：演化追蹤 + 深層溯源 + 成長方案 + 數位催眠療癒", align='C')
    
    stage1 = report_data.get('stage1', {})
    stage2 = report_data.get('stage2', {})
    stage3 = report_data.get('stage3', {})
    
    # ========== 一階：衝突演化分析 ==========
    pdf.add_page()
    pdf.chapter_title("📊 一階：衝突演化分析", (212, 175, 55))
    
    # 總體動態
    if stage1.get('overall_dynamic'):
        pdf.section_title("整體動態")
        pdf.body_text(stage1['overall_dynamic'])
    
    # 能量模式
    if stage1.get('energy_pattern'):
        pdf.key_value("能量變化模式", stage1['energy_pattern'])
    
    if stage1.get('intensity_score'):
        pdf.key_value("衝突烈度指數", f"{stage1['intensity_score']}/10")
    
    pdf.ln(5)
    
    # 演化階段
    if stage1.get('evolution_phases'):
        pdf.section_title("衝突演化階段")
        for i, phase in enumerate(stage1['evolution_phases'], 1):
            pdf.set_font(pdf.font_name, 'B', 10)
            pdf.cell(0, 6, f"階段 {i}: {phase.get('phase_name', '')}", 0, 1)
            if phase.get('description'):
                pdf.body_text(phase['description'])
    
    # 轉折點
    if stage1.get('turning_points'):
        pdf.section_title("關鍵轉折點")
        for tp in stage1['turning_points']:
            pdf.bullet_point(f"{tp.get('event', '')}: {tp.get('impact', '')}")
    
    # 修復分析
    if stage1.get('repair_analysis'):
        repair = stage1['repair_analysis']
        pdf.section_title("修復分析")
        if repair.get('attempts_made'):
            pdf.body_text(f"修復嘗試: {repair['attempts_made']}")
        if repair.get('missed_opportunities'):
            pdf.body_text(f"錯過的機會: {repair['missed_opportunities']}")
    
    # ========== 二階：深層溯源分析 ==========
    pdf.add_page()
    pdf.chapter_title("💡 二階：深層溯源與接納橋樑", (236, 72, 153))
    
    # 冰山分析
    if stage2.get('iceberg_analysis'):
        pdf.section_title("冰山下方分析")
        for party, analysis in stage2['iceberg_analysis'].items():
            pdf.set_font(pdf.font_name, 'B', 10)
            pdf.cell(0, 6, f"【{party}】", 0, 1)
            if isinstance(analysis, dict):
                if analysis.get('underlying_fear'):
                    pdf.body_text(f"深層恐懼: {analysis['underlying_fear']}")
                if analysis.get('unmet_need'):
                    pdf.body_text(f"未滿足需求: {analysis['unmet_need']}")
                if analysis.get('core_longing'):
                    pdf.body_text(f"核心渴望: {analysis['core_longing']}")
    
    # 依附動態
    if stage2.get('attachment_dynamic'):
        pdf.section_title("依附動態分析")
        pdf.body_text(stage2['attachment_dynamic'])
    
    # 療癒性重構
    if stage2.get('healing_reframes'):
        pdf.section_title("療癒性重構")
        for reframe in stage2['healing_reframes']:
            if isinstance(reframe, dict):
                pdf.bullet_point(f"{reframe.get('original', '')} → {reframe.get('reframed', '')}")
            else:
                pdf.bullet_point(str(reframe))
    
    # 療癒訊息
    if stage2.get('healing_message'):
        pdf.section_title("療癒訊息")
        pdf.body_text(stage2['healing_message'])
    
    # ========== 三階：個人成長行動方案 ==========
    pdf.add_page()
    pdf.chapter_title("🌱 三階：個人成長行動方案", (34, 197, 94))
    
    # 定位
    if stage3.get('positioning'):
        pdf.section_title("定位與立場")
        pdf.body_text(stage3['positioning'])
    
    # 我能做的修復
    if stage3.get('repair_self_led'):
        repair = stage3['repair_self_led']
        pdf.section_title("我能做的修復")
        if isinstance(repair, dict):
            if repair.get('self_care'):
                pdf.body_text(f"自我照顧: {repair['self_care']}")
            if repair.get('proactive_options'):
                pdf.body_text(f"主動選項: {repair['proactive_options']}")
        else:
            pdf.body_text(str(repair))
    
    # 認識我的模式
    if stage3.get('my_patterns'):
        patterns = stage3['my_patterns']
        pdf.section_title("認識我的模式")
        if isinstance(patterns, dict):
            if patterns.get('triggers'):
                pdf.body_text(f"觸發點: {patterns['triggers']}")
            if patterns.get('blind_spots'):
                pdf.body_text(f"盲點: {patterns['blind_spots']}")
            if patterns.get('ideal_self'):
                pdf.body_text(f"理想自我: {patterns['ideal_self']}")
    
    # 替代路徑
    if stage3.get('alternative_paths'):
        pdf.section_title("替代路徑")
        for alt in stage3['alternative_paths']:
            if isinstance(alt, dict):
                pdf.bullet_point(f"原本: {alt.get('original', '')} → 替代: {alt.get('alternative', '')}")
            else:
                pdf.bullet_point(str(alt))
    
    # 我的邊界
    if stage3.get('my_boundaries'):
        boundaries = stage3['my_boundaries']
        pdf.section_title("我的邊界與底線")
        if isinstance(boundaries, dict):
            if boundaries.get('core_needs'):
                pdf.body_text(f"核心需求: {boundaries['core_needs']}")
            if boundaries.get('non_negotiables'):
                pdf.body_text(f"絕對底線: {boundaries['non_negotiables']}")
    
    # 意義重構
    if stage3.get('meaning_making'):
        meaning = stage3['meaning_making']
        pdf.section_title("意義重構")
        if isinstance(meaning, dict):
            if meaning.get('insight'):
                pdf.body_text(f"洞見: {meaning['insight']}")
            if meaning.get('growth_lesson'):
                pdf.body_text(f"成長功課: {meaning['growth_lesson']}")
            if meaning.get('self_compassion'):
                pdf.body_text(f"自我疼惜: {meaning['self_compassion']}")
        else:
            pdf.body_text(str(meaning))
    
    # 反思提問
    if stage3.get('reflection_prompts'):
        pdf.section_title("反思提問")
        for prompt in stage3['reflection_prompts']:
            pdf.bullet_point(prompt)
    
    # 結語
    if stage3.get('closing'):
        pdf.section_title("結語")
        pdf.body_text(stage3['closing'])
    
    # ========== 四階：數位催眠療癒說明 ==========
    pdf.add_page()
    pdf.chapter_title("🎵 四階：數位催眠療癒", (139, 92, 246))
    
    pdf.section_title("關於您的專屬療癒音頻")
    pdf.body_text(
        "根據以上三階段的分析，我們為您生成了一段專屬的數位催眠療癒音頻。"
        "這段音頻融合了艾瑞克森式催眠技術與神經心理學，專為您的情境設計。\n\n"
        "請在安靜、舒適的環境中聆聽，閉上眼睛，讓溫暖的聲音引導您進入深度放鬆與重建。"
    )
    
    pdf.section_title("療癒音頻結構")
    pdf.bullet_point("案件連結開場：確認這是專屬於您的療癒")
    pdf.bullet_point("穩定化階段：呼吸引導，激活迷走神經")
    pdf.bullet_point("同感鏡映階段：情緒標記，被看見的感覺")
    pdf.bullet_point("重新框架與賦權：認知重構，力量重建")
    
    pdf.ln(10)
    pdf.set_font(pdf.font_name, '', 9)
    pdf.set_text_color(128, 128, 128)
    pdf.multi_cell(0, 5, 
        "提醒：療癒音頻請透過網頁版播放器聆聽。\n"
        "本報告僅供個人使用，不構成專業醫療或心理諮詢建議。"
    )
    
    # 輸出
    if output_path:
        pdf.output(str(output_path))
        return output_path.read_bytes()
    else:
        return pdf.output()
