"""
Build script: PyInstaller --onedir --noconsole → README 同梱 → ZIP
Usage: python build.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DIST_DIR = ROOT / "dist"
APP_NAME = "LoopbackTranscriber"
ZIP_NAME = "LoopbackTranscriber_Release"


def main():
    # 1. PyInstaller でビルド
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "main.py",
        "--name", APP_NAME,
        "--noconsole",
        "--onedir",
        "--noconfirm",
        "--collect-all", "customtkinter",
        "--collect-all", "faster_whisper",
        "--collect-all", "ctranslate2",
        "--collect-all", "soundcard",
        "--hidden-import", "keyboard",
    ]
    print("=== PyInstaller ビルド開始 ===")
    subprocess.run(cmd, check=True, cwd=ROOT)

    # 2. README.md を出力ディレクトリへコピー
    app_dir = DIST_DIR / APP_NAME
    shutil.copy(ROOT / "README.md", app_dir / "README.md")
    print("README.md をコピーしました")

    # 3. ZIP 圧縮（dist/LoopbackTranscriber/ → LoopbackTranscriber_Release.zip）
    zip_path = ROOT / ZIP_NAME
    shutil.make_archive(str(zip_path), "zip", DIST_DIR, APP_NAME)
    print(f"=== 完了: {zip_path}.zip ===")


if __name__ == "__main__":
    main()
