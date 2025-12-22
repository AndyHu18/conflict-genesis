#!/usr/bin/env python3
"""
Conflict Genesis - 音訊衝突源頭判定系統
主程式入口與命令行介面

使用方式:
    python main.py <audio_file>
    python main.py <audio_file> --context "這是一對情侶的對話"
    python main.py <audio_file> --verbose
"""

import argparse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

from conflict_analyzer import (
    ConflictAnalyzer,
    ConflictAnalysisResult,
    AudioProcessor
)
from conflict_analyzer.conflict_analyzer import ConflictAnalyzerError, AnalysisConfig


def print_banner():
    """印出程式 Banner"""
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   ⚔️  Conflict Genesis - 音訊衝突源頭判定系統  ⚔️                ║
║                                                                  ║
║   利用 Gemini AI 多模態能力分析對話，判斷衝突發起者             ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def check_environment():
    """檢查運行環境"""
    print("🔍 環境檢查中...")
    
    issues = []
    
    # 檢查 API Key
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        issues.append("❌ 未設置 GEMINI_API_KEY 環境變數")
    else:
        print(f"✅ API Key 已設置 (長度: {len(api_key)})")
    
    # 檢查 FFmpeg
    processor = AudioProcessor()
    if processor.ffmpeg_available:
        print("✅ FFmpeg 已安裝")
    else:
        issues.append("⚠️ FFmpeg 未安裝 (部分功能受限)")
    
    # 檢查 Python 版本
    if sys.version_info >= (3, 10):
        print(f"✅ Python 版本: {sys.version_info.major}.{sys.version_info.minor}")
    else:
        issues.append(f"⚠️ Python 版本 ({sys.version_info.major}.{sys.version_info.minor}) 建議 3.10+")
    
    if issues:
        print("\n⚠️ 發現以下問題:")
        for issue in issues:
            print(f"   {issue}")
        
        # 如果缺少 API Key 則無法繼續
        if any("GEMINI_API_KEY" in i for i in issues):
            print("\n💡 設置 API Key 的方法:")
            print("   1. 創建 .env 檔案，加入: GEMINI_API_KEY=your_api_key")
            print("   2. 或設置環境變數: set GEMINI_API_KEY=your_api_key (Windows)")
            return False
    
    print()
    return True


def analyze_audio(
    audio_path: str,
    additional_context: str = "",
    model: str = "gemini-3-flash-preview",
    verbose: bool = True
) -> ConflictAnalysisResult:
    """
    分析音訊檔案
    
    Args:
        audio_path: 音訊檔案路徑
        additional_context: 額外情境說明
        model: 使用的模型
        verbose: 是否輸出詳細資訊
        
    Returns:
        分析結果
    """
    # 創建配置
    config = AnalysisConfig(model=model)
    
    # 初始化分析器
    analyzer = ConflictAnalyzer(config=config)
    
    # 執行分析
    result = analyzer.analyze_with_retry(
        audio_path=audio_path,
        additional_context=additional_context,
        verbose=verbose,
        max_retries=3
    )
    
    return result


def export_result(result: ConflictAnalysisResult, output_path: str):
    """
    匯出分析結果為 JSON
    
    Args:
        result: 分析結果
        output_path: 輸出路徑
    """
    import json
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)
    
    print(f"📁 結果已匯出: {output_path}")


def main():
    """主程式入口"""
    parser = argparse.ArgumentParser(
        description="Conflict Genesis - 音訊衝突源頭判定系統",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
    python main.py conversation.mp3
    python main.py argument.wav --context "這是一對夫妻關於財務的對話"
    python main.py debate.mp3 --output result.json --model gemini-2.0-flash
        """
    )
    
    parser.add_argument(
        "audio_file",
        type=str,
        nargs="?",
        help="要分析的音訊檔案路徑"
    )
    
    parser.add_argument(
        "-c", "--context",
        type=str,
        default="",
        help="額外的情境說明，有助於更準確的分析"
    )
    
    parser.add_argument(
        "-m", "--model",
        type=str,
        default="gemini-3-flash-preview",
        help="使用的 Gemini 模型 (預設: gemini-3-flash-preview)"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="匯出結果的 JSON 檔案路徑"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=True,
        help="輸出詳細分析過程 (預設: 開啟)"
    )
    
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="靜默模式，僅輸出最終結果"
    )
    
    parser.add_argument(
        "--check",
        action="store_true",
        help="僅檢查環境配置，不執行分析"
    )
    
    parser.add_argument(
        "--info",
        action="store_true",
        help="顯示音訊檔案資訊，不執行分析"
    )
    
    args = parser.parse_args()
    
    # 印出 Banner
    if not args.quiet:
        print_banner()
    
    # 僅檢查環境
    if args.check:
        check_environment()
        return
    
    # 檢查是否提供了音訊檔案
    if not args.audio_file:
        parser.print_help()
        print("\n❌ 錯誤: 請提供要分析的音訊檔案路徑")
        sys.exit(1)
    
    # 驗證檔案存在
    audio_path = Path(args.audio_file)
    if not audio_path.exists():
        print(f"❌ 檔案不存在: {audio_path}")
        sys.exit(1)
    
    # 僅顯示檔案資訊
    if args.info:
        processor = AudioProcessor()
        info = processor.get_audio_info(str(audio_path))
        duration_str = processor.format_duration(info.duration_seconds)
        tokens = processor.estimate_tokens(info.duration_seconds)
        
        print(f"📁 檔案資訊:")
        print(f"   路徑: {info.file_path}")
        print(f"   格式: {info.format}")
        print(f"   時長: {duration_str}")
        print(f"   大小: {info.file_size_bytes / 1024:.1f} KB")
        print(f"   取樣率: {info.sample_rate or 'N/A'} Hz")
        print(f"   聲道數: {info.channels or 'N/A'}")
        print(f"   預估 Token: {tokens:,}")
        return
    
    # 環境檢查
    if not check_environment():
        sys.exit(1)
    
    # 執行分析
    try:
        verbose = not args.quiet
        
        result = analyze_audio(
            audio_path=str(audio_path),
            additional_context=args.context,
            model=args.model,
            verbose=verbose
        )
        
        # 匯出結果
        if args.output:
            export_result(result, args.output)
        
        # 返回退出碼
        sys.exit(0)
        
    except ConflictAnalyzerError as e:
        print(f"\n❌ 分析錯誤: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ 使用者中斷操作")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 未預期錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
