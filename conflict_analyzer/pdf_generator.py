"""
Lumina 心語 - PDF 報告生成模組 v2.0
設計風格：黑金奢華 + 現代卡片式布局
生成視覺驚艷的四階段分析 PDF 報告
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from fpdf import FPDF


# ============ 設計系統：色彩主題 ============
class DesignSystem:
    """設計系統 - 黑金奢華主題"""
    
    # 主色調
    PRIMARY_GOLD = (212, 175, 55)       # #D4AF37 金色
    SECONDARY_GOLD = (201, 169, 98)     # #C9A962 淺金
    DARK_BG = (26, 26, 26)              # #1A1A1A 深黑
    LIGHT_BG = (245, 242, 237)          # #F5F2ED 米白
    
    # 階段專屬色
    STAGE1_COLOR = (220, 160, 50)       # 金橙色
    STAGE2_COLOR = (200, 100, 150)      # 玫瑰紅
    STAGE3_COLOR = (100, 200, 150)      # 薄荷綠
    STAGE4_COLOR = (150, 120, 220)      # 夢幻紫
    
    # 文字色
    TEXT_DARK = (40, 40, 40)
    TEXT_MUTED = (120, 120, 120)
    TEXT_LIGHT = (250, 250, 250)
    
    # 裝飾色
    BORDER_SUBTLE = (230, 225, 215)
    ACCENT_LINE = (212, 175, 55)


class LuminaReportPDF(FPDF):
    """Lumina 心語 - 視覺驚艷的 PDF 報告"""
    
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=25)
        self.set_margins(left=18, top=18, right=18)
        
        self.font_name = "Helvetica"
        self.use_chinese = False
        self.current_stage_color = DesignSystem.PRIMARY_GOLD
        
        # 載入中文字體
        self._load_chinese_font()
    
    def _load_chinese_font(self):
        """載入中文字體"""
        font_paths = [
            "C:/Windows/Fonts/msyh.ttc",      # 微軟雅黑
            "C:/Windows/Fonts/msjh.ttc",      # 微軟正黑體
            "C:/Windows/Fonts/simsun.ttc",    # 宋體
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    self.add_font("Chinese", "", font_path, uni=True)
                    self.font_name = "Chinese"
                    self.use_chinese = True
                    print(f"📍[PDF] 使用字體: {font_path}")
                    break
                except Exception as e:
                    continue
    
    def header(self):
        """精緻頁眉"""
        # 金色細線
        self.set_draw_color(*DesignSystem.PRIMARY_GOLD)
        self.set_line_width(0.5)
        self.line(18, 12, self.w - 18, 12)
        
        # 標題文字
        self.set_font(self.font_name, '', 8)
        self.set_text_color(*DesignSystem.TEXT_MUTED)
        self.set_y(14)
        self.cell(0, 5, self.safe_text('Lumina 心語｜專業衝突分析報告'), 0, 1, 'C')
    
    def footer(self):
        """精緻頁腳"""
        self.set_y(-18)
        
        # 金色細線
        self.set_draw_color(*DesignSystem.PRIMARY_GOLD)
        self.set_line_width(0.3)
        self.line(18, self.h - 15, self.w - 18, self.h - 15)
        
        # 頁碼
        self.set_font(self.font_name, '', 8)
        self.set_text_color(*DesignSystem.TEXT_MUTED)
        self.cell(0, 5, self.safe_text(f'— {self.page_no()} —'), 0, 0, 'C')
    
    def safe_text(self, text: str) -> str:
        """安全處理文本，修復排版問題"""
        if not text:
            return ""
        text = str(text)
        
        # 移除可能導致空隙的問題字符
        # 1. 將全角空格替換為半角空格
        text = text.replace('\u3000', ' ')  # 全角空格
        text = text.replace('\u00A0', ' ')  # Non-breaking space
        text = text.replace('\t', ' ')      # Tab
        
        # 2. 移除多餘的連續空格
        import re
        text = re.sub(r' +', ' ', text)
        
        # 3. 中文標點替換（非使用中文字體時）
        if not self.use_chinese:
            replacements = {
                '：': ': ', '，': ', ', '。': '. ', '！': '! ',
                '？': '? ', '「': '"', '」': '"', '（': '(', '）': ')',
                '、': ', ', '；': '; ', '"': '"', '"': '"',
                '【': '[', '】': ']', '…': '...', '｜': '|',
            }
            for ch, rep in replacements.items():
                text = text.replace(ch, rep)
        
        return text
    
    # ============ 封面設計元素 ============
    
    def draw_cover_background(self):
        """繪製封面深色背景"""
        self.set_fill_color(*DesignSystem.DARK_BG)
        self.rect(0, 0, self.w, self.h, 'F')
        
        # 金色裝飾線條
        self.set_draw_color(*DesignSystem.PRIMARY_GOLD)
        self.set_line_width(1)
        
        # 上方裝飾框
        self.line(30, 40, self.w - 30, 40)
        self.line(30, 40, 30, 55)
        self.line(self.w - 30, 40, self.w - 30, 55)
        
        # 下方裝飾框
        self.line(30, self.h - 50, self.w - 30, self.h - 50)
        self.line(30, self.h - 50, 30, self.h - 65)
        self.line(self.w - 30, self.h - 50, self.w - 30, self.h - 65)
    
    def draw_gold_divider(self, y: float, style: str = 'full'):
        """繪製金色分隔線"""
        self.set_draw_color(*DesignSystem.PRIMARY_GOLD)
        
        if style == 'full':
            self.set_line_width(0.5)
            self.line(18, y, self.w - 18, y)
        elif style == 'center':
            self.set_line_width(0.3)
            center = self.w / 2
            self.line(center - 40, y, center + 40, y)
            # 中心點裝飾
            self.set_fill_color(*DesignSystem.PRIMARY_GOLD)
            self.ellipse(center - 1.5, y - 1.5, 3, 3, 'F')
        elif style == 'dots':
            self.set_fill_color(*DesignSystem.PRIMARY_GOLD)
            for i in range(5):
                x = self.w / 2 - 20 + i * 10
                self.ellipse(x, y, 2, 2, 'F')
    
    # ============ 階段標題設計 ============
    
    def stage_header(self, stage_num: int, title: str, subtitle: str = ""):
        """階段標題區塊"""
        colors = {
            1: DesignSystem.STAGE1_COLOR,
            2: DesignSystem.STAGE2_COLOR,
            3: DesignSystem.STAGE3_COLOR,
            4: DesignSystem.STAGE4_COLOR,
        }
        color = colors.get(stage_num, DesignSystem.PRIMARY_GOLD)
        self.current_stage_color = color
        
        # 色塊背景
        self.set_fill_color(*color)
        self.rect(0, 20, self.w, 28, 'F')
        
        # 階段編號
        self.set_font(self.font_name, 'B' if self.font_name == "Helvetica" else '', 11)
        self.set_text_color(*DesignSystem.TEXT_LIGHT)
        self.set_xy(18, 24)
        stage_labels = {1: "STAGE 01", 2: "STAGE 02", 3: "STAGE 03", 4: "STAGE 04"}
        self.cell(0, 6, stage_labels.get(stage_num, f"STAGE {stage_num:02d}"), 0, 1)
        
        # 階段標題
        self.set_font(self.font_name, 'B' if self.font_name == "Helvetica" else '', 16)
        self.set_xy(18, 32)
        self.cell(0, 8, self.safe_text(title), 0, 1)
        
        # 副標題
        if subtitle:
            self.set_font(self.font_name, '', 9)
            self.set_text_color(220, 220, 220)  # 淺灰色代替透明白
            self.set_xy(18, 40)
            self.cell(0, 5, self.safe_text(subtitle), 0, 1)
        
        self.set_y(55)
        self.set_text_color(*DesignSystem.TEXT_DARK)
    
    # ============ 內容區塊設計 ============
    
    def section_card(self, title: str, content: str):
        """卡片式內容區塊"""
        if not content:
            return
        
        start_y = self.get_y()
        
        # 卡片背景
        self.set_fill_color(252, 251, 248)  # 淺米色
        self.set_draw_color(*DesignSystem.BORDER_SUBTLE)
        
        # 計算內容高度
        self.set_font(self.font_name, '', 10)
        content_width = self.w - 50
        
        # 標題
        self.set_font(self.font_name, 'B' if self.font_name == "Helvetica" else '', 11)
        self.set_text_color(*self.current_stage_color)
        self.set_x(22)
        self.cell(0, 8, self.safe_text(f"▎{title}"), 0, 1)
        
        # 內容
        self.set_font(self.font_name, '', 10)
        self.set_text_color(*DesignSystem.TEXT_DARK)
        self.set_x(24)
        self.multi_cell(content_width, 6, self.safe_text(content), align='L')
        self.ln(4)
    
    def key_value_row(self, key: str, value: str):
        """鍵值對行"""
        if not value:
            return
        
        self.set_font(self.font_name, 'B' if self.font_name == "Helvetica" else '', 10)
        self.set_text_color(*self.current_stage_color)
        self.set_x(24)
        self.cell(50, 6, self.safe_text(f"● {key}"), 0, 0)
        
        self.set_font(self.font_name, '', 10)
        self.set_text_color(*DesignSystem.TEXT_DARK)
        self.multi_cell(self.w - 80, 6, self.safe_text(str(value)), align='L')
        self.ln(2)
    
    def bullet_item(self, text: str, indent: int = 0):
        """項目符號"""
        if not text:
            return
        
        self.set_font(self.font_name, '', 10)
        self.set_text_color(*DesignSystem.TEXT_DARK)
        
        x_offset = 24 + indent * 10
        bullet_color = self.current_stage_color
        
        # 彩色圓點
        self.set_fill_color(*bullet_color)
        self.ellipse(x_offset, self.get_y() + 2, 2.5, 2.5, 'F')
        
        self.set_x(x_offset + 6)
        self.multi_cell(self.w - x_offset - 24, 6, self.safe_text(text), align='L')
        self.ln(1)
    
    def quote_block(self, text: str):
        """引言區塊"""
        if not text:
            return
        
        # 左側裝飾線
        self.set_draw_color(*self.current_stage_color)
        self.set_line_width(1.5)
        start_y = self.get_y()
        
        # 內容
        self.set_fill_color(250, 248, 245)
        self.set_font(self.font_name, '', 10)
        self.set_text_color(*DesignSystem.TEXT_DARK)
        self.set_x(30)
        self.multi_cell(self.w - 50, 7, self.safe_text(text), align='L')
        
        end_y = self.get_y()
        self.line(24, start_y, 24, end_y)
        self.ln(4)


def generate_pdf_report(
    report_data: Dict[str, Any],
    report_id: str,
    output_path: Optional[Path] = None
) -> bytes:
    """
    生成視覺驚艷的四階段 PDF 報告
    """
    pdf = LuminaReportPDF()
    
    # ========== 封面頁 ==========
    pdf.add_page()
    pdf.draw_cover_background()
    
    # 主標題
    pdf.set_font(pdf.font_name, 'B' if pdf.font_name == "Helvetica" else '', 36)
    pdf.set_text_color(*DesignSystem.PRIMARY_GOLD)
    pdf.set_y(80)
    pdf.cell(0, 15, pdf.safe_text("Lumina"), 0, 1, 'C')
    
    pdf.set_font(pdf.font_name, '', 18)
    pdf.set_text_color(*DesignSystem.SECONDARY_GOLD)
    pdf.cell(0, 10, pdf.safe_text("心語"), 0, 1, 'C')
    
    # 分隔裝飾
    pdf.draw_gold_divider(pdf.get_y() + 10, 'center')
    
    # 副標題
    pdf.set_y(130)
    pdf.set_font(pdf.font_name, '', 14)
    pdf.set_text_color(*DesignSystem.TEXT_LIGHT)
    pdf.cell(0, 8, pdf.safe_text("專業衝突分析報告"), 0, 1, 'C')
    
    pdf.ln(30)
    
    # 報告資訊
    pdf.set_font(pdf.font_name, '', 10)
    pdf.set_text_color(*DesignSystem.TEXT_MUTED)
    pdf.cell(0, 6, pdf.safe_text(f"報告編號：{report_id}"), 0, 1, 'C')
    pdf.cell(0, 6, pdf.safe_text(f"生成時間：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}"), 0, 1, 'C')
    
    # 底部說明
    pdf.set_y(pdf.h - 70)
    pdf.set_font(pdf.font_name, '', 9)
    pdf.set_text_color(*DesignSystem.TEXT_MUTED)
    pdf.multi_cell(0, 5, pdf.safe_text(
        "四階段深度分析\n"
        "衝突演化 • 深層溯源 • 成長方案 • 數位療癒"
    ), align='C')
    
    pdf.set_y(pdf.h - 40)
    pdf.set_font(pdf.font_name, '', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, pdf.safe_text("Powered by Advanced AI Analysis Engine"), 0, 1, 'C')
    
    stage1 = report_data.get('stage1', {})
    stage2 = report_data.get('stage2', {})
    stage3 = report_data.get('stage3', {})
    
    # ========== 第一階段：衝突演化追蹤 ==========
    pdf.add_page()
    pdf.stage_header(1, "衝突演化追蹤", "追蹤衝突從萌芽到高峰的演化軌跡")
    
    if stage1.get('overall_dynamic'):
        pdf.section_card("整體動態", stage1['overall_dynamic'])
    
    if stage1.get('energy_pattern'):
        pdf.key_value_row("能量模式", stage1['energy_pattern'])
    
    if stage1.get('intensity_score'):
        pdf.key_value_row("衝突強度", f"{stage1['intensity_score']}/10")
    
    # 演化階段
    if stage1.get('evolution_phases'):
        pdf.ln(5)
        pdf.set_font(pdf.font_name, 'B' if pdf.font_name == "Helvetica" else '', 11)
        pdf.set_text_color(*pdf.current_stage_color)
        pdf.set_x(22)
        pdf.cell(0, 8, pdf.safe_text("▎演化階段"), 0, 1)
        
        for i, phase in enumerate(stage1['evolution_phases'], 1):
            phase_name = phase.get('phase_name', f'階段 {i}')
            desc = phase.get('description', '')
            pdf.bullet_item(f"{phase_name}：{desc}")
    
    # 轉折點
    if stage1.get('turning_points'):
        pdf.ln(5)
        pdf.set_font(pdf.font_name, 'B' if pdf.font_name == "Helvetica" else '', 11)
        pdf.set_text_color(*pdf.current_stage_color)
        pdf.set_x(22)
        pdf.cell(0, 8, pdf.safe_text("▎關鍵轉折點"), 0, 1)
        
        for tp in stage1['turning_points']:
            event = tp.get('event', tp.get('moment', ''))
            impact = tp.get('impact', tp.get('why_critical', ''))
            if event:
                pdf.bullet_item(f"{event}" + (f" — {impact}" if impact else ""))
    
    # ========== 第二階段：深層溯源 ==========
    pdf.add_page()
    pdf.stage_header(2, "深層溯源與接納橋樑", "探索冰山下的脆弱需求與依附動態")
    
    # 冰山分析
    if stage2.get('iceberg_analysis'):
        iceberg = stage2['iceberg_analysis']
        
        pdf.set_font(pdf.font_name, 'B' if pdf.font_name == "Helvetica" else '', 11)
        pdf.set_text_color(*pdf.current_stage_color)
        pdf.set_x(22)
        pdf.cell(0, 8, pdf.safe_text("▎冰山模型分析"), 0, 1)
        
        if isinstance(iceberg, list):
            for analysis in iceberg:
                if isinstance(analysis, dict):
                    party = analysis.get('party', analysis.get('speaker', ''))
                    if party:
                        pdf.set_font(pdf.font_name, 'B' if pdf.font_name == "Helvetica" else '', 10)
                        pdf.set_text_color(*DesignSystem.TEXT_DARK)
                        pdf.set_x(24)
                        pdf.cell(0, 7, pdf.safe_text(f"【{party}】"), 0, 1)
                    
                    fields = [
                        ('underlying_fear', '深層恐懼'),
                        ('unmet_need', '未滿足需求'),
                        ('core_longing', '核心渴望'),
                        ('surface_behavior', '表層行為'),
                        ('feelings', '感受'),
                        ('perception', '認知'),
                        ('expectation', '期待'),
                        ('longing', '渴望'),
                    ]
                    for key, label in fields:
                        if analysis.get(key):
                            pdf.bullet_item(f"{label}：{analysis[key]}", indent=1)
                    pdf.ln(3)
    
    if stage2.get('attachment_dynamic'):
        pdf.section_card("依附動態", stage2['attachment_dynamic'])
    
    if stage2.get('healing_message'):
        pdf.ln(3)
        pdf.set_font(pdf.font_name, 'B' if pdf.font_name == "Helvetica" else '', 11)
        pdf.set_text_color(*pdf.current_stage_color)
        pdf.set_x(22)
        pdf.cell(0, 8, pdf.safe_text("▎療癒訊息"), 0, 1)
        pdf.quote_block(stage2['healing_message'])
    
    # ========== 第三階段：個人成長行動方案 ==========
    pdf.add_page()
    pdf.stage_header(3, "個人成長行動方案", "聚焦「我能做什麼」的具體行動")
    
    if stage3.get('positioning'):
        pdf.section_card("定位", stage3['positioning'])
    
    # 我能做的修復
    if stage3.get('repair_self_led'):
        repair = stage3['repair_self_led']
        if isinstance(repair, dict):
            pdf.set_font(pdf.font_name, 'B' if pdf.font_name == "Helvetica" else '', 11)
            pdf.set_text_color(*pdf.current_stage_color)
            pdf.set_x(22)
            pdf.cell(0, 8, pdf.safe_text("▎我能做的修復"), 0, 1)
            
            if repair.get('self_care'):
                pdf.bullet_item(f"自我照顧：{repair['self_care']}")
            if repair.get('proactive_options'):
                pdf.bullet_item(f"主動選項：{repair['proactive_options']}")
    
    # 我的模式
    if stage3.get('my_patterns'):
        patterns = stage3['my_patterns']
        if isinstance(patterns, dict):
            pdf.ln(3)
            pdf.set_font(pdf.font_name, 'B' if pdf.font_name == "Helvetica" else '', 11)
            pdf.set_text_color(*pdf.current_stage_color)
            pdf.set_x(22)
            pdf.cell(0, 8, pdf.safe_text("▎認識我的模式"), 0, 1)
            
            if patterns.get('triggers'):
                pdf.bullet_item(f"觸發點：{patterns['triggers']}")
            if patterns.get('blind_spots'):
                pdf.bullet_item(f"盲點：{patterns['blind_spots']}")
            if patterns.get('ideal_self'):
                pdf.bullet_item(f"理想的自己：{patterns['ideal_self']}")
    
    # 替代路徑
    alts = stage3.get('alternative_paths', stage3.get('alternatives'))
    if alts:
        pdf.ln(3)
        pdf.set_font(pdf.font_name, 'B' if pdf.font_name == "Helvetica" else '', 11)
        pdf.set_text_color(*pdf.current_stage_color)
        pdf.set_x(22)
        pdf.cell(0, 8, pdf.safe_text("▎替代路徑"), 0, 1)
        
        if isinstance(alts, list):
            for alt in alts:
                if isinstance(alt, dict):
                    orig = alt.get('original', alt.get('what_i_did', ''))
                    new = alt.get('alternative', alt.get('what_i_could_try', ''))
                    if orig and new:
                        pdf.bullet_item(f"從「{orig}」→ 嘗試「{new}」")
        elif isinstance(alts, dict):
            if alts.get('what_i_did'):
                pdf.bullet_item(f"我做了：{alts['what_i_did']}")
            if alts.get('what_i_could_try'):
                pdf.bullet_item(f"我可以嘗試：{alts['what_i_could_try']}")
            if alts.get('micro_experiment'):
                pdf.bullet_item(f"微小實驗：{alts['micro_experiment']}")
    
    # 結語
    if stage3.get('closing'):
        pdf.ln(5)
        pdf.set_font(pdf.font_name, 'B' if pdf.font_name == "Helvetica" else '', 11)
        pdf.set_text_color(*pdf.current_stage_color)
        pdf.set_x(22)
        pdf.cell(0, 8, pdf.safe_text("▎結語"), 0, 1)
        pdf.quote_block(stage3['closing'])
    
    # ========== 第四階段：數位催眠療癒 ==========
    pdf.add_page()
    pdf.stage_header(4, "數位催眠療癒", "專屬於您的療癒引導音頻")
    
    pdf.section_card(
        "關於您的專屬療癒音頻",
        "基於以上三階段的深度分析，我們為您生成了一段個人化的數位催眠療癒音頻。"
        "這段音頻結合了艾瑞克森式催眠技術與神經心理學，專門為您的情況量身打造。"
        "\n\n請在安靜舒適的環境中聆聽，閉上眼睛，讓溫暖的聲音引導您進入深度放鬆與重建。"
    )
    
    pdf.ln(5)
    pdf.set_font(pdf.font_name, 'B' if pdf.font_name == "Helvetica" else '', 11)
    pdf.set_text_color(*pdf.current_stage_color)
    pdf.set_x(22)
    pdf.cell(0, 8, pdf.safe_text("▎療癒音頻結構"), 0, 1)
    
    pdf.bullet_item("案件錨定開場：確認這段療癒是專屬於您的")
    pdf.bullet_item("穩定化階段：呼吸導引，激活迷走神經")
    pdf.bullet_item("共情鏡映階段：情緒標籤，感受被看見")
    pdf.bullet_item("重構與賦能：認知重構，力量重建")
    
    # 底部提醒
    pdf.ln(15)
    pdf.draw_gold_divider(pdf.get_y(), 'dots')
    pdf.ln(8)
    
    pdf.set_font(pdf.font_name, '', 9)
    pdf.set_text_color(*DesignSystem.TEXT_MUTED)
    pdf.multi_cell(0, 5, pdf.safe_text(
        "提醒：請透過網頁播放器聆聽療癒音頻。\n"
        "本報告僅供個人使用，不構成專業醫療或心理諮詢建議。"
    ), align='C')
    
    # 輸出
    if output_path:
        pdf.output(str(output_path))
        return output_path.read_bytes()
    else:
        return pdf.output()
