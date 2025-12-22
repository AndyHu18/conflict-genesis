#!/usr/bin/env python3
"""
Conflict Genesis - 使用示範
展示如何透過 Python 程式碼使用分析器
"""

import os
import sys
from pathlib import Path

# 載入環境變數
from dotenv import load_dotenv
load_dotenv()

from conflict_analyzer import (
    ConflictAnalyzer,
    ConflictAnalysisResult,
    AudioProcessor
)


def demo_with_audio_file(audio_path: str):
    """
    完整示範：分析實際音訊檔案
    
    Args:
        audio_path: 音訊檔案路徑
    """
    print("=" * 60)
    print("🎬 Conflict Genesis 使用示範")
    print("=" * 60)
    
    # Step 1: 初始化分析器
    print("\n📍 Step 1: 初始化分析器...")
    analyzer = ConflictAnalyzer()
    
    # Step 2: 查看音訊資訊
    print("\n📍 Step 2: 查看音訊資訊...")
    audio_info = analyzer.get_audio_info(audio_path)
    duration_str = analyzer.audio_processor.format_duration(audio_info.duration_seconds)
    print(f"   檔案: {Path(audio_path).name}")
    print(f"   格式: {audio_info.format}")
    print(f"   時長: {duration_str}")
    print(f"   預估 Token: {analyzer.audio_processor.estimate_tokens(audio_info.duration_seconds):,}")
    
    # Step 3: 執行分析
    print("\n📍 Step 3: 執行衝突分析...")
    result = analyzer.analyze(
        audio_path=audio_path,
        additional_context="請特別注意是否存在被動攻擊行為",
        verbose=True  # 輸出詳細結果
    )
    
    # Step 4: 程式化處理結果
    print("\n📍 Step 4: 程式化處理結果...")
    
    if result.conflict_detected:
        print(f"   ⚠️ 發現衝突！發起者是: {result.instigator}")
        print(f"   衝突類型: {result.conflict_type}")
        print(f"   烈度評分: {result.conflict_intensity_score}/10")
        
        # 可以根據烈度決定後續動作
        if result.conflict_intensity_score >= 7:
            print("   💥 這是一場激烈的衝突，建議進行調解介入")
        elif result.conflict_intensity_score >= 4:
            print("   ⚡ 這是一場中度衝突，建議雙方冷靜")
        else:
            print("   💬 這是一場輕微分歧，通常可自行解決")
    else:
        print("   ✅ 未偵測到衝突，對話整體和諧")
    
    return result


def demo_schema():
    """
    示範：查看輸出 Schema
    """
    print("=" * 60)
    print("📊 輸出 Schema 示範")
    print("=" * 60)
    
    from conflict_analyzer.schemas import ConflictAnalysisResult
    import json
    
    schema = ConflictAnalysisResult.model_json_schema()
    print(json.dumps(schema, indent=2, ensure_ascii=False)[:1500] + "...")


def demo_quick_analysis():
    """
    示範：快速分析一句話
    （用於沒有音訊檔案時的測試）
    """
    print("=" * 60)
    print("💬 快速文字分析示範（無音訊）")
    print("=" * 60)
    
    from google import genai
    from conflict_analyzer.prompts import SYSTEM_INSTRUCTION
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ 未設置 API Key")
        return
    
    client = genai.Client(api_key=api_key)
    
    # 模擬對話逐字稿
    transcript = """
    Speaker A: 我們需要討論一下這個月的開支。
    Speaker B: 又是錢的事？你每次都在念這個。
    Speaker A: 我只是想說我們應該注意一下...
    Speaker B: (打斷) 好了好了，你每次都這樣，真煩人。
    Speaker A: (提高音量) 我煩人？是你根本不願意溝通！
    Speaker B: 隨便你怎麼想。(冷漠地)
    """
    
    prompt = f"""
    請分析以下對話逐字稿，判斷誰是衝突的發起者。
    
    對話內容：
    {transcript}
    
    請依照你的專業分析，判斷：
    1. 是否存在衝突？
    2. 誰是衝突發起者？
    3. 衝突類型是什麼？
    4. 導火線是哪句話？
    """
    
    print("\n📍 正在分析模擬對話...")
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "system_instruction": SYSTEM_INSTRUCTION,
            "temperature": 0.7
        }
    )
    
    print("\n📝 分析結果:")
    print(response.text)


if __name__ == "__main__":
    # 檢查是否提供了音訊檔案
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        if Path(audio_file).exists():
            demo_with_audio_file(audio_file)
        else:
            print(f"❌ 找不到檔案: {audio_file}")
    else:
        # 沒有音訊檔案時，執行其他示範
        print("💡 提示: 可提供音訊檔案路徑進行完整示範")
        print("   例如: python demo.py conversation.mp3")
        print()
        
        # 執行 Schema 示範
        demo_schema()
        print()
        
        # 執行快速文字分析示範
        demo_quick_analysis()
