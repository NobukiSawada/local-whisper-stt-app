"""
Step 1: Windows loopback audio capture test script.
Records 5 seconds of PC speaker output and saves to test_output.wav.
"""

import soundcard as sc
import soundfile as sf
import numpy as np

SAMPLE_RATE = 16000  # 16kHz — matches Whisper's expected input
DURATION = 5         # seconds
OUTPUT_FILE = "test_output.wav"


def find_loopback_device():
    """Return the first available loopback (speaker output) device."""
    all_mics = sc.all_microphones(include_loopback=True)
    loopback_devices = [m for m in all_mics if m.isloopback]

    if not loopback_devices:
        raise RuntimeError(
            "ループバックデバイスが見つかりません。\n"
            "Windowsサウンド設定で「ステレオミキサー」が有効になっているか確認してください。"
        )

    # Prefer the default speaker's loopback
    default_speaker_name = sc.default_speaker().name
    for device in loopback_devices:
        if default_speaker_name in device.name:
            return device

    return loopback_devices[0]


def record_loopback(duration=DURATION, sample_rate=SAMPLE_RATE, output_file=OUTPUT_FILE):
    device = find_loopback_device()
    print(f"録音デバイス: {device.name}")
    print(f"録音開始 ({duration}秒間)...")

    with device.recorder(samplerate=sample_rate) as recorder:
        frames = recorder.record(numframes=int(duration * sample_rate))

    # Stereo → Mono (Whisper は mono を想定)
    if frames.ndim > 1 and frames.shape[1] > 1:
        frames = frames.mean(axis=1)

    sf.write(output_file, frames, sample_rate)
    print(f"保存完了: {output_file}  (サンプルレート: {sample_rate} Hz, {duration}秒)")


if __name__ == "__main__":
    record_loopback()
