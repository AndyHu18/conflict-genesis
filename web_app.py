#!/usr/bin/env python3
"""
衝突基因 - 網頁介面 v3.0
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

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'aiff', 'aac', 'ogg', 'flac', 'm4a'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>衝突基因 - 專業衝突分析報告</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0a12;
            --bg-secondary: #12121c;
            --bg-card: rgba(25, 25, 40, 0.9);
            --accent-gold: #d4af37;
            --accent-gold-light: #f4d03f;
            --accent-primary: #6366f1;
            --accent-secondary: #8b5cf6;
            --accent-danger: #ef4444;
            --accent-success: #22c55e;
            --accent-warning: #f59e0b;
            --accent-healing: #ec4899;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --border-color: rgba(212, 175, 55, 0.2);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Noto Sans TC', sans-serif; background: var(--bg-primary); color: var(--text-primary); min-height: 100vh; }
        .bg-animation { position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 0;
            background: radial-gradient(ellipse at 20% 20%, rgba(212, 175, 55, 0.05) 0%, transparent 50%),
                        radial-gradient(ellipse at 80% 80%, rgba(99, 102, 241, 0.05) 0%, transparent 50%); }
        .container { max-width: 1100px; margin: 0 auto; padding: 40px 20px; position: relative; z-index: 1; }
        header { text-align: center; margin-bottom: 50px; }
        .logo { font-size: 3.5rem; margin-bottom: 15px; background: linear-gradient(135deg, var(--accent-gold), var(--accent-gold-light)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; letter-spacing: 8px; }
        .tagline { color: var(--text-secondary); font-size: 1.2rem; font-weight: 300; letter-spacing: 2px; }
        .premium-badge { display: inline-flex; align-items: center; gap: 8px; margin-top: 20px; padding: 8px 20px; background: linear-gradient(135deg, rgba(212, 175, 55, 0.15), rgba(212, 175, 55, 0.05)); border: 1px solid var(--border-color); border-radius: 30px; font-size: 0.85rem; color: var(--accent-gold); }
        .card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 20px; padding: 35px; margin-bottom: 30px; backdrop-filter: blur(20px); }
        .card-header { display: flex; align-items: center; gap: 15px; margin-bottom: 25px; padding-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .card-icon { font-size: 1.8rem; }
        .card-title { font-size: 1.3rem; font-weight: 600; background: linear-gradient(135deg, var(--text-primary), var(--text-secondary)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .upload-zone { border: 2px dashed var(--border-color); border-radius: 16px; padding: 50px; text-align: center; cursor: pointer; transition: all 0.4s; background: linear-gradient(135deg, rgba(212, 175, 55, 0.02), rgba(99, 102, 241, 0.02)); }
        .upload-zone:hover, .upload-zone.dragover { border-color: var(--accent-gold); background: linear-gradient(135deg, rgba(212, 175, 55, 0.08), rgba(99, 102, 241, 0.05)); }
        .upload-zone input[type="file"] { display: none; }
        .upload-icon { font-size: 4rem; margin-bottom: 20px; opacity: 0.8; }
        .upload-text { color: var(--text-primary); font-size: 1.1rem; margin-bottom: 10px; }
        .upload-hint { color: var(--text-muted); font-size: 0.9rem; }
        .file-info { display: none; margin-top: 20px; padding: 18px; background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 12px; }
        .file-info.show { display: flex; align-items: center; gap: 12px; }
        .context-textarea { width: 100%; padding: 18px; min-height: 100px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 12px; color: var(--text-primary); font-size: 1rem; resize: vertical; }
        .context-textarea:focus { outline: none; border-color: var(--accent-gold); }
        .context-textarea::placeholder { color: var(--text-muted); }
        
        .advanced-toggle { display: flex; align-items: center; gap: 10px; padding: 12px 0; cursor: pointer; color: var(--text-muted); font-size: 0.85rem; user-select: none; }
        .advanced-toggle:hover { color: var(--text-secondary); }
        .advanced-toggle .arrow { transition: transform 0.3s; }
        .advanced-toggle.open .arrow { transform: rotate(90deg); }
        .advanced-content { display: none; margin-top: 15px; }
        .advanced-content.show { display: block; }
        .prompt-section { margin-bottom: 20px; padding: 20px; background: rgba(0,0,0,0.2); border-radius: 12px; }
        .prompt-label { color: var(--text-muted); font-size: 0.85rem; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }
        .stage-badge-1 { background: var(--accent-gold); color: #000; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
        .stage-badge-2 { background: var(--accent-healing); color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
        .stage-badge-3 { background: var(--accent-success); color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
        .stage-badge-4 { background: var(--accent-secondary); color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
        
        /* 底部固定療育音頻播放器 */
        .healing-player {
            position: fixed;
            bottom: -150px;
            left: 0;
            right: 0;
            background: linear-gradient(180deg, rgba(20,20,35,0.98), rgba(15,15,25,1));
            backdrop-filter: blur(20px);
            border-top: 2px solid var(--accent-secondary);
            padding: 20px 30px;
            z-index: 9999;
            transition: bottom 0.5s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 -10px 50px rgba(139, 92, 246, 0.3);
        }
        .healing-player.show { bottom: 0; }
        .healing-player-content {
            max-width: 900px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            gap: 25px;
        }
        .healing-player-icon {
            font-size: 3rem;
            animation: pulse-glow 2s ease-in-out infinite;
        }
        @keyframes pulse-glow {
            0%, 100% { transform: scale(1); filter: drop-shadow(0 0 10px rgba(139, 92, 246, 0.5)); }
            50% { transform: scale(1.1); filter: drop-shadow(0 0 20px rgba(139, 92, 246, 0.8)); }
        }
        .healing-player-info { flex: 1; }
        .healing-player-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 5px;
        }
        .healing-player-subtitle {
            font-size: 0.85rem;
            color: var(--accent-secondary);
        }
        .healing-play-btn {
            width: 70px;
            height: 70px;
            border-radius: 50%;
            border: none;
            background: linear-gradient(135deg, var(--accent-secondary), #6366f1);
            color: #fff;
            font-size: 2rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s;
            box-shadow: 0 5px 30px rgba(139, 92, 246, 0.5);
        }
        .healing-play-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 10px 50px rgba(139, 92, 246, 0.7);
        }
        .healing-close-btn {
            position: absolute;
            top: 10px;
            right: 15px;
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 1.2rem;
            cursor: pointer;
        }
        .healing-close-btn:hover { color: var(--text-primary); }
        .audio-progress {
            flex: 1;
            height: 6px;
            background: rgba(255,255,255,0.1);
            border-radius: 3px;
            overflow: hidden;
            cursor: pointer;
        }
        .audio-progress-bar {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, var(--accent-secondary), var(--accent-healing));
            transition: width 0.1s linear;
        }
        .prompt-textarea { width: 100%; min-height: 200px; padding: 15px; background: #0d0d15; border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; color: var(--text-secondary); font-family: monospace; font-size: 0.8rem; resize: vertical; }
        .prompt-textarea:focus { outline: none; border-color: var(--accent-primary); }
        .prompt-actions { display: flex; gap: 10px; margin-top: 10px; }
        .btn-small { padding: 8px 15px; font-size: 0.8rem; border-radius: 6px; border: 1px solid var(--border-color); background: transparent; color: var(--text-muted); cursor: pointer; transition: all 0.3s; }
        .btn-small:hover { border-color: var(--accent-gold); color: var(--accent-gold); }
        
        .btn-primary { width: 100%; padding: 18px 30px; font-size: 1.1rem; font-weight: 600; border: none; border-radius: 12px; cursor: pointer; transition: all 0.3s ease; background: linear-gradient(135deg, var(--accent-gold), #c09b30); color: #000; letter-spacing: 1px; display: flex; align-items: center; justify-content: center; gap: 10px; }
        .btn-primary:hover:not(:disabled) { transform: translateY(-3px); box-shadow: 0 15px 50px rgba(212, 175, 55, 0.4); }
        .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-download { padding: 12px 25px; font-size: 0.95rem; font-weight: 500; border: 1px solid var(--accent-gold); border-radius: 8px; background: transparent; color: var(--accent-gold); cursor: pointer; transition: all 0.3s; display: inline-flex; align-items: center; gap: 8px; }
        .btn-download:hover { background: var(--accent-gold); color: #000; }
        
        .loading-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 1000; background: rgba(10, 10, 18, 0.95); backdrop-filter: blur(10px); }
        .loading-overlay.show { display: flex; align-items: center; justify-content: center; }
        .loading-container { text-align: center; max-width: 500px; padding: 40px; }
        .particles { position: absolute; width: 100%; height: 100%; overflow: hidden; pointer-events: none; }
        .particle { position: absolute; width: 4px; height: 4px; background: var(--accent-gold); border-radius: 50%; animation: float 8s infinite ease-in-out; opacity: 0.6; }
        @keyframes float { 0%, 100% { transform: translateY(100vh); opacity: 0; } 10% { opacity: 0.8; } 90% { opacity: 0.8; } 100% { transform: translateY(-100vh); opacity: 0; } }
        .progress-ring-container { position: relative; width: 180px; height: 180px; margin: 0 auto 30px; }
        .progress-ring { transform: rotate(-90deg); }
        .progress-ring-bg { fill: none; stroke: rgba(255,255,255,0.1); stroke-width: 8; }
        .progress-ring-fill { fill: none; stroke: url(#goldGradient); stroke-width: 8; stroke-linecap: round; stroke-dasharray: 502; stroke-dashoffset: 502; transition: stroke-dashoffset 0.5s ease; }
        .progress-percent { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 2.5rem; font-weight: 700; background: linear-gradient(135deg, var(--accent-gold), var(--accent-gold-light)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .loading-title { font-size: 1.5rem; font-weight: 600; margin-bottom: 15px; }
        .loading-stage { font-size: 1rem; color: var(--accent-gold); margin-bottom: 25px; min-height: 25px; }
        .stage-list { text-align: left; padding: 20px; background: rgba(255,255,255,0.03); border-radius: 12px; }
        .stage-item { display: flex; align-items: center; gap: 12px; padding: 12px 0; color: var(--text-muted); border-bottom: 1px solid rgba(255,255,255,0.05); transition: color 0.3s; }
        .stage-item:last-child { border-bottom: none; }
        .stage-item.active { color: var(--accent-gold); }
        .stage-item.done { color: var(--accent-success); }
        .stage-icon { width: 24px; text-align: center; }
        
        .result-container { display: none; }
        .result-container.show { display: block; }
        
        .stage-tabs { display: flex; gap: 10px; margin-bottom: 30px; }
        .stage-tab { flex: 1; padding: 15px; border: 2px solid var(--border-color); border-radius: 12px; background: transparent; color: var(--text-secondary); cursor: pointer; transition: all 0.3s; font-size: 1rem; font-weight: 600; }
        .stage-tab.active { border-color: var(--accent-gold); background: rgba(212, 175, 55, 0.1); color: var(--accent-gold); }
        .stage-tab:hover:not(.active) { border-color: var(--text-muted); }
        .stage-content { display: none; }
        .stage-content.active { display: block; }
        
        .report-header { text-align: center; padding: 40px; background: linear-gradient(135deg, rgba(212, 175, 55, 0.1), rgba(99, 102, 241, 0.05)); border: 1px solid var(--border-color); border-radius: 20px; margin-bottom: 30px; }
        .report-title { font-size: 2rem; font-weight: 700; margin-bottom: 10px; background: linear-gradient(135deg, var(--accent-gold), var(--accent-gold-light)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .report-meta { color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 20px; }
        .report-summary { font-size: 1.3rem; font-style: italic; color: var(--text-primary); padding: 25px; background: rgba(0,0,0,0.3); border-radius: 12px; border-left: 4px solid var(--accent-gold); text-align: left; line-height: 1.8; }
        
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
        
        /* Stage 2 Styles */
        .stage2-header { text-align: center; padding: 40px; background: linear-gradient(135deg, rgba(236, 72, 153, 0.1), rgba(139, 92, 246, 0.05)); border: 1px solid rgba(236, 72, 153, 0.3); border-radius: 20px; margin-bottom: 30px; }
        .stage2-title { font-size: 2rem; font-weight: 700; margin-bottom: 10px; background: linear-gradient(135deg, var(--accent-healing), var(--accent-secondary)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        
        .iceberg-card { background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.05)); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 16px; padding: 25px; margin-bottom: 20px; }
        .iceberg-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
        .iceberg-section { margin-bottom: 15px; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 10px; }
        .iceberg-label { font-size: 0.75rem; color: var(--accent-primary); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        
        .healing-card { background: linear-gradient(135deg, rgba(236, 72, 153, 0.1), rgba(236, 72, 153, 0.02)); border: 1px solid rgba(236, 72, 153, 0.3); border-radius: 16px; padding: 25px; margin-bottom: 20px; }
        .healing-original { padding: 15px; background: rgba(239, 68, 68, 0.1); border-radius: 10px; margin-bottom: 15px; color: var(--accent-danger); }
        .healing-arrow { text-align: center; font-size: 1.5rem; margin: 10px 0; color: var(--accent-healing); }
        .healing-translation { padding: 15px; background: rgba(236, 72, 153, 0.1); border-radius: 10px; margin-bottom: 15px; color: var(--accent-healing); }
        .healing-response { padding: 15px; background: rgba(34, 197, 94, 0.1); border-radius: 10px; color: var(--accent-success); border-left: 3px solid var(--accent-success); }
        
        .action-card { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 16px; padding: 25px; margin-bottom: 20px; }
        .action-header { font-weight: 600; color: var(--accent-warning); margin-bottom: 15px; }
        .action-item { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 12px; padding: 12px; background: rgba(0,0,0,0.2); border-radius: 8px; }
        .action-icon { font-size: 1.2rem; }
        .action-label { font-size: 0.75rem; color: var(--text-muted); margin-bottom: 5px; }
        
        .healing-message { text-align: center; padding: 30px; background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(236, 72, 153, 0.1)); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 16px; margin-top: 30px; }
        .healing-message-text { font-size: 1.2rem; font-style: italic; line-height: 1.8; color: var(--text-primary); }
        
        /* Stage 3 Styles */
        .stage3-header { text-align: center; padding: 40px; background: linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(34, 197, 94, 0.05)); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 20px; margin-bottom: 30px; }
        .stage3-title { font-size: 2rem; font-weight: 700; margin-bottom: 10px; background: linear-gradient(135deg, var(--accent-success), #4ade80); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .growth-section { padding: 25px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 16px; margin-bottom: 20px; }
        .growth-title { font-size: 1.3rem; font-weight: 600; color: var(--accent-success); margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }
        .growth-item { padding: 20px; background: rgba(0,0,0,0.2); border-radius: 10px; margin-bottom: 15px; }
        .growth-item .text-content { font-size: 1.1rem; line-height: 1.9; }
        .growth-label { font-size: 0.9rem; color: var(--accent-success); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; font-weight: 600; }
        .prompt-list { list-style: none; padding: 0; }
        .prompt-list li { padding: 18px 20px; margin-bottom: 12px; background: rgba(34, 197, 94, 0.1); border-left: 4px solid var(--accent-success); border-radius: 0 12px 12px 0; font-size: 1.1rem; line-height: 1.7; }
        .closing-box { text-align: center; padding: 40px; background: linear-gradient(135deg, rgba(34, 197, 94, 0.15), rgba(99, 102, 241, 0.1)); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 16px; margin-top: 30px; }
        .closing-text { font-size: 1.3rem; font-style: italic; line-height: 1.9; color: var(--text-primary); }
        
        .download-section { display: flex; justify-content: center; gap: 20px; padding: 30px; margin-top: 30px; background: var(--bg-card); border-radius: 16px; border: 1px solid var(--border-color); }
        .error-box { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); padding: 25px; border-radius: 16px; color: #fca5a5; }
        footer { text-align: center; padding: 40px 20px; color: var(--text-muted); font-size: 0.85rem; border-top: 1px solid rgba(255,255,255,0.05); margin-top: 50px; }
        footer a { color: var(--accent-gold); text-decoration: none; }
        .text-content { line-height: 1.8; color: var(--text-secondary); }
    </style>
</head>
<body>
    <div class="bg-animation"></div>
    <div class="container">
        <header>
            <div class="logo">衝突基因</div>
            <p class="tagline">極致中立的衝突演化追蹤器</p>
            <div class="premium-badge">
                <span>👑</span><span>三階段專業分析</span><span>|</span><span>演化追蹤 + 深層溯源 + 成長方案</span>
            </div>
        </header>

        <div class="card" id="uploadCard">
            <div class="card-header"><span class="card-icon">🎙️</span><span class="card-title">上傳音訊檔案</span></div>
            <div class="upload-zone" id="uploadZone">
                <input type="file" id="audioFile" accept=".wav,.mp3,.aiff,.aac,.ogg,.flac,.m4a">
                <div class="upload-icon">📁</div>
                <div class="upload-text">點擊或拖放音訊檔案至此處</div>
                <div class="upload-hint">支援格式：WAV、MP3、AAC、FLAC、M4A</div>
            </div>
            <div class="file-info" id="fileInfo"><span>✅</span><span id="fileName"></span><span id="fileSize" style="color: var(--text-muted);"></span></div>
        </div>

        <div class="card">
            <div class="card-header"><span class="card-icon">💬</span><span class="card-title">情境說明（選填）</span></div>
            <textarea class="context-textarea" id="contextInput" placeholder="請描述對話雙方的關係，例如：&#10;• 這是一對夫妻關於家庭財務的討論&#10;• 這是主管與員工關於專案進度的對話"></textarea>
            
            <div class="advanced-toggle" onclick="toggleAdvanced()">
                <span class="arrow">▶</span>
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

        <button class="btn-primary" id="analyzeBtn" disabled><span>🔬</span><span>開始四階段專業分析</span></button>

        <div class="result-container" id="resultContainer">
            <div class="stage-tabs">
                <button class="stage-tab active" onclick="switchStage(1)">📊 一階：衝突演化</button>
                <button class="stage-tab" onclick="switchStage(2)">💡 二階：深層溯源</button>
                <button class="stage-tab" onclick="switchStage(3)">🌱 三階：成長方案</button>
                <button class="stage-tab" onclick="switchStage(4)">🎨 總結與圖像</button>
            </div>

            <!-- Stage 1 Content -->
            <div class="stage-content active" id="stage1Content">
                <div class="report-header">
                    <div class="report-title">📊 衝突演化分析報告</div>
                    <div class="report-meta">分析時間：<span id="reportTime"></span> | 報告編號：<span id="reportId"></span></div>
                    <div class="report-summary" id="overallDynamic"></div>
                </div>

                <div class="metrics-grid">
                    <div class="metric-card"><div class="metric-value" id="energyPattern"></div><div class="metric-label">能量變化模式</div></div>
                    <div class="metric-card"><div class="metric-value" id="phaseCount"></div><div class="metric-label">演化階段數</div></div>
                    <div class="metric-card"><div class="metric-value" id="intensityScore"></div><div class="metric-label">衝突烈度指數</div></div>
                </div>

                <div class="card"><div class="card-header"><span class="card-icon">📍</span><span class="card-title">衝突演化階段</span></div><div id="evolutionMap"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon">⚡</span><span class="card-title">關鍵轉折點</span></div><div id="turningPoints"></div></div>
                <div class="card">
                    <div class="card-header"><span class="card-icon">👁️</span><span class="card-title">雙方視角分析</span></div>
                    <div class="perspective-grid" id="dualPerspective"></div>
                    <div class="mismatch-box"><div class="mismatch-title">🔄 核心落差</div><div id="coreMismatch" class="text-content"></div></div>
                </div>
                <div class="card">
                    <div class="repair-section">
                        <div class="repair-title"><span>💡</span><span>修復嘗試分析</span></div>
                        <div id="repairAnalysis"></div>
                    </div>
                </div>
            </div>

            <!-- Stage 2 Content -->
            <div class="stage-content" id="stage2Content">
                <div class="stage2-header">
                    <div class="stage2-title">💡 深層溯源與接納橋樑</div>
                    <div class="report-meta">將行為轉化為未滿足的內心需求</div>
                    <div class="report-summary" id="deepInsight" style="border-left-color: var(--accent-healing);"></div>
                </div>

                <div class="card"><div class="card-header"><span class="card-icon">🧊</span><span class="card-title">冰山下方分析</span></div><div id="icebergAnalysis"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon">🔗</span><span class="card-title">依附動態 & 認知風格</span></div>
                    <div class="phase-card"><div class="phase-name">依附動態</div><div class="text-content" id="attachmentDynamic"></div></div>
                    <div class="phase-card"><div class="phase-name">認知風格差異</div><div class="text-content" id="cognitiveClash"></div></div>
                </div>
                <div class="card"><div class="card-header"><span class="card-icon">🔄</span><span class="card-title">視角轉換練習</span></div><div id="perspectiveShifts"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon">💕</span><span class="card-title">療癒性重構</span></div><div id="healingReframes"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon">🛠️</span><span class="card-title">可執行的微小改變</span></div><div id="actionableChanges"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon">⚖️</span><span class="card-title">共同責任重構</span></div><div class="text-content" id="sharedResponsibility"></div></div>
                <div class="healing-message"><div class="healing-message-text" id="healingMessage"></div></div>
            </div>

            <!-- Stage 3 Content -->
            <div class="stage-content" id="stage3Content">
                <div class="stage3-header">
                    <div class="stage3-title">🌱 個人成長行動方案</div>
                    <div class="report-meta">專注「我能做什麼」而非「如何讓對方改變」</div>
                    <div class="report-summary" id="positioning" style="border-left-color: var(--accent-success);"></div>
                </div>

                <div class="card"><div class="card-header"><span class="card-icon">💖</span><span class="card-title">我能做的修復</span></div><div id="repairSelfLed"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon">📝</span><span class="card-title">認識我的模式</span></div><div id="knowMyPatterns"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon">🧰</span><span class="card-title">我的調節工具箱</span></div><div id="myToolkit"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon">🚧</span><span class="card-title">替代路徑</span></div><div id="alternatives"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon">🛡️</span><span class="card-title">我的邊界與底線</span></div><div id="myBoundaries"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon">✨</span><span class="card-title">意義重構</span></div><div id="meaningMaking"></div></div>
                <div class="card"><div class="card-header"><span class="card-icon">❓</span><span class="card-title">反思提問</span></div><ul class="prompt-list" id="reflectionPrompts"></ul></div>
                <div class="closing-box"><div class="closing-text" id="closingMessage"></div></div>
            </div>

            <!-- Stage 4: Summary & Images -->
            <div class="stage-content" id="stage4Content">
                <div class="stage3-header" style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(99, 102, 241, 0.05)); border-color: rgba(139, 92, 246, 0.3);">
                    <div class="stage3-title" style="background: linear-gradient(135deg, #8b5cf6, #6366f1); -webkit-background-clip: text;">🎨 分析總結與視覺化</div>
                    <div class="report-meta">自動提取三階段核心洞見，生成視覺化圖像與催眠療癒音頻</div>
                </div>

                <!-- 生成進度區塊 -->
                <div class="card" id="generationProgressCard">
                    <div class="card-header"><span class="card-icon">⚙️</span><span class="card-title">自動生成進度</span></div>
                    <div style="padding: 20px;">
                        <!-- 圖片生成進度 -->
                        <div style="margin-bottom: 25px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <span style="color: var(--accent-gold); font-weight: 600;">🖼️ 視覺化圖像</span>
                                <span id="imageProgressText" style="color: var(--text-muted);">準備中...</span>
                            </div>
                            <div style="height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden;">
                                <div id="imageProgressBar" style="height: 100%; width: 0%; background: linear-gradient(90deg, var(--accent-gold), #f4d03f); transition: width 0.5s;"></div>
                            </div>
                        </div>
                        <!-- 音頻生成進度 -->
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <span style="color: var(--accent-secondary); font-weight: 600;">🎵 數位催眠療癒音頻（分段生成）</span>
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

                <!-- 視覺化簡報卡片展示區 (圖上文下，2x2 格子) -->
                <div id="generatedImagesContainer" style="display:none;">
                    <div class="card" style="background: transparent; padding: 0; border: none;">
                        <div class="card-header" style="padding: 20px 0;"><span class="card-icon">✨</span><span class="card-title">四大分析洞察</span></div>
                        
                        <!-- 2x2 Grid -->
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                            
                            <!-- Card 1: 衝突演化 -->
                            <div class="insight-card" id="slideCard1" style="background: linear-gradient(180deg, rgba(245,158,11,0.06), rgba(20,20,25,0.95)); border: 1px solid rgba(245,158,11,0.25); border-radius: 16px; overflow: hidden; transition: transform 0.3s, box-shadow 0.3s;">
                                <div style="position: relative;">
                                    <img id="imgStage1" style="width:100%; height:200px; object-fit:cover; display:block;" alt="Stage 1">
                                    <div style="position:absolute; top:12px; left:12px; background:rgba(245,158,11,0.9); color:#000; padding:4px 10px; border-radius:20px; font-size:0.75rem; font-weight:600;">STAGE 1</div>
                                </div>
                                <div style="padding: 20px;">
                                    <h3 id="slideTitle1" style="color: #F59E0B; font-size: 1.2rem; margin: 0 0 8px 0; font-weight: 700;">衝突演化</h3>
                                    <p id="slideInsight1" style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.5; margin: 0 0 12px 0; min-height: 40px;">每一場衝突都是一面鏡子。</p>
                                    <ul id="slideBullets1" style="list-style: none; padding: 0; margin: 0;">
                                        <li style="color: var(--text-muted); font-size: 0.85rem; padding: 5px 0; display: flex; align-items: flex-start;"><span style="color:#F59E0B; margin-right:8px;">•</span><span>載入中...</span></li>
                                    </ul>
                                </div>
                            </div>
                            
                            <!-- Card 2: 深層溯源 -->
                            <div class="insight-card" id="slideCard2" style="background: linear-gradient(180deg, rgba(8,145,178,0.06), rgba(20,20,25,0.95)); border: 1px solid rgba(8,145,178,0.25); border-radius: 16px; overflow: hidden; transition: transform 0.3s, box-shadow 0.3s;">
                                <div style="position: relative;">
                                    <img id="imgStage2" style="width:100%; height:200px; object-fit:cover; display:block;" alt="Stage 2">
                                    <div style="position:absolute; top:12px; left:12px; background:rgba(8,145,178,0.9); color:#fff; padding:4px 10px; border-radius:20px; font-size:0.75rem; font-weight:600;">STAGE 2</div>
                                </div>
                                <div style="padding: 20px;">
                                    <h3 id="slideTitle2" style="color: #0891B2; font-size: 1.2rem; margin: 0 0 8px 0; font-weight: 700;">深層溯源</h3>
                                    <p id="slideInsight2" style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.5; margin: 0 0 12px 0; min-height: 40px;">憤怒的表面之下，往往藏著最柔軟的渴望。</p>
                                    <ul id="slideBullets2" style="list-style: none; padding: 0; margin: 0;">
                                        <li style="color: var(--text-muted); font-size: 0.85rem; padding: 5px 0; display: flex; align-items: flex-start;"><span style="color:#0891B2; margin-right:8px;">•</span><span>載入中...</span></li>
                                    </ul>
                                </div>
                            </div>
                            
                            <!-- Card 3: 成長方案 -->
                            <div class="insight-card" id="slideCard3" style="background: linear-gradient(180deg, rgba(34,197,94,0.06), rgba(20,20,25,0.95)); border: 1px solid rgba(34,197,94,0.25); border-radius: 16px; overflow: hidden; transition: transform 0.3s, box-shadow 0.3s;">
                                <div style="position: relative;">
                                    <img id="imgStage3" style="width:100%; height:200px; object-fit:cover; display:block;" alt="Stage 3">
                                    <div style="position:absolute; top:12px; left:12px; background:rgba(34,197,94,0.9); color:#000; padding:4px 10px; border-radius:20px; font-size:0.75rem; font-weight:600;">STAGE 3</div>
                                </div>
                                <div style="padding: 20px;">
                                    <h3 id="slideTitle3" style="color: #22C55E; font-size: 1.2rem; margin: 0 0 8px 0; font-weight: 700;">成長方案</h3>
                                    <p id="slideInsight3" style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.5; margin: 0 0 12px 0; min-height: 40px;">改變不是背叛自己，而是給自己更多選擇。</p>
                                    <ul id="slideBullets3" style="list-style: none; padding: 0; margin: 0;">
                                        <li style="color: var(--text-muted); font-size: 0.85rem; padding: 5px 0; display: flex; align-items: flex-start;"><span style="color:#22C55E; margin-right:8px;">•</span><span>載入中...</span></li>
                                    </ul>
                                </div>
                            </div>
                            
                            <!-- Card 4: 療癒旅程 -->
                            <div class="insight-card" id="slideCard4" style="background: linear-gradient(180deg, rgba(236,72,153,0.06), rgba(20,20,25,0.95)); border: 1px solid rgba(236,72,153,0.25); border-radius: 16px; overflow: hidden; transition: transform 0.3s, box-shadow 0.3s;">
                                <div style="position: relative;">
                                    <img id="imgCombined" style="width:100%; height:200px; object-fit:cover; display:block;" alt="Combined">
                                    <div style="position:absolute; top:12px; left:12px; background:rgba(236,72,153,0.9); color:#fff; padding:4px 10px; border-radius:20px; font-size:0.75rem; font-weight:600;">STAGE 4</div>
                                </div>
                                <div style="padding: 20px;">
                                    <h3 id="slideTitle4" style="color: #EC4899; font-size: 1.2rem; margin: 0 0 8px 0; font-weight: 700;">療癒旅程</h3>
                                    <p id="slideInsight4" style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.5; margin: 0 0 12px 0; min-height: 40px;">修復不是回到從前，而是創造更美好的未來。</p>
                                    <ul id="slideBullets4" style="list-style: none; padding: 0; margin: 0;">
                                        <li style="color: var(--text-muted); font-size: 0.85rem; padding: 5px 0; display: flex; align-items: flex-start;"><span style="color:#EC4899; margin-right:8px;">•</span><span>載入中...</span></li>
                                    </ul>
                                </div>
                            </div>
                            
                        </div>
                    </div>
                </div>

                <!-- 音頻就緒提示 -->
                <div class="card" id="audioReadyCard" style="display:none;">
                    <div class="card-header"><span class="card-icon">🎵</span><span class="card-title">數位催眠療癒音頻已就緒</span></div>
                    <div style="padding: 20px; text-align: center;">
                        <p style="color: var(--accent-secondary); font-size: 1.1rem; margin-bottom: 15px;">✨ 您的專屬療癒音頻已準備完成</p>
                        <p style="color: var(--text-muted);">點擊下方巨型按鈕開始您的療癒之旅</p>
                    </div>
                </div>
            </div>

            <div class="download-section" style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
                <button class="btn-download" onclick="downloadPDF()" style="background: linear-gradient(135deg, var(--accent-gold), #c09b30); color: #000; border: none;">
                    <span>📑</span><span>下載 PDF 報告</span>
                </button>
                <button class="btn-download" onclick="downloadJSON()"><span>📄</span><span>下載 JSON 數據</span></button>
            </div>
        </div>

        <div class="card" id="errorCard" style="display: none;"><div class="error-box"><strong>❌ 分析失敗</strong><p id="errorMessage" style="margin-top: 15px;"></p></div></div>

        <footer>
            <p>衝突基因 © 2024 | 四階段分析：演化追蹤 + 深層溯源 + 成長方案 + 數位催眠療癒</p>
            <p style="margin-top: 10px;">本報告由先進原生心靈引擎驅動生成</p>
        </footer>
    </div>

    <!-- 底部固定巨型療育音頻播放器 (心跳脈動效果) -->
    <div class="healing-player" id="healingPlayer">
        <button class="healing-close-btn" onclick="closeHealingPlayer()">✕</button>
        <div class="healing-player-content">
            <div class="healing-player-icon" style="animation: pulse-glow 2s ease-in-out infinite;">🎵</div>
            <div class="healing-player-info">
                <div class="healing-player-title">✨ 開始您的專屬療癒引導</div>
                <div class="healing-player-subtitle">閉上眼睛，讓艾瑞克森式催眠帶您進入深度放鬆</div>
                <div class="audio-progress" onclick="seekAudio(event)">
                    <div class="audio-progress-bar" id="audioProgressBar"></div>
                </div>
            </div>
            <button class="healing-play-btn" id="healingPlayBtn" onclick="toggleHealingAudio()" style="width: 80px; height: 80px; font-size: 2rem; background: linear-gradient(135deg, var(--accent-healing), #d946a8); box-shadow: 0 0 30px rgba(236,72,153,0.6); animation: pulse-button 1.5s ease-in-out infinite;">▶</button>
        </div>
        <audio id="healingAudio" style="display:none;"></audio>
    </div>

    <style>
        @keyframes pulse-glow {
            0%, 100% { transform: scale(1); filter: brightness(1); }
            50% { transform: scale(1.1); filter: brightness(1.3); }
        }
        @keyframes pulse-button {
            0%, 100% { box-shadow: 0 0 20px rgba(236,72,153,0.4); }
            50% { box-shadow: 0 0 40px rgba(236,72,153,0.8), 0 0 60px rgba(236,72,153,0.4); }
        }
    </style>

    <div class="loading-overlay" id="loadingOverlay">
        <div class="particles" id="particles"></div>
        <div class="loading-container">
            <div class="progress-ring-container">
                <svg class="progress-ring" width="180" height="180">
                    <defs><linearGradient id="goldGradient" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#d4af37"/><stop offset="100%" style="stop-color:#f4d03f"/></linearGradient></defs>
                    <circle class="progress-ring-bg" cx="90" cy="90" r="80"></circle>
                    <circle class="progress-ring-fill" id="progressRing" cx="90" cy="90" r="80"></circle>
                </svg>
                <div class="progress-percent" id="progressPercent">0%</div>
            </div>
            <div class="loading-title" id="loadingTitle">正在深度分析中...</div>
            <div class="loading-stage" id="loadingStage">準備分析環境</div>
            <div class="stage-list">
                <div class="stage-item" id="s1"><span class="stage-icon">⏳</span>上傳音訊檔案</div>
                <div class="stage-item" id="s2"><span class="stage-icon">⏳</span>一階：建立聲學基線</div>
                <div class="stage-item" id="s3"><span class="stage-icon">⏳</span>一階：追蹤演化軌跡</div>
                <div class="stage-item" id="s4"><span class="stage-icon">⏳</span>一階：識別轉折點</div>
                <div class="stage-item" id="s5"><span class="stage-icon">⏳</span>二階：冰山下方溯源</div>
                <div class="stage-item" id="s6"><span class="stage-icon">⏳</span>二階：療癒橋樑建構</div>
                <div class="stage-item" id="s7"><span class="stage-icon">⏳</span>三階：個人成長行動方案</div>
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
        }

        function createParticles() {
            const c = document.getElementById('particles');
            for (let i = 0; i < 30; i++) { const p = document.createElement('div'); p.className = 'particle'; p.style.left = Math.random() * 100 + '%'; p.style.animationDelay = Math.random() * 8 + 's'; p.style.animationDuration = (5 + Math.random() * 5) + 's'; c.appendChild(p); }
        }
        createParticles();

        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('audioFile');
        const analyzeBtn = document.getElementById('analyzeBtn');
        uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('dragover'); });
        uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
        uploadZone.addEventListener('drop', e => { e.preventDefault(); uploadZone.classList.remove('dragover'); if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]); });
        uploadZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', e => { if (e.target.files.length > 0) handleFile(e.target.files[0]); });
        function handleFile(file) { selectedFile = file; document.getElementById('fileName').textContent = file.name; document.getElementById('fileSize').textContent = `(${(file.size / 1048576).toFixed(1)} MB)`; document.getElementById('fileInfo').classList.add('show'); analyzeBtn.disabled = false; }

        let progressInterval;
        function startProgress() {
            let progress = 0;
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
                if (idx < stages.length && progress >= stages[idx].pct) {
                    document.getElementById('loadingStage').textContent = stages[idx].text;
                    if (idx >= 4 && idx < 6) document.getElementById('loadingTitle').textContent = '正在深層溯源...';
                    if (idx >= 6) document.getElementById('loadingTitle').textContent = '正在建構成長方案...';
                    const el = document.getElementById(stages[idx].id);
                    el.classList.add('active'); el.querySelector('.stage-icon').textContent = '🔄';
                    if (idx > 0) { const prev = document.getElementById(stages[idx - 1].id); prev.classList.remove('active'); prev.classList.add('done'); prev.querySelector('.stage-icon').textContent = '✅'; }
                    idx++;
                }
            }, 100);
        }
        function stopProgress() {
            clearInterval(progressInterval);
            document.getElementById('progressPercent').textContent = '100%';
            document.getElementById('progressRing').style.strokeDashoffset = 0;
            document.querySelectorAll('.stage-item').forEach(el => { el.classList.remove('active'); el.classList.add('done'); el.querySelector('.stage-icon').textContent = '✅'; });
        }

        analyzeBtn.addEventListener('click', async () => {
            if (!selectedFile) return;
            document.getElementById('resultContainer').classList.remove('show');
            document.getElementById('errorCard').style.display = 'none';
            document.getElementById('loadingOverlay').classList.add('show');
            document.getElementById('loadingTitle').textContent = '正在深度分析中...';
            analyzeBtn.disabled = true;
            document.querySelectorAll('.stage-item').forEach(el => { el.classList.remove('active', 'done'); el.querySelector('.stage-icon').textContent = '⏳'; });
            document.getElementById('progressRing').style.strokeDashoffset = 502;
            document.getElementById('progressPercent').textContent = '0%';
            startProgress();

            const formData = new FormData();
            formData.append('audio', selectedFile);
            formData.append('context', document.getElementById('contextInput').value);
            formData.append('stage1_prompt', document.getElementById('stage1Prompt').value);
            formData.append('stage2_prompt', document.getElementById('stage2Prompt').value);
            formData.append('stage3_prompt', document.getElementById('stage3Prompt').value);

            try {
                const resp = await fetch('/analyze', { method: 'POST', body: formData });
                const data = await resp.json();
                stopProgress();
                setTimeout(() => {
                    document.getElementById('loadingOverlay').classList.remove('show');
                    if (data.success) { fullResult = data.result; displayResult(data.result, data.report_id); }
                    else showError(data.error);
                }, 800);
            } catch (err) { stopProgress(); document.getElementById('loadingOverlay').classList.remove('show'); showError('網路錯誤：' + err.message); }
            finally { analyzeBtn.disabled = false; }
        });

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
            if (s1.evolution_map) s1.evolution_map.forEach((p, i) => { evo.innerHTML += `<div class="phase-card"><div class="phase-header"><div class="phase-name">階段 ${i + 1}：${p.phase}</div></div><div class="phase-desc">${p.description}</div><div class="contribution-grid"><div class="contribution-box"><div class="contribution-label">A 的貢獻</div><div class="text-content">${p.speaker_a_contribution}</div></div><div class="contribution-box"><div class="contribution-label">B 的貢獻</div><div class="text-content">${p.speaker_b_contribution}</div></div></div><div style="margin-top:15px;padding:12px;background:rgba(99,102,241,0.1);border-radius:8px;"><strong style="color:var(--accent-primary);">🔑 關鍵觀察：</strong> ${p.key_observation}</div></div>`; });

            const tp = document.getElementById('turningPoints'); tp.innerHTML = '';
            if (s1.turning_points) s1.turning_points.forEach(t => { tp.innerHTML += `<div class="turning-point"><div class="turning-moment">⚡ ${t.moment}</div><div class="turning-why"><strong>為什麼關鍵：</strong> ${t.why_critical}</div><div class="turning-alt"><strong>💡 錯失的替代：</strong> ${t.missed_alternative}</div></div>`; });

            if (s1.dual_perspective) { document.getElementById('dualPerspective').innerHTML = `<div class="perspective-box"><div class="perspective-header"><div class="speaker-avatar">A</div><div style="font-weight:600;">A 的體驗</div></div><div class="text-content">${s1.dual_perspective.speaker_a_experience}</div></div><div class="perspective-box"><div class="perspective-header"><div class="speaker-avatar">B</div><div style="font-weight:600;">B 的體驗</div></div><div class="text-content">${s1.dual_perspective.speaker_b_experience}</div></div>`; document.getElementById('coreMismatch').textContent = s1.dual_perspective.core_mismatch; }

            if (s1.repair_analysis) document.getElementById('repairAnalysis').innerHTML = `<div class="repair-item"><div class="repair-label">修復嘗試</div><div class="text-content">${s1.repair_analysis.attempts}</div></div><div class="repair-item"><div class="repair-label">回應方式</div><div class="text-content">${s1.repair_analysis.responses}</div></div><div class="repair-item"><div class="repair-label">錯失機會</div><div class="text-content">${s1.repair_analysis.missed_opportunities}</div></div>`;

            // Stage 2
            document.getElementById('deepInsight').textContent = s2.deep_insight_summary;

            const ice = document.getElementById('icebergAnalysis'); ice.innerHTML = '';
            if (s2.iceberg_analysis) s2.iceberg_analysis.forEach(i => { ice.innerHTML += `<div class="iceberg-card"><div class="iceberg-header"><div class="speaker-avatar">${i.speaker_id}</div><div style="font-weight:600;">說話者 ${i.speaker_id}</div></div><div class="iceberg-section"><div class="iceberg-label">表面行為</div><div>${i.surface_behavior}</div></div><div class="iceberg-section"><div class="iceberg-label">深層恐懼</div><div>${i.underlying_fear}</div></div><div class="iceberg-section"><div class="iceberg-label">深層渴望</div><div>${i.underlying_desire}</div></div><div class="iceberg-section"><div class="iceberg-label">未滿足的需求</div><div>${i.unmet_need}</div></div><div class="iceberg-section"><div class="iceberg-label">可能的觸發來源</div><div>${i.possible_trigger}</div></div></div>`; });

            document.getElementById('attachmentDynamic').textContent = s2.attachment_dynamic;
            document.getElementById('cognitiveClash').textContent = s2.cognitive_style_clash;

            const ps = document.getElementById('perspectiveShifts'); ps.innerHTML = '';
            if (s2.perspective_shifts) s2.perspective_shifts.forEach(p => { ps.innerHTML += `<div class="phase-card"><div class="phase-name">給 ${p.for_speaker} 的練習</div><div style="padding:15px;background:rgba(139,92,246,0.1);border-radius:10px;margin-bottom:10px;"><strong>🤔 ${p.prompt}</strong></div><div class="text-content">${p.insight}</div></div>`; });

            const hr = document.getElementById('healingReframes'); hr.innerHTML = '';
            if (s2.healing_reframes) s2.healing_reframes.forEach(h => { hr.innerHTML += `<div class="healing-card"><div class="healing-original">❌ ${h.original_statement}</div><div class="healing-arrow">↓ 翻譯成 ↓</div><div class="healing-translation">💕 ${h.vulnerable_translation}</div><div class="healing-response">✅ 對方可以這樣回應：${h.compassionate_response}</div></div>`; });

            const ac = document.getElementById('actionableChanges'); ac.innerHTML = '';
            if (s2.actionable_changes) s2.actionable_changes.forEach(a => { ac.innerHTML += `<div class="action-card"><div class="action-header">給 ${a.for_speaker} 的建議</div><div class="action-item"><span class="action-icon">🎯</span><div><div class="action-label">觸發情境</div><div>${a.trigger_situation}</div></div></div><div class="action-item"><span class="action-icon">❌</span><div><div class="action-label">舊模式</div><div>${a.old_pattern}</div></div></div><div class="action-item"><span class="action-icon">✅</span><div><div class="action-label">新做法</div><div>${a.new_approach}</div></div></div><div class="action-item" style="background:rgba(34,197,94,0.1);"><span class="action-icon">🛑</span><div><div class="action-label">降溫用語</div><div style="color:var(--accent-success);font-weight:600;">${a.cooling_phrase}</div></div></div></div>`; });

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
                <div class="growth-item" style="background:rgba(34,197,94,0.15);"><div class="growth-label">🧪 這週的微小實驗</div><div class="text-content" style="font-weight:600;">${alt.micro_experiment}</div></div>`;

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
                <div class="growth-item" style="background:rgba(34,197,94,0.15);"><div class="growth-label">💌 送給自己的話</div><div class="text-content" style="font-style:italic;">${mm.message_to_self}</div></div>`;

            // 反思提問
            const rp = document.getElementById('reflectionPrompts');
            rp.innerHTML = '';
            if (s3.reflection_prompts) s3.reflection_prompts.forEach(q => { rp.innerHTML += `<li>🤔 ${q}</li>`; });

            // 結語
            document.getElementById('closingMessage').textContent = s3.closing;

            document.getElementById('resultContainer').classList.add('show');
            switchStage(1);
            document.getElementById('resultContainer').scrollIntoView({ behavior: 'smooth' });
            
            // 分析完成後自動開始生成療育音頻
            onAnalysisComplete();
        }

        function showError(msg) { document.getElementById('errorMessage').textContent = msg; document.getElementById('errorCard').style.display = 'block'; }
        function downloadJSON() { if (!fullResult) return; const blob = new Blob([JSON.stringify(fullResult, null, 2)], { type: 'application/json' }); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `衝突分析報告_${new Date().toISOString().slice(0, 10)}.json`; a.click(); }
        function downloadPDF() { 
            if (!currentReportId) { alert('請先完成分析'); return; } 
            window.open(`/download-pdf/${currentReportId}`, '_blank'); 
        }
        
        let currentReportId = null;
        
        // 自動生成圖片（帶進度）- 整合 VisualArchitect 簡報
        async function generateImagesAuto() {
            if (!currentReportId) return;
            
            const progressBar = document.getElementById('imageProgressBar');
            const progressText = document.getElementById('imageProgressText');
            const container = document.getElementById('generatedImagesContainer');
            
            progressText.textContent = '🎨 VisualArchitect 正在設計簡報...';
            progressBar.style.width = '10%';
            
            // 模擬進度
            let progress = 10;
            const progressSteps = [
                { pct: 20, text: '🎨 VisualArchitect 分析中...' },
                { pct: 35, text: '📊 設計 Stage 1 簡報...' },
                { pct: 50, text: '💡 設計 Stage 2 簡報...' },
                { pct: 65, text: '🌱 設計 Stage 3 簡報...' },
                { pct: 80, text: '🎵 渲染高質量圖像...' },
            ];
            let stepIdx = 0;
            
            const progressInterval = setInterval(() => {
                if (stepIdx < progressSteps.length && progress >= progressSteps[stepIdx].pct - 5) {
                    progressText.textContent = progressSteps[stepIdx].text;
                    stepIdx++;
                }
                if (progress < 85) {
                    progress += Math.random() * 3;
                    progressBar.style.width = Math.min(progress, 85) + '%';
                }
            }, 800);
            
            try {
                const resp = await fetch('/generate-images', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ report_id: currentReportId })
                });
                
                const data = await resp.json();
                clearInterval(progressInterval);
                
                if (data.success && data.images) {
                    progressBar.style.width = '100%';
                    progressText.textContent = '✅ 視覺化簡報生成完成！';
                    
                    // 顯示圖片
                    if (data.images.stage1) document.getElementById('imgStage1').src = 'data:image/png;base64,' + data.images.stage1;
                    if (data.images.stage2) document.getElementById('imgStage2').src = 'data:image/png;base64,' + data.images.stage2;
                    if (data.images.stage3) document.getElementById('imgStage3').src = 'data:image/png;base64,' + data.images.stage3;
                    if (data.images.combined) document.getElementById('imgCombined').src = 'data:image/png;base64,' + data.images.combined;
                    
                    // 填充簡報卡片數據（如果有 slides 數據）
                    if (data.slides && data.slides.length > 0) {
                        const stageKeys = ['1', '2', '3', '4'];
                        const stageColors = ['#F59E0B', '#0891B2', '#22C55E', '#EC4899'];
                        
                        data.slides.forEach((slide, i) => {
                            const num = stageKeys[i];
                            const color = stageColors[i];
                            
                            // 更新標題
                            const titleEl = document.getElementById('slideTitle' + num);
                            if (titleEl && slide.slide_title) titleEl.textContent = slide.slide_title;
                            
                            // 更新引言
                            const insightEl = document.getElementById('slideInsight' + num);
                            if (insightEl && slide.core_insight) insightEl.textContent = slide.core_insight;
                            
                            // 更新要點列表（新的格式）
                            const bulletsEl = document.getElementById('slideBullets' + num);
                            if (bulletsEl && slide.data_bullets && slide.data_bullets.length > 0) {
                                bulletsEl.innerHTML = slide.data_bullets.map(bullet => 
                                    `<li style="color: var(--text-muted); font-size: 0.85rem; padding: 5px 0; display: flex; align-items: flex-start;">
                                        <span style="color:${color}; margin-right:8px;">•</span>
                                        <span>${bullet}</span>
                                    </li>`
                                ).join('');
                            }
                        });
                    }
                    
                    container.style.display = 'block';
                    return true;
                } else {
                    progressText.textContent = '❌ 圖像生成失敗';
                    console.error('圖像生成失敗:', data.error);
                    return false;
                }
            } catch (err) {
                clearInterval(progressInterval);
                progressText.textContent = '❌ 網路錯誤';
                console.error('圖像生成錯誤:', err);
                return false;
            }
        }
        
        // 療育音頻播放器功能
        let healingAudioReady = false;
        
        // 自動生成音頻（帶進度）
        async function generateHealingAudioAuto() {
            if (!currentReportId) return false;
            
            const progressBar = document.getElementById('audioGenProgressBar');
            const progressText = document.getElementById('audioProgressText');
            const audioReadyCard = document.getElementById('audioReadyCard');
            const partsProgress = document.getElementById('audioPartsProgress');
            
            progressText.textContent = '正在生成分段療癒腳本...';
            progressBar.style.width = '5%';
            partsProgress.style.display = 'block';
            partsProgress.textContent = '📝 正在生成療育文稿...';
            
            // 分段進度模擬
            let progress = 5;
            const progressSteps = [
                { pct: 15, text: '📝 正在生成療育文稿...' },
                { pct: 25, text: '✂️ 拆分文稿為多個片段...' },
                { pct: 40, text: '🎙️ 正在生成 PART_1 音頻...' },
                { pct: 55, text: '🎙️ 正在生成 PART_2 音頻...' },
                { pct: 65, text: '🎙️ 正在生成 PART_3 音頻...' },
                { pct: 75, text: '🎙️ 正在生成更多片段...' },
                { pct: 85, text: '🧵 正在編織您的專屬療癒能量...' },
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
                
                const data = await resp.json();
                clearInterval(progressInterval);
                
                if (data.success && data.audio_base64) {
                    progressBar.style.width = '100%';
                    progressText.textContent = '✅ 音頻生成完成！';
                    partsProgress.textContent = `🎵 已成功串接 ${data.parts_count || 6} 個音頻片段`;
                    
                    // 設置音頻
                    const audio = document.getElementById('healingAudio');
                    audio.src = 'data:audio/wav;base64,' + data.audio_base64;
                    
                    // 設置進度條更新
                    audio.addEventListener('timeupdate', updateAudioProgress);
                    audio.addEventListener('ended', onAudioEnded);
                    
                    healingAudioReady = true;
                    
                    // 顯示就緒卡片
                    audioReadyCard.style.display = 'block';
                    
                    // 彈出播放器
                    document.getElementById('healingPlayer').classList.add('show');
                    
                    return true;
                } else {
                    progressText.textContent = '❌ 音頻生成失敗';
                    console.error('音頻生成失敗:', data.error);
                    return false;
                }
            } catch (err) {
                clearInterval(progressInterval);
                progressText.textContent = '❌ 網路錯誤';
                console.error('音頻生成錯誤:', err);
                return false;
            }
        }
        
        function updateAudioProgress() {
            const audio = document.getElementById('healingAudio');
            if (audio.duration) {
                const progress = (audio.currentTime / audio.duration) * 100;
                document.getElementById('audioProgressBar').style.width = progress + '%';
            }
        }
        
        function onAudioEnded() {
            document.getElementById('healingPlayBtn').textContent = '▶';
            document.getElementById('audioProgressBar').style.width = '0%';
        }
        
        function toggleHealingAudio() {
            const audio = document.getElementById('healingAudio');
            const btn = document.getElementById('healingPlayBtn');
            
            if (!healingAudioReady) {
                btn.textContent = '⏳';
                return;
            }
            
            if (audio.paused) {
                audio.play();
                btn.textContent = '⏸';
            } else {
                audio.pause();
                btn.textContent = '▶';
            }
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
            document.getElementById('healingPlayBtn').textContent = '▶';
        }
        
        // 三階分析完成後自動**並行**生成圖片和音頻
        async function onAnalysisComplete() {
            // 重置進度
            document.getElementById('imageProgressBar').style.width = '0%';
            document.getElementById('audioGenProgressBar').style.width = '0%';
            document.getElementById('imageProgressText').textContent = '準備中...';
            document.getElementById('audioProgressText').textContent = '準備中...';
            document.getElementById('generatedImagesContainer').style.display = 'none';
            document.getElementById('audioReadyCard').style.display = 'none';
            
            // 並行生成圖片和音頻（不互相等待）
            console.log('📍 開始並行生成圖像和音頻...');
            
            const [imageResult, audioResult] = await Promise.all([
                generateImagesAuto(),
                generateHealingAudioAuto()
            ]);
            
            console.log('📍 所有自動生成完成！', { imageResult, audioResult });
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


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


@app.route('/generate-images', methods=['POST'])
def generate_images():
    """生成四張視覺化圖像"""
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
        
        # 轉換圖像為 base64
        images = {}
        for key, img_bytes in result["images"].items():
            if img_bytes:
                images[key] = ImageGenerator.bytes_to_base64(img_bytes)
        
        return jsonify({
            'success': True,
            'images': images,
            'slides': result.get("slides", []),  # 返回簡報數據
            'message': f'成功生成 {len(images)} 張高質量圖像'
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'圖像生成錯誤：{str(e)}'})


@app.route('/generate-audio', methods=['POST'])
def generate_audio():
    """生成療育音頻"""
    try:
        data = request.get_json()
        report_id = data.get('report_id')
        stage4_prompt = data.get('stage4_prompt', DEFAULT_STAGE4_PROMPT)
        voice = data.get('voice', 'warm_female')
        
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
        
        # 生成療育音頻
        generator = HealingAudioGenerator()
        
        audio_folder = app.config['IMAGES_FOLDER'] / report_id
        audio_folder.mkdir(exist_ok=True)
        
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
            'message': '療育音頻生成成功'
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'音頻生成錯誤：{str(e)}'})


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
        
        # 生成 PDF
        pdf_bytes = generate_pdf_report(report_data, report_id)
        
        # 返回 PDF 下載
        from io import BytesIO
        pdf_buffer = BytesIO(pdf_bytes)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"衝突分析報告_{report_id}.pdf"
        )
        
    except Exception as e:
        traceback.print_exc()
        return f"PDF 生成錯誤：{str(e)}", 500


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("👑 衝突基因 - 四階段專業分析系統 v4.0")
    print("=" * 60)
    print("🔬 一階：衝突演化追蹤器")
    print("💡 二階：深層溯源與接納橋樑")
    print("🌱 三階：個人成長行動方案")
    print("🎵 四階：數位催眠療癒")
    print("=" * 60)
    print("🌐 請在瀏覽器開啟：http://localhost:5000")
    print("=" * 60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

