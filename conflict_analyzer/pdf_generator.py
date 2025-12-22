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
        self.set_auto_page_break(auto=True, margin=25)
        self.set_margins(left=20, top=20, right=20)
        
        self.font_name = "Helvetica"  # 預設使用內建字體
        self.use_chinese = False
        
        # 嘗試添加中文字體
        font_paths = [
            ("C:/Windows/Fonts/msyh.ttc", 0),      # 微軟雅黑
            ("C:/Windows/Fonts/msjh.ttc", 0),      # 微軟正黑體
            ("C:/Windows/Fonts/simsun.ttc", 0),    # 宋體
            ("C:/Windows/Fonts/simhei.ttf", None), # 黑體
        ]
        
        for font_info in font_paths:
            font_path = font_info[0]
            font_index = font_info[1] if len(font_info) > 1 else None
            
            if os.path.exists(font_path):
                try:
                    if font_path.endswith('.ttc') and font_index is not None:
                        self.add_font("Chinese", "", font_path, uni=True)
                    else:
                        self.add_font("Chinese", "", font_path, uni=True)
                    self.font_name = "Chinese"
                    self.use_chinese = True
                    print(f"📍[PDF] 使用字體: {font_path}")
                    break
                except Exception as e:
                    print(f"⚠️ 字體載入失敗 {font_path}: {e}")
                    continue
        
        if not self.use_chinese:
            print("⚠️ [PDF] 無法載入中文字體，使用內建字體")
    
    def header(self):
        """頁眉"""
        self.set_font(self.font_name, '', 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, 'Conflict Genesis - Analysis Report', 0, 1, 'C')
        self.ln(3)
    
    def footer(self):
        """頁腳"""
        self.set_y(-20)
        self.set_font(self.font_name, '', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    
    def safe_text(self, text: str) -> str:
        """安全處理文本，移除無法渲染的字符"""
        if not text:
            return ""
        # 移除可能造成問題的特殊字符
        text = str(text)
        # 如果不使用中文字體，轉換為 ASCII 安全文本
        if not self.use_chinese:
            # 替換中文標點
            replacements = {
                '：': ': ', '，': ', ', '。': '. ', '！': '! ',
                '？': '? ', '「': '"', '」': '"', '（': '(', '）': ')',
                '、': ', ', '；': '; ', '"': '"', '"': '"',
                '【': '[', '】': ']', '…': '...',
            }
            for ch, rep in replacements.items():
                text = text.replace(ch, rep)
        return text
    
    def chapter_title(self, title: str, color: tuple = (70, 130, 180)):
        """章節標題"""
        self.set_font(self.font_name, 'B' if self.font_name == "Helvetica" else '', 14)
        self.set_text_color(*color)
        self.cell(0, 12, self.safe_text(title), 0, 1)
        self.set_text_color(0, 0, 0)
        self.ln(4)
    
    def section_title(self, title: str):
        """小節標題"""
        self.set_font(self.font_name, 'B' if self.font_name == "Helvetica" else '', 11)
        self.set_text_color(60, 60, 60)
        self.cell(0, 8, self.safe_text(title), 0, 1)
        self.set_text_color(0, 0, 0)
        self.ln(2)
    
    def body_text(self, text: str):
        """正文"""
        if not text:
            return
        self.set_font(self.font_name, '', 10)
        self.set_text_color(40, 40, 40)
        # 確保有足夠的寬度
        safe_text = self.safe_text(text)
        if safe_text:
            self.multi_cell(0, 6, safe_text)
            self.ln(3)
    
    def key_value(self, key: str, value: str):
        """鍵值對"""
        if not value:
            return
        self.set_font(self.font_name, 'B' if self.font_name == "Helvetica" else '', 10)
        self.set_text_color(80, 80, 80)
        key_text = self.safe_text(f"{key}: ")
        self.cell(0, 6, key_text, 0, 1)
        self.set_font(self.font_name, '', 10)
        self.set_text_color(40, 40, 40)
        value_text = self.safe_text(str(value))
        if value_text:
            self.multi_cell(0, 6, value_text)
        self.ln(2)
    
    def bullet_point(self, text: str):
        """項目符號"""
        if not text:
            return
        self.set_font(self.font_name, '', 10)
        self.set_text_color(40, 40, 40)
        safe_text = self.safe_text(text)
        if safe_text:
            self.cell(8, 6, "-", 0, 0)
            self.multi_cell(0, 6, safe_text)


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
    pdf.set_font(pdf.font_name, 'B' if pdf.font_name == "Helvetica" else '', 22)
    pdf.set_text_color(70, 130, 180)
    pdf.ln(50)
    pdf.cell(0, 15, "Conflict Genesis", 0, 1, 'C')
    pdf.set_font(pdf.font_name, '', 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "Professional Conflict Analysis Report", 0, 1, 'C')
    pdf.ln(25)
    pdf.set_font(pdf.font_name, '', 10)
    pdf.cell(0, 8, f"Report ID: {report_id}", 0, 1, 'C')
    pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'C')
    pdf.ln(35)
    pdf.set_font(pdf.font_name, '', 9)
    pdf.set_text_color(130, 130, 130)
    pdf.multi_cell(0, 5, "Powered by Advanced AI Analysis\nFour-Stage Analysis: Evolution + Deep Source + Growth Plan + Digital Healing", align='C')
    
    stage1 = report_data.get('stage1', {})
    stage2 = report_data.get('stage2', {})
    stage3 = report_data.get('stage3', {})
    
    # ========== 一階：衝突演化分析 ==========
    pdf.add_page()
    pdf.chapter_title("Stage 1: Conflict Evolution Analysis", (220, 160, 50))
    
    # 總體動態
    if stage1.get('overall_dynamic'):
        pdf.section_title("Overall Dynamic")
        pdf.body_text(stage1['overall_dynamic'])
    
    # 能量模式
    if stage1.get('energy_pattern'):
        pdf.key_value("Energy Pattern", stage1['energy_pattern'])
    
    if stage1.get('intensity_score'):
        pdf.key_value("Conflict Intensity", f"{stage1['intensity_score']}/10")
    
    pdf.ln(3)
    
    # 演化階段
    if stage1.get('evolution_phases'):
        pdf.section_title("Evolution Phases")
        for i, phase in enumerate(stage1['evolution_phases'], 1):
            phase_name = phase.get('phase_name', f'Phase {i}')
            pdf.set_font(pdf.font_name, 'B' if pdf.font_name == "Helvetica" else '', 10)
            pdf.cell(0, 6, pdf.safe_text(f"Phase {i}: {phase_name}"), 0, 1)
            if phase.get('description'):
                pdf.body_text(phase['description'])
    
    # 轉折點
    if stage1.get('turning_points'):
        pdf.section_title("Key Turning Points")
        for tp in stage1['turning_points']:
            event = tp.get('event', '')
            impact = tp.get('impact', '')
            pdf.bullet_point(f"{event}: {impact}")
    
    # 修復分析
    if stage1.get('repair_analysis'):
        repair = stage1['repair_analysis']
        pdf.section_title("Repair Analysis")
        if repair.get('attempts_made'):
            pdf.body_text(f"Repair Attempts: {repair['attempts_made']}")
        if repair.get('missed_opportunities'):
            pdf.body_text(f"Missed Opportunities: {repair['missed_opportunities']}")
    
    # ========== 二階：深層溯源分析 ==========
    pdf.add_page()
    pdf.chapter_title("Stage 2: Deep Source Analysis", (200, 80, 130))
    
    # 冰山分析
    if stage2.get('iceberg_analysis'):
        pdf.section_title("Iceberg Analysis")
        for party, analysis in stage2['iceberg_analysis'].items():
            pdf.set_font(pdf.font_name, 'B' if pdf.font_name == "Helvetica" else '', 10)
            pdf.cell(0, 6, pdf.safe_text(f"[{party}]"), 0, 1)
            if isinstance(analysis, dict):
                if analysis.get('underlying_fear'):
                    pdf.body_text(f"Underlying Fear: {analysis['underlying_fear']}")
                if analysis.get('unmet_need'):
                    pdf.body_text(f"Unmet Need: {analysis['unmet_need']}")
                if analysis.get('core_longing'):
                    pdf.body_text(f"Core Longing: {analysis['core_longing']}")
    
    # 依附動態
    if stage2.get('attachment_dynamic'):
        pdf.section_title("Attachment Dynamic")
        pdf.body_text(stage2['attachment_dynamic'])
    
    # 療癒性重構
    if stage2.get('healing_reframes'):
        pdf.section_title("Healing Reframes")
        for reframe in stage2['healing_reframes']:
            if isinstance(reframe, dict):
                orig = reframe.get('original', '')
                reframed = reframe.get('reframed', '')
                pdf.bullet_point(f"{orig} -> {reframed}")
            else:
                pdf.bullet_point(str(reframe))
    
    # 療癒訊息
    if stage2.get('healing_message'):
        pdf.section_title("Healing Message")
        pdf.body_text(stage2['healing_message'])
    
    # ========== 三階：個人成長行動方案 ==========
    pdf.add_page()
    pdf.chapter_title("Stage 3: Personal Growth Action Plan", (50, 180, 100))
    
    # 定位
    if stage3.get('positioning'):
        pdf.section_title("Positioning")
        pdf.body_text(stage3['positioning'])
    
    # 我能做的修復
    if stage3.get('repair_self_led'):
        repair = stage3['repair_self_led']
        pdf.section_title("Self-Led Repair")
        if isinstance(repair, dict):
            if repair.get('self_care'):
                pdf.body_text(f"Self Care: {repair['self_care']}")
            if repair.get('proactive_options'):
                pdf.body_text(f"Proactive Options: {repair['proactive_options']}")
        else:
            pdf.body_text(str(repair))
    
    # 認識我的模式
    if stage3.get('my_patterns'):
        patterns = stage3['my_patterns']
        pdf.section_title("My Patterns")
        if isinstance(patterns, dict):
            if patterns.get('triggers'):
                pdf.body_text(f"Triggers: {patterns['triggers']}")
            if patterns.get('blind_spots'):
                pdf.body_text(f"Blind Spots: {patterns['blind_spots']}")
            if patterns.get('ideal_self'):
                pdf.body_text(f"Ideal Self: {patterns['ideal_self']}")
    
    # 替代路徑
    if stage3.get('alternative_paths'):
        pdf.section_title("Alternative Paths")
        for alt in stage3['alternative_paths']:
            if isinstance(alt, dict):
                orig = alt.get('original', '')
                alternative = alt.get('alternative', '')
                pdf.bullet_point(f"Original: {orig} -> Alternative: {alternative}")
            else:
                pdf.bullet_point(str(alt))
    
    # 我的邊界
    if stage3.get('my_boundaries'):
        boundaries = stage3['my_boundaries']
        pdf.section_title("My Boundaries")
        if isinstance(boundaries, dict):
            if boundaries.get('core_needs'):
                pdf.body_text(f"Core Needs: {boundaries['core_needs']}")
            if boundaries.get('non_negotiables'):
                pdf.body_text(f"Non-Negotiables: {boundaries['non_negotiables']}")
    
    # 意義重構
    if stage3.get('meaning_making'):
        meaning = stage3['meaning_making']
        pdf.section_title("Meaning Making")
        if isinstance(meaning, dict):
            if meaning.get('insight'):
                pdf.body_text(f"Insight: {meaning['insight']}")
            if meaning.get('growth_lesson'):
                pdf.body_text(f"Growth Lesson: {meaning['growth_lesson']}")
            if meaning.get('self_compassion'):
                pdf.body_text(f"Self Compassion: {meaning['self_compassion']}")
        else:
            pdf.body_text(str(meaning))
    
    # 反思提問
    if stage3.get('reflection_prompts'):
        pdf.section_title("Reflection Prompts")
        for prompt in stage3['reflection_prompts']:
            pdf.bullet_point(prompt)
    
    # 結語
    if stage3.get('closing'):
        pdf.section_title("Closing")
        pdf.body_text(stage3['closing'])
    
    # ========== 四階：數位催眠療癒說明 ==========
    pdf.add_page()
    pdf.chapter_title("Stage 4: Digital Hypnotic Healing", (140, 100, 200))
    
    pdf.section_title("About Your Personal Healing Audio")
    pdf.body_text(
        "Based on the three-stage analysis above, we have generated a personalized digital hypnotic healing audio for you. "
        "This audio combines Ericksonian hypnosis techniques with neuropsychology, designed specifically for your situation.\n\n"
        "Please listen in a quiet, comfortable environment, close your eyes, and let the warm voice guide you into deep relaxation and reconstruction."
    )
    
    pdf.section_title("Healing Audio Structure")
    pdf.bullet_point("Case Anchoring Opening: Confirming this healing is exclusively for you")
    pdf.bullet_point("Stabilization Phase: Breathing guidance, activating the vagus nerve")
    pdf.bullet_point("Empathic Mirroring Phase: Emotion labeling, feeling seen")
    pdf.bullet_point("Reframing and Empowerment: Cognitive restructuring, power rebuilding")
    
    pdf.ln(12)
    pdf.set_font(pdf.font_name, '', 9)
    pdf.set_text_color(130, 130, 130)
    pdf.multi_cell(0, 5, 
        "Reminder: Please listen to the healing audio through the web player.\n"
        "This report is for personal use only and does not constitute professional medical or psychological advice."
    )
    
    # 輸出
    if output_path:
        pdf.output(str(output_path))
        return output_path.read_bytes()
    else:
        return pdf.output()
