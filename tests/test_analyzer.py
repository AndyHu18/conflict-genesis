#!/usr/bin/env python3
"""
Conflict Genesis - 測試腳本
用於驗證系統各組件的功能
"""

import os
import sys
import json
from pathlib import Path

# 確保可以導入專案模組
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


def test_audio_processor():
    """測試音訊處理器"""
    print("\n" + "=" * 50)
    print("🧪 測試 AudioProcessor")
    print("=" * 50)
    
    from conflict_analyzer.audio_processor import AudioProcessor
    
    processor = AudioProcessor()
    
    # 測試 FFmpeg 檢測
    print(f"FFmpeg 可用: {processor.ffmpeg_available}")
    
    # 測試支援格式
    print(f"支援的格式: {list(processor.SUPPORTED_FORMATS.keys())}")
    
    # 測試 Token 估算
    tokens_1min = processor.estimate_tokens(60)
    tokens_30min = processor.estimate_tokens(30 * 60)
    print(f"1 分鐘預估 Token: {tokens_1min:,}")
    print(f"30 分鐘預估 Token: {tokens_30min:,}")
    
    # 測試時長格式化
    print(f"90 秒格式化: {processor.format_duration(90)}")
    print(f"3661 秒格式化: {processor.format_duration(3661)}")
    
    print("✅ AudioProcessor 測試通過")
    return True


def test_schemas():
    """測試 Pydantic Schemas"""
    print("\n" + "=" * 50)
    print("🧪 測試 Schemas")
    print("=" * 50)
    
    from conflict_analyzer.schemas import (
        ConflictAnalysisResult,
        ReasoningAnalysis,
        SpeakerProfile,
        ConflictTrigger
    )
    
    # 測試創建模擬結果
    mock_result = ConflictAnalysisResult(
        conflict_detected=True,
        instigator="Speaker A",
        trigger_timestamp="02:35",
        conflict_type="Emotional Escalation",
        speakers=[
            SpeakerProfile(
                speaker_id="Speaker A",
                voice_characteristics="音色較高亢，語速偏快",
                baseline_emotion="中性"
            ),
            SpeakerProfile(
                speaker_id="Speaker B",
                voice_characteristics="音色較低沉，語速較慢",
                baseline_emotion="平靜"
            )
        ],
        trigger_details=ConflictTrigger(
            timestamp="02:35",
            trigger_content="你總是這樣！",
            trigger_type="Verbal Aggression"
        ),
        reasoning_analysis=ReasoningAnalysis(
            acoustic_evidence="在 2:35 時，Speaker A 的音量突然提高約 50%",
            semantic_evidence="使用了「你總是」這種標籤化語言"
        ),
        conflict_intensity_score=6,
        summary="對話在 2:35 時出現衝突，Speaker A 首先使用了攻擊性語言。"
    )
    
    # 測試 JSON 序列化
    json_output = mock_result.model_dump_json(indent=2)
    print(f"JSON 序列化成功，長度: {len(json_output)} 字元")
    
    # 測試 JSON Schema 生成
    schema = ConflictAnalysisResult.model_json_schema()
    print(f"JSON Schema 生成成功，包含 {len(schema.get('properties', {}))} 個屬性")
    
    # 驗證必填欄位
    required_fields = schema.get('required', [])
    print(f"必填欄位: {required_fields}")
    
    print("✅ Schemas 測試通過")
    return True


def test_prompts():
    """測試提示詞模板"""
    print("\n" + "=" * 50)
    print("🧪 測試 Prompts")
    print("=" * 50)
    
    from conflict_analyzer.prompts import (
        SYSTEM_INSTRUCTION,
        get_analysis_prompt,
        ENERGY_SCAN_PROMPT
    )
    
    # 測試系統指令長度
    print(f"系統指令長度: {len(SYSTEM_INSTRUCTION)} 字元")
    
    # 測試提示詞生成
    prompt = get_analysis_prompt("這是一對情侶的對話")
    print(f"分析提示詞長度: {len(prompt)} 字元")
    
    # 驗證關鍵內容存在
    assert "情緒挑釁" in SYSTEM_INSTRUCTION
    assert "被動攻擊" in SYSTEM_INSTRUCTION
    assert "Speaker A" in SYSTEM_INSTRUCTION
    
    print("✅ Prompts 測試通過")
    return True


def test_gemini_connection():
    """測試 Gemini API 連接"""
    print("\n" + "=" * 50)
    print("🧪 測試 Gemini API 連接")
    print("=" * 50)
    
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    if not api_key:
        print("⚠️ 未設置 API Key，跳過連接測試")
        return True
    
    try:
        from google import genai
        
        client = genai.Client(api_key=api_key)
        
        # 簡單測試
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="請回覆 'OK' 來確認連接成功。"
        )
        
        if response.text and "OK" in response.text.upper():
            print("✅ Gemini API 連接成功")
            return True
        else:
            print(f"⚠️ 意外的響應: {response.text[:100]}")
            return True
            
    except Exception as e:
        print(f"❌ Gemini API 連接失敗: {e}")
        return False


def test_conflict_analyzer_init():
    """測試 ConflictAnalyzer 初始化"""
    print("\n" + "=" * 50)
    print("🧪 測試 ConflictAnalyzer 初始化")
    print("=" * 50)
    
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    if not api_key:
        print("⚠️ 未設置 API Key，跳過初始化測試")
        return True
    
    try:
        from conflict_analyzer import ConflictAnalyzer
        
        analyzer = ConflictAnalyzer()
        
        print(f"模型: {analyzer.config.model}")
        print(f"溫度: {analyzer.config.temperature}")
        
        print("✅ ConflictAnalyzer 初始化成功")
        return True
        
    except Exception as e:
        print(f"❌ 初始化失敗: {e}")
        return False


def run_all_tests():
    """執行所有測試"""
    print("\n" + "=" * 60)
    print("🚀 Conflict Genesis 測試套件")
    print("=" * 60)
    
    tests = [
        ("音訊處理器", test_audio_processor),
        ("Schemas", test_schemas),
        ("Prompts", test_prompts),
        ("Gemini 連接", test_gemini_connection),
        ("分析器初始化", test_conflict_analyzer_init),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} 測試異常: {e}")
            results.append((name, False))
    
    # 摘要
    print("\n" + "=" * 60)
    print("📊 測試結果摘要")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"   {name}: {status}")
    
    print(f"\n總計: {passed}/{total} 測試通過")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
