#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple API Key Test - Outputs to file
"""
import os
import sys
from pathlib import Path

# Setup
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
output_file = project_root / 'tests' / 'test_result.log'

from dotenv import load_dotenv
load_dotenv(project_root / '.env')

# API Keys
API_KEYS = [
    ("Primary", "AIzaSyApMiwmJpbo0vX58K_n4sfCN6bqBDDd4Tk"),
    ("Backup", "AIzaSyAL0_cJPEpN9hWBNDfFcgfbrkjvbWI01ks"),
    ("Backup2", "AIzaSyACKhhmtMMjdOrjP1o7H9ZoFl5vSt_Wxkc"),
]

def write_log(msg):
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')
    print(msg)

def main():
    # Clear log
    if output_file.exists():
        output_file.unlink()
    
    write_log("=" * 60)
    write_log("Conflict Genesis - API Key Diagnostic")
    write_log("=" * 60)
    
    results = []
    
    for name, key in API_KEYS:
        write_log(f"\n[TEST] {name}: {key[:15]}...{key[-4:]}")
        try:
            from google import genai
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents="Say: OK"
            )
            if response and response.text:
                write_log(f"  [OK] Response: {response.text.strip()[:50]}")
                results.append((name, True, None))
            else:
                write_log(f"  [FAIL] Empty response")
                results.append((name, False, "Empty"))
        except Exception as e:
            write_log(f"  [FAIL] {type(e).__name__}: {str(e)[:150]}")
            results.append((name, False, str(e)[:150]))
    
    # Test ConflictAnalyzer
    write_log(f"\n[TEST] ConflictAnalyzer init")
    try:
        from conflict_analyzer import ConflictAnalyzer
        analyzer = ConflictAnalyzer()
        write_log(f"  [OK] Model: {analyzer.config.model}")
        results.append(("ConflictAnalyzer", True, None))
    except Exception as e:
        write_log(f"  [FAIL] {type(e).__name__}: {str(e)[:150]}")
        results.append(("ConflictAnalyzer", False, str(e)[:150]))
    
    # Summary
    write_log("\n" + "=" * 60)
    write_log("SUMMARY")
    write_log("=" * 60)
    
    all_ok = True
    for name, ok, err in results:
        status = "OK" if ok else "FAIL"
        write_log(f"  [{status}] {name}")
        if not ok:
            all_ok = False
    
    write_log("=" * 60)
    write_log(f"Result: {'ALL PASSED' if all_ok else 'SOME FAILED'}")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
