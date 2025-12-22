"""
Lumina 心語 - BGM 資源管理器
自動下載免費的背景音樂素材

支援來源：
1. 內置預設 BGM URLs（使用 Pixabay Music 的公開連結）
2. 本地文件夾
"""

import os
import requests
from pathlib import Path
from typing import Optional, List, Dict
from io import BytesIO

# 預設的免費療癒 BGM 資源
# 這些是 Pixabay Music 的公開免費音樂（需要手動驗證連結）
# 建議用戶自行下載並放入 assets/bgm/

DEFAULT_BGM_SOURCES = {
    "healing_ambient": {
        "name": "Healing Ambient",
        "description": "溫柔的環境音，適合療癒情境",
        "filename": "healing_ambient.mp3",
        "duration_sec": 180,
        "mood": ["calm", "healing", "default"]
    },
    "gentle_piano": {
        "name": "Gentle Piano",
        "description": "輕柔的鋼琴曲，適合情緒疏導",
        "filename": "gentle_piano.mp3",
        "duration_sec": 240,
        "mood": ["sad", "ambient", "vulnerability"]
    },
    "meditation_432hz": {
        "name": "Meditation 432Hz",
        "description": "432Hz 療癒頻率，深度放鬆",
        "filename": "meditation_432hz.mp3",
        "duration_sec": 300,
        "mood": ["soothing", "fear", "anxiety"]
    }
}


