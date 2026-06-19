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
    print("=== PyInstaller build start ===")
    subprocess.run(cmd, check=True, cwd=ROOT)

    # 2. Copy README.md into the output directory
    app_dir = DIST_DIR / APP_NAME
    shutil.copy(ROOT / "README.md", app_dir / "README.md")
    print("Copied README.md")

    # 3. ZIP (dist/LoopbackTranscriber/ -> LoopbackTranscriber_Release.zip)
    zip_path = ROOT / ZIP_NAME
    shutil.make_archive(str(zip_path), "zip", DIST_DIR, APP_NAME)
    print(f"=== Done: {zip_path}.zip ===")


if __name__ == "__main__":
    main()
