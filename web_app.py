#!/usr/bin/env python3
"""
Lumina 心語 - 網頁介面 v3.0
一階：衝突演化追蹤器
二階：深層溯源與接納橋樑
三階：個人成長行動方案
"""

import os
import json
import uuid
import traceback
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

from conflict_analyzer import ConflictAnalyzer, AudioProcessor
from conflict_analyzer.conflict_analyzer import AnalysisConfig, ConflictAnalyzerError
from conflict_analyzer.prompts import DEFAULT_STAGE1_PROMPT, DEFAULT_STAGE2_PROMPT, DEFAULT_STAGE3_PROMPT, DEFAULT_STAGE4_PROMPT
from conflict_analyzer.image_generator import ImageGenerator
from conflict_analyzer.healing_audio import HealingAudioGenerator
from conflict_analyzer.pdf_generator import generate_pdf_report

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = Path(__file__).parent / 'uploads'
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)
app.config['REPORTS_FOLDER'] = Path(__file__).parent / 'reports'
app.config['REPORTS_FOLDER'].mkdir(exist_ok=True)
app.config['IMAGES_FOLDER'] = Path(__file__).parent / 'generated_images'
app.config['IMAGES_FOLDER'].mkdir(exist_ok=True)

# CORS 設定 - 允許 Vercel 前端跨域請求
from flask_cors import CORS
CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://conflict-genesis-web.vercel.app",
        ],
        "origins_regex": r"https://.*\.vercel\.app",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
    }
})

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'aiff', 'aac', 'ogg', 'flac', 'm4a'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_event_topic(report_data: dict) -> str:
    """
    從分析結果中提取事件主題，用於 PDF 檔名和簡介
    
    提取優先順序：
    1. stage1.overall_dynamic 的前 15 個字
    2. stage1.energy_pattern 的前 15 個字
    3. stage2.deep_insight_summary 的前 15 個字
    4. 預設返回 None
    """
    import re
    
    stage1 = report_data.get('stage1', {})
    stage2 = report_data.get('stage2', {})
    
    # 嘗試從不同欄位提取主題
    candidates = [
        stage1.get('overall_dynamic'),
        stage1.get('energy_pattern'),
        stage2.get('deep_insight_summary'),
    ]
    
    for text in candidates:
        if text and isinstance(text, str) and len(text) > 3:
            # 清理並截取前 15 個字
            cleaned = re.sub(r'[^\w\u4e00-\u9fff]', '', text)[:15]
            if len(cleaned) >= 2:
                return cleaned
    
    return None


