#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Key 快速測試腳本
測試 Gemini API 連線狀態
"""

import os
import sys
from pathlib import Path

# 添加專案根目錄到路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env')

# API Keys 清單
API_KEYS = {
    "Primary (workflow)": "AIzaSyApMiwmJpbo0vX58K_n4sfCN6bqBDDd4Tk",
    "Backup (env)": "AIzaSyAL0_cJPEpN9hWBNDfFcgfbrkjvbWI01ks",
    "Backup 2": "AIzaSyACKhhmtMMjdOrjP1o7H9ZoFl5vSt_Wxkc",
}

def test_api_key(name: str, api_key: str) -> bool:
    """測試單個 API Key"""
    print(f"\n{'='*60}")
    print(f"[TEST] {name}")
    print(f"   Key: {api_key[:20]}...{api_key[-4:]}")
    print('='*60)
    
    try:
        from google import genai
        
        client = genai.Client(api_key=api_key)
        
        # 簡單測試請求
        print("   Sending test request...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Reply with: Hello, API works!"
        )
        
        if response and response.text:
            print(f"   [OK] Success! Response: {response.text[:80]}...")
            return True
        else:
            print(f"   [FAIL] Empty response")
            return False
            
    except Exception as e:
        print(f"   [FAIL] Error: {type(e).__name__}: {str(e)[:200]}")
        return False

def test_conflict_analyzer():
    """測試 ConflictAnalyzer 初始化"""
    print(f"\n{'='*60}")
    print("[TEST] ConflictAnalyzer Initialization")
    print('='*60)
    
    try:
        from conflict_analyzer import ConflictAnalyzer
        
        analyzer = ConflictAnalyzer()
        print(f"   [OK] ConflictAnalyzer initialized successfully")
        print(f"   Model: {analyzer.config.model}")
        print(f"   API Key source: GEMINI_API_KEY env var")
        return True
        
    except Exception as e:
        print(f"   [FAIL] Init failed: {type(e).__name__}: {str(e)}")
        return False

def main():
    print("\n" + "="*60)
    print("   Conflict Genesis - API Key Diagnostic Test")
    print("="*60)
    
    results = {}
    
    # 1. 測試所有 API Keys
    for name, key in API_KEYS.items():
        results[name] = test_api_key(name, key)
    
    # 2. 測試 ConflictAnalyzer
    results["ConflictAnalyzer"] = test_conflict_analyzer()
    
    # 3. 總結
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    
    all_passed = True
    for name, passed in results.items():
        status = "[OK]  " if passed else "[FAIL]"
        print(f"   {status} - {name}")
        if not passed:
            all_passed = False
    
    print('='*60)
    
    if all_passed:
        print("[SUCCESS] All tests passed! API connection OK.")
        print("   Issue might be Render platform timeout.")
    else:
        print("[WARNING] Some tests failed. Check API Key or network.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