class BGMResourceManager:
    """
    BGM 資源管理器
    
    負責下載、管理和選擇背景音樂
    """
    
    def __init__(self, bgm_folder: Optional[Path] = None):
        """
        初始化 BGM 資源管理器
        
        Args:
            bgm_folder: BGM 存放文件夾
        """
        if bgm_folder:
            self.bgm_folder = Path(bgm_folder)
        else:
            self.bgm_folder = Path(__file__).parent.parent / "assets" / "bgm"
        
        # 確保文件夾存在
        self.bgm_folder.mkdir(parents=True, exist_ok=True)
    
    def get_status(self) -> Dict:
        """
        獲取 BGM 資源狀態
        
        Returns:
            包含可用 BGM 數量和詳情的字典
        """
        available = self._scan_local_bgm()
        
        return {
            "folder": str(self.bgm_folder),
            "available_count": len(available),
            "available_files": [f.name for f in available],
            "has_bgm": len(available) > 0
        }
    
    def _scan_local_bgm(self) -> List[Path]:
        """
        掃描本地 BGM 文件
        
        Returns:
            BGM 文件路徑列表
        """
        supported_formats = [".mp3", ".wav", ".ogg", ".m4a", ".flac"]
        bgm_files = []
        
        if self.bgm_folder.exists():
            for f in self.bgm_folder.iterdir():
                if f.suffix.lower() in supported_formats:
                    bgm_files.append(f)
        
        return bgm_files
    
    def create_placeholder_bgm(self) -> bool:
        """
        創建一個佔位符說明文件
        
        Returns:
            是否成功創建
        """
        readme_path = self.bgm_folder / "README.txt"
        
        if not readme_path.exists():
            content = """# 背景音樂文件夾 (BGM Folder)

請將療癒風格的 MP3 文件放入此文件夾。

## 推薦免費音樂來源：

1. **Pixabay Music** (推薦)
   - 網址：https://pixabay.com/music/
   - 搜索：ambient, meditation, healing, calm
   - 完全免費，可商業使用

2. **Free Music Archive**
   - 網址：https://freemusicarchive.org/
   - 搜索：ambient, electronic, meditation

3. **Uppbeat** (需註冊)
   - 網址：https://uppbeat.io/
   - 搜索：meditation, relaxation

## 文件命名建議：

- healing_ambient.mp3    → 通用療癒
- calm_piano.mp3         → 平靜鋼琴
- soothing_nature.mp3    → 舒緩自然音
- meditation_432hz.mp3   → 432Hz 冥想

## 系統會自動：

1. 根據情緒選擇合適的 BGM
2. 將 BGM 音量降低 20dB
3. 自動裁切/循環以匹配語音長度
4. 添加淡入淡出效果

---
Lumina 心語 v4.1.0
"""
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            print(f"📄 已創建 BGM 說明文件: {readme_path}")
            return True
        
        return False
    
    def download_sample_bgm(self) -> bool:
        """
        下載免費的示範 BGM
        
        使用公開可用的免費音樂 URL 下載療癒風格的背景音樂
        支援多個備用來源，確保至少一個可用
        
        Returns:
            是否成功下載至少一個文件
        """
        # 公開可用的免費音樂 URL（多個備用來源）
        # 使用 Bensound, Internet Archive 等公開域音樂
        sample_urls = [
            # === 療癒環境音 ===
            {
                "name": "healing_ambient.mp3",
                "urls": [
                    "https://www.bensound.com/bensound-music/bensound-slowmotion.mp3",
                    "https://ia800500.us.archive.org/4/items/MeditationMusic_936/01_Peaceful_Forest.mp3",
                ],
                "mood": ["calm", "healing", "default"]
            },
            # === 平靜鋼琴 ===
            {
                "name": "calm_piano.mp3",
                "urls": [
                    "https://www.bensound.com/bensound-music/bensound-thejazzpiano.mp3",
                    "https://ia800500.us.archive.org/4/items/MeditationMusic_936/02_Sunset_Dreams.mp3",
                ],
                "mood": ["sad", "ambient", "vulnerability"]
            },
            # === 432Hz 冥想 ===
            {
                "name": "meditation_432hz.mp3",
                "urls": [
                    "https://www.bensound.com/bensound-music/bensound-dreams.mp3",
                    "https://ia800500.us.archive.org/4/items/MeditationMusic_936/03_Deep_Relaxation.mp3",
                ],
                "mood": ["soothing", "fear", "anxiety"]
            },
            # === 新增：柔和晨光 ===
            {
                "name": "gentle_morning.mp3",
                "urls": [
                    "https://www.bensound.com/bensound-music/bensound-sunny.mp3",
                    "https://www.bensound.com/bensound-music/bensound-clearday.mp3",
                ],
                "mood": ["hopeful", "growth", "new_beginning"]
            },
            # === 新增：深度放鬆 ===
            {
                "name": "deep_relaxation.mp3",
                "urls": [
                    "https://www.bensound.com/bensound-music/bensound-relaxing.mp3",
                    "https://www.bensound.com/bensound-music/bensound-betterdays.mp3",
                ],
                "mood": ["relaxation", "peace", "comfort"]
            },
            # === 新增：溫柔擁抱 ===
            {
                "name": "tender_embrace.mp3",
                "urls": [
                    "https://www.bensound.com/bensound-music/bensound-love.mp3",
                    "https://www.bensound.com/bensound-music/bensound-memories.mp3",
                ],
                "mood": ["love", "compassion", "connection"]
            },
            # === 新增：內心平靜 ===
            {
                "name": "inner_peace.mp3",
                "urls": [
                    "https://www.bensound.com/bensound-music/bensound-tomorrow.mp3",
                    "https://www.bensound.com/bensound-music/bensound-dreams.mp3",
                ],
                "mood": ["meditation", "mindfulness", "stillness"]
            },
            # === 新增：自然療癒 ===
            {
                "name": "nature_healing.mp3",
                "urls": [
                    "https://www.bensound.com/bensound-music/bensound-acoustic-breeze.mp3",
                    "https://www.bensound.com/bensound-music/bensound-sweet.mp3",
                ],
                "mood": ["nature", "organic", "grounding"]
            },
            # === 新增：夢境漫步 ===
            {
                "name": "dreamwalk.mp3",
                "urls": [
                    "https://www.bensound.com/bensound-music/bensound-once-again.mp3",
                    "https://www.bensound.com/bensound-music/bensound-november.mp3",
                ],
                "mood": ["dreamy", "ethereal", "contemplation"]
            },
            # === 新增：重生希望 ===
            {
                "name": "rebirth_hope.mp3",
                "urls": [
                    "https://www.bensound.com/bensound-music/bensound-newdawn.mp3",
                    "https://www.bensound.com/bensound-music/bensound-epic.mp3",
                ],
                "mood": ["empowerment", "strength", "transformation"]
            },
            # === 新增：溫馨家園 ===
            {
                "name": "cozy_home.mp3",
                "urls": [
                    "https://www.bensound.com/bensound-music/bensound-littleidea.mp3",
                    "https://www.bensound.com/bensound-music/bensound-ukulele.mp3",
                ],
                "mood": ["warmth", "safety", "belonging"]
            },
        ]
        
        print("\n" + "=" * 50)
        print("🎵 開始下載免費 BGM 素材...")
        print("=" * 50)
        
        downloaded = 0
        
        for item in sample_urls:
            file_path = self.bgm_folder / item["name"]
            
            if file_path.exists():
                print(f"   ⏩ 跳過（已存在）: {item['name']}")
                downloaded += 1
                continue
            
            # 嘗試多個 URL
            success = False
            for url in item["urls"]:
                try:
                    print(f"   ⏬ 嘗試下載: {item['name']}...")
                    print(f"      來源: {url[:50]}...")
                    
                    resp = requests.get(
                        url,
                        timeout=120,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        },
                        stream=True
                    )
                    
                    if resp.status_code == 200:
                        # 流式下載以支援大文件
                        total_size = 0
                        with open(file_path, "wb") as f:
                            for chunk in resp.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                                    total_size += len(chunk)
                        
                        if total_size > 10000:  # 至少 10KB
                            print(f"   ✅ 下載成功: {item['name']} ({total_size//1024} KB)")
                            downloaded += 1
                            success = True
                            break
                        else:
                            print(f"   ⚠️ 文件太小，嘗試下一個來源...")
                            file_path.unlink(missing_ok=True)
                    else:
                        print(f"   ⚠️ HTTP {resp.status_code}，嘗試下一個來源...")
                        
                except requests.exceptions.Timeout:
                    print(f"   ⚠️ 下載超時，嘗試下一個來源...")
                except Exception as e:
                    print(f"   ⚠️ 下載錯誤: {e}")
            
            if not success:
                print(f"   ❌ 無法下載: {item['name']}（所有來源都失敗）")
        
        # 如果沒有成功下載任何文件，生成靜音備用
        if downloaded == 0:
            print("\n📍 無法從網路下載，嘗試生成本地備用音軌...")
            generated = self._generate_ambient_bgm()
            if generated:
                downloaded = 1
        
        print("=" * 50)
        print(f"✅ BGM 準備完成！可用數量: {downloaded}")
        print("=" * 50 + "\n")
        
        self.create_placeholder_bgm()
        return downloaded > 0
    
    def _generate_ambient_bgm(self) -> Optional[Path]:
        """
        使用 pydub 生成簡單的環境音樂
        
        這是一個備用方案：當無法下載外部音樂時，
        使用程式生成輕柔的白噪音/環境音。
        
        Returns:
            生成的文件路徑
        """
        try:
            from pydub import AudioSegment
            from pydub.generators import WhiteNoise
            import random
            
            print("📍 生成程序化環境音樂...")
            
            # 生成 5 分鐘的極輕白噪音（模擬空氣感）
            duration_ms = 5 * 60 * 1000  # 5 分鐘
            
            # 白噪音基底（非常低音量）
            noise = WhiteNoise().to_audio_segment(duration=duration_ms)
            noise = noise - 35  # 降低 35dB，形成極輕的「空氣感」
            
            # 添加淡入淡出
            noise = noise.fade_in(5000).fade_out(5000)
            
            output_path = self.bgm_folder / "ambient_generated.mp3"
            noise.export(str(output_path), format="mp3")
            
            print(f"   ✅ 環境音生成完成: {output_path}")
            return output_path
            
        except ImportError:
            print("   ⚠️ pydub 未安裝，無法生成環境音")
            return None
        except Exception as e:
            print(f"   ❌ 生成失敗: {e}")
            return None


def ensure_bgm_available() -> Dict:
    """
    便捷函數：確保 BGM 資源可用
    
    Returns:
        BGM 狀態字典
    """
    manager = BGMResourceManager()
    status = manager.get_status()
    
    if not status["has_bgm"]:
        manager.create_placeholder_bgm()
        print("⚠️ 未找到 BGM 文件，請手動添加 MP3 到 assets/bgm/")
    
    return status


# 模組載入時自動檢查
if __name__ == "__main__":
    status = ensure_bgm_available()
    print(f"BGM 狀態: {status}")
