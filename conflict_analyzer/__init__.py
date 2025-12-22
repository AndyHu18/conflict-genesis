"""
衝突基因 - 極致中立的衝突演化追蹤器
四階段完整分析：
  一階：衝突演化追蹤
  二階：深層溯源與接納橋樑
  三階：個人成長行動方案
  四階：療育音頻生成
"""

from .conflict_analyzer import ConflictAnalyzer, AnalysisConfig, ConflictAnalyzerError
from .audio_processor import AudioProcessor, AudioInfo, AudioSegment
from .schemas import (
    # 一階輸出
    ConflictAnalysisResult,
    Stage1Result,
    EvolutionPhase,
    TurningPoint,
    DualPerspective,
    RepairAnalysis,
    # 二階輸出
    Stage2Result,
    IcebergAnalysis,
    PerspectiveShift,
    DefenseMechanismInsight,
    HealingReframe,
    ActionableChange,
    # 三階輸出
    Stage3Result,
    SelfRepair,
    MyPatterns,
    MyToolkit,
    AlternativePath,
    MyBoundaries,
    MeaningMaking,
    # 完整結果
    FullAnalysisResult,
    # 枚舉
    EnergyPattern,
    # 錯誤
    AnalysisError
)
from .prompts import (
    DEFAULT_STAGE1_PROMPT,
    DEFAULT_STAGE2_PROMPT,
    DEFAULT_STAGE3_PROMPT,
    DEFAULT_STAGE4_PROMPT,
    DEFAULT_SYSTEM_PROMPT,
    SYSTEM_INSTRUCTION
)
from .healing_audio import HealingAudioGenerator, generate_healing_audio_from_analysis
from .image_generator import ImageGenerator

__all__ = [
    # 核心類別
    "ConflictAnalyzer",
    "AnalysisConfig",
    "ConflictAnalyzerError",
    "AudioProcessor",
    "AudioInfo",
    "AudioSegment",
    # 一階輸出
    "ConflictAnalysisResult",
    "Stage1Result",
    "EvolutionPhase",
    "TurningPoint",
    "DualPerspective",
    "RepairAnalysis",
    # 二階輸出
    "Stage2Result",
    "IcebergAnalysis",
    "PerspectiveShift",
    "DefenseMechanismInsight",
    "HealingReframe",
    "ActionableChange",
    # 三階輸出
    "Stage3Result",
    "SelfRepair",
    "MyPatterns",
    "MyToolkit",
    "AlternativePath",
    "MyBoundaries",
    "MeaningMaking",
    # 完整結果
    "FullAnalysisResult",
    # Prompts
    "DEFAULT_STAGE1_PROMPT",
    "DEFAULT_STAGE2_PROMPT",
    "DEFAULT_STAGE3_PROMPT",
    "DEFAULT_STAGE4_PROMPT",
    "DEFAULT_SYSTEM_PROMPT",
    # 療育音頻
    "HealingAudioGenerator",
    "generate_healing_audio_from_analysis",
    "ImageGenerator",
    # 錯誤
    "AnalysisError"
]

__version__ = "4.0.0"