def sanitize_filename(filename: str) -> str:
    """
    清理檔名中的非法字符，保留中文
    """
    import re
    if not filename:
        return "衝突分析"
    
    # 移除或替換非法字符
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    sanitized = re.sub(r'\s+', '_', sanitized)
    sanitized = sanitized[:30]  # 限制長度
    
    return sanitized if sanitized else "衝突分析"


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lumina 心語 - 專業衝突分析報告</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            /* 高端暖色系 Premium Warm Palette */
            --bg-primary: #FAF8F5;           /* 象牙白 Ivory */
            --bg-secondary: #F5F2ED;         /* 亞麻色 Linen */
            --bg-card: rgba(255, 253, 250, 0.95);  /* 奶油白 Cream */
            
            /* 四階段主色 */
            --accent-stage1: #C9A962;        /* 琥珀金 Amber Gold */
            --accent-stage2: #B87351;        /* 赤陶褐 Terracotta */
            --accent-stage3: #A3B899;        /* 鼠尾草綠 Sage Green */
            --accent-stage4: #D4A5A5;        /* 珊瑚玫瑰 Coral Rose */
            
            /* 功能色 */
            --accent-gold: #C9A962;
            --accent-gold-light: #D4B87A;
            --accent-primary: #8B7355;       /* 摩卡棕 Mocha */
            --accent-secondary: #A69080;     /* 駝色 Taupe */
            --accent-danger: #C17A6E;        /* 暖紅 Warm Red */
            --accent-success: #A3B899;       /* 鼠尾草綠 */
            --accent-warning: #D4A574;       /* 焦糖色 Caramel */
            --accent-healing: #D4A5A5;       /* 珊瑚玫瑰 */
            
            /* 文字色 - 高對比度版本 */
            --text-primary: #2A2218;         /* 深棕色 Dark Brown - 更深 */
            --text-secondary: #4A3D32;       /* 中棕色 Medium Brown - 加深 */
            --text-muted: #5D4F42;           /* 淺棕色 Light Brown - 加深 */
            --border-color: rgba(201, 169, 98, 0.25);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Noto Sans TC', sans-serif; background: var(--bg-primary); color: var(--text-primary); min-height: 100vh; }
        .bg-animation { position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 0; }
        #heroCanvas { position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 0; }
        .container { max-width: 1100px; margin: 0 auto; padding: 40px 20px; position: relative; z-index: 1; }
        
        /* Hero Section - 大師級視覺設計 */
        header { 
            text-align: center; 
            margin-bottom: 50px; 
            padding: 80px 40px 60px;
            background: linear-gradient(135deg, #1a1512 0%, #2d2319 40%, #3d2d1f 70%, #1a1512 100%);
            border-radius: 24px;
            position: relative;
            overflow: hidden;
            box-shadow: 0 25px 80px rgba(0, 0, 0, 0.4);
        }
        header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(ellipse 80% 50% at 50% 0%, rgba(212, 175, 55, 0.15) 0%, transparent 50%),
                radial-gradient(ellipse 60% 40% at 20% 80%, rgba(139, 115, 85, 0.1) 0%, transparent 40%),
                radial-gradient(ellipse 60% 40% at 80% 80%, rgba(184, 134, 11, 0.1) 0%, transparent 40%);
            pointer-events: none;
        }
        header::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, transparent, #D4AF37, #F4D03F, #D4AF37, transparent);
        }
        .logo { 
            font-size: 4rem; 
            margin-bottom: 20px; 
            color: #F4D03F; 
            font-family: 'Playfair Display', serif; 
            font-weight: 700; 
            letter-spacing: 8px;
            text-shadow: 0 4px 20px rgba(244, 208, 63, 0.4), 0 0 60px rgba(212, 175, 55, 0.2);
            position: relative;
            z-index: 1;
        }
        .tagline { 
            color: #E8DCC8; 
            font-size: 1.3rem; 
            font-weight: 400; 
            letter-spacing: 3px;
            margin-bottom: 10px;
            position: relative;
            z-index: 1;
            text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
        }
        .premium-badge { 
            display: inline-flex; 
            align-items: center; 
            gap: 12px; 
            margin-top: 25px; 
            padding: 14px 32px; 
            background: linear-gradient(135deg, rgba(212, 175, 55, 0.2), rgba(184, 134, 11, 0.15)); 
            border: 1px solid rgba(244, 208, 63, 0.4); 
            border-radius: 50px; 
            font-size: 1.05rem; 
            color: #F4D03F; 
            font-weight: 500;
            position: relative;
            z-index: 1;
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }
        .card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 35px; margin-bottom: 30px; box-shadow: 0 4px 20px rgba(139, 115, 85, 0.08); }
        .card-header { display: flex; align-items: center; gap: 15px; margin-bottom: 25px; padding-bottom: 20px; border-bottom: 1px solid rgba(139, 115, 85, 0.1); }
        .card-icon { font-size: 1.5rem; color: var(--accent-gold); }
        .card-title { font-size: 1.3rem; font-weight: 600; color: var(--text-primary); font-family: 'Playfair Display', serif; }
        .upload-zone { border: 2px dashed var(--border-color); border-radius: 12px; padding: 50px; text-align: center; cursor: pointer; transition: all 0.4s; background: rgba(201, 169, 98, 0.03); }
        .upload-zone:hover, .upload-zone.dragover { border-color: var(--accent-gold); background: rgba(201, 169, 98, 0.08); }
        .upload-zone input[type="file"] { display: none; }
        .upload-icon { font-size: 3rem; margin-bottom: 20px; color: var(--accent-gold); opacity: 0.8; }
        .upload-text { color: var(--text-primary); font-size: 1.1rem; margin-bottom: 10px; }
        .upload-hint { color: var(--text-muted); font-size: 0.9rem; }
        .file-info { display: none; margin-top: 20px; padding: 18px; background: rgba(163, 184, 153, 0.15); border: 1px solid rgba(163, 184, 153, 0.4); border-radius: 8px; }
        .file-info.show { display: flex; align-items: center; gap: 12px; }
        .context-textarea { width: 100%; padding: 18px; min-height: 100px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-primary); font-size: 1rem; resize: vertical; }
        .context-textarea:focus { outline: none; border-color: var(--accent-gold); }
        .context-textarea::placeholder { color: var(--text-muted); }
        
        .advanced-toggle { display: flex; align-items: center; gap: 10px; padding: 12px 0; cursor: pointer; color: var(--text-muted); font-size: 0.85rem; user-select: none; }
        .advanced-toggle:hover { color: var(--text-secondary); }
        .advanced-toggle .arrow { transition: transform 0.3s; }
        .advanced-toggle.open .arrow { transform: rotate(90deg); }
        .advanced-content { display: none; margin-top: 15px; }
        .advanced-content.show { display: block; }
        .prompt-section { margin-bottom: 20px; padding: 20px; background: rgba(139, 115, 85, 0.05); border-radius: 8px; }
        .prompt-label { color: var(--text-muted); font-size: 0.85rem; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }
        .stage-badge-1 { background: var(--accent-stage1); color: #3D3428; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
        .stage-badge-2 { background: var(--accent-stage2); color: #FDF8F3; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
        .stage-badge-3 { background: var(--accent-stage3); color: #2D3A28; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
        .stage-badge-4 { background: var(--accent-stage4); color: #4A3535; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
        
        /* 底部固定療育音頻播放器 - 黑金奢華配色 */
        .healing-player {
            position: fixed !important;
            bottom: -150px;
            left: 0 !important;
            right: 0 !important;
            background: linear-gradient(180deg, #1A1A1A, #0D0D0D);
            backdrop-filter: blur(20px);
            border-top: 1px solid rgba(201, 169, 98, 0.4);
            padding: 20px 30px;
            z-index: 9999 !important;
            transition: bottom 0.5s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 -4px 30px rgba(0, 0, 0, 0.5);
        }
        .healing-player.show { bottom: 0 !important; }
        .healing-player-content {
            max-width: 900px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            gap: 25px;
        }
        .healing-player-icon {
            width: 50px;
            height: 50px;
            background: radial-gradient(circle at 30% 30%, #D4AF37, #8B7355);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 20px rgba(201, 169, 98, 0.3);
        }
        .healing-player-icon::before {
            content: '🎵';
            font-size: 1.5rem;
        }
        .healing-player-info { flex: 1; }
        .healing-player-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #F5F2ED;
            margin-bottom: 5px;
            font-family: 'Playfair Display', serif;
        }
        .healing-player-subtitle {
            font-size: 0.85rem;
            color: rgba(255, 255, 255, 0.6);
        }
        /* 播放按鈕 - 黑金奢華設計 */
        .healing-play-btn {
            width: 64px;
            height: 64px;
            border-radius: 50%;
            border: 2px solid #D4AF37;
            background: linear-gradient(145deg, #1A1A1A, #0D0D0D);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
            box-shadow: 
                0 0 20px rgba(201, 169, 98, 0.2),
                inset 0 0 10px rgba(201, 169, 98, 0.1);
            position: relative;
            overflow: hidden;
        }
        .healing-play-btn::before {
            content: '';
            position: absolute;
            width: 0;
            height: 0;
            border-left: 16px solid #D4AF37;
            border-top: 10px solid transparent;
            border-bottom: 10px solid transparent;
            margin-left: 4px;
            transition: all 0.3s ease;
        }
        .healing-play-btn.playing::before {
            content: '';
            width: 20px;
            height: 20px;
            border-left: 6px solid #D4AF37;
            border-right: 6px solid #D4AF37;
            border-top: none;
            border-bottom: none;
            margin-left: 0;
        }
        .healing-play-btn:hover {
            background: linear-gradient(145deg, #D4AF37, #8B7355);
            border-color: #F4D03F;
            transform: scale(1.08);
            box-shadow: 
                0 0 30px rgba(201, 169, 98, 0.5),
                0 0 60px rgba(201, 169, 98, 0.2);
        }
        .healing-play-btn:hover::before {
            border-left-color: #0D0D0D;
        }
        .healing-play-btn.playing:hover::before {
            border-left-color: #0D0D0D;
            border-right-color: #0D0D0D;
        }
        .healing-close-btn {
            position: absolute;
            top: 10px;
            right: 15px;
            background: none;
            border: none;
            color: rgba(255, 255, 255, 0.4);
            font-size: 1.2rem;
            cursor: pointer;
            transition: color 0.3s;
        }
        .healing-close-btn::before {
            content: '✕';
        }
        .healing-close-btn:hover { color: #D4AF37; }
        /* 進度條包裝器 */
        .audio-progress-wrapper {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-top: 10px;
        }
        .audio-progress {
            flex: 1;
            height: 60px;  /* 增加高度以容納聲波可視化 */
            background: linear-gradient(180deg, rgba(13, 13, 13, 0.9), rgba(26, 26, 26, 0.8));
            border-radius: 12px;
            overflow: hidden;
            cursor: pointer;
            position: relative;
            border: 1px solid rgba(201, 169, 98, 0.2);
            box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.5);
        }
        .audio-progress-bar {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, rgba(212, 175, 55, 0.15), rgba(244, 208, 63, 0.25));
            transition: width 0.1s linear;
            border-radius: 12px;
            position: absolute;
            top: 0;
            left: 0;
        }
        /* 時間顯示 */
        .audio-time {
            font-size: 0.85rem;
            color: rgba(255, 255, 255, 0.7);
            font-family: 'SF Mono', 'Consolas', monospace;
            white-space: nowrap;
            min-width: 80px;
            text-align: right;
        }
        .audio-time span:first-child {
            color: #D4AF37;
        }
        /* 控制按鈕組 */
        .audio-controls {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .audio-ctrl-btn {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            border: 1px solid rgba(201, 169, 98, 0.4);
            background: linear-gradient(145deg, rgba(26, 26, 26, 0.9), rgba(13, 13, 13, 0.9));
            color: #D4AF37;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
        }
        .audio-ctrl-btn:hover {
            background: linear-gradient(145deg, rgba(212, 175, 55, 0.2), rgba(139, 115, 85, 0.2));
            border-color: #D4AF37;
            transform: scale(1.1);
            box-shadow: 0 0 15px rgba(201, 169, 98, 0.3);
        }
        .audio-ctrl-btn:disabled {
            opacity: 0.3;
            cursor: not-allowed;
            transform: none;
        }
        .audio-ctrl-btn svg {
            width: 18px;
            height: 18px;
        }
        .prompt-textarea { width: 100%; min-height: 200px; padding: 15px; background: #0d0d15; border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; color: var(--text-secondary); font-family: monospace; font-size: 0.8rem; resize: vertical; }
        .prompt-textarea:focus { outline: none; border-color: var(--accent-primary); }
        .prompt-actions { display: flex; gap: 10px; margin-top: 10px; }
        .btn-small { padding: 8px 15px; font-size: 0.8rem; border-radius: 6px; border: 1px solid var(--border-color); background: transparent; color: var(--text-muted); cursor: pointer; transition: all 0.3s; }
        .btn-small:hover { border-color: var(--accent-gold); color: var(--accent-gold); }
        
        .btn-primary { 
            width: 100%; 
            padding: 20px 35px; 
            font-size: 1.2rem; 
            font-weight: 700; 
            border: none; 
            border-radius: 16px; 
            cursor: pointer; 
            transition: all 0.3s ease; 
            background: linear-gradient(135deg, #D4AF37 0%, #B8860B 50%, #8B6914 100%); 
            color: #1a1a1a; 
            letter-spacing: 2px; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            gap: 15px;
            position: relative;
            overflow: hidden;
            margin-bottom: 20px;
        }
        .btn-primary:not(:disabled) {
            animation: btn-glow 2s ease-in-out infinite;
        }
        @keyframes btn-glow {
            0%, 100% { box-shadow: 0 5px 30px rgba(212, 175, 55, 0.4); }
            50% { box-shadow: 0 8px 50px rgba(212, 175, 55, 0.7), 0 0 20px rgba(244, 208, 63, 0.3); }
        }
        .btn-primary::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            transition: left 0.5s ease;
        }
        .btn-primary:hover:not(:disabled)::before {
            left: 100%;
        }
        .btn-primary:hover:not(:disabled) { 
            transform: translateY(-4px) scale(1.02); 
            box-shadow: 0 20px 60px rgba(212, 175, 55, 0.5); 
        }
        .btn-primary:disabled { 
            opacity: 0.4; 
            cursor: not-allowed; 
            animation: none;
        }
        .btn-primary .btn-arrow {
            font-size: 1.4rem;
            transition: transform 0.3s ease;
        }
        .btn-primary:hover:not(:disabled) .btn-arrow {
            transform: translateX(8px);
        }
        .btn-primary .btn-icon {
            font-size: 1.3rem;
        }
        .btn-download { padding: 12px 25px; font-size: 0.95rem; font-weight: 500; border: 1px solid var(--accent-gold); border-radius: 8px; background: transparent; color: var(--accent-gold); cursor: pointer; transition: all 0.3s; display: inline-flex; align-items: center; gap: 8px; }
        .btn-download:hover { background: var(--accent-gold); color: #000; }
        
        .loading-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 1000; background: rgba(10, 10, 18, 0.95); backdrop-filter: blur(10px); overflow: hidden; }
        .loading-overlay.show { display: flex; align-items: center; justify-content: center; }
        .loading-container { text-align: center; max-width: 500px; padding: 40px; position: relative; z-index: 10; }
        /* 多層次粒子系統 */
        .particles { position: absolute; width: 100%; height: 100%; overflow: hidden; pointer-events: none; }
        .particle { position: absolute; width: 4px; height: 4px; background: var(--accent-gold); border-radius: 50%; animation: float 8s infinite ease-in-out; opacity: 0.6; box-shadow: 0 0 6px rgba(212, 175, 55, 0.8); }
        .particle.large { width: 8px; height: 8px; opacity: 0.3; animation-duration: 12s; box-shadow: 0 0 15px rgba(212, 175, 55, 0.6), 0 0 30px rgba(212, 175, 55, 0.3); }
        .particle.glow { width: 3px; height: 3px; background: #fff; opacity: 0.9; animation-duration: 6s; box-shadow: 0 0 8px #fff, 0 0 12px var(--accent-gold); }
        @keyframes float { 0%, 100% { transform: translateY(100vh) scale(0); opacity: 0; } 10% { opacity: 0.8; transform: translateY(80vh) scale(1); } 90% { opacity: 0.8; transform: translateY(-80vh) scale(1); } 100% { transform: translateY(-100vh) scale(0); opacity: 0; } }
        /* 脈動光暈效果 */
        .loading-glow { position: absolute; width: 400px; height: 400px; top: 50%; left: 50%; transform: translate(-50%, -50%); background: radial-gradient(circle, rgba(212, 175, 55, 0.15) 0%, transparent 70%); animation: pulse-glow-loading 3s ease-in-out infinite; pointer-events: none; z-index: 1; }
        @keyframes pulse-glow-loading { 0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.5; } 50% { transform: translate(-50%, -50%) scale(1.3); opacity: 0.8; } }

        .progress-ring-container { position: relative; width: 180px; height: 180px; margin: 0 auto 30px; }
        /* 水波上升動畫 - 高對比青藍色 */
        .water-fill-container {
            position: absolute;
            width: 160px;
            height: 160px;
            top: 10px;
            left: 10px;
            border-radius: 50%;
            overflow: hidden;
            opacity: 0;
            transition: opacity 0.5s ease;
            z-index: 1;
        }
        .water-fill-container.active {
            opacity: 1;
        }
        .water-fill {
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 0%;
            background: linear-gradient(180deg, 
                rgba(0, 212, 255, 0.4) 0%, 
                rgba(0, 150, 255, 0.6) 50%, 
                rgba(100, 200, 255, 0.8) 100%);
            transition: height 0.3s ease;
            box-shadow: 0 0 20px rgba(0, 200, 255, 0.5);
        }
        .water-wave {
            position: absolute;
            bottom: 0;
            left: -50%;
            width: 200%;
            height: 100%;
            background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1440 320'%3E%3Cpath fill='rgba(100,220,255,0.7)' d='M0,96L48,112C96,128,192,160,288,176C384,192,480,192,576,181.3C672,171,768,149,864,149.3C960,149,1056,171,1152,181.3C1248,192,1344,192,1392,192L1440,192L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z'%3E%3C/path%3E%3C/svg%3E") repeat-x;
            background-size: 50% 30px;
            background-position: 0 bottom;
            animation: wave 2s linear infinite;
            pointer-events: none;
        }
        @keyframes wave {
            0% { transform: translateX(0); }
            100% { transform: translateX(50%); }
        }
        .water-fill-container.active .water-wave {
            animation: wave 2s linear infinite, water-shimmer 3s ease-in-out infinite;
        }
        @keyframes water-shimmer {
            0%, 100% { opacity: 0.8; }
            50% { opacity: 1; }
        }
        
        /* ===== 火焰加熱動畫 ===== */
        .fire-container {
            position: absolute;
            bottom: -30px;
            left: 50%;
            transform: translateX(-50%);
            width: 180px;
            height: 60px;
            display: flex;
            justify-content: center;
            gap: 4px;
            opacity: 0;
            transition: opacity 0.5s ease;
            z-index: 10;
        }
        .fire-container.active {
            opacity: 1;
        }
        .flame {
            width: 15px;
            height: 45px;
            background: linear-gradient(0deg, 
                #ff4500 0%, 
                #ff6b35 30%, 
                #ffa500 60%, 
                #ffd700 80%, 
                rgba(255, 255, 0, 0.3) 100%);
            border-radius: 50% 50% 30% 30%;
            animation: flicker 0.3s ease-in-out infinite alternate;
            filter: blur(1px);
            box-shadow: 0 0 10px #ff6b35, 0 0 20px #ff4500, 0 0 30px rgba(255, 69, 0, 0.5);
        }
        .flame:nth-child(1) { animation-delay: 0s; height: 35px; }
        .flame:nth-child(2) { animation-delay: 0.1s; height: 50px; }
        .flame:nth-child(3) { animation-delay: 0.15s; height: 45px; }
        .flame:nth-child(4) { animation-delay: 0.05s; height: 55px; }
        .flame:nth-child(5) { animation-delay: 0.2s; height: 40px; }
        .flame:nth-child(6) { animation-delay: 0.08s; height: 48px; }
        .flame:nth-child(7) { animation-delay: 0.12s; height: 38px; }
        
        @keyframes flicker {
            0% { 
                transform: scaleY(1) scaleX(1) translateY(0);
                opacity: 0.9;
            }
            100% { 
                transform: scaleY(1.2) scaleX(0.9) translateY(-5px);
                opacity: 1;
            }
        }
        
        /* 水缸加熱變色 - 從藍到紅的漸變 */
        .water-fill.heating {
            animation: heat-water 15s ease-in-out forwards;
        }
        @keyframes heat-water {
            0% {
                background: linear-gradient(180deg, 
                    rgba(0, 212, 255, 0.4) 0%, 
                    rgba(0, 150, 255, 0.6) 50%, 
                    rgba(100, 200, 255, 0.8) 100%);
                box-shadow: 0 0 20px rgba(0, 200, 255, 0.5);
            }
            25% {
                background: linear-gradient(180deg, 
                    rgba(100, 200, 255, 0.4) 0%, 
                    rgba(150, 100, 200, 0.5) 50%, 
                    rgba(200, 100, 150, 0.7) 100%);
                box-shadow: 0 0 20px rgba(150, 100, 200, 0.5);
            }
            50% {
                background: linear-gradient(180deg, 
                    rgba(200, 100, 150, 0.4) 0%, 
                    rgba(255, 100, 100, 0.6) 50%, 
                    rgba(255, 150, 100, 0.8) 100%);
                box-shadow: 0 0 20px rgba(255, 100, 100, 0.5);
            }
            75% {
                background: linear-gradient(180deg, 
                    rgba(255, 80, 80, 0.5) 0%, 
                    rgba(255, 120, 80, 0.7) 50%, 
                    rgba(255, 180, 100, 0.9) 100%);
                box-shadow: 0 0 25px rgba(255, 100, 50, 0.6);
            }
            100% {
                background: linear-gradient(180deg, 
                    rgba(255, 50, 50, 0.5) 0%, 
                    rgba(255, 100, 50, 0.7) 50%, 
                    rgba(255, 200, 100, 0.9) 100%);
                box-shadow: 0 0 30px rgba(255, 80, 0, 0.7), 0 0 50px rgba(255, 150, 0, 0.4);
            }
        }
        
        /* 沸腾氣泡效果 */
        .water-wave.boiling {
            animation: wave 1s linear infinite, bubble-rise 0.5s ease-in-out infinite;
        }
        @keyframes bubble-rise {
            0%, 100% { transform: translateX(0) translateY(0); }
            50% { transform: translateX(2px) translateY(-3px); }
        }
        
        /* ===== 冷卻動畫 - 紅色從上往下逐漸變回藍色 ===== */
        .water-fill.cooling {
            animation: cool-water 12s ease-in-out forwards;
        }
        @keyframes cool-water {
            0% {
                background: linear-gradient(180deg, 
                    rgba(255, 50, 50, 0.5) 0%, 
                    rgba(255, 100, 50, 0.7) 50%, 
                    rgba(255, 200, 100, 0.9) 100%);
                box-shadow: 0 0 30px rgba(255, 80, 0, 0.7);
            }
            25% {
                background: linear-gradient(180deg, 
                    rgba(100, 150, 200, 0.4) 0%, 
                    rgba(255, 100, 100, 0.6) 35%, 
                    rgba(255, 150, 80, 0.8) 100%);
                box-shadow: 0 0 25px rgba(150, 100, 150, 0.5);
            }
            50% {
                background: linear-gradient(180deg, 
                    rgba(80, 180, 220, 0.4) 0%, 
                    rgba(120, 160, 200, 0.5) 50%, 
                    rgba(200, 100, 100, 0.7) 100%);
                box-shadow: 0 0 20px rgba(100, 150, 200, 0.5);
            }
            75% {
                background: linear-gradient(180deg, 
                    rgba(50, 200, 255, 0.4) 0%, 
                    rgba(80, 180, 230, 0.5) 60%, 
                    rgba(150, 150, 180, 0.7) 100%);
                box-shadow: 0 0 20px rgba(50, 180, 255, 0.5);
            }
            100% {
                background: linear-gradient(180deg, 
                    rgba(0, 212, 255, 0.4) 0%, 
                    rgba(0, 180, 255, 0.5) 50%, 
                    rgba(100, 200, 255, 0.8) 100%);
                box-shadow: 0 0 20px rgba(0, 200, 255, 0.6);
            }
        }
        
        /* 冷卻時波浪變平靜 */
        .water-wave.cooling {
            animation: wave 3s linear infinite, gentle-shimmer 2s ease-in-out infinite;
        }
        @keyframes gentle-shimmer {
            0%, 100% { opacity: 0.7; }
            50% { opacity: 0.9; }
        }
        
        .progress-ring { transform: rotate(-90deg); position: relative; z-index: 2; }
        .progress-ring-bg { fill: none; stroke: rgba(255,255,255,0.1); stroke-width: 8; }
        .progress-ring-fill { fill: none; stroke: url(#goldGradient); stroke-width: 8; stroke-linecap: round; stroke-dasharray: 502; stroke-dashoffset: 502; transition: stroke-dashoffset 0.5s ease; }
        .progress-percent { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 2.5rem; font-weight: 700; background: linear-gradient(135deg, var(--accent-gold), var(--accent-gold-light)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .loading-title { font-size: 1.5rem; font-weight: 600; margin-bottom: 15px; color: #F5F2ED; }
        .loading-stage { font-size: 1rem; color: var(--accent-gold); margin-bottom: 25px; min-height: 25px; }
        .stage-list { text-align: left; padding: 20px; background: rgba(255,255,255,0.03); border-radius: 12px; }
        .stage-item { display: flex; align-items: center; gap: 12px; padding: 12px 0; color: rgba(255,255,255,0.6); border-bottom: 1px solid rgba(255,255,255,0.05); transition: color 0.3s; }
        .stage-item:last-child { border-bottom: none; }
        .stage-item.active { color: var(--accent-gold); }
        .stage-item.done { color: var(--accent-success); }
        .stage-icon { width: 24px; text-align: center; }
        
        .result-container { display: none; position: relative; overflow: hidden; margin-top: 40px; }
        .result-container.show { display: block; }
        /* 結果區域金色極光背景 */
        .result-container::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            right: -50%;
            bottom: -50%;
            background: radial-gradient(circle at 30% 20%, rgba(212, 175, 55, 0.08) 0%, transparent 40%),
                        radial-gradient(circle at 70% 80%, rgba(201, 169, 98, 0.06) 0%, transparent 40%);
            animation: aurora-flow 15s ease-in-out infinite;
            pointer-events: none;
            z-index: 0;
        }
        @keyframes aurora-flow {
            0%, 100% { transform: translate(0, 0) rotate(0deg) scale(1); }
            25% { transform: translate(5%, 5%) rotate(2deg) scale(1.05); }
            50% { transform: translate(-3%, 10%) rotate(-1deg) scale(1.02); }
            75% { transform: translate(-5%, -3%) rotate(1deg) scale(1.08); }
        }
        .result-container > * { position: relative; z-index: 1; }
        
        .stage-tabs { display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }
        .stage-tab { 
            flex: 1; 
            min-width: 150px;
            padding: 16px 20px; 
            border: none; 
            border-radius: 14px; 
            background: rgba(50, 50, 50, 0.8); 
            color: #ffffff; 
            cursor: pointer; 
            transition: all 0.3s ease; 
            font-size: 1rem; 
            font-weight: 600;
            text-shadow: 0 1px 2px rgba(0,0,0,0.3);
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        /* 一階：金色琥珀 */
        .stage-tab:nth-child(1) { 
            background: linear-gradient(135deg, #D4AF37 0%, #B8860B 100%); 
            color: #1a1a1a;
            text-shadow: none;
        }
        .stage-tab:nth-child(1):hover { box-shadow: 0 6px 25px rgba(212, 175, 55, 0.5); transform: translateY(-2px); }
        /* 二階：赤陶暖橙 */
        .stage-tab:nth-child(2) { 
            background: linear-gradient(135deg, #E07B4F 0%, #B85A3C 100%); 
            color: #ffffff;
        }
        .stage-tab:nth-child(2):hover { box-shadow: 0 6px 25px rgba(224, 123, 79, 0.5); transform: translateY(-2px); }
        /* 三階：森林療癒綠 */
        .stage-tab:nth-child(3) { 
            background: linear-gradient(135deg, #5B8C5A 0%, #3D5A35 100%); 
            color: #ffffff;
        }
        .stage-tab:nth-child(3):hover { box-shadow: 0 6px 25px rgba(91, 140, 90, 0.5); transform: translateY(-2px); }
        /* 四階：靈性紫羅蘭 */
        .stage-tab:nth-child(4) { 
            background: linear-gradient(135deg, #9B7EDE 0%, #7B5FC7 100%); 
            color: #ffffff;
        }
        .stage-tab:nth-child(4):hover { box-shadow: 0 6px 25px rgba(155, 126, 222, 0.5); transform: translateY(-2px); }
        
        .stage-tab.active { 
            transform: translateY(-3px) scale(1.02); 
            box-shadow: 0 8px 30px rgba(0,0,0,0.3);
        }
        .stage-tab.active::after {
            content: '';
            position: absolute;
            bottom: -8px;
            left: 50%;
            transform: translateX(-50%);
            width: 0; 
            height: 0;
            border-left: 8px solid transparent;
            border-right: 8px solid transparent;
        }
        .stage-content { display: none; }
        .stage-content.active { display: block; }
        
        /* 階段導航按鈕 */
        .stage-nav {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 40px;
            padding: 25px 0;
            border-top: 1px solid rgba(139, 115, 85, 0.2);
        }
        .stage-nav-btn {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 14px 28px;
            border: 2px solid;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            background: transparent;
        }
        .stage-nav-btn.prev {
            border-color: #8B4513;
            color: #5D2E0C;
            background: rgba(139, 69, 19, 0.1);
        }
        .stage-nav-btn.prev:hover {
            background: linear-gradient(135deg, #8B4513, #A0522D);
            color: #fff;
            transform: translateX(-5px);
            box-shadow: 0 6px 20px rgba(139, 69, 19, 0.35);
        }
        .stage-nav-btn.next {
            border-color: #8B6914;
            color: #5D4507;
            background: rgba(139, 105, 20, 0.1);
        }
        .stage-nav-btn.next:hover {
            background: linear-gradient(135deg, #B8860B, #D4AF37);
            color: #fff;
            transform: translateX(5px);
            box-shadow: 0 6px 25px rgba(184, 134, 11, 0.4);
        }
        .stage-nav-btn:disabled {
            opacity: 0.3;
            cursor: not-allowed;
        }
        .stage-nav-placeholder {
            width: 180px;
        }
        /* 頂部導航樣式 */
        .stage-nav.stage-nav-top {
            margin-top: 0;
            margin-bottom: 30px;
            border-top: none;
            border-bottom: 1px solid rgba(139, 115, 85, 0.2);
            padding-top: 0;
            padding-bottom: 25px;
        }
        
        /* Stage 1 Header - 金色琥珀系 */
        .report-header { 
            text-align: center; 
            padding: 50px 40px; 
            background: linear-gradient(165deg, rgba(212, 175, 55, 0.12) 0%, rgba(139, 115, 85, 0.08) 50%, rgba(201, 169, 98, 0.05) 100%); 
            border: 1px solid rgba(212, 175, 55, 0.25); 
            border-radius: 24px; 
            margin-bottom: 30px;
            position: relative;
            overflow: hidden;
        }
        .report-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, transparent, #D4AF37, #F4D03F, #D4AF37, transparent);
        }
        .report-header::after {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(ellipse at center, rgba(212, 175, 55, 0.08) 0%, transparent 50%);
            animation: header-glow 8s ease-in-out infinite;
            pointer-events: none;
        }
        @keyframes header-glow {
            0%, 100% { opacity: 0.5; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.1); }
        }
        .report-title { 
            font-size: 2.2rem; 
            font-weight: 700; 
            margin-bottom: 12px; 
            color: #8B6914;
            text-shadow: 0 2px 4px rgba(139, 105, 20, 0.15);
            position: relative;
            z-index: 1;
            font-family: 'Playfair Display', Georgia, serif;
            letter-spacing: 2px;
        }
        .report-meta { 
            color: #5D4A37; 
            font-size: 0.95rem; 
            margin-bottom: 20px; 
            position: relative; 
            z-index: 1; 
            font-weight: 500;
        }
        .report-summary { 
            font-size: 1.15rem; 
            font-style: normal; 
            color: #2A2218; 
            padding: 25px 30px; 
            background: linear-gradient(135deg, rgba(139, 105, 20, 0.08), rgba(201, 169, 98, 0.05)); 
            border-radius: 16px; 
            border-left: 5px solid #B8860B; 
            border: 1px solid rgba(139, 105, 20, 0.2);
            border-left: 5px solid #B8860B;
            text-align: left; 
            line-height: 1.9; 
            position: relative; 
            z-index: 1;
            box-shadow: 0 4px 15px rgba(139, 105, 20, 0.08);
        }
        
        .metrics-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
        .metrics-grid .metric-card:first-child { grid-column: span 2; }
        @media (max-width: 768px) { .metrics-grid { grid-template-columns: 1fr; } .metrics-grid .metric-card:first-child { grid-column: span 1; } }
        .metric-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; padding: 25px; text-align: center; transition: all 0.3s; }
        .metric-card:hover { transform: translateY(-5px); border-color: var(--accent-gold); }
        .metric-card:first-child .metric-value { font-size: 1.1rem; line-height: 1.8; font-weight: 500; }
        .metric-value { font-size: 2.5rem; font-weight: 700; background: linear-gradient(135deg, var(--accent-gold), var(--accent-gold-light)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 8px; }
        .metric-label { color: var(--text-secondary); font-size: 0.9rem; }
        
        .phase-card { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 16px; padding: 25px; margin-bottom: 20px; }
        .phase-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .phase-name { font-size: 1.2rem; font-weight: 600; color: var(--accent-gold); }
        .phase-desc { margin-bottom: 20px; line-height: 1.7; color: var(--text-secondary); }
        .contribution-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        @media (max-width: 700px) { .contribution-grid { grid-template-columns: 1fr; } }
        .contribution-box { padding: 15px; background: rgba(255,255,255,0.03); border-radius: 10px; }
        .contribution-label { font-size: 0.8rem; color: var(--text-muted); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }
        
        .turning-point { background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(245, 158, 11, 0.02)); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 16px; padding: 25px; margin-bottom: 20px; }
        .turning-moment { font-size: 1.1rem; font-weight: 600; color: var(--accent-warning); margin-bottom: 15px; }
        .turning-why { margin-bottom: 15px; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 10px; }
        .turning-alt { color: var(--accent-success); padding: 15px; background: rgba(34, 197, 94, 0.1); border-radius: 10px; border-left: 3px solid var(--accent-success); }
        
        .perspective-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 25px; }
        @media (max-width: 768px) { .perspective-grid { grid-template-columns: 1fr; } }
        .perspective-box { background: var(--bg-secondary); border-radius: 16px; padding: 25px; border: 1px solid var(--border-color); }
        .perspective-header { display: flex; align-items: center; gap: 12px; margin-bottom: 15px; }
        .speaker-avatar { width: 45px; height: 45px; background: linear-gradient(135deg, var(--accent-gold), var(--accent-primary)); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; font-weight: 700; }
        
        .mismatch-box { margin-top: 20px; padding: 20px; background: rgba(139, 92, 246, 0.1); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 12px; }
        .mismatch-title { color: var(--accent-secondary); font-weight: 600; margin-bottom: 10px; }
        
        .repair-section { padding: 25px; background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(34, 197, 94, 0.02)); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 16px; }
        .repair-title { color: var(--accent-success); font-weight: 600; margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }
        .repair-item { margin-bottom: 15px; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 10px; }
        .repair-label { font-size: 0.8rem; color: var(--text-muted); margin-bottom: 8px; }
        /* Stage 2 Styles - 赤陶暖褐系 */
        .stage2-header { 
            text-align: center; 
            padding: 50px 40px; 
            background: linear-gradient(165deg, rgba(184, 115, 81, 0.15) 0%, rgba(139, 92, 66, 0.10) 50%, rgba(107, 74, 53, 0.05) 100%); 
            border: 1px solid rgba(184, 115, 81, 0.3); 
            border-radius: 24px; 
            margin-bottom: 30px;
            position: relative;
            overflow: hidden;
        }
        .stage2-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, transparent, #B87351, #D49A6A, #B87351, transparent);
        }
        .stage2-header::after {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(ellipse at center, rgba(184, 115, 81, 0.1) 0%, transparent 50%);
            animation: header-glow 8s ease-in-out infinite;
            pointer-events: none;
        }
        .stage2-title { 
            font-size: 2.2rem; 
            font-weight: 700; 
            margin-bottom: 12px; 
            color: #5C2D0E;
            text-shadow: 0 2px 4px rgba(139, 69, 19, 0.12);
            position: relative;
            z-index: 1;
            font-family: 'Playfair Display', Georgia, serif;
            letter-spacing: 2px;
        }
        .stage2-subtitle {
            font-size: 1rem;
            color: #4A2E15;
            font-style: italic;
            font-weight: 500;
            position: relative;
            z-index: 1;
        }
        /* Stage 2 專屬報告摘要 */
        .stage2-header .report-summary {
            background: linear-gradient(135deg, rgba(139, 69, 19, 0.08), rgba(184, 115, 81, 0.05));
            border: 1px solid rgba(139, 69, 19, 0.2);
            border-left: 5px solid #8B4513;
            color: #3A2518;
            box-shadow: 0 4px 15px rgba(139, 69, 19, 0.08);
        }
        /* Stage 3 專屬報告摘要 */
        .stage3-header .report-summary {
            background: linear-gradient(135deg, rgba(45, 80, 22, 0.08), rgba(107, 143, 98, 0.05));
            border: 1px solid rgba(45, 80, 22, 0.2);
            border-left: 5px solid #2D5016;
            color: #1E2D16;
            box-shadow: 0 4px 15px rgba(45, 80, 22, 0.08);
        }
        /* Stage 2 專屬 meta */
        .stage2-header .report-meta {
            color: #4A2E15;
        }
        /* Stage 3 專屬 meta */
        .stage3-header .report-meta {
            color: #2A3D1A;
        }
        
        .iceberg-card { background: rgba(255, 253, 250, 0.95); border: 1px solid rgba(139, 115, 85, 0.3); border-radius: 16px; padding: 25px; margin-bottom: 20px; }
        .iceberg-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; flex-wrap: nowrap; }
        .iceberg-header .speaker-avatar { flex-shrink: 0; }
        .iceberg-header > div:last-child { white-space: nowrap; }
        .iceberg-section { margin-bottom: 15px; padding: 15px; background: rgba(139, 115, 85, 0.08); border-radius: 10px; border-left: 3px solid var(--accent-primary); }
        .iceberg-label { font-size: 0.85rem; color: #3A2E22; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        
        .healing-card { background: rgba(255, 253, 250, 0.95); border: 1px solid rgba(212, 165, 165, 0.4); border-radius: 16px; padding: 25px; margin-bottom: 20px; }
        .healing-original { padding: 15px; background: rgba(193, 122, 110, 0.1); border-radius: 10px; margin-bottom: 15px; color: #6B3530; border-left: 3px solid var(--accent-danger); }
        .healing-arrow { text-align: center; font-size: 1.5rem; margin: 10px 0; color: #4A3530; }
        .healing-translation { padding: 15px; background: rgba(212, 165, 165, 0.15); border-radius: 10px; margin-bottom: 15px; color: #4A3030; border-left: 3px solid var(--accent-healing); }
        .healing-response { padding: 15px; background: rgba(163, 184, 153, 0.15); border-radius: 10px; color: #2A4025; border-left: 3px solid var(--accent-success); }
        
        .action-card { background: rgba(255, 253, 250, 0.95); border: 1px solid rgba(212, 165, 116, 0.4); border-radius: 16px; padding: 25px; margin-bottom: 20px; }
        .action-header { font-weight: 600; color: #4A3820; margin-bottom: 15px; }
        .action-item { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 12px; padding: 12px; background: rgba(212, 165, 116, 0.08); border-radius: 8px; }
        .action-icon { font-size: 1.2rem; }
        .action-label { font-size: 0.85rem; color: #4A3820; font-weight: 600; margin-bottom: 5px; }
        
        .healing-message { text-align: center; padding: 30px; background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(236, 72, 153, 0.1)); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 16px; margin-top: 30px; }
        .healing-message-text { font-size: 1.2rem; font-style: italic; line-height: 1.8; color: var(--text-primary); }
        
        /* Stage 3 Styles - 森林療癒綠系 */
        .stage3-header { 
            text-align: center; 
            padding: 50px 40px; 
            background: linear-gradient(165deg, rgba(163, 184, 153, 0.18) 0%, rgba(61, 90, 53, 0.10) 50%, rgba(34, 197, 94, 0.05) 100%); 
            border: 1px solid rgba(163, 184, 153, 0.4); 
            border-radius: 24px; 
            margin-bottom: 30px;
            position: relative;
            overflow: hidden;
        }
        .stage3-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, transparent, #3D5A35, #6B8F62, #3D5A35, transparent);
        }
        .stage3-header::after {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(ellipse at center, rgba(163, 184, 153, 0.12) 0%, transparent 50%);
            animation: header-glow 8s ease-in-out infinite;
            pointer-events: none;
        }
        .stage3-title { 
            font-size: 2.2rem; 
            font-weight: 700; 
            margin-bottom: 12px; 
            color: #1E3A10;
            text-shadow: 0 2px 4px rgba(45, 80, 22, 0.12);
            position: relative;
            z-index: 1;
            font-family: 'Playfair Display', Georgia, serif;
            letter-spacing: 2px;
        }
        .stage3-subtitle {
            font-size: 1rem;
            color: #2A3D1A;
            font-style: italic;
            font-weight: 500;
            position: relative;
            z-index: 1;
        }
        .growth-section { padding: 25px; background: rgba(255, 253, 250, 0.95); border: 1px solid rgba(139, 115, 85, 0.2); border-radius: 16px; margin-bottom: 20px; }
        .growth-title { font-size: 1.3rem; font-weight: 600; color: #2A4025; margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }
        .growth-item { padding: 20px; background: rgba(163, 184, 153, 0.1); border-radius: 10px; margin-bottom: 15px; border-left: 3px solid var(--accent-stage3); }
        .growth-item .text-content { font-size: 1.1rem; line-height: 1.9; color: var(--text-primary); }
        .growth-label { font-size: 0.9rem; color: #2A4025; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
        .prompt-list { list-style: none; padding: 0; }
        .prompt-list li { padding: 18px 20px; margin-bottom: 12px; background: rgba(34, 197, 94, 0.1); border-left: 4px solid var(--accent-success); border-radius: 0 12px 12px 0; font-size: 1.1rem; line-height: 1.7; }
        .closing-box { text-align: center; padding: 40px; background: linear-gradient(135deg, rgba(34, 197, 94, 0.15), rgba(99, 102, 241, 0.1)); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 16px; margin-top: 30px; }
        .closing-text { font-size: 1.3rem; font-style: italic; line-height: 1.9; color: var(--text-primary); }
        
        /* 音頻就緒播放按鈕 */
        .audio-ready-play-btn {
            display: inline-flex;
            flex-direction: column;
            align-items: center;
            gap: 15px;
            padding: 25px 50px;
            background: linear-gradient(135deg, #9B7EDE 0%, #7B5FC7 50%, #5B3FA7 100%);
            border: none;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 8px 30px rgba(155, 126, 222, 0.4);
        }
        .audio-ready-play-btn:hover {
            transform: translateY(-5px) scale(1.02);
            box-shadow: 0 15px 50px rgba(155, 126, 222, 0.6);
        }
        .play-btn-circle {
            width: 70px;
            height: 70px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 3px solid rgba(255, 255, 255, 0.5);
            animation: pulse-play 2s ease-in-out infinite;
        }
        @keyframes pulse-play {
            0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.4); }
            50% { transform: scale(1.05); box-shadow: 0 0 20px 10px rgba(255, 255, 255, 0.2); }
        }
        .play-btn-icon {
            font-size: 2rem;
            color: #ffffff;
            margin-left: 5px;
        }
        .play-btn-text {
            font-size: 1.2rem;
            font-weight: 600;
            color: #ffffff;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        /* 浮動短語雲 */
        .floating-phrases-container {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            pointer-events: none;
            overflow: hidden;
        }
        .floating-phrase {
            position: absolute;
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(4px);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9rem;
            color: #3D5A35;
            box-shadow: 0 4px 15px rgba(163, 184, 153, 0.3);
            white-space: nowrap;
            animation: phrase-float 12s ease-in-out forwards;
            opacity: 0;
        }
        @keyframes phrase-float {
            0% {
                opacity: 0;
                transform: translateY(20px) scale(0.9);
            }
            10% {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
            70% {
                opacity: 1;
                transform: translateY(-10px) scale(1);
            }
            100% {
                opacity: 0;
                transform: translateY(-30px) scale(0.95);
            }
        }
        
        .download-section { display: flex; justify-content: center; gap: 20px; padding: 30px; margin-top: 30px; background: var(--bg-card); border-radius: 16px; border: 1px solid var(--border-color); }
        .error-box { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); padding: 25px; border-radius: 16px; color: #fca5a5; }
        footer { text-align: center; padding: 40px 20px; color: var(--text-muted); font-size: 0.85rem; border-top: 1px solid rgba(255,255,255,0.05); margin-top: 50px; }
        footer a { color: var(--accent-gold); text-decoration: none; }
        .text-content { line-height: 1.8; color: var(--text-secondary); }
        
        /* 嵌入式備用播放器 */
        .embedded-player-card {
            background: linear-gradient(135deg, rgba(26, 26, 26, 0.98), rgba(40, 35, 30, 0.95));
            border: 1px solid rgba(212, 175, 55, 0.4);
            border-radius: 16px;
            padding: 20px 25px;
            margin-bottom: 25px;
            box-shadow: 0 8px 30px rgba(212, 175, 55, 0.15);
        }
        .embedded-player-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 15px;
        }
        .embedded-player-icon {
            font-size: 1.5rem;
        }
        .embedded-player-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--accent-gold);
            font-family: 'Playfair Display', serif;
        }
        .embedded-player-body {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .embedded-play-btn {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            border: 2px solid var(--accent-gold);
            background: linear-gradient(145deg, #2A2520, #1A1A1A);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s;
            flex-shrink: 0;
        }
        .embedded-play-btn .play-icon {
            width: 0;
            height: 0;
            border-left: 14px solid var(--accent-gold);
            border-top: 8px solid transparent;
            border-bottom: 8px solid transparent;
            margin-left: 4px;
        }
        .embedded-play-btn.playing .play-icon {
            border-left: 5px solid var(--accent-gold);
            border-right: 5px solid var(--accent-gold);
            border-top: none;
            border-bottom: none;
            width: 14px;
            height: 18px;
            margin-left: 0;
        }
        .embedded-play-btn:hover {
            background: linear-gradient(145deg, var(--accent-gold), #8B7355);
            transform: scale(1.05);
        }
        .embedded-play-btn:hover .play-icon {
            border-left-color: #1A1A1A;
        }
        .embedded-progress-wrapper {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .embedded-progress {
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }
        .embedded-progress-bar {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, var(--accent-gold), #F4D03F);
            transition: width 0.1s;
            border-radius: 4px;
        }
        .embedded-time {
            font-size: 0.85rem;
            color: rgba(255, 255, 255, 0.6);
            font-family: 'SF Mono', 'Consolas', monospace;
        }
        .embedded-time span:first-child {
            color: var(--accent-gold);
        }
    </style>
</head>
<body>
    <canvas id="heroCanvas"></canvas>
    <div class="bg-animation"></div>
    <div class="container">
        <header>
            <div class="logo">Lumina 心語</div>
            <p class="tagline">極致中立的衝突演化追蹤器</p>
            <div class="premium-badge">
                <span></span><span>三階段專業分析</span><span>|</span><span>演化追蹤 + 深層溯源 + 成長方案</span>
            </div>
        </header>

        <div class="card" id="uploadCard">
            <div class="card-header"><span class="card-icon">️</span><span class="card-title">上傳音訊檔案</span></div>
            <div class="upload-zone" id="uploadZone">
                <input type="file" id="audioFile" accept=".wav,.mp3,.aiff,.aac,.ogg,.flac,.m4a">
                <div class="upload-icon"></div>
                <div class="upload-text">點擊或拖放音訊檔案至此處</div>
                <div class="upload-hint">支援格式：WAV、MP3、AAC、FLAC、M4A</div>
            </div>
            <div class="file-info" id="fileInfo"><span></span><span id="fileName"></span><span id="fileSize" style="color: var(--text-muted);"></span></div>
        </div>

        <div class="card">
            <div class="card-header"><span class="card-icon"></span><span class="card-title">情境說明（選填）</span></div>
            <textarea class="context-textarea" id="contextInput" placeholder="請描述對話雙方的關係，例如：&#10;• 這是一對夫妻關於家庭財務的討論&#10;• 這是主管與員工關於專案進度的對話"></textarea>
            
            <div class="advanced-toggle" onclick="toggleAdvanced()">
                <span class="arrow"></span>
                <span>Advanced Settings (System Prompts)</span>
            </div>
            <div class="advanced-content" id="advancedContent">
                <div class="prompt-section">
                    <div class="prompt-label"><span class="stage-badge-1">STAGE 1</span> Conflict Evolution Analyzer</div>
                    <textarea class="prompt-textarea" id="stage1Prompt"></textarea>
                    <div class="prompt-actions">
                        <button class="btn-small" onclick="resetPrompt(1)">Reset</button>
                        <button class="btn-small" onclick="copyPrompt(1)">Copy</button>
                    </div>
                </div>
                <div class="prompt-section">
                    <div class="prompt-label"><span class="stage-badge-2">STAGE 2</span> Deep Root & Empathy Bridge</div>
                    <textarea class="prompt-textarea" id="stage2Prompt"></textarea>
                    <div class="prompt-actions">
                        <button class="btn-small" onclick="resetPrompt(2)">Reset</button>
                        <button class="btn-small" onclick="copyPrompt(2)">Copy</button>
                    </div>
                </div>
                <div class="prompt-section">
                    <div class="prompt-label"><span class="stage-badge-3">STAGE 3</span> Personal Growth Action Plan</div>
                    <textarea class="prompt-textarea" id="stage3Prompt"></textarea>
                    <div class="prompt-actions">
                        <button class="btn-small" onclick="resetPrompt(3)">Reset</button>
                        <button class="btn-small" onclick="copyPrompt(3)">Copy</button>
                    </div>
                </div>
                <div class="prompt-section">
                    <div class="prompt-label"><span class="stage-badge-4">STAGE 4</span> Digital Hypnotic Healing (數位催眠療癒)</div>
                    <textarea class="prompt-textarea" id="stage4Prompt"></textarea>
                    <div class="prompt-actions">
                        <button class="btn-small" onclick="resetPrompt(4)">Reset</button>
                        <button class="btn-small" onclick="copyPrompt(4)">Copy</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- 錯誤提示卡片 -->
        <div class="card" id="errorCard" style="display: none; border-color: var(--accent-danger); background: rgba(193, 122, 110, 0.1);">
            <div class="card-header"><span class="card-icon">⚠️</span><span class="card-title" style="color: var(--accent-danger);">分析失敗</span></div>
            <div id="errorMessage" style="padding: 20px; color: var(--text-secondary);"></div>
        </div>

        <button class="btn-primary analyze-btn-animated" id="analyzeBtn" disabled>
            <span class="btn-text">開始四階段專業分析</span>
            <span class="btn-arrow">→</span>
        </button>

        <div class="result-container" id="resultContainer">
            <div class="stage-tabs">
                <button class="stage-tab active" onclick="switchStage(1)"> 一階：衝突演化</button>
                <button class="stage-tab" onclick="switchStage(2)"> 二階：深層溯源</button>
                <button class="stage-tab" onclick="switchStage(3)"> 三階：成長方案</button>
                <button class="stage-tab" onclick="switchStage(4)">✨ 療癒與重點</button>
            </div>

            <!-- Stage 1 Content -->
            <div class="stage-content active" id="stage1Content">
                <!-- Stage 1 頂部四按鈕 -->
                <div class="stage-tabs in-page-tabs">
                    <button class="stage-tab active" onclick="switchStage(1)">一階：衝突演化</button>
                    <button class="stage-tab" onclick="switchStage(2)">二階：深層溯源</button>
                    <button class="stage-tab" onclick="switchStage(3)">三階：成長方案</button>
                    <button class="stage-tab" onclick="switchStage(4)">✨ 療癒與重點</button>
                </div>
                
                <div class="report-header">
                    <div class="report-title"> 衝突演化分析報告</div>
                    <div class="report-meta">分析時間：<span id="reportTime"></span> | 報告編號：<span id="reportId"></span></div>
                    <div class="report-summary" id="overallDynamic"></div>
                </div>

                <div class="metrics-grid">
                    <div class="metric-card"><div class="metric-value" id="energyPattern"></div><div class="metric-label">能量變化模式</div></div>
                    <div class="metric-card"><div class="metric-value" id="phaseCount"></div><div class="metric-label">演化階段數</div></div>
                    <div class="metric-card"><div class="metric-value" id="intensityScore"></div><div class="metric-label">衝突烈度指數</div></div>
                </div>

                <div class="card"><div class="card-header"><span class="card-icon"></span><span class="card-title">衝突演化階段</span></div><div id="evolutionMap"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon"></span><span class="card-title">關鍵轉折點</span></div><div id="turningPoints"></div></div>
                <div class="card">
                    <div class="card-header"><span class="card-icon">️</span><span class="card-title">雙方視角分析</span></div>
                    <div class="perspective-grid" id="dualPerspective"></div>
                    <div class="mismatch-box"><div class="mismatch-title"> 核心落差</div><div id="coreMismatch" class="text-content"></div></div>
                </div>
                <div class="card">
                    <div class="repair-section">
                        <div class="repair-title"><span></span><span>修復嘗試分析</span></div>
                        <div id="repairAnalysis"></div>
                    </div>
                </div>
                
                <!-- Stage 1 底部四按鈕 -->
                <div class="stage-tabs in-page-tabs" style="margin-top: 30px;">
                    <button class="stage-tab active" onclick="switchStage(1)">一階：衝突演化</button>
                    <button class="stage-tab" onclick="switchStage(2)">二階：深層溯源</button>
                    <button class="stage-tab" onclick="switchStage(3)">三階：成長方案</button>
                    <button class="stage-tab" onclick="switchStage(4)">✨ 療癒與重點</button>
                </div>
                
                <!-- Stage 1 導航 -->
                <div class="stage-nav" style="margin-top: 15px;">
                    <div class="stage-nav-placeholder"></div>
                    <button class="stage-nav-btn next" onclick="switchStage(2)">
                        二階：深層溯源 →
                    </button>
                </div>
                
                <!-- Stage 1 下載區塊 -->
                <div class="download-section in-page-download" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding: 30px; background: linear-gradient(135deg, rgba(26, 26, 26, 0.95), rgba(13, 13, 13, 0.98)); border-radius: 20px; border: 1px solid rgba(201, 169, 98, 0.3); margin-top: 20px;">
                    <button class="download-card" onclick="downloadPDF()">
                        <div class="download-icon">📄</div>
                        <div class="download-info">
                            <div class="download-title">PDF 分析報告</div>
                            <div class="download-desc">點擊下載完整分析報告</div>
                        </div>
                        <div class="download-arrow">→</div>
                    </button>
                    <button class="download-card premium" onclick="downloadFullPackage()">
                        <div class="download-badge">✨ 完整版</div>
                        <div class="download-icon">📦</div>
                        <div class="download-info">
                            <div class="download-title">PDF + 視覺化圖像</div>
                            <div class="download-desc">包含 4 張視覺化圖像</div>
                        </div>
                        <div class="download-arrow">→</div>
                    </button>
                </div>
            </div>

            <!-- Stage 2 Content -->
            <div class="stage-content" id="stage2Content">
                <!-- Stage 2 頂部四按鈕 -->
                <div class="stage-tabs in-page-tabs">
                    <button class="stage-tab" onclick="switchStage(1)">一階：衝突演化</button>
                    <button class="stage-tab active" onclick="switchStage(2)">二階：深層溯源</button>
                    <button class="stage-tab" onclick="switchStage(3)">三階：成長方案</button>
                    <button class="stage-tab" onclick="switchStage(4)">✨ 療癒與重點</button>
                </div>
                
                <div class="stage2-header">
                    <div class="stage2-title"> 深層溯源與接納橋樑</div>
                    <div class="report-meta">將行為轉化為未滿足的內心需求</div>
                    <div class="report-summary" id="deepInsight"></div>
                </div>

                <div class="card"><div class="card-header"><span class="card-icon"></span><span class="card-title">冰山下方分析</span></div><div id="icebergAnalysis"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon"></span><span class="card-title">依附動態 & 認知風格</span></div>
                    <div class="phase-card"><div class="phase-name">依附動態</div><div class="text-content" id="attachmentDynamic"></div></div>
                    <div class="phase-card"><div class="phase-name">認知風格差異</div><div class="text-content" id="cognitiveClash"></div></div>
                </div>
                <div class="card"><div class="card-header"><span class="card-icon"></span><span class="card-title">視角轉換練習</span></div><div id="perspectiveShifts"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon"></span><span class="card-title">療癒性重構</span></div><div id="healingReframes"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon">️</span><span class="card-title">可執行的微小改變</span></div><div id="actionableChanges"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon">️</span><span class="card-title">共同責任重構</span></div><div class="text-content" id="sharedResponsibility"></div></div>
                <div class="healing-message"><div class="healing-message-text" id="healingMessage"></div></div>
                
                <!-- Stage 2 底部四按鈕 -->
                <div class="stage-tabs in-page-tabs" style="margin-top: 30px;">
                    <button class="stage-tab" onclick="switchStage(1)">一階：衝突演化</button>
                    <button class="stage-tab active" onclick="switchStage(2)">二階：深層溯源</button>
                    <button class="stage-tab" onclick="switchStage(3)">三階：成長方案</button>
                    <button class="stage-tab" onclick="switchStage(4)">✨ 療癒與重點</button>
                </div>
                
                <!-- Stage 2 導航 -->
                <div class="stage-nav" style="margin-top: 15px;">
                    <button class="stage-nav-btn prev" onclick="switchStage(1)">
                        ← 一階：衝突演化
                    </button>
                    <button class="stage-nav-btn next" onclick="switchStage(3)">
                        三階：成長方案 →
                    </button>
                </div>
                
                <!-- Stage 2 下載區塊 -->
                <div class="download-section in-page-download" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding: 30px; background: linear-gradient(135deg, rgba(26, 26, 26, 0.95), rgba(13, 13, 13, 0.98)); border-radius: 20px; border: 1px solid rgba(201, 169, 98, 0.3); margin-top: 20px;">
                    <button class="download-card" onclick="downloadPDF()">
                        <div class="download-icon">📄</div>
                        <div class="download-info">
                            <div class="download-title">PDF 分析報告</div>
                            <div class="download-desc">點擊下載完整分析報告</div>
                        </div>
                        <div class="download-arrow">→</div>
                    </button>
                    <button class="download-card premium" onclick="downloadFullPackage()">
                        <div class="download-badge">✨ 完整版</div>
                        <div class="download-icon">📦</div>
                        <div class="download-info">
                            <div class="download-title">PDF + 視覺化圖像</div>
                            <div class="download-desc">包含 4 張視覺化圖像</div>
                        </div>
                        <div class="download-arrow">→</div>
                    </button>
                </div>
            </div>

            <!-- Stage 3 Content -->
            <div class="stage-content" id="stage3Content">
                <!-- Stage 3 頂部四按鈕 -->
                <div class="stage-tabs in-page-tabs">
                    <button class="stage-tab" onclick="switchStage(1)">一階：衝突演化</button>
                    <button class="stage-tab" onclick="switchStage(2)">二階：深層溯源</button>
                    <button class="stage-tab active" onclick="switchStage(3)">三階：成長方案</button>
                    <button class="stage-tab" onclick="switchStage(4)">✨ 療癒與重點</button>
                </div>
                
                <div class="stage3-header">
                    <div class="stage3-title"> 個人成長行動方案</div>
                    <div class="report-meta">專注「我能做什麼」而非「如何讓對方改變」</div>
                    <div class="report-summary" id="positioning"></div>
                </div>

                <div class="card"><div class="card-header"><span class="card-icon"></span><span class="card-title">我能做的修復</span></div><div id="repairSelfLed"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon"></span><span class="card-title">認識我的模式</span></div><div id="knowMyPatterns"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon"></span><span class="card-title">我的調節工具箱</span></div><div id="myToolkit"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon"></span><span class="card-title">替代路徑</span></div><div id="alternatives"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon">️</span><span class="card-title">我的邊界與底線</span></div><div id="myBoundaries"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon"></span><span class="card-title">意義重構</span></div><div id="meaningMaking"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon"></span><span class="card-title">反思提問</span></div><ul class="prompt-list" id="reflectionPrompts"></ul></div>
                <div class="closing-box"><div class="closing-text" id="closingMessage"></div></div>
                
                <!-- Stage 3 底部四按鈕 -->
                <div class="stage-tabs in-page-tabs" style="margin-top: 30px;">
                    <button class="stage-tab" onclick="switchStage(1)">一階：衝突演化</button>
                    <button class="stage-tab" onclick="switchStage(2)">二階：深層溯源</button>
                    <button class="stage-tab active" onclick="switchStage(3)">三階：成長方案</button>
                    <button class="stage-tab" onclick="switchStage(4)">✨ 療癒與重點</button>
                </div>
                
                <!-- Stage 3 導航 -->
                <div class="stage-nav" style="margin-top: 15px;">
                    <button class="stage-nav-btn prev" onclick="switchStage(2)">
                        ← 二階：深層溯源
                    </button>
                    <button class="stage-nav-btn next" onclick="switchStage(4)">
                        四階：療癒與重點 →
                    </button>
                </div>
                
                <!-- Stage 3 下載區塊 -->
                <div class="download-section in-page-download" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding: 30px; background: linear-gradient(135deg, rgba(26, 26, 26, 0.95), rgba(13, 13, 13, 0.98)); border-radius: 20px; border: 1px solid rgba(201, 169, 98, 0.3); margin-top: 20px;">
                    <button class="download-card" onclick="downloadPDF()">
                        <div class="download-icon">📄</div>
                        <div class="download-info">
                            <div class="download-title">PDF 分析報告</div>
                            <div class="download-desc">點擊下載完整分析報告</div>
                        </div>
                        <div class="download-arrow">→</div>
                    </button>
                    <button class="download-card premium" onclick="downloadFullPackage()">
                        <div class="download-badge">✨ 完整版</div>
                        <div class="download-icon">📦</div>
                        <div class="download-info">
                            <div class="download-title">PDF + 視覺化圖像</div>
                            <div class="download-desc">包含 4 張視覺化圖像</div>
                        </div>
                        <div class="download-arrow">→</div>
                    </button>
                </div>
            </div>

            <!-- Stage 4: Summary & Images -->
            <div class="stage-content" id="stage4Content">
                <!-- Stage 4 頂部四按鈕 -->
                <div class="stage-tabs in-page-tabs">
                    <button class="stage-tab" onclick="switchStage(1)">一階：衝突演化</button>
                    <button class="stage-tab" onclick="switchStage(2)">二階：深層溯源</button>
                    <button class="stage-tab" onclick="switchStage(3)">三階：成長方案</button>
                    <button class="stage-tab active" onclick="switchStage(4)">✨ 療癒與重點</button>
                </div>
                
                <div class="stage3-header" style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(99, 102, 241, 0.05)); border-color: rgba(139, 92, 246, 0.3);">
                    <div class="stage3-title" style="background: linear-gradient(135deg, #8b5cf6, #6366f1); -webkit-background-clip: text;"> 分析總結與視覺化</div>
                    <div class="report-meta">自動提取三階段核心洞見，生成視覺化圖像與催眠療癒音頻</div>
                </div>

                <!-- 生成進度區塊 -->
                <div class="card" id="generationProgressCard">
                    <div class="card-header"><span class="card-icon">️</span><span class="card-title">自動生成進度</span></div>
                    <div style="padding: 20px;">
                        <!-- 圖片生成進度 -->
                        <div style="margin-bottom: 25px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <span style="color: var(--accent-gold); font-weight: 600;">️ 視覺化圖像</span>
                                <span id="imageProgressText" style="color: var(--text-muted);">準備中...</span>
                            </div>
                            <div style="height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden;">
                                <div id="imageProgressBar" style="height: 100%; width: 0%; background: linear-gradient(90deg, var(--accent-gold), #f4d03f); transition: width 0.5s;"></div>
                            </div>
                        </div>
                        <!-- 音頻生成進度 -->
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <span style="color: var(--accent-secondary); font-weight: 600;"> 數位催眠療癒音頻（分段生成）</span>
                                <span id="audioProgressText" style="color: var(--text-muted);">等待圖像完成...</span>
                            </div>
                            <div style="height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden;">
                                <div id="audioGenProgressBar" style="height: 100%; width: 0%; background: linear-gradient(90deg, var(--accent-secondary), #6366f1); transition: width 0.5s;"></div>
                            </div>
                            <div id="audioPartsProgress" style="margin-top: 8px; font-size: 0.85rem; color: var(--text-muted); display: none;">
                                正在編織您的專屬療癒能量...
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 視覺化簡報卡片展示區（單列大圖） -->
                <div id="generatedImagesContainer" style="display:none;">
                    <!-- 嵌入式備用播放器 -->
                    <div class="embedded-player-card" id="embeddedPlayerCard" style="display:none;">
                        <div class="embedded-player-header">
                            <span class="embedded-player-icon">🎵</span>
                            <span class="embedded-player-title">專屬療癒音頻</span>
                        </div>
                        <div class="embedded-player-body">
                            <button class="embedded-play-btn" id="embeddedPlayBtn" onclick="toggleHealingAudio()">
                                <span class="play-icon"></span>
                            </button>
                            <div class="embedded-progress-wrapper">
                                <div class="embedded-progress" onclick="seekAudio(event)">
                                    <div class="embedded-progress-bar" id="embeddedProgressBar"></div>
                                </div>
                                <div class="embedded-time">
                                    <span id="embeddedCurrentTime">0:00</span> / <span id="embeddedTotalTime">0:00</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card" style="background: transparent; padding: 0; border: none;">
                        <div class="card-header" style="padding: 20px 0;"><span class="card-icon"></span><span class="card-title">四大分析視覺簡報</span></div>
                        
                        <!-- 單列排列 -->
                        <div style="display: flex; flex-direction: column; gap: 24px;">
                            
                            <!-- Card 1: 覺察時刻 (琥珀金) -->
                            <div class="insight-card" id="slideCard1" style="background: #FDF8F3; border: 1px solid #C9A962; border-radius: 16px; overflow: hidden; transition: transform 0.3s, box-shadow 0.3s; box-shadow: 0 4px 20px rgba(201,169,98,0.15);">
                                <div style="position: relative;">
                                    <img id="imgStage1" style="width:100%; aspect-ratio:16/9; object-fit:cover; display:block; min-height: 320px;" alt="Stage 1 - 覺察時刻">
                                    <div style="position:absolute; top:16px; left:16px; background:#C9A962; color:#3D3428; padding:6px 16px; border-radius:4px; font-size:0.75rem; font-weight:600; letter-spacing:2px; text-transform:uppercase;">Stage 1</div>
                                </div>
                                <div style="padding: 20px 24px; background: linear-gradient(180deg, #FDF8F3 0%, #FAF6F1 100%);">
                                    <h3 id="slideTitle1" style="color: #3D3428; font-size: 1.2rem; margin: 0 0 8px 0; font-weight: 600; font-family: Georgia, serif;">覺察時刻</h3>
                                    <ul id="slideBullets1" style="list-style: none; padding: 0; margin: 0;">
                                    </ul>
                                </div>
                            </div>
                            
                            <!-- Card 2: 深層對話 (赤陶褐) -->
                            <div class="insight-card" id="slideCard2" style="background: #FAF5F2; border: 1px solid #B87351; border-radius: 16px; overflow: hidden; transition: transform 0.3s, box-shadow 0.3s; box-shadow: 0 4px 20px rgba(184,115,81,0.15);">
                                <div style="position: relative;">
                                    <img id="imgStage2" style="width:100%; aspect-ratio:16/9; object-fit:cover; display:block; min-height: 320px;" alt="Stage 2 - 深層對話">
                                    <div style="position:absolute; top:16px; left:16px; background:#B87351; color:#FDF8F3; padding:6px 16px; border-radius:4px; font-size:0.75rem; font-weight:600; letter-spacing:2px; text-transform:uppercase;">Stage 2</div>
                                </div>
                                <div style="padding: 20px 24px; background: linear-gradient(180deg, #FAF5F2 0%, #F7F2EF 100%);">
                                    <h3 id="slideTitle2" style="color: #4A3C35; font-size: 1.2rem; margin: 0 0 8px 0; font-weight: 600; font-family: Georgia, serif;">深層對話</h3>
                                    <ul id="slideBullets2" style="list-style: none; padding: 0; margin: 0;">
                                    </ul>
                                </div>
                            </div>
                            
                            <!-- Card 3: 成長蛻變 (鼠尾草綠) - 帶浮動短語雲 -->
                            <div class="insight-card" id="slideCard3" style="background: #F7FAF6; border: 1px solid #A3B899; border-radius: 16px; overflow: hidden; transition: transform 0.3s, box-shadow 0.3s; box-shadow: 0 4px 20px rgba(163,184,153,0.15);">
                                <div style="position: relative;">
                                    <img id="imgStage3" style="width:100%; aspect-ratio:16/9; object-fit:cover; display:block; min-height: 320px;" alt="Stage 3 - 成長蛻變">
                                    <div style="position:absolute; top:16px; left:16px; background:#A3B899; color:#2D3A28; padding:6px 16px; border-radius:4px; font-size:0.75rem; font-weight:600; letter-spacing:2px; text-transform:uppercase;">Stage 3</div>
                                    <!-- 浮動短語雲容器 -->
                                    <div id="floatingPhrasesContainer" class="floating-phrases-container"></div>
                                </div>
                                <div style="padding: 20px 24px; background: linear-gradient(180deg, #F7FAF6 0%, #F4F7F3 100%);">
                                    <h3 id="slideTitle3" style="color: #3A4A35; font-size: 1.2rem; margin: 0 0 8px 0; font-weight: 600; font-family: Georgia, serif;">成長蛻變</h3>
                                    <ul id="slideBullets3" style="list-style: none; padding: 0; margin: 0;">
                                    </ul>
                                </div>
                            </div>
                            
                            <!-- Card 4: 和諧共處 (珊瑚玫瑰) -->
                            <div class="insight-card" id="slideCard4" style="background: #FDF8F8; border: 1px solid #D4A5A5; border-radius: 16px; overflow: hidden; transition: transform 0.3s, box-shadow 0.3s; box-shadow: 0 4px 20px rgba(212,165,165,0.15);">
                                <div style="position: relative;">
                                    <img id="imgCombined" style="width:100%; aspect-ratio:16/9; object-fit:cover; display:block; min-height: 320px;" alt="Stage 4 - 和諧共處">
                                    <div style="position:absolute; top:16px; left:16px; background:#D4A5A5; color:#4A3535; padding:6px 16px; border-radius:4px; font-size:0.75rem; font-weight:600; letter-spacing:2px; text-transform:uppercase;">Stage 4</div>
                                </div>
                                <div style="padding: 20px 24px; background: linear-gradient(180deg, #FDF8F8 0%, #FAF5F5 100%);">
                                    <h3 id="slideTitle4" style="color: #4A3535; font-size: 1.2rem; margin: 0 0 8px 0; font-weight: 600; font-family: Georgia, serif;">和諧共處</h3>
                                    <ul id="slideBullets4" style="list-style: none; padding: 0; margin: 0;">
                                    </ul>
                                </div>
                            </div>
                            
                        </div>
                </div>
                
                <!-- Stage 4 底部四按鈕 -->
                <div class="stage-tabs in-page-tabs" style="margin-top: 30px;">
                    <button class="stage-tab" onclick="switchStage(1)">一階：衝突演化</button>
                    <button class="stage-tab" onclick="switchStage(2)">二階：深層溯源</button>
                    <button class="stage-tab" onclick="switchStage(3)">三階：成長方案</button>
                    <button class="stage-tab active" onclick="switchStage(4)">✨ 療癒與重點</button>
                </div>
                
                <!-- Stage 4 導航 -->
                <div class="stage-nav" style="margin-top: 15px;">
                    <button class="stage-nav-btn prev" onclick="switchStage(3)">
                        ← 三階：成長方案
                    </button>
                    <div class="stage-nav-placeholder"></div>
                </div>
                
                <!-- Stage 4 下載區塊 -->
                <div class="download-section in-page-download" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding: 30px; background: linear-gradient(135deg, rgba(26, 26, 26, 0.95), rgba(13, 13, 13, 0.98)); border-radius: 20px; border: 1px solid rgba(201, 169, 98, 0.3); margin-top: 20px;">
                    <button id="downloadPdfBtn" class="download-card" onclick="downloadPDF()">
                        <div class="download-icon">📄</div>
                        <div class="download-info">
                            <div class="download-title">PDF 分析報告</div>
                            <div class="download-desc" id="pdfDownloadStatus">點擊下載完整分析報告</div>
                        </div>
                        <div class="download-arrow">→</div>
                    </button>
                    <button id="downloadFullBtn" class="download-card premium" onclick="downloadFullPackage()">
                        <div class="download-badge">✨ 完整版</div>
                        <div class="download-icon">📦</div>
                        <div class="download-info">
                            <div class="download-title">PDF + 視覺化圖像</div>
                            <div class="download-desc" id="fullDownloadStatus">包含 4 張視覺化圖像</div>
                        </div>
                        <div class="download-arrow">→</div>
                    </button>
                </div>
            </div>
            <!-- ↑ End of stage4Content -->
            
            
            <style>
                .download-card {
                    display: flex;
                    align-items: center;
                    gap: 15px;
                    padding: 25px 30px;
                    background: linear-gradient(145deg, rgba(40, 35, 30, 0.9), rgba(26, 26, 26, 0.95));
                    border: 2px solid rgba(201, 169, 98, 0.3);
                    border-radius: 16px;
                    cursor: pointer;
                    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                    position: relative;
                    overflow: hidden;
                }
                .download-card:disabled {
                    opacity: 0.6;
                    cursor: not-allowed;
                }
                .download-card:not(:disabled):hover {
                    border-color: #D4AF37;
                    transform: translateY(-3px);
                    box-shadow: 0 15px 40px rgba(212, 175, 55, 0.25);
                }
                .download-card:not(:disabled):hover .download-arrow {
                    transform: translateX(5px);
                    color: #D4AF37;
                }
                .download-card.premium {
                    background: linear-gradient(145deg, rgba(60, 45, 25, 0.95), rgba(40, 30, 15, 0.98));
                    border-color: rgba(212, 175, 55, 0.5);
                }
                .download-card.premium:not(:disabled):hover {
                    border-color: #F4D03F;
                    box-shadow: 0 15px 50px rgba(244, 208, 63, 0.3);
                }
                .download-badge {
                    position: absolute;
                    top: -1px;
                    right: -1px;
                    background: linear-gradient(135deg, #D4AF37, #F4D03F);
                    color: #1A1A1A;
                    font-size: 0.7rem;
                    font-weight: 700;
                    padding: 5px 12px;
                    border-radius: 0 14px 0 10px;
                }
                .download-icon {
                    font-size: 2.5rem;
                    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
                }
                .download-info {
                    flex: 1;
                    text-align: left;
                }
                .download-title {
                    font-size: 1.2rem;
                    font-weight: 600;
                    color: #F5F2ED;
                    margin-bottom: 5px;
                    font-family: 'Playfair Display', serif;
                }
                .download-desc {
                    font-size: 0.85rem;
                    color: rgba(255, 255, 255, 0.6);
                }
                .download-card:not(:disabled) .download-desc {
                    color: #D4AF37;
                }
                .download-arrow {
                    font-size: 1.5rem;
                    color: rgba(255, 255, 255, 0.3);
                    transition: all 0.3s;
                }
                @media (max-width: 768px) {
                    .download-section { grid-template-columns: 1fr !important; }
                }
            </style>

        </div>

        <div class="card" id="errorCard" style="display: none;"><div class="error-box"><strong> 分析失敗</strong><p id="errorMessage" style="margin-top: 15px;"></p></div></div>

        <footer>
            <p>Lumina 心語 ✦ 2025 | 四階段分析：演化追蹤 + 深層溯源 + 成長方案 + 數位催眠療癒</p>
            <p style="margin-top: 10px;">由智能大腦 AI 引擎驅動生成</p>
        </footer>
    </div>

    <!-- 底部固定巨型療育音頻播放器 (心跳脈動效果) -->
    <div class="healing-player" id="healingPlayer">
        <button class="healing-close-btn" onclick="closeHealingPlayer()"></button>
        <div class="healing-player-content">
            <div class="healing-player-icon" style="animation: pulse-glow 2s ease-in-out infinite;"></div>
            <div class="healing-player-info">
                <div class="healing-player-title">🎵 開始您的專屬療癒引導</div>
                <div class="healing-player-subtitle" id="playerSubtitle">閉上眼睛，讓艾瑞克森式催眠帶您進入深度放鬆</div>
                <!-- 進度條和時間 -->
                <div class="audio-progress-wrapper">
                    <div class="audio-progress" onclick="seekAudio(event)">
                        <div class="audio-progress-bar" id="audioProgressBar"></div>
                        <!-- 嵌入式波形視覺化 -->
                        <canvas id="audioVisualizer" width="300" height="60" style="display:none;"></canvas>
                    </div>
                    <div class="audio-time">
                        <span id="audioCurrentTime">0:00</span>
                        <span>/</span>
                        <span id="audioTotalTime">0:00</span>
                    </div>
                </div>
            </div>
            <!-- 控制按鈕組 -->
            <div class="audio-controls">
                <button class="audio-ctrl-btn" id="prevBtn" onclick="prevTrack()" title="上一段">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/>
                    </svg>
                </button>
                <button class="healing-play-btn" id="healingPlayBtn" onclick="toggleHealingAudio()"></button>
                <button class="audio-ctrl-btn" id="nextBtn" onclick="nextTrack()" title="下一段">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/>
                    </svg>
                </button>
            </div>
        </div>
        <audio id="healingAudio" style="display:none;"></audio>
    </div>

    <style>
        @keyframes pulse-glow {
            0%, 100% { transform: scale(1); filter: brightness(1); }
            50% { transform: scale(1.05); filter: brightness(1.1); }
        }
        /* 音頻生成中動畫 */
        @keyframes loading-pulse {
            0%, 100% { opacity: 0.5; }
            50% { opacity: 1; }
        }
        .healing-player.generating .healing-player-title::after {
            content: '生成中...';
            animation: loading-pulse 1.5s infinite;
            color: #D4AF37;
        }
        .healing-player.generating .healing-play-btn {
            opacity: 0.5;
            pointer-events: none;
        }
        /* 生成完成閃爍動畫 */
        @keyframes ready-flash {
            0%, 100% { box-shadow: 0 -4px 30px rgba(0, 0, 0, 0.5); border-color: rgba(201, 169, 98, 0.4); }
            50% { box-shadow: 0 -4px 50px rgba(212, 175, 55, 0.6), 0 0 30px rgba(212, 175, 55, 0.3); border-color: #D4AF37; }
        }
        .healing-player.ready {
            animation: ready-flash 1s ease-in-out 3;
        }
        /* 音頻波形可視化 - 嵌入進度條內部，更大更鮮豔 */
        #audioVisualizer {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border-radius: 12px;
            background: transparent;
            pointer-events: none;
            z-index: 2;
        }
        .healing-player.playing #audioVisualizer {
            display: block !important;
        }
        /* 静止狀態的裝飾波紋 */
        .audio-progress::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 5%;
            right: 5%;
            height: 2px;
            background: linear-gradient(90deg, transparent, rgba(201, 169, 98, 0.3), transparent);
            transform: translateY(-50%);
            z-index: 1;
        }
        /* 播放時隱藏裝飾線 */
        .healing-player.playing .audio-progress::before {
            display: none;
        }
    </style>

    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-glow"></div>
        <div class="particles" id="particles"></div>
        <div class="loading-container">
            <div class="progress-ring-container">
                <!-- 水波上升動畫 -->
                <div class="water-fill-container" id="waterFillContainer">
                    <div class="water-fill" id="waterFill"></div>
                    <div class="water-wave" id="waterWave"></div>
                </div>
                <svg class="progress-ring" width="180" height="180">
                    <defs><linearGradient id="goldGradient" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#d4af37"/><stop offset="100%" style="stop-color:#f4d03f"/></linearGradient></defs>
                    <circle class="progress-ring-bg" cx="90" cy="90" r="80"></circle>
                    <circle class="progress-ring-fill" id="progressRing" cx="90" cy="90" r="80"></circle>
                </svg>
                <div class="progress-percent" id="progressPercent">0%</div>
                <!-- 火焰加熱動畫 -->
                <div class="fire-container" id="fireContainer">
                    <div class="flame"></div>
                    <div class="flame"></div>
                    <div class="flame"></div>
                    <div class="flame"></div>
                    <div class="flame"></div>
                    <div class="flame"></div>
                    <div class="flame"></div>
                </div>
            </div>
            <div class="loading-title" id="loadingTitle">正在深度分析中...</div>
            <div class="loading-stage" id="loadingStage">準備分析環境</div>
            <div class="stage-list">
                <div class="stage-item" id="s1"><span class="stage-icon"></span>上傳音訊檔案</div>
                <div class="stage-item" id="s2"><span class="stage-icon"></span>一階：建立聲學基線</div>
                <div class="stage-item" id="s3"><span class="stage-icon"></span>一階：追蹤演化軌跡</div>
                <div class="stage-item" id="s4"><span class="stage-icon"></span>一階：識別轉折點</div>
                <div class="stage-item" id="s5"><span class="stage-icon"></span>二階：冰山下方溯源</div>
                <div class="stage-item" id="s6"><span class="stage-icon"></span>二階：療癒橋樑建構</div>
                <div class="stage-item" id="s7"><span class="stage-icon"></span>三階：個人成長行動方案</div>
            </div>
        </div>
    </div>

    <script>
        let fullResult = null;
        let selectedFile = null;
        const defaultPrompt1 = `''' + DEFAULT_STAGE1_PROMPT.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${') + '''`;
        const defaultPrompt2 = `''' + DEFAULT_STAGE2_PROMPT.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${') + '''`;
        const defaultPrompt3 = `''' + DEFAULT_STAGE3_PROMPT.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${') + '''`;
        const defaultPrompt4 = `''' + DEFAULT_STAGE4_PROMPT.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${') + '''`;

        document.getElementById('stage1Prompt').value = defaultPrompt1;
        document.getElementById('stage2Prompt').value = defaultPrompt2;
        document.getElementById('stage3Prompt').value = defaultPrompt3;
        document.getElementById('stage4Prompt').value = defaultPrompt4;

        function toggleAdvanced() {
            document.querySelector('.advanced-toggle').classList.toggle('open');
            document.getElementById('advancedContent').classList.toggle('show');
        }
        function resetPrompt(stage) { 
            const prompts = [defaultPrompt1, defaultPrompt2, defaultPrompt3, defaultPrompt4];
            document.getElementById('stage' + stage + 'Prompt').value = prompts[stage - 1]; 
        }
        function copyPrompt(stage) { navigator.clipboard.writeText(document.getElementById('stage' + stage + 'Prompt').value); }
        function switchStage(stage) {
            document.querySelectorAll('.stage-tab').forEach((t, i) => t.classList.toggle('active', i === stage - 1));
            document.querySelectorAll('.stage-content').forEach((c, i) => c.classList.toggle('active', i === stage - 1));
            
            // 顯示/隱藏 Stage 4 導航按鈕
            const stage4Nav = document.getElementById('stage4Nav');
            if (stage4Nav) {
                stage4Nav.style.display = stage === 4 ? 'flex' : 'none';
            }
            
            // 滾動到對應階段內容的開頭
            const stageContentIds = ['stage1Content', 'stage2Content', 'stage3Content', 'stage4Content'];
            const targetElement = document.getElementById(stageContentIds[stage - 1]);
            if (targetElement) {
                // 稍微延遲以確保內容切換完成
                setTimeout(() => {
                    targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 100);
            }
        }

        function createParticles() {
            const c = document.getElementById('particles');
            // 普通金色粒子
            for (let i = 0; i < 35; i++) {
                const p = document.createElement('div');
                p.className = 'particle';
                p.style.left = Math.random() * 100 + '%';
                p.style.animationDelay = Math.random() * 8 + 's';
                p.style.animationDuration = (6 + Math.random() * 6) + 's';
                c.appendChild(p);
            }
            // 大型光暈粒子
            for (let i = 0; i < 8; i++) {
                const p = document.createElement('div');
                p.className = 'particle large';
                p.style.left = Math.random() * 100 + '%';
                p.style.animationDelay = Math.random() * 12 + 's';
                p.style.animationDuration = (10 + Math.random() * 8) + 's';
                c.appendChild(p);
            }
            // 小型閃爍光點
            for (let i = 0; i < 15; i++) {
                const p = document.createElement('div');
                p.className = 'particle glow';
                p.style.left = Math.random() * 100 + '%';
                p.style.animationDelay = Math.random() * 6 + 's';
                p.style.animationDuration = (4 + Math.random() * 4) + 's';
                c.appendChild(p);
            }
        }
        createParticles();

        // ========== Hero 區域動態背景動畫 ==========
        (function initHeroAnimation() {
            const canvas = document.getElementById('heroCanvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            let width, height;
            let particles = [];
            let auroraOffset = 0;
            let animationId;

            // 調整畫布大小
            function resize() {
                width = canvas.width = window.innerWidth;
                height = canvas.height = window.innerHeight;
                initParticles();
            }

            // 初始化療癒光點
            function initParticles() {
                particles = [];
                const count = Math.min(60, Math.floor(width * height / 20000));
                for (let i = 0; i < count; i++) {
                    particles.push({
                        x: Math.random() * width,
                        y: Math.random() * height,
                        vx: (Math.random() - 0.5) * 0.3,
                        vy: -Math.random() * 0.5 - 0.2,
                        size: Math.random() * 3 + 1,
                        alpha: Math.random() * 0.5 + 0.2,
                        pulse: Math.random() * Math.PI * 2,
                        pulseSpeed: Math.random() * 0.02 + 0.01
                    });
                }
            }

            // 繪製極光效果 - 增強對比度
            function drawAurora() {
                auroraOffset += 0.003;
                const gradient1 = ctx.createLinearGradient(0, 0, width, height * 0.6);
                gradient1.addColorStop(0, 'rgba(201, 169, 98, 0)');
                gradient1.addColorStop(0.2, `rgba(201, 169, 98, ${0.12 + Math.sin(auroraOffset) * 0.05})`);
                gradient1.addColorStop(0.4, `rgba(212, 175, 55, ${0.18 + Math.sin(auroraOffset * 1.5) * 0.07})`);
                gradient1.addColorStop(0.6, `rgba(184, 115, 81, ${0.12 + Math.sin(auroraOffset * 0.8) * 0.05})`);
                gradient1.addColorStop(1, 'rgba(139, 115, 85, 0)');

                ctx.fillStyle = gradient1;
                ctx.fillRect(0, 0, width, height);

                // 第二層極光 - 波動效果
                const waveY = height * 0.25 + Math.sin(auroraOffset * 2) * 60;
                const gradient2 = ctx.createRadialGradient(
                    width * 0.3, waveY, 0,
                    width * 0.3, waveY, width * 0.5
                );
                gradient2.addColorStop(0, `rgba(212, 175, 55, ${0.20 + Math.sin(auroraOffset * 1.2) * 0.08})`);
                gradient2.addColorStop(0.4, `rgba(201, 169, 98, ${0.12 + Math.sin(auroraOffset) * 0.05})`);
                gradient2.addColorStop(1, 'rgba(201, 169, 98, 0)');
                ctx.fillStyle = gradient2;
                ctx.fillRect(0, 0, width, height);

                // 第三層極光 - 右下角呼吸光暈
                const waveY2 = height * 0.7 + Math.sin(auroraOffset * 1.5) * 40;
                const gradient3 = ctx.createRadialGradient(
                    width * 0.75, waveY2, 0,
                    width * 0.75, waveY2, width * 0.4
                );
                gradient3.addColorStop(0, `rgba(184, 115, 81, ${0.15 + Math.sin(auroraOffset * 0.9) * 0.06})`);
                gradient3.addColorStop(0.5, `rgba(139, 115, 85, ${0.08 + Math.sin(auroraOffset * 1.3) * 0.04})`);
                gradient3.addColorStop(1, 'rgba(139, 115, 85, 0)');
                ctx.fillStyle = gradient3;
                ctx.fillRect(0, 0, width, height);
            }

            // 繪製浮動光點
            function drawParticles() {
                particles.forEach(p => {
                    p.x += p.vx;
                    p.y += p.vy;
                    p.pulse += p.pulseSpeed;

                    // 邊界循環
                    if (p.y < -20) { p.y = height + 20; p.x = Math.random() * width; }
                    if (p.x < -20) p.x = width + 20;
                    if (p.x > width + 20) p.x = -20;

                    const pulseAlpha = p.alpha * (0.7 + Math.sin(p.pulse) * 0.3);
                    const pulseSize = p.size * (0.9 + Math.sin(p.pulse) * 0.15);

                    // 外層光暈 - 增強可見度
                    const gradient = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, pulseSize * 6);
                    gradient.addColorStop(0, `rgba(255, 215, 100, ${pulseAlpha * 1.2})`);
                    gradient.addColorStop(0.3, `rgba(212, 175, 55, ${pulseAlpha * 0.7})`);
                    gradient.addColorStop(0.6, `rgba(201, 169, 98, ${pulseAlpha * 0.25})`);
                    gradient.addColorStop(1, 'rgba(201, 169, 98, 0)');

                    ctx.beginPath();
                    ctx.fillStyle = gradient;
                    ctx.arc(p.x, p.y, pulseSize * 6, 0, Math.PI * 2);
                    ctx.fill();

                    // 核心亮點 - 更亮更明顯
                    ctx.beginPath();
                    ctx.fillStyle = `rgba(255, 250, 240, ${pulseAlpha * 0.8})`;
                    ctx.arc(p.x, p.y, pulseSize * 0.5, 0, Math.PI * 2);
                    ctx.fill();
                });
            }

            // 動畫循環
            function animate() {
                ctx.clearRect(0, 0, width, height);
                drawAurora();
                drawParticles();
                animationId = requestAnimationFrame(animate);
            }

            // 啟動
            window.addEventListener('resize', resize);
            resize();
            animate();

            // 可見性優化 - 頁面不可見時暫停動畫
            document.addEventListener('visibilitychange', () => {
                if (document.hidden) {
                    cancelAnimationFrame(animationId);
                } else {
                    animate();
                }
            });
        })();

        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('audioFile');
        const analyzeBtn = document.getElementById('analyzeBtn');
        
        console.log('📍 上傳區域初始化:', { uploadZone: !!uploadZone, fileInput: !!fileInput, analyzeBtn: !!analyzeBtn });
        
        if (uploadZone && fileInput) {
            uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('dragover'); });
            uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
            uploadZone.addEventListener('drop', e => { e.preventDefault(); uploadZone.classList.remove('dragover'); if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]); });
            uploadZone.addEventListener('click', (e) => { 
                console.log('📍 上傳區域點擊'); 
                e.stopPropagation();
                fileInput.click(); 
            });
            fileInput.addEventListener('change', e => { 
                console.log('📍 檔案選擇變更:', e.target.files);
                if (e.target.files.length > 0) handleFile(e.target.files[0]); 
            });
        } else {
            console.error('❌ 上傳區域元素未找到');
        }
        
        function handleFile(file) { 
            console.log('📍 處理檔案:', file.name);
            selectedFile = file; 
            document.getElementById('fileName').textContent = file.name; 
            document.getElementById('fileSize').textContent = `(${(file.size / 1048576).toFixed(1)} MB)`; 
            document.getElementById('fileInfo').classList.add('show'); 
            if (analyzeBtn) analyzeBtn.disabled = false; 
        }

        let progressInterval;
        let waterFillInterval = null;
        let waterFillStarted = false;
        
        function startProgress() {
            let progress = 0;
            waterFillStarted = false;
            const stages = [
                { pct: 8, text: '上傳音訊中...', id: 's1' },
                { pct: 18, text: '一階：建立聲學基線...', id: 's2' },
                { pct: 28, text: '一階：追蹤演化軌跡...', id: 's3' },
                { pct: 38, text: '一階：識別轉折點...', id: 's4' },
                { pct: 52, text: '二階：冰山下方溯源...', id: 's5' },
                { pct: 66, text: '二階：療癒橋樑建構...', id: 's6' },
                { pct: 85, text: '三階：個人成長方案...', id: 's7' }
            ];
            let idx = 0;
            progressInterval = setInterval(() => {
                progress += 0.3;
                if (progress > 98) progress = 98;
                document.getElementById('progressRing').style.strokeDashoffset = 502 - (502 * progress / 100);
                document.getElementById('progressPercent').textContent = Math.round(progress) + '%';
                
                // 當進度達到 98% 時，啟動水波上升動畫
                if (progress >= 98 && !waterFillStarted) {
                    waterFillStarted = true;
                    startWaterFillAnimation();
                }
                
                if (idx < stages.length && progress >= stages[idx].pct) {
                    document.getElementById('loadingStage').textContent = stages[idx].text;
                    if (idx >= 4 && idx < 6) document.getElementById('loadingTitle').textContent = '正在深層溯源...';
                    if (idx >= 6) document.getElementById('loadingTitle').textContent = '正在建構成長方案...';
                    const el = document.getElementById(stages[idx].id);
                    el.classList.add('active'); el.querySelector('.stage-icon').textContent = '⏳';
                    if (idx > 0) { const prev = document.getElementById(stages[idx - 1].id); prev.classList.remove('active'); prev.classList.add('done'); prev.querySelector('.stage-icon').textContent = '✓'; }
                    idx++;
                }
            }, 100);
        }
        
        // 水波上升動畫
        let heatingPhaseStarted = false;
        
        function startWaterFillAnimation() {
            const container = document.getElementById('waterFillContainer');
            const waterFill = document.getElementById('waterFill');
            container.classList.add('active');
            heatingPhaseStarted = false;
            
            let waterLevel = 0;
            document.getElementById('loadingTitle').textContent = '✨ 正在整合分析結果...';
            document.getElementById('loadingStage').textContent = '即將完成，請稍候片刻';
            
            waterFillInterval = setInterval(() => {
                waterLevel += 0.3;  // 慢速上升，配合分析時間
                
                // 當水滿到 95% 時，啟動火焰加熱階段
                if (waterLevel >= 95 && !heatingPhaseStarted) {
                    heatingPhaseStarted = true;
                    waterLevel = 100;
                    waterFill.style.height = '100%';
                    startHeatingPhase();
                }
                
                if (waterLevel <= 95) {
                    waterFill.style.height = waterLevel + '%';
                }
            }, 100);
        }
        
        // 火焰加熱階段 - 水從藍色變紅色
        function startHeatingPhase() {
            clearInterval(waterFillInterval);
            waterFillInterval = null;
            
            const fireContainer = document.getElementById('fireContainer');
            const waterFill = document.getElementById('waterFill');
            const waterWave = document.getElementById('waterWave');
            
            // 顯示火焰
            fireContainer.classList.add('active');
            
            // 開始加熱動畫 - 水變色
            waterFill.classList.add('heating');
            waterWave.classList.add('boiling');
            
            // 更新文字提示
            document.getElementById('loadingTitle').textContent = '🔥 正在煉化分析精華...';
            document.getElementById('loadingStage').textContent = '萃取核心洞察中';
            
            // 階段性更新提示文字
            setTimeout(() => {
                document.getElementById('loadingTitle').textContent = '✨ 療癒能量凝聚中...';
                document.getElementById('loadingStage').textContent = '即將完成，感謝您的耐心';
            }, 8000);
            
            // 15秒後開始冷卻階段
            setTimeout(() => {
                startCoolingPhase();
            }, 15000);
        }
        
        // 冷卻階段 - 水從紅色逐漸冷卻變回藍色
        function startCoolingPhase() {
            const fireContainer = document.getElementById('fireContainer');
            const waterFill = document.getElementById('waterFill');
            const waterWave = document.getElementById('waterWave');
            
            // 熄滅火焰
            fireContainer.classList.remove('active');
            
            // 移除加熱效果，添加冷卻效果
            waterFill.classList.remove('heating');
            waterWave.classList.remove('boiling');
            waterFill.classList.add('cooling');
            waterWave.classList.add('cooling');
            
            // 更新文字提示為「報告撰寫中」
            document.getElementById('loadingTitle').textContent = '📝 報告撰寫中...';
            document.getElementById('loadingStage').textContent = '正在組織分析結果與建議';
            
            // 冷卻過程中的文字更新
            setTimeout(() => {
                document.getElementById('loadingTitle').textContent = '📖 整理療癒方案...';
                document.getElementById('loadingStage').textContent = '為您量身打造成長路徑';
            }, 6000);
            
            setTimeout(() => {
                document.getElementById('loadingTitle').textContent = '✅ 報告即將完成！';
                document.getElementById('loadingStage').textContent = '感謝您的耐心等待';
            }, 12000);
        }
        
        function stopWaterFillAnimation() {
            if (waterFillInterval) {
                clearInterval(waterFillInterval);
                waterFillInterval = null;
            }
            
            // 如果還沒進入加熱階段，快速填滿
            const waterFill = document.getElementById('waterFill');
            if (waterFill) waterFill.style.height = '100%';
            
            // 清除火焰和加熱效果
            const fireContainer = document.getElementById('fireContainer');
            if (fireContainer) fireContainer.classList.remove('active');
            
            // 重置水的顏色（為下次使用）
            if (waterFill) {
                waterFill.classList.remove('heating', 'cooling');
            }
            const waterWave = document.getElementById('waterWave');
            if (waterWave) {
                waterWave.classList.remove('boiling', 'cooling');
            }
        }
        
        function stopProgress() {
            clearInterval(progressInterval);
            stopWaterFillAnimation();
            document.getElementById('progressPercent').textContent = '100%';
            document.getElementById('progressRing').style.strokeDashoffset = 0;
            document.querySelectorAll('.stage-item').forEach(el => { el.classList.remove('active'); el.classList.add('done'); el.querySelector('.stage-icon').textContent = '✓'; });
        }

        analyzeBtn.addEventListener('click', async () => {
            if (!selectedFile) return;
            document.getElementById('resultContainer').classList.remove('show');
            document.getElementById('errorCard').style.display = 'none';
            document.getElementById('loadingOverlay').classList.add('show');
            document.getElementById('loadingTitle').textContent = '正在深度分析中...';
            analyzeBtn.disabled = true;
            document.querySelectorAll('.stage-item').forEach(el => { el.classList.remove('active', 'done'); el.querySelector('.stage-icon').textContent = '○'; });
            document.getElementById('progressRing').style.strokeDashoffset = 502;
            document.getElementById('progressPercent').textContent = '0%';
            // 重置水波動畫
            const waterContainer = document.getElementById('waterFillContainer');
            const waterFill = document.getElementById('waterFill');
            if (waterContainer) waterContainer.classList.remove('active');
            if (waterFill) waterFill.style.height = '0%';
            startProgress();

            const formData = new FormData();
            formData.append('audio', selectedFile);
            formData.append('context', document.getElementById('contextInput').value);
            formData.append('stage1_prompt', document.getElementById('stage1Prompt').value);
            formData.append('stage2_prompt', document.getElementById('stage2Prompt').value);
            formData.append('stage3_prompt', document.getElementById('stage3Prompt').value);

            // ============ 使用流式分析 (SSE) 避免超時 ============
            try {
                const response = await fetch('/analyze-stream', { 
                    method: 'POST', 
                    body: formData 
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let stage1Data = null, stage2Data = null, stage3Data = null;
                let reportId = null;
                
                // 進度映射：每個階段完成時更新進度
                const stageProgress = { 1: 35, 2: 65, 3: 90 };
                const stageItems = ['s1', 's2', 's3', 's4', 's5', 's6', 's7'];
                const stageItemMap = { 1: [1, 2, 3, 4], 2: [5, 6], 3: [7] };
                
                function updateStageUI(stage, status) {
                    const items = stageItemMap[stage] || [];
                    items.forEach((idx, i) => {
                        const el = document.getElementById('s' + idx);
                        if (!el) return;
                        if (status === 'active' && i === items.length - 1) {
                            el.classList.add('active');
                            el.classList.remove('done');
                            el.querySelector('.stage-icon').textContent = '⏳';
                        } else if (status === 'done') {
                            el.classList.remove('active');
                            el.classList.add('done');
                            el.querySelector('.stage-icon').textContent = '✓';
                        }
                    });
                }
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';
                    
                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue;
                        const jsonStr = line.substring(6);
                        if (!jsonStr.trim()) continue;
                        
                        try {
                            const event = JSON.parse(jsonStr);
                            console.log('📍 SSE 事件:', event.type, event);
                            
                            switch (event.type) {
                                case 'status':
                                    document.getElementById('loadingStage').textContent = event.message;
                                    if (event.stage) {
                                        updateStageUI(event.stage, 'active');
                                        if (event.stage === 2) document.getElementById('loadingTitle').textContent = '正在深層溯源...';
                                        if (event.stage === 3) document.getElementById('loadingTitle').textContent = '正在建構成長方案...';
                                    }
                                    break;
                                    
                                case 'stage_complete':
                                    updateStageUI(event.stage, 'done');
                                    const prog = stageProgress[event.stage] || 50;
                                    document.getElementById('progressRing').style.strokeDashoffset = 502 - (502 * prog / 100);
                                    document.getElementById('progressPercent').textContent = prog + '%';
                                    
                                    if (event.stage === 1) stage1Data = event.result;
                                    if (event.stage === 2) stage2Data = event.result;
                                    if (event.stage === 3) stage3Data = event.result;
                                    break;
                                    
                                case 'complete':
                                    reportId = event.report_id;
                                    stopProgress();
                                    setTimeout(() => {
                                        document.getElementById('loadingOverlay').classList.remove('show');
                                        fullResult = event.result;
                                        displayResult(event.result, event.report_id);
                                    }, 500);
                                    break;
                                    
                                case 'error':
                                    stopProgress();
                                    document.getElementById('loadingOverlay').classList.remove('show');
                                    showError(event.message);
                                    break;
                            }
                        } catch (parseErr) {
                            console.warn('SSE JSON 解析錯誤:', parseErr, jsonStr);
                        }
                    }
                }
                
                // 如果沒收到 complete 事件但有資料，嘗試顯示結果
                if (!reportId && stage1Data && stage2Data && stage3Data) {
                    stopProgress();
                    document.getElementById('loadingOverlay').classList.remove('show');
                    showError('分析完成但未收到報告 ID，請重試');
                }
                
            } catch (err) { 
                console.error('分析錯誤:', err);
                stopProgress(); 
                document.getElementById('loadingOverlay').classList.remove('show'); 
                showError('網路錯誤：' + err.message); 
            } finally { 
                analyzeBtn.disabled = false; 
            }
        });
        
        // 顯示錯誤訊息
        function showError(message) {
            const errorCard = document.getElementById('errorCard');
            const errorMessage = document.getElementById('errorMessage');
            if (errorCard && errorMessage) {
                errorMessage.textContent = message;
                errorCard.style.display = 'block';
                errorCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else {
                alert('分析失敗：' + message);
            }
        }

        // 類似 Windows 通知的 Toast 提示
        function showToast(message, type = 'info') {
            // 創建容器如果不存在
            let container = document.getElementById('toast-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toast-container';
                container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 99999; display: flex; flex-direction: column; gap: 10px; pointer-events: none;';
                document.body.appendChild(container);
            }

            const toast = document.createElement('div');
            const bgColor = type === 'audio' ? '#C9A962' : (type === 'image' ? '#B87351' : (type === 'pdf' ? '#22C55E' : '#6366F1')); // Gold for audio, Terra for image, Green for PDF
            const icon = type === 'audio' ? '🎵' : (type === 'image' ? '🎨' : (type === 'pdf' ? '📄' : 'ℹ️'));
            
            toast.style.cssText = `
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-left: 4px solid ${bgColor};
                padding: 16px 20px;
                border-radius: 8px;
                box-shadow: 0 8px 25px rgba(0,0,0,0.15);
                display: flex;
                align-items: center;
                gap: 12px;
                min-width: 280px;
                transform: translateX(120%);
                transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.4s ease;
                font-family: 'Segoe UI', sans-serif;
                margin-bottom: 10px;
                pointer-events: auto;
                opacity: 0;
            `;
            
            toast.innerHTML = `
                <div style="font-size: 1.4rem; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));">${icon}</div>
                <div style="display: flex; flex-direction: column;">
                    <span style="color: #333; font-weight: 600; font-size: 0.95rem;">${type === 'audio' ? '音頻播放' : (type === 'image' ? '圖像生成' : (type === 'pdf' ? 'PDF 報告' : '系統通知'))}</span>
                    <span style="color: #666; font-size: 0.85rem; margin-top: 2px;">${message}</span>
                </div>
            `;
            
            container.appendChild(toast);
            
            // 進場動畫
            requestAnimationFrame(() => {
                toast.style.transform = 'translateX(0)';
                toast.style.opacity = '1';
                // 播放音效 (可選)
                // const audio = new Audio('/static/notification_simple-01.wav');
                // audio.volume = 0.2;
                // audio.play().catch(e => {}); 
            });
            
            // 5秒後自動移除
            setTimeout(() => {
                toast.style.transform = 'translateX(120%)';
                toast.style.opacity = '0';
                setTimeout(() => toast.remove(), 400);
            }, 5000);
        }

        function displayResult(r, reportId) {
            currentReportId = reportId;  // 儲存報告 ID 供圖像生成使用
            const s1 = r.stage1, s2 = r.stage2;
            document.getElementById('reportTime').textContent = new Date().toLocaleString('zh-TW');
            document.getElementById('reportId').textContent = reportId;
            document.getElementById('overallDynamic').textContent = s1.overall_dynamic;
            document.getElementById('energyPattern').textContent = s1.energy_pattern;
            document.getElementById('phaseCount').textContent = s1.evolution_map?.length || 0;
            document.getElementById('intensityScore').textContent = (s1.intensity_score || 5) + '/10';

            const evo = document.getElementById('evolutionMap'); evo.innerHTML = '';
            if (s1.evolution_map) s1.evolution_map.forEach((p, i) => { evo.innerHTML += `<div class="phase-card"><div class="phase-header"><div class="phase-name">階段 ${i + 1}：${p.phase}</div></div><div class="phase-desc">${p.description}</div><div class="contribution-grid"><div class="contribution-box"><div class="contribution-label">A 的貢獻</div><div class="text-content">${p.speaker_a_contribution}</div></div><div class="contribution-box"><div class="contribution-label">B 的貢獻</div><div class="text-content">${p.speaker_b_contribution}</div></div></div><div style="margin-top:15px;padding:12px;background:rgba(99,102,241,0.1);border-radius:8px;"><strong style="color:var(--accent-primary);"> 關鍵觀察：</strong> ${p.key_observation}</div></div>`; });

            const tp = document.getElementById('turningPoints'); tp.innerHTML = '';
            if (s1.turning_points) s1.turning_points.forEach(t => { tp.innerHTML += `<div class="turning-point"><div class="turning-moment"> ${t.moment}</div><div class="turning-why"><strong>為什麼關鍵：</strong> ${t.why_critical}</div><div class="turning-alt"><strong> 錯失的替代：</strong> ${t.missed_alternative}</div></div>`; });

            if (s1.dual_perspective) { document.getElementById('dualPerspective').innerHTML = `<div class="perspective-box"><div class="perspective-header"><div class="speaker-avatar">A</div><div style="font-weight:600;">A 的體驗</div></div><div class="text-content">${s1.dual_perspective.speaker_a_experience}</div></div><div class="perspective-box"><div class="perspective-header"><div class="speaker-avatar">B</div><div style="font-weight:600;">B 的體驗</div></div><div class="text-content">${s1.dual_perspective.speaker_b_experience}</div></div>`; document.getElementById('coreMismatch').textContent = s1.dual_perspective.core_mismatch; }

            if (s1.repair_analysis) document.getElementById('repairAnalysis').innerHTML = `<div class="repair-item"><div class="repair-label">修復嘗試</div><div class="text-content">${s1.repair_analysis.attempts}</div></div><div class="repair-item"><div class="repair-label">回應方式</div><div class="text-content">${s1.repair_analysis.responses}</div></div><div class="repair-item"><div class="repair-label">錯失機會</div><div class="text-content">${s1.repair_analysis.missed_opportunities}</div></div>`;

            // Stage 2
            document.getElementById('deepInsight').textContent = s2.deep_insight_summary;

            const ice = document.getElementById('icebergAnalysis'); ice.innerHTML = '';
            if (s2.iceberg_analysis) s2.iceberg_analysis.forEach(i => { ice.innerHTML += `<div class="iceberg-card"><div class="iceberg-header"><div class="speaker-avatar">${i.speaker_id}</div><div style="font-weight:600;">說話者 ${i.speaker_id}</div></div><div class="iceberg-section"><div class="iceberg-label">表面行為</div><div>${i.surface_behavior}</div></div><div class="iceberg-section"><div class="iceberg-label">深層恐懼</div><div>${i.underlying_fear}</div></div><div class="iceberg-section"><div class="iceberg-label">深層渴望</div><div>${i.underlying_desire}</div></div><div class="iceberg-section"><div class="iceberg-label">未滿足的需求</div><div>${i.unmet_need}</div></div><div class="iceberg-section"><div class="iceberg-label">可能的觸發來源</div><div>${i.possible_trigger}</div></div></div>`; });

            document.getElementById('attachmentDynamic').textContent = s2.attachment_dynamic;
            document.getElementById('cognitiveClash').textContent = s2.cognitive_style_clash;

            const ps = document.getElementById('perspectiveShifts'); ps.innerHTML = '';
            if (s2.perspective_shifts) s2.perspective_shifts.forEach(p => { ps.innerHTML += `<div class="phase-card"><div class="phase-name">給 ${p.for_speaker} 的練習</div><div style="padding:15px;background:rgba(139,92,246,0.1);border-radius:10px;margin-bottom:10px;"><strong> ${p.prompt}</strong></div><div class="text-content">${p.insight}</div></div>`; });

            const hr = document.getElementById('healingReframes'); hr.innerHTML = '';
            if (s2.healing_reframes) s2.healing_reframes.forEach(h => { hr.innerHTML += `<div class="healing-card"><div class="healing-original"> ${h.original_statement}</div><div class="healing-arrow">↓ 翻譯成 ↓</div><div class="healing-translation"> ${h.vulnerable_translation}</div><div class="healing-response"> 對方可以這樣回應：${h.compassionate_response}</div></div>`; });

            const ac = document.getElementById('actionableChanges'); ac.innerHTML = '';
            if (s2.actionable_changes) s2.actionable_changes.forEach(a => { ac.innerHTML += `<div class="action-card"><div class="action-header">給 ${a.for_speaker} 的建議</div><div class="action-item"><span class="action-icon"></span><div><div class="action-label">觸發情境</div><div>${a.trigger_situation}</div></div></div><div class="action-item"><span class="action-icon"></span><div><div class="action-label">舊模式</div><div>${a.old_pattern}</div></div></div><div class="action-item"><span class="action-icon"></span><div><div class="action-label">新做法</div><div>${a.new_approach}</div></div></div><div class="action-item" style="background:rgba(34,197,94,0.1);"><span class="action-icon"></span><div><div class="action-label">降溫用語</div><div style="color:var(--accent-success);font-weight:600;">${a.cooling_phrase}</div></div></div></div>`; });

            document.getElementById('sharedResponsibility').textContent = s2.shared_responsibility;
            document.getElementById('healingMessage').textContent = s2.healing_message;

            // Stage 3
            const s3 = r.stage3;
            document.getElementById('positioning').textContent = s3.positioning;

            // 我能做的修復
            const rsl = s3.repair_self_led;
            document.getElementById('repairSelfLed').innerHTML = `
                <div class="growth-item"><div class="growth-label">自我情緒照顧</div><div class="text-content">${rsl.emotional_care}</div></div>
                <div class="growth-item"><div class="growth-label">內在整理</div><div class="text-content">${rsl.inner_clarity}</div></div>
                <div class="growth-item"><div class="growth-label">主動修復選項</div><div class="text-content">${rsl.proactive_options}</div></div>
                <div class="growth-item"><div class="growth-label">如果對方沒有回應</div><div class="text-content">${rsl.if_no_response}</div></div>`;

            // 認識我的模式
            const kmp = s3.know_my_patterns;
            document.getElementById('knowMyPatterns').innerHTML = `
                <div class="growth-item"><div class="growth-label">我的觸發點</div><div class="text-content">${kmp.triggers}</div></div>
                <div class="growth-item"><div class="growth-label">我的盲點</div><div class="text-content">${kmp.blind_spots}</div></div>
                <div class="growth-item"><div class="growth-label">理想的我 vs 現在的我</div><div class="text-content">${kmp.ideal_self}</div></div>
                <div class="growth-item"><div class="growth-label">縮小差距的切入點</div><div class="text-content">${kmp.gap_bridge}</div></div>`;

            // 我的調節工具箱
            const mt = s3.my_toolkit;
            document.getElementById('myToolkit').innerHTML = `
                <div class="growth-item"><div class="growth-label">我的預警信號</div><div class="text-content">${mt.warning_signs}</div></div>
                <div class="growth-item"><div class="growth-label">對我有效的降溫方法</div><div class="text-content">${mt.cooling_methods}</div></div>
                <div class="growth-item"><div class="growth-label">不需要對方同意的暫停策略</div><div class="text-content">${mt.solo_pause_strategy}</div></div>`;

            // 替代路徑
            const alt = s3.alternatives;
            document.getElementById('alternatives').innerHTML = `
                <div class="growth-item"><div class="growth-label">這次我做的</div><div class="text-content">${alt.what_i_did}</div></div>
                <div class="growth-item"><div class="growth-label">我可以嘗試的</div><div class="text-content">${alt.what_i_could_try}</div></div>
                <div class="growth-item"><div class="growth-label">為什麼對我比較好</div><div class="text-content">${alt.why_better_for_me}</div></div>
                <div class="growth-item" style="background:rgba(34,197,94,0.15);"><div class="growth-label"> 這週的微小實驗</div><div class="text-content" style="font-weight:600;">${alt.micro_experiment}</div></div>`;

            // 我的邊界
            const mb = s3.my_boundaries;
            document.getElementById('myBoundaries').innerHTML = `
                <div class="growth-item"><div class="growth-label">我的核心需求</div><div class="text-content">${mb.core_needs}</div></div>
                <div class="growth-item"><div class="growth-label">接受程度</div><div class="text-content">${mb.acceptance_levels}</div></div>
                <div class="growth-item"><div class="growth-label">如何表達邊界</div><div class="text-content">${mb.how_to_express}</div></div>
                <div class="growth-item"><div class="growth-label">如何保護自己</div><div class="text-content">${mb.how_to_protect}</div></div>`;

            // 意義重構
            const mm = s3.meaning_making;
            document.getElementById('meaningMaking').innerHTML = `
                <div class="growth-item"><div class="growth-label">這次照見了什麼</div><div class="text-content">${mm.what_this_reveals}</div></div>
                <div class="growth-item"><div class="growth-label">我正在學習的功課</div><div class="text-content">${mm.lesson_learning}</div></div>
                <div class="growth-item" style="background:rgba(34,197,94,0.15);"><div class="growth-label"> 送給自己的話</div><div class="text-content" style="font-style:italic;">${mm.message_to_self}</div></div>`;

            // 反思提問
            const rp = document.getElementById('reflectionPrompts');
            rp.innerHTML = '';
            if (s3.reflection_prompts) s3.reflection_prompts.forEach(q => { rp.innerHTML += `<li> ${q}</li>`; });

            // 結語
            document.getElementById('closingMessage').textContent = s3.closing;

            document.getElementById('resultContainer').classList.add('show');
            switchStage(1);
            document.getElementById('resultContainer').scrollIntoView({ behavior: 'smooth' });
            
            // 分析完成，啟用 PDF 下載按鈕
            updateDownloadButtons(true, false);
            
            // 啟動浮動短語雲（從分析結果提取短語）
            startFloatingPhrases(r);
            
            // 分析完成後自動開始生成療育音頻
            onAnalysisComplete();
        }
        
        // 浮動短語雲系統
        let phraseIntervalId = null;
        function startFloatingPhrases(result) {
            const container = document.getElementById('floatingPhrasesContainer');
            if (!container) return;
            
            // 從分析結果中提取有意義的短語
            const phrases = extractPhrases(result);
            if (phrases.length === 0) return;
            
            let idx = 0;
            
            function createPhrase() {
                if (phrases.length === 0) return;
                
                // 隨機選取短語
                const phrase = phrases[idx % phrases.length];
                idx++;
                
                const el = document.createElement('div');
                el.className = 'floating-phrase';
                el.textContent = phrase;
                
                // 隨機位置（避免重疊）
                el.style.left = (10 + Math.random() * 60) + '%';
                el.style.top = (20 + Math.random() * 50) + '%';
                
                container.appendChild(el);
                
                // 動畫結束後移除
                setTimeout(() => {
                    el.remove();
                }, 12000);
            }
            
            // 啟動：每 8 秒出現一個短語
            createPhrase();
            phraseIntervalId = setInterval(createPhrase, 8000);
        }
        
        function extractPhrases(result) {
            const phrases = [];
            const s3 = result.stage3 || {};
            
            // 從 Stage 3 提取關鍵短語
            if (s3.positioning) {
                // 截取前 20 個字
                const pos = s3.positioning.slice(0, 30);
                if (pos.length > 10) phrases.push('✨ ' + pos + '...');
            }
            
            // 從反思提問中提取
            if (s3.reflection_prompts && Array.isArray(s3.reflection_prompts)) {
                s3.reflection_prompts.slice(0, 3).forEach(q => {
                    const short = q.slice(0, 25);
                    if (short.length > 8) phrases.push('💭 ' + short + '...');
                });
            }
            
            // 從意義重構中提取
            if (s3.meaning_making) {
                if (s3.meaning_making.message_to_self) {
                    const msg = s3.meaning_making.message_to_self.slice(0, 28);
                    if (msg.length > 10) phrases.push('💫 ' + msg + '...');
                }
            }
            
            // 從我的邊界中提取
            if (s3.my_boundaries && s3.my_boundaries.core_needs) {
                const needs = s3.my_boundaries.core_needs.slice(0, 25);
                if (needs.length > 8) phrases.push('🌿 ' + needs + '...');
            }
            
            // 從 Stage 2 提取
            const s2 = result.stage2 || {};
            if (s2.deep_insight_summary) {
                const insight = s2.deep_insight_summary.slice(0, 28);
                if (insight.length > 12) phrases.push('🔮 ' + insight + '...');
            }
            
            return phrases;
        }

        function showError(msg) { document.getElementById('errorMessage').textContent = msg; document.getElementById('errorCard').style.display = 'block'; }
        
        // 下載 PDF 報告
        function downloadPDF() { 
            if (!currentReportId) { alert('請先完成分析'); return; }
            showToast('正在生成 PDF 分析報告，請稍候...', 'pdf');
            window.open(`/download-pdf/${currentReportId}`, '_blank'); 
        }
        
        // 下載完整包（PDF 內嵌圖片）
        async function downloadFullPackage() {
            if (!currentReportId || !imagesReady) { 
                alert('圖片尚未生成完成，請稍候'); 
                return; 
            }
            
            showToast('正在生成完整版 PDF（含視覺化圖像），請稍候...', 'pdf');
            const btn = document.getElementById('downloadFullBtn');
            const status = document.getElementById('fullDownloadStatus');
            btn.disabled = true;
            status.textContent = '⏳ 正在生成完整版 PDF...';
            
            try {
                // 收集所有圖片的 base64
                const imgIds = ['imgStage1', 'imgStage2', 'imgStage3', 'imgCombined'];
                const images = [];
                
                imgIds.forEach(id => {
                    const img = document.getElementById(id);
                    if (img && img.src && img.src.startsWith('data:image')) {
                        // 提取 base64 部分（去掉 data:image/png;base64, 前綴）
                        const base64 = img.src.split(',')[1];
                        images.push(base64);
                    } else {
                        images.push(null);  // 該圖片生成失敗
                    }
                });
                
                // 呼叫後端生成帶圖片的 PDF
                const resp = await fetch('/download-pdf-with-images', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        report_id: currentReportId,
                        images: images
                    })
                });
                
                if (resp.ok) {
                    // 下載 PDF
                    const blob = await resp.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `衝突分析報告_完整版_${currentReportId}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                    
                    status.textContent = '✅ 下載完成！';
                } else {
                    const error = await resp.json();
                    throw new Error(error.error || '下載失敗');
                }
            } catch (err) {
                console.error('下載完整版 PDF 失敗:', err);
                status.textContent = '❌ 下載失敗，請重試';
                alert('下載失敗：' + err.message);
            } finally {
                btn.disabled = false;
            }
        }
        
        // 按鈕狀態管理
        let imagesReady = false;
        
        function updateDownloadButtons(pdfReady, imagesComplete) {
            const pdfBtn = document.getElementById('downloadPdfBtn');
            const fullBtn = document.getElementById('downloadFullBtn');
            const pdfStatus = document.getElementById('pdfDownloadStatus');
            const fullStatus = document.getElementById('fullDownloadStatus');
            
            if (pdfReady) {
                pdfBtn.disabled = false;
                pdfStatus.textContent = '✅ 點擊下載完整分析報告';
            }
            
            if (imagesComplete) {
                imagesReady = true;
                fullBtn.disabled = false;
                fullStatus.textContent = '✅ 包含 4 張視覺化圖像';
            } else if (pdfReady) {
                fullStatus.textContent = '⏳ 圖片生成中...';
            }
        }
        
        let currentReportId = null;
        
        // 自動生成圖片（逐張請求模式 + 容錯設計）
        // ⚠️ 實現「增量渲染」：成功的立即顯示，失敗的顯示佔位符 + 重試按鈕
        let failedStages = [];  // 記錄失敗的階段，供重試使用
        
        async function generateImagesAuto() {
            if (!currentReportId) return false;
            
            const progressBar = document.getElementById('imageProgressBar');
            const progressText = document.getElementById('imageProgressText');
            const container = document.getElementById('generatedImagesContainer');
            
            // 配色系統
            const stageKeys = ['stage1', 'stage2', 'stage3', 'combined'];
            const stageNames = ['衝突演化', '深層溯源', '成長方案', '融合總覽'];
            const imgIds = ['imgStage1', 'imgStage2', 'imgStage3', 'imgCombined'];
            const stageColors = ['#C9A962', '#B87351', '#A3B899', '#D4A5A5'];
            const textColors = ['#6B5B4F', '#6B5B4F', '#5A6B55', '#6B5555'];
            
            let successCount = 0;
            failedStages = [];  // 重置失敗清單
            
            // 先顯示容器
            container.style.display = 'block';
            
            // ⚠️ 關鍵修正：在生成前顯示「生成中」佔位符
            for (let i = 0; i < 4; i++) {
                showLoadingPlaceholder(imgIds[i], i, stageNames[i]);
            }
            
            console.log('📍 開始逐張生成圖像（增量渲染模式）...');
            
            // ============ 逐張請求：每張圖獨立連線 ============
            for (let i = 0; i < 4; i++) {
                const key = stageKeys[i];
                const name = stageNames[i];
                const imgId = imgIds[i];
                const pct = ((i + 1) / 4) * 85 + 10;
                
                progressText.textContent = `🎨 [${i+1}/4] 正在渲染「${name}」...`;
                progressBar.style.width = `${10 + i * 20}%`;
                
                // 更新當前圖的佔位符為「正在生成」
                showLoadingPlaceholder(imgId, i, name, true);
                
                console.log(`📍[${i+1}/4] 請求生成：${key}`);
                
                // ⚠️ 自動重試 20 次
                let imageSuccess = false;
                let lastError = null;
                
                for (let attempt = 1; attempt <= 20 && !imageSuccess; attempt++) {
                    if (attempt > 1) {
                        console.log(`🔄[${i+1}/4] ${key} 第 ${attempt} 次重試...`);
                        progressText.textContent = `🔄 [${i+1}/4]「${name}」重試中 (${attempt}/20)...`;
                        await new Promise(r => setTimeout(r, 2000));  // 重試前等待 2 秒
                    }
                    
                    try {
                        const resp = await fetch('/generate-single-image', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ 
                                report_id: currentReportId,
                                stage_index: i
                            })
                        });
                        
                        const data = await resp.json();
                        
                        if (data.success && data.image_base64) {
                            console.log(`✅[${i+1}/4] ${key} 生成成功！`);
                            successCount++;
                            imageSuccess = true;
                            
                            // 🔔 如果是第一張圖 (Stage 1)，跳出通知
                            if (i === 0) {
                                showToast('視覺化圖與分析摘要已生成！', 'image');
                            }
                            
                            // 即時顯示圖片
                            const imgEl = document.getElementById(imgId);
                            if (imgEl) {
                                imgEl.src = 'data:image/png;base64,' + data.image_base64;
                                imgEl.style.opacity = '1';
                                // 移除可能存在的重試按鈕
                                const retryBtn = imgEl.parentElement.querySelector('.retry-btn');
                                if (retryBtn) retryBtn.remove();
                            }
                            
                            // 填充簡報卡片數據
                            if (data.slide) {
                                const num = i < 3 ? (i + 1).toString() : '4';
                                const color = stageColors[i];
                                const textColor = textColors[i];
                                
                                const titleEl = document.getElementById('slideTitle' + num);
                                if (titleEl && data.slide.slide_title) titleEl.textContent = data.slide.slide_title;
                                
                                const insightEl = document.getElementById('slideInsight' + num);
                                if (insightEl && data.slide.core_insight) insightEl.textContent = data.slide.core_insight;
                                
                                const bulletsEl = document.getElementById('slideBullets' + num);
                                if (bulletsEl && data.slide.data_bullets && data.slide.data_bullets.length > 0) {
                                    bulletsEl.innerHTML = data.slide.data_bullets.map(bullet => 
                                        `<li style="color: ${textColor}; font-size: 0.9rem; padding: 6px 0; display: flex; align-items: flex-start;">
                                            <span style="color:${color}; margin-right:10px;">—</span>
                                            <span>${bullet}</span>
                                        </li>`
                                    ).join('');
                                }
                            }
                            
                            progressBar.style.width = `${pct}%`;
                        } else {
                            lastError = data.error;
                            console.warn(`❌[${i+1}/4] ${key} 第 ${attempt} 次失敗:`, data.error);
                        }
                    } catch (err) {
                        lastError = err.message;
                        console.error(`❌[${i+1}/4] ${key} 第 ${attempt} 次請求錯誤:`, err);
                    }
                }
                
                // 20 次都失敗後才顯示手動重試
                if (!imageSuccess) {
                    console.error(`❌[${i+1}/4] ${key} 自動重試 20 次失敗，顯示手動重試按鈕`);
                    failedStages.push(i);
                    showFailedPlaceholder(imgId, i, name);
                }
                
                // 每張圖之間等待一小段時間
                await new Promise(r => setTimeout(r, 300));
            }
            
            // 顯示最終結果
            progressBar.style.width = '100%';
            
            if (successCount === 4) {
                progressText.textContent = `✅ 視覺化簡報完成（4/4 張成功）`;
                // 全部成功，啟用完整包下載按鈕
                updateDownloadButtons(true, true);
            } else if (successCount > 0) {
                progressText.innerHTML = `✅ 已完成 ${successCount}/4 張 <span style="color:#F59E0B;">（${4-successCount} 張失敗，可重試）</span>`;
                // 部分成功也啟用（至少有圖）
                updateDownloadButtons(true, true);
            } else {
                progressText.innerHTML = `❌ 圖像生成失敗 <button onclick="generateImagesAuto()" style="margin-left:10px;padding:4px 12px;background:#C9A962;color:white;border:none;border-radius:4px;cursor:pointer;">全部重試</button>`;
            }
            
            console.log(`✅ 圖像處理完成！成功：${successCount}/4`);
            return successCount > 0;
        }
        
        // 顯示「生成中」佔位符
        function showLoadingPlaceholder(imgId, stageIndex, stageName, isActive = false) {
            const imgEl = document.getElementById(imgId);
            if (!imgEl) return;
            
            const stageColors = ['#C9A962', '#B87351', '#A3B899', '#D4A5A5'];
            const color = stageColors[stageIndex] || '#C9A962';
            
            // 移除可能存在的重試按鈕
            const retryBtn = imgEl.parentElement?.querySelector('.retry-btn');
            if (retryBtn) retryBtn.remove();
            
            if (isActive) {
                // 正在生成中（動態）
                imgEl.src = 'data:image/svg+xml,' + encodeURIComponent(`
                    <svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
                        <rect fill="#1A1A1A" width="400" height="300" rx="12"/>
                        <circle cx="180" cy="150" r="8" fill="${color}" opacity="0.8">
                            <animate attributeName="opacity" values="0.8;0.3;0.8" dur="1.5s" repeatCount="indefinite"/>
                        </circle>
                        <circle cx="200" cy="150" r="8" fill="${color}" opacity="0.6">
                            <animate attributeName="opacity" values="0.6;0.8;0.6" dur="1.5s" repeatCount="indefinite"/>
                        </circle>
                        <circle cx="220" cy="150" r="8" fill="${color}" opacity="0.4">
                            <animate attributeName="opacity" values="0.4;0.6;0.4" dur="1.5s" repeatCount="indefinite"/>
                        </circle>
                        <text x="200" y="190" fill="${color}" font-size="14" text-anchor="middle" font-family="sans-serif">正在渲染「${stageName}」...</text>
                    </svg>
                `);
            } else {
                // 等待中（靜態）
                imgEl.src = 'data:image/svg+xml,' + encodeURIComponent(`
                    <svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
                        <rect fill="#1A1A1A" width="400" height="300" rx="12"/>
                        <circle cx="200" cy="140" r="20" fill="none" stroke="${color}" stroke-width="2" opacity="0.4"/>
                        <text x="200" y="145" fill="${color}" font-size="16" text-anchor="middle" font-family="sans-serif" opacity="0.6">${stageIndex + 1}</text>
                        <text x="200" y="185" fill="#888" font-size="12" text-anchor="middle" font-family="sans-serif">等待生成...</text>
                    </svg>
                `);
            }
            imgEl.style.opacity = '1';
        }
        
        // 顯示失敗佔位符 + 重試按鈕
        function showFailedPlaceholder(imgId, stageIndex, stageName) {
            const imgEl = document.getElementById(imgId);
            if (!imgEl) return;
            
            // 設置佔位符樣式
            imgEl.src = 'data:image/svg+xml,' + encodeURIComponent(`
                <svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
                    <rect fill="#2A2A2A" width="400" height="300" rx="12"/>
                    <text x="200" y="140" fill="#888" font-size="14" text-anchor="middle" font-family="sans-serif">圖像生成失敗</text>
                    <text x="200" y="165" fill="#666" font-size="12" text-anchor="middle" font-family="sans-serif">點擊下方按鈕重試</text>
                </svg>
            `);
            imgEl.style.opacity = '0.6';
            
            // 添加重試按鈕（如果還沒有）
            if (!imgEl.parentElement.querySelector('.retry-btn')) {
                const retryBtn = document.createElement('button');
                retryBtn.className = 'retry-btn';
                retryBtn.innerHTML = `🔄 重試「${stageName}」`;
                retryBtn.style.cssText = 'position:absolute;bottom:10px;left:50%;transform:translateX(-50%);padding:8px 16px;background:linear-gradient(135deg,#C9A962,#B87351);color:white;border:none;border-radius:20px;cursor:pointer;font-size:12px;z-index:10;';
                retryBtn.onclick = () => retrySingleImage(stageIndex);
                imgEl.parentElement.style.position = 'relative';
                imgEl.parentElement.appendChild(retryBtn);
            }
        }
        
        // 單張圖像重試
        async function retrySingleImage(stageIndex) {
            const stageKeys = ['stage1', 'stage2', 'stage3', 'combined'];
            const stageNames = ['衝突演化', '深層溯源', '成長方案', '融合總覽'];
            const imgIds = ['imgStage1', 'imgStage2', 'imgStage3', 'imgCombined'];
            const stageColors = ['#C9A962', '#B87351', '#A3B899', '#D4A5A5'];
            const textColors = ['#6B5B4F', '#6B5B4F', '#5A6B55', '#6B5555'];
            
            const key = stageKeys[stageIndex];
            const name = stageNames[stageIndex];
            const imgId = imgIds[stageIndex];
            
            console.log(`🔄 重試生成：${key}`);
            
            // 顯示載入中
            const imgEl = document.getElementById(imgId);
            if (imgEl) {
                imgEl.src = 'data:image/svg+xml,' + encodeURIComponent(`
                    <svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
                        <rect fill="#2A2A2A" width="400" height="300" rx="12"/>
                        <text x="200" y="150" fill="#C9A962" font-size="14" text-anchor="middle" font-family="sans-serif">⏳ 正在重新生成...</text>
                    </svg>
                `);
                // 暫時隱藏重試按鈕
                const retryBtn = imgEl.parentElement.querySelector('.retry-btn');
                if (retryBtn) retryBtn.style.display = 'none';
            }
            
            try {
                const resp = await fetch('/generate-single-image', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        report_id: currentReportId,
                        stage_index: stageIndex
                    })
                });
                
                const data = await resp.json();
                
                if (data.success && data.image_base64) {
                    console.log(`✅ ${key} 重試成功！`);
                    
                    // 更新圖片
                    if (imgEl) {
                        imgEl.src = 'data:image/png;base64,' + data.image_base64;
                        imgEl.style.opacity = '1';
                        const retryBtn = imgEl.parentElement.querySelector('.retry-btn');
                        if (retryBtn) retryBtn.remove();
                    }
                    
                    // 更新簡報卡片
                    if (data.slide) {
                        const num = stageIndex < 3 ? (stageIndex + 1).toString() : '4';
                        const color = stageColors[stageIndex];
                        const textColor = textColors[stageIndex];
                        
                        const titleEl = document.getElementById('slideTitle' + num);
                        if (titleEl && data.slide.slide_title) titleEl.textContent = data.slide.slide_title;
                        
                        const insightEl = document.getElementById('slideInsight' + num);
                        if (insightEl && data.slide.core_insight) insightEl.textContent = data.slide.core_insight;
                    }
                    
                    // 從失敗清單移除
                    failedStages = failedStages.filter(s => s !== stageIndex);
                    
                    // 更新進度文字
                    const progressText = document.getElementById('imageProgressText');
                    if (failedStages.length === 0) {
                        progressText.textContent = `✅ 視覺化簡報完成（4/4 張成功）`;
                    } else {
                        progressText.innerHTML = `✅ 已完成 ${4 - failedStages.length}/4 張 <span style="color:#F59E0B;">（${failedStages.length} 張失敗，可重試）</span>`;
                    }
                    
                    return true;
                } else {
                    console.warn(`❌ ${key} 重試失敗:`, data.error);
                    showFailedPlaceholder(imgId, stageIndex, name);
                    const retryBtn = imgEl?.parentElement.querySelector('.retry-btn');
                    if (retryBtn) retryBtn.style.display = 'block';
                    return false;
                }
            } catch (err) {
                console.error(`❌ ${key} 重試請求錯誤:`, err);
                showFailedPlaceholder(imgId, stageIndex, name);
                const retryBtn = imgEl?.parentElement.querySelector('.retry-btn');
                if (retryBtn) retryBtn.style.display = 'block';
                return false;
            }
        }
        
        // 療育音頻播放器功能
        let healingAudioReady = false;
        
        // ============ Web Audio API 混音器 (AudioNarrator) ============
        // 支援 BGM + 語音的即時混音，帶自動避讓 (Ducking) 效果
        class AudioNarrator {
            constructor() {
                this.audioCtx = null;
                this.bgmGain = null;
                this.voiceGain = null;
                this.bgmSource = null;
                this.bgmVolume = 0.25;
                this.duckingVolume = 0.08;
            }
            
            async init() {
                if (this.audioCtx) return;
                this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                this.bgmGain = this.audioCtx.createGain();
                this.voiceGain = this.audioCtx.createGain();
                this.bgmGain.gain.value = this.bgmVolume;
                this.bgmGain.connect(this.audioCtx.destination);
                this.voiceGain.connect(this.audioCtx.destination);
            }
            
            async loadBGM(url) {
                await this.init();
                try {
                    const response = await fetch(url);
                    const arrayBuffer = await response.arrayBuffer();
                    const audioBuffer = await this.audioCtx.decodeAudioData(arrayBuffer);
                    
                    this.bgmSource = this.audioCtx.createBufferSource();
                    this.bgmSource.buffer = audioBuffer;
                    this.bgmSource.loop = true;
                    this.bgmSource.connect(this.bgmGain);
                    this.bgmSource.start(0);
                    console.log("🎵 BGM 已啟動");
                } catch (err) {
                    console.warn("🎵 BGM 加載失敗:", err);
                }
            }
            
            async playVoice(audioBlob) {
                await this.init();
                const arrayBuffer = await audioBlob.arrayBuffer();
                const audioBuffer = await this.audioCtx.decodeAudioData(arrayBuffer);
                
                // Ducking: 降低 BGM 音量
                this.fadeBGM(this.duckingVolume);
                
                const source = this.audioCtx.createBufferSource();
                source.buffer = audioBuffer;
                source.connect(this.voiceGain);
                
                return new Promise(resolve => {
                    source.onended = () => {
                        this.fadeBGM(this.bgmVolume);  // 恢復 BGM 音量
                        resolve();
                    };
                    source.start(0);
                });
            }
            
            fadeBGM(targetVolume) {
                if (!this.bgmGain) return;
                const now = this.audioCtx.currentTime;
                this.bgmGain.gain.linearRampToValueAtTime(targetVolume, now + 0.5);
            }
            
            stop() {
                if (this.bgmSource) {
                    this.bgmSource.stop();
                    this.bgmSource = null;
                }
            }
        }
        
        const audioNarrator = new AudioNarrator();
        
        // ========== 串流音頻播放器 ==========
        class StreamingAudioPlayer {
            constructor() {
                this.audioQueue = [];  // 音頻片段隊列
                this.currentIndex = 0;
                this.isPlaying = false;
                this.audioElement = null;
                this.totalParts = 0;
                this.receivedParts = 0;
                this.onStatusUpdate = null;
            }
            
            init(audioElement, statusCallback) {
                this.audioElement = audioElement;
                this.onStatusUpdate = statusCallback;
                this.audioQueue = [];
                this.currentIndex = 0;
                this.isPlaying = false;
                this.totalParts = 0;
                this.receivedParts = 0;
                this.partDurations = [];  // 追蹤每個片段的時長
                this.totalDuration = 0;   // 總時長
                this.elapsedBeforeCurrent = 0;  // 當前片段之前已播放的時間
                
                // 當前片段播放結束時，自動播放下一個
                this.audioElement.onended = () => this.playNext();
                
                // 綁定 timeupdate 事件以更新進度條
                this.audioElement.ontimeupdate = () => this.updateProgress();
                
                // 當片段載入完成時，記錄其時長
                this.audioElement.onloadedmetadata = () => {
                    if (this.currentIndex < this.partDurations.length) {
                        this.partDurations[this.currentIndex] = this.audioElement.duration;
                        this.totalDuration = this.partDurations.reduce((sum, d) => sum + (d || 0), 0);
                    }
                };
            }
            
            // 更新進度條
            updateProgress() {
                if (!this.audioElement || !this.isPlaying) return;
                
                const currentPartTime = this.audioElement.currentTime || 0;
                const totalElapsed = this.elapsedBeforeCurrent + currentPartTime;
                
                // 估算總時長（基於已收到的片段）
                const avgPartDuration = this.totalDuration / (this.partDurations.filter(d => d > 0).length || 1);
                const estimatedTotal = avgPartDuration * this.totalParts;
                
                const progress = estimatedTotal > 0 ? (totalElapsed / estimatedTotal) * 100 : 0;
                
                const progressBar = document.getElementById('audioProgressBar');
                const currentTimeEl = document.getElementById('audioCurrentTime');
                const totalTimeEl = document.getElementById('audioTotalTime');
                
                if (progressBar) progressBar.style.width = Math.min(progress, 100) + '%';
                if (currentTimeEl) currentTimeEl.textContent = this.formatTime(totalElapsed);
                if (totalTimeEl) totalTimeEl.textContent = this.formatTime(estimatedTotal);
                
                // 同步備用播放器
                const embeddedBar = document.getElementById('embeddedProgressBar');
                const embeddedCurrent = document.getElementById('embeddedCurrentTime');
                const embeddedTotal = document.getElementById('embeddedTotalTime');
                if (embeddedBar) embeddedBar.style.width = Math.min(progress, 100) + '%';
                if (embeddedCurrent) embeddedCurrent.textContent = this.formatTime(totalElapsed);
                if (embeddedTotal) embeddedTotal.textContent = this.formatTime(estimatedTotal);
            }
            
            formatTime(seconds) {
                if (!seconds || isNaN(seconds)) return '0:00';
                const mins = Math.floor(seconds / 60);
                const secs = Math.floor(seconds % 60);
                return `${mins}:${secs.toString().padStart(2, '0')}`;
            }
            
            // 添加新的音頻片段到隊列
            addAudioPart(base64Audio, partNumber) {
                const audioUrl = 'data:audio/wav;base64,' + base64Audio;
                this.audioQueue.push({ url: audioUrl, part: partNumber });
                this.receivedParts++;
                this.partDurations.push(0);  // 預留位置
                
                console.log(`📥 收到音頻片段 ${partNumber}/${this.totalParts}`);
                
                // 如果是第一個片段且還沒開始播放，立即開始！
                if (this.audioQueue.length === 1 && !this.isPlaying) {
                    this.startPlaying();
                }
                
                // 每次添加新片段時更新按鈕狀態
                if (typeof updateControlButtons === 'function') {
                    updateControlButtons();
                }
            }
            
            startPlaying() {
                if (this.audioQueue.length === 0) return;
                
                this.isPlaying = true;
                this.currentIndex = 0;
                this.playCurrentPart();
                
                // 啟動波形可視化和 UI 更新
                if (typeof startVisualizer === 'function') {
                    startVisualizer();
                }
                if (typeof updatePlayingState === 'function') {
                    updatePlayingState(true);
                }
            }
            
            playCurrentPart() {
                if (this.currentIndex >= this.audioQueue.length) {
                    // 還沒有更多片段，等待...
                    if (this.receivedParts < this.totalParts) {
                        console.log('⏳ 等待更多片段...');
                        // 設置一個檢查器，等待新片段
                        const waitForNext = setInterval(() => {
                            if (this.currentIndex < this.audioQueue.length) {
                                clearInterval(waitForNext);
                                this.playCurrentPart();
                            } else if (this.receivedParts >= this.totalParts) {
                                clearInterval(waitForNext);
                                this.onComplete();
                            }
                        }, 500);
                    } else {
                        this.onComplete();
                    }
                    return;
                }
                
                const part = this.audioQueue[this.currentIndex];
                this.audioElement.src = part.url;
                this.audioElement.play().catch(e => console.error('播放錯誤:', e));
                
                if (this.onStatusUpdate) {
                    this.onStatusUpdate(`🎵 正在播放 ${part.part}/${this.totalParts}...`);
                }
                
                // 更新控制按鈕和片段信息
                if (typeof updateControlButtons === 'function') {
                    updateControlButtons();
                }
                if (typeof updateTrackInfo === 'function') {
                    updateTrackInfo();
                }
            }
            
            playNext() {
                // 累加已播放片段的時長
                if (this.currentIndex < this.partDurations.length) {
                    this.elapsedBeforeCurrent += this.partDurations[this.currentIndex] || 0;
                }
                this.currentIndex++;
                this.playCurrentPart();
            }
            
            onComplete() {
                this.isPlaying = false;
                if (this.onStatusUpdate) {
                    this.onStatusUpdate('✅ 療癒音頻播放完成');
                }
                console.log('✅ 所有音頻片段播放完成');
                
                // 更新 UI 狀態
                if (typeof updatePlayingState === 'function') {
                    updatePlayingState(false);
                }
                if (typeof stopVisualizer === 'function') {
                    stopVisualizer();
                }
                if (typeof updateControlButtons === 'function') {
                    updateControlButtons();
                }
            }
            
            pause() {
                if (this.audioElement) {
                    this.audioElement.pause();
                    this.isPlaying = false;
                }
            }
            
            resume() {
                if (this.audioElement && !this.isPlaying) {
                    this.audioElement.play();
                    this.isPlaying = true;
                }
            }
            
            // 播放上一段
            playPrev() {
                if (this.currentIndex > 0) {
                    // 扣除當前片段的時長
                    if (this.currentIndex > 0 && this.currentIndex <= this.partDurations.length) {
                        this.elapsedBeforeCurrent -= this.partDurations[this.currentIndex - 1] || 0;
                    }
                    this.currentIndex--;
                    this.playCurrentPart();
                    return true;
                }
                return false;
            }
            
            // 手動跳到下一段
            skipNext() {
                if (this.currentIndex < this.audioQueue.length - 1) {
                    this.playNext();
                    return true;
                }
                return false;
            }
            
            // 獲取當前片段索引
            getCurrentPart() {
                return this.currentIndex + 1;
            }
            
            // 獲取總片段數
            getTotalParts() {
                return this.totalParts;
            }
            
            // 判斷是否有上一段
            hasPrev() {
                return this.currentIndex > 0;
            }
            
            // 判斷是否有下一段
            hasNext() {
                return this.currentIndex < this.audioQueue.length - 1;
            }
        }
        
        const streamingPlayer = new StreamingAudioPlayer();
        
        // 串流式生成療育音頻（邊生成邊播放）
        async function generateHealingAudioStream() {
            if (!currentReportId) return false;
            
            const progressBar = document.getElementById('audioGenProgressBar');
            const progressText = document.getElementById('audioProgressText');
            const partsProgress = document.getElementById('audioPartsProgress');
            const healingPlayer = document.getElementById('healingPlayer');
            const audio = document.getElementById('healingAudio');
            
            // 初始化串流播放器
            streamingPlayer.init(audio, (status) => {
                partsProgress.textContent = status;
            });
            
            // 顯示播放器（生成中狀態）
            healingPlayer.classList.add('show', 'generating');
            healingPlayer.classList.remove('ready', 'playing');
            document.querySelector('.healing-player-title').textContent = '🎵 療癒音頻串流生成中...';
            
            progressText.textContent = '正在連接串流...';
            progressBar.style.width = '5%';
            partsProgress.style.display = 'block';
            
            const stage4Prompt = document.getElementById('stage4Prompt').value;
            
            try {
                const response = await fetch('/generate-audio-stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        report_id: currentReportId,
                        stage4_prompt: stage4Prompt,
                        voice: 'warm_female'
                    })
                });
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    buffer += decoder.decode(value, { stream: true });
                    
                    // 解析 SSE 事件
                    const lines = buffer.split('\\n');
                    buffer = lines.pop() || '';  // 保留不完整的行
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                handleStreamEvent(data, progressBar, progressText, partsProgress);
                            } catch (e) {
                                console.warn('解析 SSE 事件失敗:', line);
                            }
                        }
                    }
                }
                
                // 處理完成 - 檢查是否真的有音頻片段
                if (streamingPlayer.audioQueue.length === 0) {
                    // 沒有任何音頻片段成功，降級到傳統模式
                    console.warn('⚠️ 串流模式沒有成功生成任何片段，降級到傳統模式...');
                    progressText.textContent = '⚠️ 串流失敗，切換到傳統模式...';
                    return await generateHealingAudioAuto();
                }
                
                progressBar.style.width = '100%';
                progressText.textContent = `✅ 串流生成完成！(${streamingPlayer.audioQueue.length} 個片段)`;
                healingPlayer.classList.remove('generating');
                healingPlayer.classList.add('ready');
                document.querySelector('.healing-player-title').textContent = '🎵 串流療癒音頻';
                healingAudioReady = true;
                
                return true;
                
            } catch (err) {
                console.error('串流生成錯誤:', err);
                progressText.textContent = '❌ 串流生成失敗，切換到傳統模式...';
                // 降級到傳統模式
                return await generateHealingAudioAuto();
            }
        }
        
        function handleStreamEvent(data, progressBar, progressText, partsProgress) {
            switch (data.type) {
                case 'status':
                    progressText.textContent = data.message;
                    break;
                    
                case 'info':
                    streamingPlayer.totalParts = data.total_parts;
                    partsProgress.textContent = data.message;
                    progressBar.style.width = '15%';
                    break;
                    
                case 'audio':
                    // 收到音頻片段！
                    streamingPlayer.addAudioPart(data.audio_base64, data.part);
                    
                    // 🔔 如果是第一段音頻 (Part 1)，跳出通知
                    if (data.part === 1) {
                        showToast('療癒音頻開始串流播放...', 'audio');
                    }
                    
                    const pct = 15 + (data.part / data.total) * 80;
                    progressBar.style.width = pct + '%';
                    progressText.textContent = `🎙️ 已生成 ${data.part}/${data.total} 片段`;
                    break;
                    
                case 'part_error':
                    console.warn(`片段 ${data.part} 生成失敗:`, data.error);
                    break;
                    
                case 'complete_with_bgm':
                    // 🎵 收到混合了 BGM 的完整音頻！
                    console.log('🎵 收到混合 BGM 的完整音頻！方法:', data.bgm_method);
                    partsProgress.textContent = `🎵 已混合背景音樂 (${data.bgm_method})`;
                    
                    // 設置主音頻播放器使用混合後的音頻
                    const audio = document.getElementById('healingAudio');
                    audio.src = 'data:audio/wav;base64,' + data.audio_base64;
                    audio.addEventListener('timeupdate', updateAudioProgress);
                    audio.addEventListener('ended', onAudioEnded);
                    
                    // 更新 UI 狀態
                    healingAudioReady = true;
                    const healingPlayer = document.getElementById('healingPlayer');
                    healingPlayer.classList.remove('generating');
                    healingPlayer.classList.add('ready');
                    document.querySelector('.healing-player-title').textContent = '🎵 療癒音頻（含背景音樂）';
                    
                    // 顯示嵌入式備用播放器
                    const embeddedPlayer = document.getElementById('embeddedPlayerCard');
                    if (embeddedPlayer) embeddedPlayer.style.display = 'block';
                    break;
                    
                case 'bgm_skipped':
                    console.log('⚠️ BGM 跳過:', data.reason);
                    partsProgress.textContent = `⚠️ 背景音樂跳過: ${data.reason}`;
                    break;
                    
                case 'bgm_error':
                    console.warn('❌ BGM 混合錯誤:', data.error);
                    partsProgress.textContent = '⚠️ 背景音樂混合失敗，使用純語音';
                    break;
                    
                case 'complete':
                    partsProgress.textContent = `✅ 生成完成！成功 ${data.success_count || '?'} 個片段`;
                    break;
                    
                case 'error':
                    progressText.textContent = '❌ ' + data.message;
                    break;
            }
        }
        
        // 自動生成音頻（帶自動重試 3 次）
        async function generateHealingAudioAuto() {
            if (!currentReportId) return false;
            
            const progressBar = document.getElementById('audioGenProgressBar');
            const progressText = document.getElementById('audioProgressText');

            const partsProgress = document.getElementById('audioPartsProgress');
            
            progressText.textContent = '正在生成分段療癒腳本...';
            progressBar.style.width = '5%';
            partsProgress.style.display = 'block';
            partsProgress.textContent = '🎭 正在生成療育文稿...';
            
            // ⚠️ 生成開始時立即顯示播放器（生成中狀態）
            const healingPlayer = document.getElementById('healingPlayer');
            healingPlayer.classList.add('show', 'generating');
            healingPlayer.classList.remove('ready', 'playing');
            document.querySelector('.healing-player-title').textContent = '🎵 療癒音頻 ';
            
            // 分段進度模擬
            let progress = 5;
            const progressSteps = [
                { pct: 15, text: '🎭 正在生成療育文稿...' },
                { pct: 25, text: '✂️ 拆分文稿為多個片段...' },
                { pct: 40, text: '🎙️ 正在生成 PART_1 音頻...' },
                { pct: 55, text: '🎙️ 正在生成 PART_2 音頻...' },
                { pct: 65, text: '🎙️ 正在生成 PART_3 音頻...' },
                { pct: 75, text: '🎙️ 正在生成更多片段...' },
                { pct: 85, text: '🎶 正在編織您的專屬療癒能量...' },
            ];
            let stepIdx = 0;
            
            const progressInterval = setInterval(() => {
                if (stepIdx < progressSteps.length && progress >= progressSteps[stepIdx].pct - 5) {
                    partsProgress.textContent = progressSteps[stepIdx].text;
                    stepIdx++;
                }
                if (progress < 85) {
                    progress += Math.random() * 2;
                    progressBar.style.width = Math.min(progress, 85) + '%';
                }
            }, 1200);
            
            const stage4Prompt = document.getElementById('stage4Prompt').value;
            
            // ⚠️ 自動重試 20 次
            let success = false;
            let lastError = null;
            let data = null;
            
            for (let attempt = 1; attempt <= 20 && !success; attempt++) {
                if (attempt > 1) {
                    console.log(`🔄 音頻生成第 ${attempt} 次重試...`);
                    progressText.textContent = `🔄 音頻生成重試中 (${attempt}/20)...`;
                    await new Promise(r => setTimeout(r, 3000));  // 重試前等待 3 秒
                }
                
                try {
                    const resp = await fetch('/generate-audio', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            report_id: currentReportId,
                            stage4_prompt: stage4Prompt,
                            voice: 'warm_female'
                        })
                    });
                    
                    data = await resp.json();
                    
                    if (data.success && data.audio_base64) {
                        success = true;
                        console.log(`✅ 音頻生成成功！（第 ${attempt} 次嘗試）`);
                    } else {
                        lastError = data.error;
                        console.warn(`❌ 音頻生成第 ${attempt} 次失敗:`, data.error);
                    }
                } catch (err) {
                    lastError = err.message;
                    console.error(`❌ 音頻生成第 ${attempt} 次請求錯誤:`, err);
                }
            }
            
            clearInterval(progressInterval);
            
            if (success && data) {
                progressBar.style.width = '100%';
                progressText.textContent = '✅ 音頻生成完成！';
                
                // 顯示 BGM 狀態
                const bgmStatus = data.bgm_status || {};
                if (bgmStatus.success) {
                    partsProgress.textContent = `🎵 已成功串接 ${data.parts_count || 6} 個音頻片段 + 🎶 ${bgmStatus.method === 'lyria' ? 'Lyria原創BGM' : '本地BGM'}`;
                } else {
                    partsProgress.innerHTML = `🎵 已成功串接 ${data.parts_count || 6} 個音頻片段<br><span style="color:#F59E0B;">⚠️ 純語音模式（${bgmStatus.error || '無背景音樂'}）</span>`;
                    console.warn('BGM 混音未成功:', bgmStatus);
                }
                
                // 設置音頻
                const audio = document.getElementById('healingAudio');
                audio.src = 'data:audio/wav;base64,' + data.audio_base64;
                
                // 設置進度條更新
                audio.addEventListener('timeupdate', updateAudioProgress);
                audio.addEventListener('ended', onAudioEnded);
                
                healingAudioReady = true;
                

                
                // ⚠️ 生成完成：移除生成中狀態，添加就緒閃爍動畫
                const healingPlayer = document.getElementById('healingPlayer');
                healingPlayer.classList.remove('generating');
                healingPlayer.classList.add('ready');
                document.querySelector('.healing-player-title').textContent = '🎵 開始您的專屬療癒引導';
                
                // 初始化音頻波形可視化
                initAudioVisualizer(audio);
                
                // 顯示嵌入式備用播放器
                const embeddedPlayer = document.getElementById('embeddedPlayerCard');
                if (embeddedPlayer) {
                    embeddedPlayer.style.display = 'block';
                }
                
                return true;
            } else {
                progressText.innerHTML = `❌ 音頻生成失敗（重試 20 次）<button onclick="generateHealingAudioAuto()" style="margin-left:10px;padding:4px 12px;background:#C9A962;color:white;border:none;border-radius:4px;cursor:pointer;">重試</button>`;
                partsProgress.textContent = `錯誤：${lastError || '未知錯誤'}`;
                console.error('音頻生成失敗（20 次重試後）:', lastError);
                return false;
            }
        }
        
        // 格式化時間為 M:SS 格式
        function formatTime(seconds) {
            if (!seconds || isNaN(seconds)) return '0:00';
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins}:${secs.toString().padStart(2, '0')}`;
        }
        
        function updateAudioProgress() {
            const audio = document.getElementById('healingAudio');
            if (audio.duration) {
                const progress = (audio.currentTime / audio.duration) * 100;
                document.getElementById('audioProgressBar').style.width = progress + '%';
                
                // 更新時間顯示
                document.getElementById('audioCurrentTime').textContent = formatTime(audio.currentTime);
                document.getElementById('audioTotalTime').textContent = formatTime(audio.duration);
                
                // 同步備用播放器
                const embeddedBar = document.getElementById('embeddedProgressBar');
                const embeddedCurrent = document.getElementById('embeddedCurrentTime');
                const embeddedTotal = document.getElementById('embeddedTotalTime');
                if (embeddedBar) embeddedBar.style.width = progress + '%';
                if (embeddedCurrent) embeddedCurrent.textContent = formatTime(audio.currentTime);
                if (embeddedTotal) embeddedTotal.textContent = formatTime(audio.duration);
            }
        }
        
        function onAudioEnded() {
            document.getElementById('healingPlayBtn').classList.remove('playing');
            document.getElementById('audioProgressBar').style.width = '0%';
            document.getElementById('healingPlayer').classList.remove('playing');
            document.getElementById('audioCurrentTime').textContent = '0:00';
            
            // 同步備用播放器
            const embeddedBtn = document.getElementById('embeddedPlayBtn');
            const embeddedBar = document.getElementById('embeddedProgressBar');
            if (embeddedBtn) embeddedBtn.classList.remove('playing');
            if (embeddedBar) embeddedBar.style.width = '0%';
            
            stopVisualizer();
        }
        
        // ============ 音頻波形可視化 ============
        let audioContext = null;
        let analyser = null;
        let visualizerAnimationId = null;
        
        function initAudioVisualizer(audioElement) {
            try {
                if (!audioContext) {
                    audioContext = new (window.AudioContext || window.webkitAudioContext)();
                }
                
                // 避免重複連接
                if (!analyser) {
                    const source = audioContext.createMediaElementSource(audioElement);
                    analyser = audioContext.createAnalyser();
                    analyser.fftSize = 128;
                    
                    source.connect(analyser);
                    analyser.connect(audioContext.destination);
                }
                
                console.log('🎵 音頻波形可視化已初始化');
            } catch (err) {
                console.warn('🎵 波形可視化初始化失敗，使用模擬波形:', err);
            }
        }
        
        // 模擬波形動畫（用於串流模式或初始化失敗時）
        function startSimulatedVisualizer() {
            const canvas = document.getElementById('audioVisualizer');
            const container = canvas.parentElement;
            
            canvas.width = container.offsetWidth * 2;
            canvas.height = container.offsetHeight * 2;
            canvas.style.width = container.offsetWidth + 'px';
            canvas.style.height = container.offsetHeight + 'px';
            canvas.style.display = 'block';
            
            const ctx = canvas.getContext('2d');
            const barCount = 64;
            const barWidth = (canvas.width / barCount) * 0.85;
            const barGap = (canvas.width / barCount) * 0.15;
            
            // 模擬數據
            const simulatedData = new Array(barCount).fill(0);
            
            function draw() {
                visualizerAnimationId = requestAnimationFrame(draw);
                
                // 更新模擬數據（隨機波動）
                const time = Date.now() / 1000;
                for (let i = 0; i < barCount; i++) {
                    const wave1 = Math.sin(time * 2 + i * 0.2) * 0.3;
                    const wave2 = Math.sin(time * 3.5 + i * 0.15) * 0.2;
                    const wave3 = Math.sin(time * 1.2 + i * 0.3) * 0.2;
                    const random = (Math.random() - 0.5) * 0.1;
                    simulatedData[i] = 0.3 + wave1 + wave2 + wave3 + random;
                }
                
                // 透明背景
                ctx.fillStyle = 'rgba(13, 13, 13, 0.2)';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                
                const centerY = canvas.height / 2;
                let x = barGap;
                
                for (let i = 0; i < barCount; i++) {
                    const value = Math.max(0.05, Math.min(1, simulatedData[i]));
                    const barHeight = value * canvas.height * 0.45;
                    
                    const alpha = 0.4 + value * 0.4;
                    ctx.fillStyle = `rgba(212, 175, 55, ${alpha})`;
                    ctx.beginPath();
                    ctx.roundRect(x, centerY - barHeight, barWidth, barHeight, 3);
                    ctx.fill();
                    
                    ctx.fillStyle = `rgba(212, 175, 55, ${alpha * 0.3})`;
                    ctx.beginPath();
                    ctx.roundRect(x, centerY, barWidth, barHeight * 0.5, 3);
                    ctx.fill();
                    
                    x += barWidth + barGap;
                }
                
                // 呼吸中心線
                const breathe = Math.sin(time * 2) * 0.3 + 0.7;
                ctx.strokeStyle = `rgba(201, 169, 98, ${0.25 * breathe})`;
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(0, centerY);
                ctx.lineTo(canvas.width, centerY);
                ctx.stroke();
            }
            
            draw();
        }
        
        function startVisualizer() {
            // 先停止之前的動畫（避免多個動畫同時運行）
            if (visualizerAnimationId) {
                cancelAnimationFrame(visualizerAnimationId);
                visualizerAnimationId = null;
            }
            
            // 立即顯示 canvas
            const canvas = document.getElementById('audioVisualizer');
            if (canvas) {
                canvas.style.display = 'block';
            }
            
            // 如果沒有真實的音頻分析器，使用模擬波形
            if (!analyser) {
                console.log('🎵 使用模擬波形動畫');
                startSimulatedVisualizer();
                return;
            }
            
            // canvas 已在上方宣告，直接使用
            const container = canvas.parentElement;
            
            // 動態調整 canvas 尺寸以匹配進度條
            canvas.width = container.offsetWidth * 2;  // 高解析度
            canvas.height = container.offsetHeight * 2;
            canvas.style.width = container.offsetWidth + 'px';
            canvas.style.height = container.offsetHeight + 'px';
            canvas.style.display = 'block';
            
            const ctx = canvas.getContext('2d');
            analyser.fftSize = 128;  // 更多頻段
            const bufferLength = analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);
            const barWidth = (canvas.width / bufferLength) * 0.85;
            const barGap = (canvas.width / bufferLength) * 0.15;
            
            // 創建金色漸變
            const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
            gradient.addColorStop(0, 'rgba(244, 208, 63, 0.9)');    // 亮金色
            gradient.addColorStop(0.3, 'rgba(212, 175, 55, 0.8)');  // 標準金色
            gradient.addColorStop(0.7, 'rgba(184, 115, 81, 0.6)');  // 赤陶色
            gradient.addColorStop(1, 'rgba(139, 115, 85, 0.4)');    // 暗棕色
            
            function draw() {
                visualizerAnimationId = requestAnimationFrame(draw);
                
                analyser.getByteFrequencyData(dataArray);
                
                // 透明背景（帶輕微拖影效果）
                ctx.fillStyle = 'rgba(13, 13, 13, 0.3)';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                
                const centerY = canvas.height / 2;
                let x = barGap;
                
                for (let i = 0; i < bufferLength; i++) {
                    // 平滑化數據
                    const value = dataArray[i] / 255;
                    const barHeight = value * canvas.height * 0.45;
                    
                    // 上方波形
                    const alpha = 0.5 + value * 0.5;
                    ctx.fillStyle = `rgba(212, 175, 55, ${alpha})`;
                    ctx.beginPath();
                    ctx.roundRect(x, centerY - barHeight, barWidth, barHeight, 3);
                    ctx.fill();
                    
                    // 下方鏡像（較淡）
                    ctx.fillStyle = `rgba(212, 175, 55, ${alpha * 0.4})`;
                    ctx.beginPath();
                    ctx.roundRect(x, centerY, barWidth, barHeight * 0.6, 3);
                    ctx.fill();
                    
                    // 高亮點（頂部發光）
                    if (value > 0.5) {
                        ctx.fillStyle = `rgba(255, 223, 128, ${(value - 0.5) * 2})`;
                        ctx.beginPath();
                        ctx.arc(x + barWidth / 2, centerY - barHeight, 2, 0, Math.PI * 2);
                        ctx.fill();
                    }
                    
                    x += barWidth + barGap;
                }
                
                // 中心線（帶呼吸效果）
                const breathe = Math.sin(Date.now() / 500) * 0.3 + 0.7;
                ctx.strokeStyle = `rgba(201, 169, 98, ${0.3 * breathe})`;
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(0, centerY);
                ctx.lineTo(canvas.width, centerY);
                ctx.stroke();
            }
            
            draw();
        }
        
        function stopVisualizer() {
            if (visualizerAnimationId) {
                cancelAnimationFrame(visualizerAnimationId);
                visualizerAnimationId = null;
            }
            const canvas = document.getElementById('audioVisualizer');
            if (canvas) canvas.style.display = 'none';
        }
        
        function toggleHealingAudio() {
            const audio = document.getElementById('healingAudio');
            const player = document.getElementById('healingPlayer');
            
            // 判斷當前模式
            const isStreamingMode = streamingPlayer.audioQueue.length > 0;
            const isTraditionalMode = healingAudioReady && audio.src;
            
            console.log('📍 toggleHealingAudio:', { isStreamingMode, isTraditionalMode, healingAudioReady });
            
            // ⚠️ 串流模式控制
            if (isStreamingMode) {
                if (streamingPlayer.isPlaying) {
                    streamingPlayer.pause();
                    updatePlayingState(false);
                    stopVisualizer();
                } else {
                    streamingPlayer.resume();
                    updatePlayingState(true);
                    updateTrackInfo();
                    updateControlButtons();
                    startVisualizer(); 
                }
                return;
            }
            
            // ⚠️ 傳統模式控制
            if (isTraditionalMode) {
                // 確保 AudioContext 已恢復（用戶交互後）
                if (audioContext && audioContext.state === 'suspended') {
                    audioContext.resume();
                }
                
                if (audio.paused) {
                    audio.play().then(() => {
                        updatePlayingState(true);
                        player.classList.remove('ready');
                        startVisualizer();
                    }).catch(e => {
                        console.error('播放錯誤:', e);
                    });
                } else {
                    audio.pause();
                    updatePlayingState(false);
                    stopVisualizer();
                }
                return;
            }
            
            // 沒有可播放的音頻
            console.warn('⚠️ 沒有可播放的音頻');
        }
        
        function seekAudio(event) {
            const audio = document.getElementById('healingAudio');
            if (!audio.duration) return;
            
            const progressBar = event.currentTarget;
            const rect = progressBar.getBoundingClientRect();
            const clickX = event.clientX - rect.left;
            const percent = clickX / rect.width;
            
            audio.currentTime = percent * audio.duration;
        }
        
        function closeHealingPlayer() {
            const audio = document.getElementById('healingAudio');
            audio.pause();
            document.getElementById('healingPlayer').classList.remove('show');
            document.getElementById('healingPlayBtn').textContent = '';
            stopVisualizer();
            updatePlayingState(false);
        }
        
        // ============ 播放控制函數 ============
        
        // 上一段
        function prevTrack() {
            const isStreamingMode = streamingPlayer.audioQueue.length > 0;
            console.log('📍 prevTrack:', { isStreamingMode, currentIndex: streamingPlayer.currentIndex, queueLength: streamingPlayer.audioQueue.length });
            
            if (isStreamingMode) {
                // 串流模式
                if (streamingPlayer.playPrev()) {
                    updateTrackInfo();
                    updateControlButtons();
                    console.log('✅ 切換到上一段');
                } else {
                    console.log('⚠️ 已經是第一段');
                }
            } else {
                // 傳統模式：跳到開頭
                const audio = document.getElementById('healingAudio');
                if (audio && audio.src) {
                    audio.currentTime = 0;
                }
            }
        }
        
        // 下一段
        function nextTrack() {
            const isStreamingMode = streamingPlayer.audioQueue.length > 0;
            console.log('📍 nextTrack:', { isStreamingMode, currentIndex: streamingPlayer.currentIndex, queueLength: streamingPlayer.audioQueue.length });
            
            if (isStreamingMode) {
                // 串流模式
                if (streamingPlayer.skipNext()) {
                    updateTrackInfo();
                    updateControlButtons();
                    console.log('✅ 切換到下一段');
                } else {
                    console.log('⚠️ 已經是最後一段');
                }
            } else {
                // 傳統模式：跳到結尾
                const audio = document.getElementById('healingAudio');
                if (audio && audio.src && audio.duration) {
                    audio.currentTime = audio.duration;
                }
            }
        }
        
        // 更新播放狀態 UI
        function updatePlayingState(isPlaying) {
            const btn = document.getElementById('healingPlayBtn');
            const player = document.getElementById('healingPlayer');
            const embeddedBtn = document.getElementById('embeddedPlayBtn');
            
            if (isPlaying) {
                btn.classList.add('playing');
                player.classList.add('playing');
                if (embeddedBtn) embeddedBtn.classList.add('playing');
            } else {
                btn.classList.remove('playing');
                player.classList.remove('playing');
                if (embeddedBtn) embeddedBtn.classList.remove('playing');
            }
        }
        
        // 更新當前片段信息
        function updateTrackInfo() {
            const subtitle = document.getElementById('playerSubtitle');
            if (subtitle && !healingAudioReady && streamingPlayer.totalParts > 0) {
                const current = streamingPlayer.getCurrentPart();
                const total = streamingPlayer.getTotalParts();
                subtitle.textContent = `正在播放第 ${current} 段 / 共 ${total} 段`;
            }
        }
        
        // 更新控制按鈕狀態（啟用/禁用）
        function updateControlButtons() {
            const prevBtn = document.getElementById('prevBtn');
            const nextBtn = document.getElementById('nextBtn');
            
            if (!prevBtn || !nextBtn) return;
            
            const isStreamingMode = streamingPlayer.audioQueue.length > 0;
            
            if (isStreamingMode) {
                // 串流模式：根據當前位置啟用/禁用
                const hasPrev = streamingPlayer.hasPrev();
                const hasNext = streamingPlayer.hasNext();
                prevBtn.disabled = !hasPrev;
                nextBtn.disabled = !hasNext;
                console.log('📍 updateControlButtons (串流模式):', { hasPrev, hasNext, currentIndex: streamingPlayer.currentIndex });
            } else {
                // 傳統模式或無音頻：禁用
                prevBtn.disabled = true;
                nextBtn.disabled = true;
            }
        }
        
        // 初始化時禁用控制按鈕
        document.addEventListener('DOMContentLoaded', () => {
            updateControlButtons();
        });
        
        // 三階分析完成後自動生成圖片和音頻
        // ⚠️ 修正：圖像和音頻「並行」生成（各自獨立，不互相等待）
        async function onAnalysisComplete() {
            console.log('📍[onAnalysisComplete] 開始執行，currentReportId =', currentReportId);
            
            if (!currentReportId) {
                console.error('❌ currentReportId 為空，無法生成圖像和音頻！');
                document.getElementById('imageProgressText').textContent = '❌ 報告 ID 遺失';
                document.getElementById('audioProgressText').textContent = '❌ 報告 ID 遺失';
                return;
            }
            
            try {
                // 重置進度
                document.getElementById('imageProgressBar').style.width = '0%';
                document.getElementById('audioGenProgressBar').style.width = '0%';
                document.getElementById('imageProgressText').textContent = '正在啟動...';
                document.getElementById('audioProgressText').textContent = '正在啟動...';
                document.getElementById('generatedImagesContainer').style.display = 'none';
                
                // 顯示固定底部播放器
                const healingPlayer = document.getElementById('healingPlayer');
                if (healingPlayer) {
                    healingPlayer.classList.add('show');
                    healingPlayer.classList.add('generating');
                    console.log('📍 底部播放器已顯示');
                }
                const titleEl = document.querySelector('.healing-player-title');
                if (titleEl) titleEl.textContent = '🎵 正在生成您的專屬療癒音頻...';
                
                // ============ 並行生成：圖像和音頻同時進行 ============
                console.log('📍 開始並行生成（圖像 || 串流音頻）...');
                
                // 同時啟動兩個任務
                const imagePromise = generateImagesAuto().then(result => {
                    console.log('📍 圖像生成完成！', result);
                    return result;
                }).catch(err => {
                    console.error('❌ 圖像生成錯誤:', err);
                    document.getElementById('imageProgressText').textContent = '❌ 生成失敗: ' + err.message;
                    return false;
                });
                
                // 使用串流模式生成音頻（邊生成邊播放）
                const audioPromise = generateHealingAudioStream().then(result => {
                    console.log('📍 串流音頻生成完成！', result);
                    return result;
                }).catch(err => {
                    console.error('❌ 串流音頻生成錯誤:', err);
                    document.getElementById('audioProgressText').textContent = '❌ 生成失敗: ' + err.message;
                    return false;
                });
                
                // 等待兩者都完成（但它們是並行的）
                const [imageResult, audioResult] = await Promise.all([imagePromise, audioPromise]);
                
                console.log('✅ 所有自動生成完成！', { imageResult, audioResult });
            } catch (err) {
                console.error('❌ onAnalysisComplete 嚴重錯誤:', err);
            }
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/health')
def health_check():
    """健康檢查端點 - 用於前端偵測後端是否已喚醒"""
    return jsonify({
        'status': 'ok',
        'service': 'conflict-genesis-api',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        if 'audio' not in request.files:
            return jsonify({'success': False, 'error': '請選擇音訊檔案'})
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'success': False, 'error': '請選擇音訊檔案'})
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': '不支援的檔案格式'})
        
        filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
        filepath = app.config['UPLOAD_FOLDER'] / filename
        file.save(filepath)
        
        report_id = f"CG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        
        try:
            context = request.form.get('context', '')
            stage1_prompt = request.form.get('stage1_prompt', '')
            stage2_prompt = request.form.get('stage2_prompt', '')
            
            analyzer = ConflictAnalyzer()
            
            stage3_prompt = request.form.get('stage3_prompt', '')
            
            # 執行完整的三階段分析
            stage1_result, stage2_result, stage3_result = analyzer.full_analysis(
                audio_path=str(filepath),
                additional_context=context,
                stage1_prompt=stage1_prompt if stage1_prompt else None,
                stage2_prompt=stage2_prompt if stage2_prompt else None,
                stage3_prompt=stage3_prompt if stage3_prompt else None,
                verbose=True
            )
            
            # 組合結果
            full_result = {
                'stage1': stage1_result.model_dump(),
                'stage2': stage2_result.model_dump(),
                'stage3': stage3_result.model_dump()
            }
            
            # 儲存報告
            report_path = app.config['REPORTS_FOLDER'] / f"{report_id}.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(full_result, f, ensure_ascii=False, indent=2)
            
            return jsonify({
                'success': True,
                'result': full_result,
                'report_id': report_id
            })
            
        except ConflictAnalyzerError as e:
            return jsonify({'success': False, 'error': str(e)})
        except Exception as e:
            traceback.print_exc()
            return jsonify({'success': False, 'error': f'分析過程發生錯誤：{str(e)}'})
        finally:
            try:
                filepath.unlink()
            except:
                pass
                
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'伺服器錯誤：{str(e)}'})


@app.route('/analyze-stream', methods=['POST'])
def analyze_stream():
    """
    流式分析端點 (SSE) - 避免 Render 免費版 30 秒超時
    
    每完成一個階段就立即推送結果，而不是等待所有階段完成。
    這樣每個 SSE 事件都能在 30 秒內發送，避免連線超時。
    """
    from flask import Response, stream_with_context
    
    # 獲取表單數據
    if 'audio' not in request.files:
        return jsonify({'success': False, 'error': '請選擇音訊檔案'})
    
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'success': False, 'error': '請選擇音訊檔案'})
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': '不支援的檔案格式'})
    
    # 儲存檔案
    filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
    filepath = app.config['UPLOAD_FOLDER'] / filename
    file.save(filepath)
    
    context = request.form.get('context', '')
    stage1_prompt = request.form.get('stage1_prompt', '')
    stage2_prompt = request.form.get('stage2_prompt', '')
    stage3_prompt = request.form.get('stage3_prompt', '')
    
    report_id = f"CG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    
    def generate():
        try:
            analyzer = ConflictAnalyzer()
            
            # ==================== 階段 1 ====================
            yield f"data: {json.dumps({'type': 'status', 'stage': 1, 'message': '正在進行一階分析：衝突演化追蹤...'})}\n\n"
            
            try:
                stage1_result = analyzer.analyze_stage1(
                    audio_path=str(filepath),
                    additional_context=context,
                    system_prompt=stage1_prompt if stage1_prompt else None,
                    verbose=True
                )
                stage1_dict = stage1_result.model_dump()
                
                yield f"data: {json.dumps({'type': 'stage_complete', 'stage': 1, 'result': stage1_dict})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'stage': 1, 'message': f'一階分析失敗：{str(e)}'})}\n\n"
                return
            
            # ==================== 階段 2 ====================
            yield f"data: {json.dumps({'type': 'status', 'stage': 2, 'message': '正在進行二階分析：深層溯源...'})}\n\n"
            
            try:
                stage2_result = analyzer.analyze_stage2(
                    stage1_result=stage1_dict,
                    additional_context=context,
                    system_prompt=stage2_prompt if stage2_prompt else None,
                    verbose=True
                )
                stage2_dict = stage2_result.model_dump()
                
                yield f"data: {json.dumps({'type': 'stage_complete', 'stage': 2, 'result': stage2_dict})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'stage': 2, 'message': f'二階分析失敗：{str(e)}'})}\n\n"
                return
            
            # ==================== 階段 3 ====================
            yield f"data: {json.dumps({'type': 'status', 'stage': 3, 'message': '正在進行三階分析：成長方案...'})}\n\n"
            
            try:
                stage3_result = analyzer.analyze_stage3(
                    stage1_result=stage1_dict,
                    stage2_result=stage2_dict,
                    additional_context=context,
                    system_prompt=stage3_prompt if stage3_prompt else None,
                    verbose=True
                )
                stage3_dict = stage3_result.model_dump()
                
                yield f"data: {json.dumps({'type': 'stage_complete', 'stage': 3, 'result': stage3_dict})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'stage': 3, 'message': f'三階分析失敗：{str(e)}'})}\n\n"
                return
            
            # ==================== 完成：儲存報告 ====================
            full_result = {
                'stage1': stage1_dict,
                'stage2': stage2_dict,
                'stage3': stage3_dict
            }
            
            report_path = app.config['REPORTS_FOLDER'] / f"{report_id}.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(full_result, f, ensure_ascii=False, indent=2)
            
            yield f"data: {json.dumps({'type': 'complete', 'report_id': report_id, 'result': full_result})}\n\n"
            
        except Exception as e:
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': f'分析過程發生錯誤：{str(e)}'})}\n\n"
        finally:
            # 清理上傳的檔案
            try:
                filepath.unlink()
            except:
                pass
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # 禁用 Nginx/Render 的緩衝
        }
    )


@app.route('/generate-images', methods=['POST'])
def generate_images():
    """生成四張視覺化圖像（傳統模式，不推薦）"""
    # ⚠️ 此端點可能因長時間運行而超時
    # 建議使用 /generate-images-stream SSE 端點
    try:
        data = request.get_json()
        report_id = data.get('report_id')
        
        if not report_id:
            return jsonify({'success': False, 'error': '缺少報告編號'})
        
        # 讀取報告
        report_path = app.config['REPORTS_FOLDER'] / f"{report_id}.json"
        if not report_path.exists():
            return jsonify({'success': False, 'error': '找不到報告'})
        
        with open(report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        stage1 = report_data.get('stage1', {})
        stage2 = report_data.get('stage2', {})
        stage3 = report_data.get('stage3', {})
        
        # 使用 VisualArchitect 生成高質量圖片和簡報內容
        generator = ImageGenerator()
        
        image_folder = app.config['IMAGES_FOLDER'] / report_id
        image_folder.mkdir(exist_ok=True)
        
        # 呼叫新的整合方法
        result = generator.generate_all_images_with_slides(
            stage1_data=stage1,
            stage2_data=stage2,
            stage3_data=stage3,
            output_dir=image_folder
        )
        
        # 轉換圖像為 base64，並追蹤失敗的圖像
        # ============ 關鍵修復：批量模式圖文合成 ============
        images = {}
        failed_images = []
        slide_data_list = result.get("slides", [])
        stage_keys = ["stage1", "stage2", "stage3", "combined"]
        
        # 初始化 SlideComposer - 已移除，gemini-3-pro-image-preview 原生支援文字渲染
        
        for i, key in enumerate(stage_keys):
            img_bytes = result["images"].get(key)
            if img_bytes:
                # 直接使用 Imagen 生成的圖片（已包含文字）
                images[key] = ImageGenerator.bytes_to_base64(img_bytes)
                print(f"   ✅ {key} 圖像已就緒")
            else:
                failed_images.append(key)
        
        # 檢查是否有圖像生成成功
        if len(images) == 0:
            return jsonify({
                'success': False, 
                'error': '所有圖像生成失敗。請檢查 GEMINI_API_KEY 是否有效，以及網路連線狀態。',
                'failed_images': failed_images
            })
        
        return jsonify({
            'success': True,
            'images': images,
            'slides': result.get("slides", []),
            'failed_images': failed_images,
            'message': f'成功生成 {len(images)}/{len(result["images"])} 張圖像' + (f'（{len(failed_images)} 張失敗）' if failed_images else '')
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'圖像生成錯誤：{str(e)}'})


@app.route('/generate-single-image', methods=['POST'])
def generate_single_image():
    """
    生成單張視覺化圖像（推薦模式）
    
    ⚠️ 解決連線超時問題的最佳實踐：
    - 前端逐張請求，每張圖獨立連線
    - 每個請求只處理一張圖，避免長時間阻塞
    - 請求完成後立即返回，不累積記憶體
    
    Request JSON:
    {
        "report_id": "xxx",
        "stage_index": 0-3,  // 0=stage1, 1=stage2, 2=stage3, 3=combined
        "slide_data": {...}  // 可選，預先生成的 slide 數據
    }
    """
    try:
        data = request.get_json()
        report_id = data.get('report_id')
        stage_index = data.get('stage_index', 0)
        
        if not report_id:
            return jsonify({'success': False, 'error': '缺少報告編號'})
        
        # 讀取報告
        report_path = app.config['REPORTS_FOLDER'] / f"{report_id}.json"
        if not report_path.exists():
            return jsonify({'success': False, 'error': '找不到報告'})
        
        with open(report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        stage1 = report_data.get('stage1', {})
        stage2 = report_data.get('stage2', {})
        stage3 = report_data.get('stage3', {})
        
        stage_keys = ["stage1", "stage2", "stage3", "combined"]
        stage_key = stage_keys[stage_index] if stage_index < 4 else "stage1"
        
        print(f"\n📍[Single Image] 生成單張圖像：{stage_key} (index={stage_index})")
        
        # 初始化生成器
        generator = ImageGenerator()
        
        # 生成單張 slide 的 prompt
        slides = generator.visual_architect.generate_all_slides(stage1, stage2, stage3)
        
        if stage_index >= len(slides):
            return jsonify({'success': False, 'error': f'無效的 stage_index: {stage_index}'})
        
        slide = slides[stage_index]
        is_stage4 = (stage_index == 3)
        
        print(f"   📋 Slide: {slide.slide_title}")
        print(f"   🎯 Prompt 長度: {len(slide.image_prompt)} 字元")
        
        # 生成單張圖像
        image_bytes = generator.generate_image_from_prompt(
            slide.image_prompt,
            slide.stage_id,
            is_summary=is_stage4
        )
        
        # 儲存圖像
        image_folder = app.config['IMAGES_FOLDER'] / report_id
        image_folder.mkdir(exist_ok=True)
        
        if image_bytes:
            # gemini-3-pro-image-preview 原生支援文字渲染，無需 SlideComposer
            final_image_bytes = image_bytes
            
            output_path = image_folder / f"{stage_key}_visualization.png"
            with open(output_path, "wb") as f:
                f.write(final_image_bytes)
            print(f"   ✅ 生成成功！({len(final_image_bytes)} bytes)")
            
            return jsonify({
                'success': True,
                'stage_key': stage_key,
                'stage_index': stage_index,
                'image_base64': ImageGenerator.bytes_to_base64(final_image_bytes),
                'slide': slide.to_dict(),
                'message': f'{stage_key} 圖像生成成功'
            })
        else:
            print(f"   ❌ 生成失敗")
            return jsonify({
                'success': False,
                'stage_key': stage_key,
                'stage_index': stage_index,
                'error': f'{stage_key} 圖像生成失敗'
            })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'單張圖像生成錯誤：{str(e)}'})


@app.route('/prepare-slides', methods=['POST'])
def prepare_slides():
    """
    預先生成 Slide 結構（不生成圖像）
    
    這個端點快速返回 4 張 slide 的結構，
    讓前端可以先顯示佔位符，再逐張請求圖像。
    """
    try:
        data = request.get_json()
        report_id = data.get('report_id')
        
        if not report_id:
            return jsonify({'success': False, 'error': '缺少報告編號'})
        
        report_path = app.config['REPORTS_FOLDER'] / f"{report_id}.json"
        if not report_path.exists():
            return jsonify({'success': False, 'error': '找不到報告'})
        
        with open(report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        stage1 = report_data.get('stage1', {})
        stage2 = report_data.get('stage2', {})
        stage3 = report_data.get('stage3', {})
        
        # 只生成 slide 結構，不生成圖像
        from conflict_analyzer.visual_architect import VisualArchitect
        architect = VisualArchitect()
        slides = architect.generate_all_slides(stage1, stage2, stage3)
        
        slides_dict = [slide.to_dict() for slide in slides]
        
        return jsonify({
            'success': True,
            'slides': slides_dict,
            'total': len(slides_dict),
            'message': f'已準備 {len(slides_dict)} 張 Slide 結構'
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Slide 準備錯誤：{str(e)}'})

@app.route('/generate-audio', methods=['POST'])
def generate_audio():
    """生成療育音頻"""
    print("\n" + "=" * 60)
    print("🎵 [Audio API] 收到音頻生成請求")
    print("=" * 60)
    
    try:
        data = request.get_json()
        report_id = data.get('report_id')
        stage4_prompt = data.get('stage4_prompt', DEFAULT_STAGE4_PROMPT)
        voice = data.get('voice', 'warm_female')
        
        print(f"📍[Audio API] report_id: {report_id}")
        print(f"📍[Audio API] voice: {voice}")
        
        if not report_id:
            print("❌ [Audio API] 缺少 report_id")
            return jsonify({'success': False, 'error': '缺少報告編號'})
        
        # 讀取報告
        report_path = app.config['REPORTS_FOLDER'] / f"{report_id}.json"
        print(f"📍[Audio API] 報告路徑: {report_path}")
        
        if not report_path.exists():
            print(f"❌ [Audio API] 報告不存在: {report_path}")
            return jsonify({'success': False, 'error': '找不到報告'})
        
        with open(report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        stage1 = report_data.get('stage1', {})
        stage2 = report_data.get('stage2', {})
        stage3 = report_data.get('stage3', {})
        
        print(f"📍[Audio API] stage1 keys: {list(stage1.keys())[:5]}...")
        print(f"📍[Audio API] stage2 keys: {list(stage2.keys())[:5]}...")
        print(f"📍[Audio API] stage3 keys: {list(stage3.keys())[:5]}...")
        
        # 生成療育音頻
        print("📍[Audio API] 初始化 HealingAudioGenerator...")
        generator = HealingAudioGenerator()
        
        audio_folder = app.config['IMAGES_FOLDER'] / report_id
        audio_folder.mkdir(exist_ok=True)
        
        print("📍[Audio API] 開始生成療育音頻...")
        result = generator.generate_healing_audio(
            stage1_result=stage1,
            stage2_result=stage2,
            stage3_result=stage3,
            system_prompt=stage4_prompt,
            voice=voice,
            output_dir=audio_folder
        )
        
        return jsonify({
            'success': True,
            'audio_base64': result['audio_base64'],
            'duration_estimate': result['duration_estimate'],
            'voice': result['voice'],
            'parts_count': result.get('parts_count', 1),
            'bgm_status': result.get('bgm_status', {'success': False, 'method': 'unknown', 'error': None, 'voice_only': True}),
            'message': '療育音頻生成成功'
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'音頻生成錯誤：{str(e)}'})


@app.route('/generate-audio-stream', methods=['POST'])
def generate_audio_stream():
    """
    串流式生成療育音頻（SSE）
    每生成一個片段就立即推送給前端，實現邊生成邊播放
    """
    import base64
    from flask import Response, stream_with_context
    
    data = request.get_json()
    report_id = data.get('report_id')
    stage4_prompt = data.get('stage4_prompt', DEFAULT_STAGE4_PROMPT)
    voice = data.get('voice', 'warm_female')
    
    print("\n" + "=" * 60)
    print("🎵 [Audio Stream API] 串流音頻生成請求")
    print("=" * 60)
    
    def generate():
        try:
            # 驗證報告
            report_path = app.config['REPORTS_FOLDER'] / f"{report_id}.json"
            if not report_path.exists():
                yield f"data: {json.dumps({'type': 'error', 'message': '找不到報告'})}\n\n"
                return
            
            with open(report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            stage1 = report_data.get('stage1', {})
            stage2 = report_data.get('stage2', {})
            stage3 = report_data.get('stage3', {})
            
            # 初始化生成器
            generator = HealingAudioGenerator()
            
            # 1. 生成文稿
            yield f"data: {json.dumps({'type': 'status', 'message': '正在生成療育文稿...'})}\n\n"
            
            from conflict_analyzer.prompts import get_stage4_prompt
            from conflict_analyzer.healing_audio import split_script_by_parts
            
            script = generator.generate_healing_script(
                stage1, stage2, stage3, stage4_prompt
            )
            
            # 2. 拆分文稿
            parts = split_script_by_parts(script)
            total_parts = len(parts)
            
            yield f"data: {json.dumps({'type': 'info', 'total_parts': total_parts, 'message': f'文稿已拆分為 {total_parts} 個片段'})}\n\n"
            
            # 2.5 初始化串流 BGM 混合器
            from conflict_analyzer.healing_audio import StreamingBGMMixer
            yield f"data: {json.dumps({'type': 'status', 'message': '正在載入背景音樂...'})}\n\n"
            bgm_mixer = StreamingBGMMixer(stage2)
            
            if bgm_mixer.is_ready:
                yield f"data: {json.dumps({'type': 'bgm_loaded', 'bgm_file': bgm_mixer.bgm_path.name if bgm_mixer.bgm_path else None})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'bgm_warning', 'message': '無可用背景音樂，將輸出純語音'})}\n\n"
            
            # 3. 逐個生成並立即推送（邊生成邊播放，每片段都帶 BGM）
            import time as time_module
            audio_clips = []  # 收集所有片段
            failed_parts = []
            
            for i, (part_name, content) in enumerate(parts, 1):
                yield f"data: {json.dumps({'type': 'status', 'message': f'正在生成 {part_name} ({i}/{total_parts})...'})}\n\n"
                
                audio_data = None
                last_error = None
                
                # 額外重試機制（最多 20 次）
                for extra_retry in range(20):
                    try:
                        if extra_retry > 0:
                            yield f"data: {json.dumps({'type': 'status', 'message': f'{part_name} 重試中... (第 {extra_retry + 1}/20 次)'})}\n\n"
                            time_module.sleep(min(2 * extra_retry, 10))  # 最多等待 10 秒
                        
                        audio_data = generator.text_to_speech_single(content, voice, part_name)
                        break
                        
                    except Exception as e:
                        last_error = e
                        print(f"   ❌ {part_name} 第 {extra_retry + 1} 輪失敗: {e}")
                        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                            break
                
                if audio_data:
                    # 🎵 使用串流 BGM 混合器即時混合背景音樂
                    if bgm_mixer.is_ready:
                        mixed_audio = bgm_mixer.mix_segment(audio_data)
                        audio_base64 = base64.b64encode(mixed_audio).decode('utf-8')
                        print(f"   ✅ {part_name} + BGM 已推送到前端")
                    else:
                        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                        print(f"   ✅ {part_name} 已推送到前端（純語音）")
                    
                    audio_clips.append(audio_data)  # 保存原始音頻用於可能的後處理
                    
                    yield f"data: {json.dumps({'type': 'audio', 'part': i, 'total': total_parts, 'audio_base64': audio_base64, 'part_name': part_name, 'has_bgm': bgm_mixer.is_ready})}\n\n"
                else:
                    failed_parts.append({'part': part_name, 'error': str(last_error)})
                    yield f"data: {json.dumps({'type': 'part_error', 'part': i, 'error': str(last_error)})}\n\n"
            
            # 4. 嘗試混合 BGM
            if audio_clips and len(audio_clips) == total_parts:
                try:
                    yield f"data: {json.dumps({'type': 'status', 'message': '正在混合背景音樂...'})}\n\n"
                    stitched_audio = generator.stitch_audio_clips(audio_clips)
                    final_audio, bgm_status = generator._apply_bgm_mixing(stitched_audio, stage2)
                    
                    if bgm_status.get('success'):
                        final_base64 = base64.b64encode(final_audio).decode('utf-8')
                        yield f"data: {json.dumps({'type': 'complete_with_bgm', 'audio_base64': final_base64, 'bgm_method': bgm_status.get('method', 'unknown')})}\n\n"
                        print(f"   🎵 BGM 混合成功: {bgm_status.get('method')}")
                    else:
                        yield f"data: {json.dumps({'type': 'bgm_skipped', 'reason': bgm_status.get('error', '未知原因')})}\n\n"
                except Exception as bgm_error:
                    print(f"   ⚠️ BGM 混合失敗: {bgm_error}")
                    yield f"data: {json.dumps({'type': 'bgm_error', 'error': str(bgm_error)})}\n\n"
            
            # 5. 完成
            yield f"data: {json.dumps({'type': 'complete', 'message': '所有片段生成完成', 'success_count': len(audio_clips), 'fail_count': len(failed_parts)})}\n\n"
            
        except Exception as e:
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/download-pdf/<report_id>')
def download_pdf(report_id):
    """下載 PDF 報告"""
    try:
        # 讀取報告
        report_path = app.config['REPORTS_FOLDER'] / f"{report_id}.json"
        if not report_path.exists():
            return "報告不存在", 404
        
        with open(report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        # 從分析結果中提取事件主題
        event_topic = extract_event_topic(report_data)
        
        # 生成 PDF
        pdf_bytes = generate_pdf_report(report_data, report_id)
        
        # 返回 PDF 下載
        from io import BytesIO
        pdf_buffer = BytesIO(pdf_bytes)
        
        # 動態檔名
        safe_topic = sanitize_filename(event_topic) if event_topic else "衝突分析"
        download_filename = f"Lumina心語_{safe_topic}_{report_id[:8]}.pdf"
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=download_filename
        )
        
    except Exception as e:
        traceback.print_exc()
        return f"PDF 生成錯誤：{str(e)}", 500


@app.route('/download-pdf-with-images', methods=['POST'])
def download_pdf_with_images():
    """下載內嵌圖片的完整 PDF 報告"""
    try:
        data = request.get_json()
        report_id = data.get('report_id')
        images = data.get('images', [])  # 圖片 base64 陣列
        
        if not report_id:
            return jsonify({'success': False, 'error': '缺少報告編號'}), 400
        
        # 讀取報告資料
        report_path = app.config['REPORTS_FOLDER'] / f"{report_id}.json"
        if not report_path.exists():
            return jsonify({'success': False, 'error': '找不到報告'}), 404
        
        with open(report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        # 從分析結果中提取事件主題
        event_topic = extract_event_topic(report_data)
        
        # 生成內嵌圖片的 PDF
        pdf_bytes = generate_pdf_report(report_data, report_id, images=images)
        
        # 返回 PDF 下載
        from io import BytesIO
        pdf_buffer = BytesIO(pdf_bytes)
        
        # 動態檔名（完整版）
        safe_topic = sanitize_filename(event_topic) if event_topic else "衝突分析"
        download_filename = f"Lumina心語_{safe_topic}_完整版_{report_id[:8]}.pdf"
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=download_filename
        )
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'PDF 生成錯誤：{str(e)}'}), 500


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print(" Lumina 心語 - 四階段專業分析系統 v4.0")
    print("=" * 60)
    print(" 一階：衝突演化追蹤器")
    print(" 二階：深層溯源與接納橋樑")
    print(" 三階：個人成長行動方案")
    print(" 四階：數位催眠療癒")
    print("=" * 60)
    print(" 請在瀏覽器開啟：http://localhost:5000")
    print("=" * 60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

